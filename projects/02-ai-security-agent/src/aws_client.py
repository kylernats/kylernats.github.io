"""Centralised boto3 client factory, pinned to the local Floci emulator.

Every AWS call in this project goes through here. That is deliberate: it gives
one place to enforce the rule that matters most in a tool that can delete IAM
policies and rewrite bucket policies — it must never be able to reach real AWS.

Safety model
------------
1. The endpoint defaults to the local emulator and is read from the environment.
2. `_assert_local()` refuses to build a client for anything that is not a
   loopback address, unless ALLOW_NON_LOCAL_ENDPOINT=1 is set explicitly.
3. Credentials are hardcoded dummies. Even if the guard were bypassed, these
   will not authenticate against real AWS.
4. Retries are capped low so a wrong endpoint fails fast instead of hanging.
"""

from __future__ import annotations

import logging
import os
import threading
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import boto3
from botocore.client import BaseClient
from botocore.config import Config

log = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://localhost:4566"
DEFAULT_REGION = "us-east-1"

# Dummy credentials. Floci accepts anything; real AWS accepts none of this.
DUMMY_ACCESS_KEY = "test"
DUMMY_SECRET_KEY = "test"

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"}

_lock = threading.Lock()


class EndpointSafetyError(RuntimeError):
    """Raised when the configured endpoint is not a local emulator."""


def get_endpoint_url() -> str:
    """The emulator endpoint, from AWS_ENDPOINT_URL, defaulting to localhost."""
    return os.environ.get("AWS_ENDPOINT_URL", DEFAULT_ENDPOINT).rstrip("/")


def get_region() -> str:
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or DEFAULT_REGION


def is_local_endpoint(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in _LOCAL_HOSTS


def _assert_local(url: str) -> None:
    """Refuse to talk to anything that is not the local emulator.

    This module powers a remediation engine that detaches IAM policies and
    rewrites bucket policies. Pointing it at a real account by accident is the
    worst thing it could do, so that path is closed by default rather than
    documented as a warning.
    """
    if is_local_endpoint(url):
        return
    if os.environ.get("ALLOW_NON_LOCAL_ENDPOINT") == "1":
        log.warning("Non-local endpoint allowed by ALLOW_NON_LOCAL_ENDPOINT=1: %s", url)
        return
    raise EndpointSafetyError(
        f"Refusing to build an AWS client for non-local endpoint {url!r}.\n"
        "This project is built to run against the local Floci emulator only.\n"
        "Set AWS_ENDPOINT_URL to a localhost URL, or export "
        "ALLOW_NON_LOCAL_ENDPOINT=1 if you genuinely mean to target it."
    )


def _config() -> Config:
    return Config(
        region_name=get_region(),
        retries={"max_attempts": 2, "mode": "standard"},
        connect_timeout=5,
        read_timeout=15,
        # Floci is happier with path-style S3 addressing than virtual-host style,
        # which would try to resolve bucket-name.localhost.
        s3={"addressing_style": "path"},
    )


@lru_cache(maxsize=None)
def _cached_client(service: str, endpoint: str, region: str) -> BaseClient:
    return boto3.client(
        service,
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=DUMMY_ACCESS_KEY,
        aws_secret_access_key=DUMMY_SECRET_KEY,
        aws_session_token="test",
        config=_config(),
    )


def get_client(service: str) -> BaseClient:
    """Return a boto3 client for `service`, routed at the local emulator.

    Clients are cached per (service, endpoint, region); boto3 clients are
    thread-safe for calls, so sharing them is both safe and much faster than
    rebuilding one per call.
    """
    endpoint = get_endpoint_url()
    _assert_local(endpoint)
    with _lock:
        return _cached_client(service, endpoint, get_region())


@lru_cache(maxsize=None)
def _cached_resource(service: str, endpoint: str, region: str) -> Any:
    return boto3.resource(
        service,
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=DUMMY_ACCESS_KEY,
        aws_secret_access_key=DUMMY_SECRET_KEY,
        aws_session_token="test",
        config=_config(),
    )


def get_resource(service: str) -> Any:
    """Resource-style interface, for the places where it reads better."""
    endpoint = get_endpoint_url()
    _assert_local(endpoint)
    with _lock:
        return _cached_resource(service, endpoint, get_region())


# Convenience accessors, so callers do not pass service-name strings around.
def s3() -> BaseClient:          return get_client("s3")
def iam() -> BaseClient:         return get_client("iam")
def sqs() -> BaseClient:         return get_client("sqs")
def dynamodb() -> BaseClient:    return get_client("dynamodb")
def cloudtrail() -> BaseClient:  return get_client("cloudtrail")
def lambda_() -> BaseClient:     return get_client("lambda")
def sts() -> BaseClient:         return get_client("sts")


def account_id() -> str:
    """Emulator account id. Floci reports the standard all-zeros account."""
    try:
        return sts().get_caller_identity()["Account"]
    except Exception:  # pragma: no cover - emulator quirk, not worth failing on
        return "000000000000"


def health() -> dict[str, Any]:
    """Confirm the emulator is reachable before doing real work.

    Returns a dict rather than raising, so callers can print a useful message
    instead of a stack trace when Docker simply is not running.
    """
    endpoint = get_endpoint_url()
    info: dict[str, Any] = {
        "endpoint": endpoint,
        "region": get_region(),
        "local": is_local_endpoint(endpoint),
        "reachable": False,
        "services": {},
    }
    try:
        s3().list_buckets()
        info["reachable"] = True
        info["account"] = account_id()
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info

    for name, probe in (
        ("s3", lambda: s3().list_buckets()),
        ("iam", lambda: iam().list_roles(MaxItems=1)),
        ("sqs", lambda: sqs().list_queues()),
        ("cloudtrail", lambda: cloudtrail().describe_trails()),
        ("dynamodb", lambda: dynamodb().list_tables(Limit=1)),
        ("lambda", lambda: lambda_().list_functions(MaxItems=1)),
    ):
        try:
            probe()
            info["services"][name] = "ok"
        except Exception as exc:
            info["services"][name] = f"error: {type(exc).__name__}"
    return info


def reset_clients() -> None:
    """Drop cached clients. Needed after changing endpoint/region in tests."""
    _cached_client.cache_clear()
    _cached_resource.cache_clear()


if __name__ == "__main__":
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print(json.dumps(health(), indent=2))
