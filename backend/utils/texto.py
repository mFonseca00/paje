import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, sem espaços duplicados."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())
