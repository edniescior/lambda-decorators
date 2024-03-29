import json
import logging
import os
import sys
import traceback
from functools import wraps
from json.decoder import JSONDecodeError

import boto3

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", logging.INFO))


def with_logging(handler):
    """
    Decorator which performs basic logging.

    Usage::

        >>> from lambda_decorators import with_logging
        >>>
        >>> @with_logging
        ... def my_handler(event, context):
        ...     return {"message": "Hello World"}
        >>>
        >>> my_handler({}, {})
        INFO:root:Calling my_handler
        DEBUG:root:Environment variables: {"LOG_LEVEL": "DEBUG"}
        INFO:root:Event: {}
        {'message': 'Hello World'}

    """

    @wraps(handler)
    def wrapper(event, *args, **kwargs):
        logger.info(f"Calling {handler.__name__}")
        logger.debug(f"Environment variables: {json.dumps(os.environ.copy())}")
        try:
            logger.info(f"Event: {json.dumps(event, indent=2)}")
        except JSONDecodeError:
            logger.warn(f"JSONDecodeError: Event: {event}")
        return handler(event, *args, **kwargs)

    return wrapper


def load_json_body(handler):
    """
    Decorator which loads the JSON body of a request.

    Usage::

        >>> from lambda_decorators import load_json_body
        >>>
        >>> @load_json_body
        ... def my_handler(event, context):
        ...     return {"message": event["body"]["message"]}
        >>>
        >>> my_handler({"body": {"message": "Hello World"}}, {})
        {'message': 'Hello World'}
        >>> my_handler({"body": "Hello World"}, {})
        Traceback (most recent call last):
            ...
        ValueError: No JSON object could be decoded
    """

    @wraps(handler)
    def wrapper(event, *args, **kwargs):
        if isinstance(event.get("body"), str):
            event["body"] = json.loads(event["body"])

        return handler(event, *args, **kwargs)

    return wrapper


def catch_errors(handler):
    """
    Decorator which performs catch all exception handling. It logs the error
    with a stack trace and passes on the exception to the caller.

    Usage::

        >>> from lambda_decorators import catch_errors
        >>>
        >>> @catch_errors
        ... def my_handler(event, context):
        ...     raise ValueError("boo")
        >>>
        >>> my_handler({}, {})
        ERROR    root:decorators.py:119 {"errorType": "ValueError", "errorMessage": "boo", "stackTrace":...

    """

    @wraps(handler)
    def wrapper(event, context):
        def error_msg():
            exception_type, exception_value, exception_traceback = sys.exc_info()
            traceback_string = traceback.format_exception(
                exception_type, exception_value, exception_traceback
            )
            return json.dumps(
                {
                    "errorType": exception_type.__name__,
                    "errorMessage": str(exception_value),
                    "stackTrace": traceback_string,
                }
            )

        try:
            return handler(event, context)

        # We could catch the following specifice errors:
        # ClientError, ValueError, JSONDecodeError
        # But I'm just logging them and passing it on
        # so that the function is marked as a failure. Hence,
        # just the catch-all Exception.
        except Exception as e:
            logger.error(error_msg())
            raise e

    return wrapper


def with_ssm_parameters(*parameters):
    """
    Decorator that fetches secrets from the SSM parameter store. Secrets are added
    as environment variables.

    Usage::

        >>> from lambda_decorators import with_ssm_parameters
        >>>
        >>> @with_ssm_parameters("/test/foo")
        ... def my_handler(event, context):
        ...     return {"/test/foo", os.getenv("/test/foo")}
        >>> my_handler({}, {})
        {'/test/foo': 'bar'}
    """

    def wrapper_wrapper(handler):
        @wraps(handler)
        def wrapper(event, context):
            # make sure parameters contains valid strings
            params = [p for p in parameters if isinstance(p, str)]

            if params:
                ssm = boto3.client("ssm")
                for parameter in ssm.get_parameters(Names=params, WithDecryption=True)[
                    "Parameters"
                ]:
                    os.environ[parameter["Name"]] = parameter["Value"]

            return handler(event, context)

        return wrapper

    return wrapper_wrapper


def cors_headers(origin=None, credentials=False):
    """
    Automatically injects ``Access-Control-Allow-Origin`` headers to http
    responses. Also optionally adds ``Access-Control-Allow-Credentials: True`` if
    called with ``credentials=True``

    Usage::

        >>> from lambda_decorators import cors_headers
        >>> @cors_headers()
        ... def my_handler(event, context):
        ...     return {'body': 'foobar'}
        >>> my_handler({}, object())
        {'body': 'foobar', 'headers': {'Access-Control-Allow-Origin': '*'}}
        >>> # or with custom domain
        >>> @cors_headers(origin='https://example.com', credentials=True)
        ... def my_handler_custom_origin(example, context):
        ...     return {'body': 'foobar'}
        >>> my_handler_custom_origin({}, object())
        {'body': 'foobar', 'headers': {'Access-Control-Allow-Origin': 'https://example.com',
                                       'Access-Control-Allow-Credentials': true}}
    """

    def wrapper_wrapper(handler):
        @wraps(handler)
        def wrapper(event, context):
            response = handler(event, context)
            if response is None:
                response = {}
            headers = response.setdefault("headers", {})
            if origin is not None:
                headers["Access-Control-Allow-Origin"] = origin
            else:
                headers["Access-Control-Allow-Origin"] = "*"
            if credentials:
                response["headers"]["Access-Control-Allow-Credentials"] = "true"
            return response

        return wrapper

    return wrapper_wrapper


__all__ = [
    "with_logging",
    "load_json_body",
    "catch_errors",
    "with_ssm_parameters",
    "cors_headers",
]
