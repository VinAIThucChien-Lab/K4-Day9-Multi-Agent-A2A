import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sub_input = os.path.join(BASE_DIR, "input", "input")
INPUT_DIR = sub_input if os.path.exists(sub_input) and any(f.startswith("EC_") for f in os.listdir(sub_input)) else os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGGING_DIR = os.path.join(BASE_DIR, "logs")

LLM_MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct"
