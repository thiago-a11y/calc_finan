"""
Testes unitários: Ferramentas do SyneriumX

Verifica:
- Validação de caminhos (segurança)
- Leitura de arquivos
- Listagem de diretórios
- Bloqueio de acesso fora do diretório permitido
- Proposta de edição (não aplica direto)
"""

import os
import pytest
from tools.syneriumx_tools import (
    _validar_caminho,
    LerArquivoSyneriumX,
    ListarDiretorioSyneriumX,
    ProporEdicaoSyneriumX,
    GitSyneriumX,
    SYNERIUMX_BASE,
)


@pytest.mark.unit
class TestValidacaoCaminho:
    """Testes de segurança na validação de caminhos."""

    def test_caminho_relativo_valido(self):
        """Caminho relativo dentro do projeto deve ser aceito."""
        resultado = _validar_caminho("api/config.php")
        assert resultado.startswith(SYNERIUMX_BASE)

    def test_caminho_raiz_valido(self):
        """Caminho '.' deve resolver para a raiz do projeto."""
        resultado = _validar_caminho(".")
        assert resultado == os.path.normpath(SYNERIUMX_BASE)

    def test_caminho_fora_do_projeto_bloqueado(self):
        """Caminho fora do projeto deve ser bloqueado."""
        with pytest.raises(ValueError, match="BLOQUEADO"):
            _validar_caminho("../../etc/passwd")

    def test_caminho_absoluto_fora_bloqueado(self):
        """Caminho absoluto fora do projeto deve ser bloqueado."""
        with pytest.raises(ValueError, match="BLOQUEADO"):
            _validar_caminho("/etc/passwd")

    def test_path_traversal_bloqueado(self):
        """Path traversal (../) deve ser bloqueado."""
        with pytest.raises(ValueError, match="BLOQUEADO"):
            _validar_caminho("api/../../../etc/shadow")


@pytest.mark.unit
class TestLerArquivo:
    """Testes de leitura de arquivos do SyneriumX."""

    def setup_method(self):
        self.tool = LerArquivoSyneriumX()

    def test_ler_arquivo_existente(self):
        """Deve conseguir ler um arquivo que existe."""
        # Este teste depende do SyneriumX estar em ~/propostasap
        if not os.path.isdir(SYNERIUMX_BASE):
            pytest.skip("SyneriumX não encontrado em ~/propostasap")
        resultado = self.tool._run("api/config.php")
        assert "===" in resultado
        assert "config.php" in resultado

    def test_ler_arquivo_inexistente(self):
        """Deve retornar erro para arquivo inexistente."""
        resultado = self.tool._run("arquivo_que_nao_existe_xyz.php")
        assert "não encontrado" in resultado.lower() or "Arquivo" in resultado


@pytest.mark.unit
class TestListarDiretorio:
    """Testes de listagem de diretórios."""

    def setup_method(self):
        self.tool = ListarDiretorioSyneriumX()

    def test_listar_raiz(self):
        """Deve listar a raiz do projeto."""
        if not os.path.isdir(SYNERIUMX_BASE):
            pytest.skip("SyneriumX não encontrado")
        resultado = self.tool._run("")
        assert "itens" in resultado

    def test_listar_diretorio_inexistente(self):
        """Deve retornar erro para diretório inexistente."""
        resultado = self.tool._run("pasta_que_nao_existe_xyz")
        assert "não é um diretório" in resultado


@pytest.mark.unit
class TestGitSyneriumX:
    """Testes do acesso Git."""

    def setup_method(self):
        self.tool = GitSyneriumX()

    def test_git_status(self):
        """Git status deve funcionar."""
        if not os.path.isdir(SYNERIUMX_BASE):
            pytest.skip("SyneriumX não encontrado")
        resultado = self.tool._run("status")
        assert "git status" in resultado

    def test_git_push_bloqueado(self):
        """Git push deve ser bloqueado."""
        resultado = self.tool._run("push origin main")
        assert "REQUER APROVAÇÃO" in resultado

    def test_git_reset_bloqueado(self):
        """Git reset deve ser bloqueado."""
        resultado = self.tool._run("reset --hard HEAD~1")
        assert "REQUER APROVAÇÃO" in resultado

    def test_git_merge_bloqueado(self):
        """Git merge deve ser bloqueado."""
        resultado = self.tool._run("merge feature-branch")
        assert "REQUER APROVAÇÃO" in resultado


@pytest.mark.unit
class TestProporEdicao:
    """Testes da proposta de edição (não aplica direto)."""

    def setup_method(self):
        self.tool = ProporEdicaoSyneriumX()

    def test_proposta_formato_invalido(self):
        """Deve rejeitar formato inválido."""
        resultado = self.tool._run("apenas um argumento")
        assert "formato inválido" in resultado.lower() or "Erro" in resultado

    def test_proposta_cria_arquivo_json(self):
        """Deve criar arquivo de proposta em data/propostas_edicao/."""
        resultado = self.tool._run(
            "docs/teste_pytest.md|||# Teste Pytest|||Teste automatizado de proposta"
        )
        assert "Solicitação de edição criada" in resultado
        assert "AGUARDANDO APROVAÇÃO" in resultado
