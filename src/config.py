import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
sub_input = os.path.join(BASE_DIR, "input", "input")
INPUT_DIR = sub_input if os.path.exists(sub_input) and any(f.startswith("EC_") for f in os.listdir(sub_input)) else os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
LOGGING_DIR = os.path.join(BASE_DIR, "logs")

# Model name hardcoded in source per submission rules (must not be in .env)
LLM_MODEL_NAME = "meta/llama-3.1-8b-instruct"       # NVIDIA NIM model
GROQ_MODEL_NAME = "llama-3.1-8b-instant"             # Groq model (≤10B params)
OPENAI_MODEL_NAME = "gpt-4o-mini"                    # OpenAI fast model

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
