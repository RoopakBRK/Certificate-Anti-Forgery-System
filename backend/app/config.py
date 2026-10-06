"""
app/config.py
Configuration management for the system.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:  # python-dotenv is optional; real env vars still work
    pass

# Calculate base directory (root of the project)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:

    # Secrets / API access
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    # Chat model used to structure OCR text; must be available on your Mistral tier
    MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL") or "mistral-small-latest"

    # Which LLM structures the OCR text: groq (default) | huggingface | mistral
    EXTRACTION_PROVIDER: str = (os.getenv("EXTRACTION_PROVIDER") or "groq").lower()
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b"
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    HF_MODEL: str = os.getenv("HF_MODEL") or "meta-llama/Llama-3.3-70B-Instruct"
    # Secret used to sign verification reports (set a long random value in production)
    REPORT_SECRET: str = os.getenv("REPORT_SECRET", "")
    # Comma-separated. If set, /verify* require an "X-API-Key" header matching one of them.
    API_KEYS: list = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

    # CORS: comma-separated list of allowed origins
    ALLOWED_ORIGINS: list = [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()
    ]

    # Upload / abuse limits
    MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
    MAX_CONCURRENT_VERIFICATIONS: int = int(os.getenv("MAX_CONCURRENT_VERIFICATIONS", "3"))
    QUEUE_WAIT_SECONDS: int = int(os.getenv("QUEUE_WAIT_SECONDS", "30"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    
    # OCR ensemble: engines run in parallel and vote. Available: tesseract, paddle, easyocr,
    # mistral (cloud, sends the image to Mistral). The PDF text layer is always used for PDFs.
    OCR_ENGINES: list = [e.strip().lower() for e in
                         (os.getenv("OCR_ENGINES") or "tesseract,paddle,easyocr").split(",") if e.strip()]
    OCR_ENGINE_TIMEOUT: int = int(os.getenv("OCR_ENGINE_TIMEOUT", "60"))
    OCR_WARMUP: bool = os.getenv("OCR_WARMUP", "true").lower() == "true"
    MISTRAL_OCR_MODEL: str = os.getenv("MISTRAL_OCR_MODEL") or "mistral-ocr-latest"

    # Supabase: sign-in (Google OAuth) and per-user report history.
    # The service-role key stays on the server; it is what lets the backend write reports.
    SUPABASE_URL: str = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # LLM Configuration
    LLM_ENABLED: bool = os.getenv("LLM_ENABLED", "true").lower() == "true"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "mistral")
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "30"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "500"))
    
    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Data Paths
    # Ensure this points to where your onlinelist.csv actually lives
    CSV_PATH: str = os.getenv("CSV_PATH", os.path.join(BASE_DIR, "data", "onlinelist.csv"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def extraction_api_key(cls) -> str:
        """API key for the selected EXTRACTION_PROVIDER ('' if not configured)."""
        return {"groq": cls.GROQ_API_KEY, "huggingface": cls.HF_TOKEN,
                "mistral": cls.MISTRAL_API_KEY}.get(cls.EXTRACTION_PROVIDER, "")

    @classmethod
    def get_llm_config(cls) -> dict:
        return {
            "enabled": cls.LLM_ENABLED,
            "model": cls.LLM_MODEL,
            "timeout": cls.LLM_TIMEOUT,
            "temperature": cls.LLM_TEMPERATURE,
            "max_tokens": cls.LLM_MAX_TOKENS,
            "ollama_host": cls.OLLAMA_HOST
        }

config = Config()