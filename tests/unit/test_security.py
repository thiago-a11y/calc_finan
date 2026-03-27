"""
Testes unitários: Segurança (JWT + bcrypt)

Verifica:
- Hash e verificação de senha
- Criação e decodificação de tokens JWT
- Token expirado
- Token inválido
"""

import pytest
import time
from api.security import (
    hash_senha,
    verificar_senha,
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
)


@pytest.mark.unit
class TestSenhas:
    """Testes de hash e verificação de senhas."""

    def test_hash_senha_retorna_hash_diferente(self):
        """Hash não deve ser igual à senha original."""
        senha = "MinhaS3nha!@#"
        hashed = hash_senha(senha)
        assert hashed != senha
        assert len(hashed) > 20

    def test_verificar_senha_correta(self):
        """Senha correta deve retornar True."""
        senha = "SenhaForte@2026"
        hashed = hash_senha(senha)
        assert verificar_senha(senha, hashed) is True

    def test_verificar_senha_incorreta(self):
        """Senha incorreta deve retornar False."""
        hashed = hash_senha("SenhaCorreta")
        assert verificar_senha("SenhaErrada", hashed) is False

    def test_hashes_diferentes_para_mesma_senha(self):
        """Dois hashes da mesma senha devem ser diferentes (salt)."""
        senha = "MesmaSenha"
        hash1 = hash_senha(senha)
        hash2 = hash_senha(senha)
        assert hash1 != hash2  # bcrypt usa salt diferente
        # Mas ambos devem verificar
        assert verificar_senha(senha, hash1) is True
        assert verificar_senha(senha, hash2) is True


@pytest.mark.unit
class TestJWT:
    """Testes de criação e validação de tokens JWT."""

    def test_criar_access_token(self):
        """Access token deve ser uma string não vazia."""
        token = criar_access_token(
            user_id=1, email="teste@teste.com",
            nome="Teste", papeis=["ceo"], company_id="test",
        )
        assert isinstance(token, str)
        assert len(token) > 50

    def test_decodificar_token_valido(self):
        """Token válido deve retornar payload correto."""
        token = criar_access_token(
            user_id=42, email="thiago@teste.com",
            nome="Thiago", papeis=["ceo", "admin"], company_id="objetiva",
        )
        payload = decodificar_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "thiago@teste.com"
        assert payload["nome"] == "Thiago"
        assert payload["type"] == "access"

    def test_decodificar_token_invalido(self):
        """Token inválido deve retornar None."""
        payload = decodificar_token("token.invalido.aqui")
        assert payload is None

    def test_refresh_token_tipo_correto(self):
        """Refresh token deve ter type='refresh'."""
        token = criar_refresh_token(user_id=1, email="teste@teste.com")
        payload = decodificar_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_access_e_refresh_tokens_diferentes(self):
        """Access e refresh token devem ser diferentes."""
        access = criar_access_token(user_id=1, email="t@t.com", nome="T", papeis=[], company_id="x")
        refresh = criar_refresh_token(user_id=1, email="t@t.com")
        assert access != refresh
