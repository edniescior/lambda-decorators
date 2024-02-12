import json
import logging
import os
from json import JSONDecodeError

import boto3
import moto
import pytest
from botocore.exceptions import ClientError
from decorators import (
    catch_errors,
    cors_headers,
    load_json_body,
    with_logging,
    with_ssm_parameters,
)


# ===============================================================
# Fixtures
# ===============================================================
@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"  # noqa
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"  # noqa
    os.environ["AWS_SECURITY_TOKEN"] = "testing"  # noqa
    os.environ["AWS_SESSION_TOKEN"] = "testing"  # noqa
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def ssm_client(aws_credentials):
    with moto.mock_ssm():
        yield boto3.client("ssm", region_name="us-east-1")


# ===============================================================
# Tests
# ===============================================================


# test with_logging decorator
def test_with_logging(caplog):
    caplog.set_level(logging.DEBUG)

    @with_logging
    def handler(event, context):
        return 42

    assert handler({"boo": "ya"}, {}) == 42
    assert len(caplog.records) == 3

    assert caplog.records[0].message == "Calling handler"
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].module == "decorators"

    assert "Environment variables" in caplog.records[1].message
    assert caplog.records[1].levelno == logging.DEBUG
    assert caplog.records[1].module == "decorators"

    assert caplog.records[2].message == 'Event: {\n  "boo": "ya"\n}'
    assert caplog.records[2].levelno == logging.INFO
    assert caplog.records[2].module == "decorators"


# test load_json_body
def test_load_json_body():

    @load_json_body
    def handler(event, context):
        return {"message": event["body"]["message"]}

    assert handler({"body": {"message": "Hello World"}}, {}) == {
        "message": "Hello World"
    }


# test load_json_body error
def test_load_json_body_error():

    @load_json_body
    def handler(event, context):
        return {"message": event["body"]["message"]}

    with pytest.raises(JSONDecodeError):
        handler({"body": "Hello World"}, {})


# test catch_errors with ValueError
def test_catch_errors_value(caplog):
    @catch_errors
    def handler(event, context):
        raise ValueError("boo")

    with pytest.raises(ValueError, match=r"boo"):
        handler({"body": "Hello World"}, {})

    assert (
        '''"errorType": "ValueError", "errorMessage": "boo"'''
        in caplog.records[0].message
    )
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].module == "decorators"


# test catch_errors with Boto ClientError
def test_catch_errors_client(caplog):
    @catch_errors
    def handler(event, context):
        # This function simulates a boto3 operation that raises ClientError
        raise ClientError(
            {"Error": {"Code": "MyErrorCode", "Message": "My error message"}},
            "operation_name",
        )

    with pytest.raises(
        ClientError,
        match=r"An error occurred \(MyErrorCode\) when calling the operation_name operation: My error message",
    ):
        handler({"body": "Hello World"}, {})

    assert (
        '''"errorType": "ClientError", "errorMessage": "An error occurred (MyErrorCode) when calling the \
operation_name operation: My error message"'''
        in caplog.records[0].message
    )
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].module == "decorators"


# test catch_errors with JSONDecoder exception
def test_catch_errors_jsondecoder(caplog):
    @catch_errors
    def handler(event, context):
        json.loads(event)

    with pytest.raises(JSONDecodeError, match=r"Expecting value:"):
        handler("Hello World", {})

    assert (
        """"errorType": "JSONDecodeError", "errorMessage": "Expecting value:"""
        in caplog.records[0].message
    )
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].module == "decorators"


# test with_ssm_parameters with single parameter
def test_with_ssm_parameters_single(ssm_client):

    ssm_client.put_parameter(
        Name="/test/foo",
        Description="A test parameter",
        Value="Bar",
        Type="SecureString",
    )

    @with_ssm_parameters("/test/foo")
    def my_handler(event, context):
        return {"/test/foo", os.getenv("/test/foo")}

    assert my_handler({}, {}) == {"/test/foo", "Bar"}


# test with_ssm_parameters with multiple parameters
def test_with_ssm_parameters_multi(ssm_client):

    ssm_client.put_parameter(
        Name="/test/foo",
        Description="A test parameter",
        Value="Bar",
        Type="SecureString",
    )

    ssm_client.put_parameter(
        Name="/test/man",
        Description="A second test parameter",
        Value="Chu",
        Type="SecureString",
    )

    @with_ssm_parameters("/test/foo", "/test/man")
    def my_handler(event, context):
        return (os.getenv("/test/foo"), os.getenv("/test/man"))

    assert my_handler({}, {}) == ("Bar", "Chu")


# test with_ssm_parameters with missing parameter
def test_with_ssm_parameters_none(ssm_client):

    @with_ssm_parameters("/test/boo")
    def my_handler(event, context):
        os.getenv("/test/boo")

    assert my_handler({}, {}) is None


# test with_ssm_parameters with no parameters passed in
def test_with_ssm_parameters_empty(ssm_client):

    @with_ssm_parameters()
    def my_handler(event, context):
        os.getenv("/test/boo")

    assert my_handler({}, {}) is None


# test cors_headers with no origin
def test_cors_headers_no_origin():

    @cors_headers()
    def my_handler(event, context):
        return {"body": "foobar"}

    assert my_handler({}, object()) == {
        "body": "foobar",
        "headers": {"Access-Control-Allow-Origin": "*"},
    }


# test cors_headers with an origin
def test_cors_headers_with_origin():

    @cors_headers(origin="https://example.com")
    def my_handler(event, context):
        return {"body": "foobar"}

    assert my_handler({}, object()) == {
        "body": "foobar",
        "headers": {"Access-Control-Allow-Origin": "https://example.com"},
    }


# test cors_headers with credentials
def test_cors_headers_with_credentials():

    @cors_headers(origin="https://example.com", credentials=True)
    def my_handler(event, context):
        return {"body": "foobar"}

    assert my_handler({}, object()) == {
        "body": "foobar",
        "headers": {
            "Access-Control-Allow-Origin": "https://example.com",
            "Access-Control-Allow-Credentials": "true",
        },
    }
