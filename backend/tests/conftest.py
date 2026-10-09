import os
import sys

os.environ.setdefault("MISTRAL_API_KEY", "test-key")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ["VLM_PROVIDER"] = ""   # whatever .env says, tests never send an image to a real vision model
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
