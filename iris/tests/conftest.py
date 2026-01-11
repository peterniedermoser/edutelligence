import os
import yaml
from pathlib import Path

import pytest
from unittest.mock import patch
import weaviate
from testcontainers.core.container import DockerContainer

# This is executed before all imports of tests.

ROOT = Path(__file__).resolve().parents[1]

APPLICATION_YML_PATH = str(ROOT / "application.local.yml")
LLM_CONFIG_PATH = str(ROOT / "llm_config.local.yml")

os.environ["APPLICATION_YML_PATH"] = APPLICATION_YML_PATH
os.environ["LLM_CONFIG_PATH"] = LLM_CONFIG_PATH

with open(APPLICATION_YML_PATH, "r") as f:
    config = yaml.safe_load(f)
WEAVIATE_HOST = config["test"]["weaviate"]["host"]

TESTS_IN_DOCKER = WEAVIATE_HOST == "weaviate_test"

# maybe this is a solution to patch before all imports? -> better google how to monkeypatch before all imports in python
#patcher = patch(
#    "iris.vector_database.database.weaviate.connect_to_local",
#    lambda *args, **kwargs: weaviate_client
#)
#patcher.start()


@pytest.fixture(scope="session")
def weaviate_container():
    container = (
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

    container.start()

    yield container

    container.stop()


import time
import requests

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



@pytest.fixture(scope="session")
def weaviate_client(weaviate_container):
    if wait_for_weaviate(8001 if TESTS_IN_DOCKER else int(weaviate_container.get_exposed_port(8001))):
        client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=8001 if TESTS_IN_DOCKER else int(weaviate_container.get_exposed_port(8001)),
        grpc_port=50051 if TESTS_IN_DOCKER else int(weaviate_container.get_exposed_port(50051)))

        print("im in fake connect")

        yield client

        client.close()



# Connect with Test DB instead of real one
@pytest.fixture(autouse=True)
def patch_weaviate_connect(weaviate_client):

    with patch(
            "iris.vector_database.database.weaviate.connect_to_local"
    ) as mock_connect:
        mock_connect.return_value = weaviate_client
        yield