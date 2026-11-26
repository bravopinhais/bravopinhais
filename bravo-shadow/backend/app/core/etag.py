from fastapi import HTTPException


def parse_if_match(value: str | None) -> int:
    """Interpreta ETag forte numérico enviado em If-Match."""
    if value is None:
        raise HTTPException(status_code=428, detail="Informe o cabeçalho If-Match com a versão atual do registro.")
    candidate = value.strip()
    if candidate.startswith("W/"):
        raise HTTPException(status_code=400, detail="If-Match deve conter um ETag forte.")
    if len(candidate) < 3 or not (candidate.startswith('"') and candidate.endswith('"')):
        raise HTTPException(status_code=400, detail='If-Match inválido. Use o ETag forte, por exemplo: "1".')
    version = candidate[1:-1]
    if not version.isdigit() or int(version) < 1:
        raise HTTPException(status_code=400, detail="If-Match inválido. A versão deve ser um inteiro positivo.")
    return int(version)


def format_etag(version: int) -> str:
    return f'"{version}"'
