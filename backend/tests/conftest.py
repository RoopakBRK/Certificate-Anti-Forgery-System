import os
import sys

os.environ.setdefault("MISTRAL_API_KEY", "test-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
