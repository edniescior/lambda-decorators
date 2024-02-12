# Lambda Decorators

## Description
This module provides decorators that perform common functions for AWS Lambda handlers. Using these 
decorators removes a lot of boilerplate from handler functions. Much of the inspiration comes from 
this [collection](https://github.com/dschep/lambda-decorators/blob/master/README.rst) of decorators.

## Decorators
- `with_logging`: Performs basic logging.
- `load_json_body`: Loads the JSON body of a request.
- `catch_errors`: Performs catch-all exception handling.
- `with_ssm_parameters`: Fetches secrets from the SSM parameter store.
- `cors_headers`: Automatically injects CORS headers into HTTP responses.

### Example Usage
```
Usage::

with_logging:

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


load_json_body:

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


catch_errors:

    >>> from lambda_decorators import catch_errors
    >>>
    >>> @catch_errors
    ... def my_handler(event, context):
    ...     raise ValueError("boo")
    >>>
    >>> my_handler({}, {})
    ERROR    root:decorators.py:119 {"errorType": "ValueError", "errorMessage": "boo", "stackTrace":...}


with_ssm_parameters:

    >>> from lambda_decorators import with_ssm_parameters
    >>>
    >>> @with_ssm_parameters("/test/foo")
    ... def my_handler(event, context):
    ...     return {"/test/foo", os.getenv("/test/foo")}
    >>> my_handler({}, {})
    {'/test/foo': 'bar'}


cors_headers:

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
    {'body': 'foobar', 
     'headers': {
        'Access-Control-Allow-Origin': 'https://example.com',
        'Access-Control-Allow-Credentials': true
        }
    }
```


## Getting Started
This project uses [Poetry](https://python-poetry.org/docs/#installation) for dependency management. 

To install `pipx` on macOS:
```
brew install pipx
pipx ensurepath
```
Then use `pipx`: 
```
pipx install poetry
```

Clone this repository, then create a Python [Virtual Environment](https://docs.python.org/3/tutorial/venv.html) inside the directory and activate it by running:
```
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies with:
```
make install-dependencies
```

## Development
Upgrade or add any dependencies with:
```
make upgrade-dependencies
```

Code linting is done with `flake8` and `isort`. Run linting with:
```
make lint
``` 

Run the unit tests with:
```
make test
```

## Build
The module is packaged for deployment in a zip file named `artifact.zip`. Create this with:
```
make build
```
The artifact file will created in the home directory.

## Deployment

```
curl -O https://raw.githubusercontent.com/niescies/lambda-decorators/master/lambda_decorators/decorators.py
```


## Environment Variables
The module references one environment variable:
- LOG_LEVEL: For logging (Optional: Defaults to INFO)

## Configuration


## License
This project is released under the MIT License. See
the bundled [LICENSE](LICENSE.md) file for details.
