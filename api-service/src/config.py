from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    api_key: str

    db_user: str
    db_pass: str
    db_host: str
    db_port: str
    db_name: str

    @property
    def database_url(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    amqp_user: str
    amqp_password: str
    amqp_host: str
    amqp_port: str

    @property
    def amqp_url(self):
        return f"amqp://{self.amqp_user}:{self.amqp_password}@{self.amqp_host}:{self.amqp_port}"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        extra="ignore",
    )


config = Config()
