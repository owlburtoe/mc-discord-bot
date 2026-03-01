import json
from typing import Dict, Optional, List, Any
from pydantic import Field, RootModel
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
    
    servers_file: str = Field("servers.json", alias="SERVERS_FILE")
    servers_json: Optional[str] = Field(None, alias="MC_SERVERS_JSON")

    @property
    def servers(self) -> Dict[str, Dict[str, str]]:
        """
        Load server definitions from:
        1. MC_SERVERS_JSON environment variable
        2. SERVERS_FILE (default: servers.json)
        3. Legacy MC_SERVER_N_... pattern
        """
        # 1. From JSON env var
        if self.servers_json:
            try:
                data = json.loads(self.servers_json)
                return self._parse_json_list(data)
            except Exception as e:
                print(f"Error parsing MC_SERVERS_JSON: {e}")

        # 2. From JSON file
        if os.path.exists(self.servers_file):
            try:
                with open(self.servers_file, "r") as f:
                    data = json.load(f)
                    return self._parse_json_list(data)
            except Exception as e:
                print(f"Error reading {self.servers_file}: {e}")

        # 3. Legacy pattern
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

    def _parse_json_list(self, data: Any) -> Dict[str, Dict[str, str]]:
        if not isinstance(data, list):
            raise ValueError("Server configuration must be a list of objects")
        
        parsed = {}
        for item in data:
            # Validate using Pydantic
            srv = MinecraftServer(**item)
            parsed[srv.key.lower()] = {
                "name": srv.name,
                "id": srv.id,
            }
        return parsed

settings = Settings()
