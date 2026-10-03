from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Banco de dados
    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "paje"
    db_user: str = "paje_user"
    db_password: str

    # ANVISA
    anvisa_base_url: str = "https://consultas.anvisa.gov.br"
    anvisa_delay_segundos: float = 1.5
    anvisa_tipo_bula: str = "paciente"
    anvisa_retry_tentativas: int = 3
    anvisa_retry_espera_segundos: float = 5.0

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    llm_num_ctx: int = 4096
    llm_max_result_retries: int = 1

    # Extração
    extracao_reprocessar_erro: bool = False

    # Pipeline
    pipeline_aquisicao_habilitada: bool = True
    pipeline_preprocessamento_habilitada: bool = True
    pipeline_extracao_habilitada: bool = True

    # Paths
    bulas_dir: str = "docs/bulas"
    markdown_dir: str = "docs/markdown_bulas"
    rename_path: str = "docs/RENAME_07-08-2026.xlsx"
    referencia_lista_a_path: str = "docs/medicamentos_referencia_anvisa/lista_referencia_a_11-08-2026.xlsx"
    referencia_lista_b_path: str = "docs/medicamentos_referencia_anvisa/lista_referencia_b_11-08-2026.xlsx"

    # Prompt
    prompt_version: str = "v1"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
