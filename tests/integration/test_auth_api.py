"""
Testes de integração: API de Autenticação

Verifica endpoints reais do FastAPI:
- POST /auth/login
- POST /auth/refresh
- POST /auth/trocar-senha
- Proteção de rotas com JWT
"""

import pytest


@pytest.mark.integration
class TestLoginAPI:
    """Testes do endpoint de login."""

    def test_login_sucesso(self, client, usuario_ceo):
        """Login com credenciais corretas deve retornar tokens."""
        resp = client.post("/auth/login", json={
            "email": "thiago@teste.com",
            "senha": "SenhaForte@123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["usuario"]["nome"] == "Thiago (Teste)"

    def test_login_senha_errada(self, client, usuario_ceo):
        """Login com senha errada deve retornar 401."""
        resp = client.post("/auth/login", json={
            "email": "thiago@teste.com",
            "senha": "SenhaErrada",
        })
        assert resp.status_code == 401

    def test_login_email_inexistente(self, client):
        """Login com email inexistente deve retornar 401."""
        resp = client.post("/auth/login", json={
            "email": "naoexiste@teste.com",
            "senha": "qualquer",
        })
        assert resp.status_code == 401


@pytest.mark.integration
class TestRotasProtegidas:
    """Testes de proteção de rotas com JWT."""

    def test_rota_sem_token_retorna_401(self, client):
        """Rota protegida sem token deve retornar 401."""
        resp = client.get("/api/squads")
        assert resp.status_code == 401

    def test_rota_com_token_valido(self, client, token_ceo):
        """Rota protegida com token válido deve funcionar."""
        resp = client.get("/api/squads", headers={
            "Authorization": f"Bearer {token_ceo}"
        })
        assert resp.status_code == 200

    def test_rota_com_token_invalido(self, client):
        """Rota protegida com token inválido deve retornar 401."""
        resp = client.get("/api/squads", headers={
            "Authorization": "Bearer token.invalido.aqui"
        })
        assert resp.status_code == 401


@pytest.mark.integration
class TestTrocarSenha:
    """Testes do endpoint de trocar senha."""

    def test_trocar_senha_sucesso(self, client, usuario_ceo, token_ceo):
        """Trocar senha com dados corretos deve funcionar."""
        resp = client.post("/auth/trocar-senha",
            json={
                "senha_atual": "SenhaForte@123",
                "nova_senha": "NovaSenha@456",
            },
            headers={"Authorization": f"Bearer {token_ceo}"},
        )
        assert resp.status_code == 200
        assert "sucesso" in resp.json()["mensagem"].lower()

    def test_trocar_senha_atual_errada(self, client, usuario_ceo, token_ceo):
        """Trocar senha com senha atual errada deve retornar 400."""
        resp = client.post("/auth/trocar-senha",
            json={
                "senha_atual": "SenhaErrada",
                "nova_senha": "NovaSenha@456",
            },
            headers={"Authorization": f"Bearer {token_ceo}"},
        )
        assert resp.status_code == 400
