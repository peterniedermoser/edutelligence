import os
from pathlib import Path

import pytest
from unittest.mock import patch
import weaviate
from testcontainers.core.container import DockerContainer

# This is executed before all imports of tests.

ROOT = Path(__file__).resolve().parents[1]

os.environ["APPLICATION_YML_PATH"] = str(ROOT / "application.local.yml")
os.environ["LLM_CONFIG_PATH"] = str(ROOT / "llm_config.local.yml")

TEST_WEAVIATE_HOST = "localhost"
TEST_WEAVIATE_PORT = 8002
TEST_WEAVIATE_GRPC_PORT = 50052


@pytest.fixture(scope="session")
def weaviate_container():
    container = (
        DockerContainer("cr.weaviate.io/semitechnologies/weaviate:1.32.2")
        .with_exposed_ports(TEST_WEAVIATE_PORT, TEST_WEAVIATE_GRPC_PORT)
        .with_env("QUERY_DEFAULTS_LIMIT", "25")
        .with_env("AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED", "true")
        .with_env("DEFAULT_VECTORIZER_MODULE", "none")
        .with_env("ENABLE_MODULES", "")
    )

    container.start()

    yield container

    # container.stop()


import time
import requests

def wait_for_weaviate(port, timeout=30):
    url = f"http://localhost:{port}/v1/.well-known/ready"
    start = time.time()
    while time.time() - start < timeout:
        try:
            if requests.get(url).status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)
    return True


@pytest.fixture(scope="session")
def weaviate_client(weaviate_container):

    if wait_for_weaviate(int(weaviate_container.get_exposed_port(TEST_WEAVIATE_PORT))):
        client = weaviate.connect_to_local(
        host=TEST_WEAVIATE_HOST,
        port=int(weaviate_container.get_exposed_port(TEST_WEAVIATE_PORT)),
        grpc_port=int(weaviate_container.get_exposed_port(TEST_WEAVIATE_GRPC_PORT)))


        yield client

    # client.close()


from iris.vector_database.database import VectorDatabase
from iris.vector_database.lecture_transcription_schema import init_lecture_transcription_schema
from iris.vector_database.lecture_unit_page_chunk_schema import init_lecture_unit_page_chunk_schema
from iris.vector_database.lecture_unit_schema import init_lecture_unit_schema
from iris.vector_database.lecture_unit_segment_schema import init_lecture_unit_segment_schema
from iris.vector_database.faq_schema import init_faq_schema

@pytest.fixture(autouse=True)
def patch_vector_db_init(weaviate_client):

    def _mocked_init(self):

        print("my init is in use")

        # Always use Test Client
        VectorDatabase._client_instance = weaviate_client

        self.client = VectorDatabase._client_instance
        self.lectures = init_lecture_unit_page_chunk_schema(self.client)
        self.transcriptions = init_lecture_transcription_schema(self.client)
        self.lecture_segments = init_lecture_unit_segment_schema(self.client)
        self.lecture_units = init_lecture_unit_schema(self.client)
        self.faqs = init_faq_schema(self.client)

    with patch.object(VectorDatabase, "__init__", _mocked_init):
        yield