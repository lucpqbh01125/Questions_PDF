import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    
    def __init__(self):

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL")
        
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8000"))
        
        self.max_chunk_chars = int(os.getenv("MAX_CHUNK_CHARS", "6000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "300"))
        
        self.ai_temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))
        self.ai_max_tokens = int(os.getenv("AI_MAX_TOKENS", "2500"))

        self.secret_key = os.getenv("SECRET_KEY")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
        
        self.database_url = os.getenv("DATABASE_URL")
    
    def get_masked_api_key(self) -> str:
        if not self.openai_api_key:
            return "***"
        return f"{self.openai_api_key[:3]}...{self.openai_api_key[-3:]}"

settings = Settings()
