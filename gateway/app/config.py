"""
Gateway configuration
"""
import os
from typing import Optional

class Settings:
    # Gateway settings
    GATEWAY_ID: str = os.getenv("GATEWAY_ID", "gateway-1")
    GATEWAY_NAME: str = os.getenv("GATEWAY_NAME", "Gateway-1")
    
    # Kopia settings
    KOPIA_MOUNT_PATH: str = os.getenv("KOPIA_MOUNT_PATH", "/mnt/kopia")
    REPO_PATH: str = os.getenv("REPO_PATH", "/data/repo")
    KOPIA_PASSWORD: str = os.getenv("KOPIA_PASSWORD", "hyperfilelens")
    
    # Control plane connection
    CONTROL_URL: str = os.getenv("CONTROL_URL", "http://localhost:8000")
    CONTROL_WS_URL: str = os.getenv("CONTROL_WS_URL", "ws://localhost:8000")
    
    # Index settings
    INDEX_DB_PATH: str = os.getenv("INDEX_DB_PATH", "/data/index.db")
    
    # AI settings
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "placeholder")  # placeholder, openai, custom
    AI_API_KEY: Optional[str] = os.getenv("AI_API_KEY")
    AI_API_URL: Optional[str] = os.getenv("AI_API_URL")
    
    @property
    def websocket_url(self) -> str:
        return f"{self.CONTROL_WS_URL}/ws/gateway/{self.GATEWAY_ID}"

settings = Settings()
