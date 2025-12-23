import os
from pathlib import Path

# This is executed before all imports of tests

ROOT = Path(__file__).resolve().parents[1]

os.environ["APPLICATION_YML_PATH"] = str(ROOT / "application.local.yml")
os.environ["LLM_CONFIG_PATH"] = str(ROOT / "llm_config.local.yml")