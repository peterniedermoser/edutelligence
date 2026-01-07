import os
from pathlib import Path


# Settings for tests
# This is executed before all imports of tests.

ROOT = Path(__file__).resolve().parents[1]

TEST_WEAVIATE_HOST = "localhost"
TEST_WEAVIATE_PORT = 8002
TEST_WEAVIATE_GRPC_PORT = 50052

os.environ["APPLICATION_YML_PATH"] = str(ROOT / "application.local.yml")
os.environ["LLM_CONFIG_PATH"] = str(ROOT / "llm_config.local.yml")