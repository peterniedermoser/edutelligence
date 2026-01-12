import os
import yaml
from pathlib import Path
import weaviate
from testcontainers.core.container import DockerContainer
from unittest.mock import patch
import time
import requests

# This is executed before all imports of tests.

ROOT = Path(__file__).resolve().parents[1]

APPLICATION_YML_PATH = str(ROOT / "application.local.yml")
LLM_CONFIG_PATH = str(ROOT / "llm_config.local.yml")

os.environ["APPLICATION_YML_PATH"] = APPLICATION_YML_PATH
os.environ["LLM_CONFIG_PATH"] = LLM_CONFIG_PATH


# Below a session-wide weaviate container is started for all tests via monkeypatch

with open(APPLICATION_YML_PATH, "r") as f:
    config = yaml.safe_load(f)
WEAVIATE_HOST = config["test"]["weaviate"]["host"]

TESTS_IN_DOCKER = WEAVIATE_HOST == "weaviate_test"

_TEST_WEAVIATE_CLIENT = None
_TEST_WEAVIATE_CONTAINER = None

_REAL_CONNECT_TO_LOCAL = weaviate.connect_to_local

def get_or_start_weaviate_container():
    global _TEST_WEAVIATE_CONTAINER

    if _TEST_WEAVIATE_CONTAINER is None:
        _TEST_WEAVIATE_CONTAINER = (
            DockerContainer("cr.weaviate.io/semitechnologies/weaviate:1.32.2")
            .with_name("weaviate_test")
            .with_command([
                "--host", "0.0.0.0",
                "--port", "8001",
                "--scheme", "http"
            ])
            .with_exposed_ports(8001, 50051)
            .with_env("QUERY_DEFAULTS_LIMIT", "25")
            .with_env("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
            .with_env("DEFAULT_VECTORIZER_MODULE", "none")
            .with_env("ENABLE_MODULES", "")
        )

        _TEST_WEAVIATE_CONTAINER.start()

    return _TEST_WEAVIATE_CONTAINER


def get_or_connect_client():
    global _TEST_WEAVIATE_CLIENT

    if _TEST_WEAVIATE_CLIENT is None:
        if wait_for_weaviate(8001 if TESTS_IN_DOCKER else int(get_or_start_weaviate_container().get_exposed_port(8001))):
            _TEST_WEAVIATE_CLIENT = _REAL_CONNECT_TO_LOCAL(
                host=WEAVIATE_HOST,
                port=8001 if TESTS_IN_DOCKER else int(get_or_start_weaviate_container().get_exposed_port(8001)),
                grpc_port=50051 if TESTS_IN_DOCKER else int(get_or_start_weaviate_container().get_exposed_port(50051)))

    return _TEST_WEAVIATE_CLIENT


def wait_for_weaviate(port, timeout=30):
    url = f"http://{WEAVIATE_HOST}:{port}/v1/.well-known/ready"
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url).status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return RuntimeError("Weaviate did not become ready in time")


def connect_mock(*args, **kwargs):
    return get_or_connect_client()


# Patch must be global without pytest fixtures to happen before all imports (otherwise: real connect_to_local is called in abstract_agent_pipeline.py)
patcher = patch(
    "iris.vector_database.database.weaviate.connect_to_local",
    connect_mock,
)
patcher.start()