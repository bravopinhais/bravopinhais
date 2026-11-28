"""Regressão dos limites de segurança do frontend estático Bravo Shadow."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "index.html"
HTML = FRONTEND.read_text(encoding="utf-8")
API_CLIENT = (ROOT / "frontend" / "js" / "bravo-api.js").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "frontend" / "js" / "bravo-bootstrap.js").read_text(encoding="utf-8")
GOOGLE_AUTH = (ROOT / "frontend" / "js" / "google-auth.js").read_text(encoding="utf-8")


def test_api_bootstrap_requires_explicit_same_origin_configuration():
    assert '<script type="module" src="./js/bravo-bootstrap.js"></script>' in HTML
    assert "if (!value || value.enabled !== true)" in BOOTSTRAP
    assert "api.origin !== window.location.origin" in BOOTSTRAP
    assert BOOTSTRAP.index("settings = validateConfig(config)") < BOOTSTRAP.index("initializeGoogleSession")
    assert "const config = window.BRAVO_SHADOW_CONFIG" in BOOTSTRAP


def test_business_api_uses_one_shared_http_transport():
    assert len(re.findall(r"\bfetch\s*\(", API_CLIENT)) == 1
    assert "fetch(" not in HTML
    assert "fetch(" not in BOOTSTRAP
    assert 'apiRoot + "/api/v1/auth/me"' in GOOGLE_AUTH
    assert "api.get(" in HTML
    assert "api.post(" in HTML


def test_browser_session_credentials_are_not_persisted():
    sources = "\n".join((HTML, API_CLIENT, BOOTSTRAP, GOOGLE_AUTH))
    assert re.search(r"\blocalStorage\s*(?:\.|\[)", sources) is None
    assert re.search(r"\bsessionStorage\s*(?:\.|\[)", sources) is None
    assert re.search(r"\bindexedDB\s*(?:\.|\[)", sources) is None
    assert "document.cookie" not in sources


def test_user_administration_requires_google_session_and_admin_capabilities():
    assert "Aguardando sessão Google e API HTTPS Shadow" in HTML
    assert 'if(!api||!usuariosCan("read"))return;' in HTML
    assert 'if(!usuariosApiClient||usuariosSaving)return;' in HTML
    assert "Somente Admin possui capacidades de administração de usuários." in HTML
    assert 'usuariosApiClient.post("/api/v1/usuarios",data)' in HTML
    assert "O cadastro não cria credenciais locais." in HTML


def test_frontend_does_not_reintroduce_legacy_password_login():
    assert not re.search(r'type\s*=\s*["\']password["\']', HTML, re.IGNORECASE)
    assert "js/auth.js" not in HTML
