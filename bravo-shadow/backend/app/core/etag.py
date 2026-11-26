from fastapi import HTTPException


def parse_if_match(value: str | None) -> int:
    """Interpreta ETag forte numérico enviado em If-Match."""
    if value is None:
        raise HTTPException(status_code=428, detail="Informe o cabeçalho If-Match com a versão atual do registro.")
    candidate = value.strip()
    if candidate.startswith("W/"):
        raise HTTPException(status_code=400, detail="If-Match deve conter um ETag forte.")
    candidate = candidate.strip('"')
    if not candidate.isdigit() or int(candidate) < 1:
        raise HTTPException(status_code=400, detail="If-Match inválido. Use a versão numérica retornada pela API.")
    return int(candidate)


def format_etag(version: int) -> str:
    return f'"{version}"'
