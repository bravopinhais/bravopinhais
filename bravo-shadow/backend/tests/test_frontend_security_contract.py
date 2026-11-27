"""Regressão dos limites de segurança do frontend estático Bravo Shadow."""

from pathlib import Path
import re


FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
HTML = FRONTEND.read_text(encoding="utf-8")


def _function_body(name: str, next_name: str) -> str:
    match = re.search(
        rf"function {re.escape(name)}\(\)\{{(?P<body>.*?)\n\}}\nfunction {re.escape(next_name)}",
        HTML,
        re.DOTALL,
    )
    assert match, f"Não foi possível localizar a função {name} no frontend."
    return match.group("body")


def test_github_pages_preview_blocks_api_before_network_request():
    assert 'const IS_STATIC_PREVIEW=location.hostname.endsWith("github.io")' in HTML

    match = re.search(
        r"async function apiRequest\(path,options=\{\}\)\{(?P<body>.*?)\n\}",
        HTML,
        re.DOTALL,
    )
    assert match, "O transporte centralizado apiRequest deve existir."
    body = match.group("body")

    guard = body.find("if(IS_STATIC_PREVIEW)throw new Error")
    request = body.find("fetch(")
    assert guard >= 0, "O preview estático deve bloquear chamadas à API."
    assert request >= 0, "O adaptador deve executar a chamada de rede no ambiente permitido."
    assert guard < request, "O bloqueio do GitHub Pages deve ocorrer antes de qualquer fetch."


def test_frontend_has_only_one_centralized_fetch_transport():
    assert len(re.findall(r"\bfetch\s*\(", HTML)) == 1, (
        "Toda chamada HTTP deve passar pelo adaptador apiRequest."
    )


def test_browser_session_credentials_are_not_persisted_in_web_storage():
    forbidden = re.search(
        r"\b(?:localStorage|sessionStorage|indexedDB)\b|document\.cookie",
        HTML,
        re.IGNORECASE,
    )
    assert forbidden is None, (
        "O frontend não deve persistir credenciais ou sessão em armazenamento durável do navegador."
    )


def test_user_administration_remains_closed_until_google_session_is_integrated():
    body = _function_body("usuariosView", "openModule")
    assert "Integração Google pendente" in body
    assert "Sem operações liberadas" in body
    assert "apiRequest(" not in body, (
        "A tela de usuários não deve consultar nem alterar dados antes da integração aprovada."
    )


def test_frontend_does_not_reintroduce_legacy_password_login():
    assert not re.search(r'type\s*=\s*["\']password["\']', HTML, re.IGNORECASE)
    assert "js/auth.js" not in HTML
