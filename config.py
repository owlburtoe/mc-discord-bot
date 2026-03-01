from typing import Dict, Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class MinecraftServer(BaseSettings):
    key: str
    name: str
    id: str

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    discord_token: str = Field(..., alias="DISCORD_TOKEN")
    guild_id: Optional[str] = Field(None, alias="GUILD_ID")
    allowed_channel_id: int = Field(0, alias="ALLOWED_CHANNEL_ID")
    owner_id: int = Field(0, alias="OWNER_ID")
    mod_role_id: int = Field(0, alias="MOD_ROLE_ID")

    crafty_url: str = Field(..., alias="CRAFTY_URL")
    crafty_token: str = Field(..., alias="CRAFTY_TOKEN")

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_json: bool = Field(False, alias="LOG_JSON")

    @property
    def servers(self) -> Dict[str, Dict[str, str]]:
        """
        Backward compatible server loading from MC_SERVER_N_... pattern.
        """
        srvs = {}
        for i in range(1, 21):
            key = os.getenv(f"MC_SERVER_{i}_KEY")
            name = os.getenv(f"MC_SERVER_{i}_NAME")
            uuid = os.getenv(f"MC_SERVER_{i}_ID")

            if key and uuid:
                srvs[key.lower()] = {
                    "name": name or key,
                    "id": uuid,
                }
        return srvs

settings = Settings()
