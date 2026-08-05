import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))
INPUT_DIR = os.getenv("INPUT_DIR", os.path.join(BASE_DIR, "input"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(BASE_DIR, "output"))
LOGGING_DIR = os.getenv("LOGGING_DIR", os.path.join(BASE_DIR, "logging"))

# API & LLM Config
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
LLM_MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
