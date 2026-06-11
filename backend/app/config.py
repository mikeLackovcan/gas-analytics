from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    entsog_base_url: str = "https://transparency.entsog.eu/api/v1"
    agsi_base_url: str = "https://agsi.gie.eu/api"
    agsi_api_key: str = ""
    alsi_base_url: str = "https://alsi.gie.eu/api"
    alsi_api_key: str = ""
    entsoe_base_url: str = "https://web-api.tp.entsoe.eu/api"
    entsoe_api_token: str = ""

    data_dir: Path = Path("./data")
    db_url: str = "duckdb:///./data/gas.duckdb"
    log_level: str = "INFO"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def parquet_dir(self) -> Path:
        return self.data_dir / "parquet"


settings = Settings()
settings.raw_dir.mkdir(parents=True, exist_ok=True)
settings.parquet_dir.mkdir(parents=True, exist_ok=True)
