"""
Testes unitários: Approval Gates (Portões de Aprovação)

Verifica:
- Criação de solicitações
- Auto-aprovação dentro do limite
- Aprovação/rejeição manual
- Listagem de pendentes
"""

import pytest
from gates.approval_gates import ApprovalGate, TipoAprovacao, SolicitacaoAprovacao


@pytest.mark.unit
class TestApprovalGate:
    """Testes do sistema de Approval Gates."""

    def setup_method(self):
        """Cria uma instância limpa para cada teste."""
        self.gate = ApprovalGate()

    def test_criar_solicitacao_pendente(self):
        """Solicitação de deploy deve ficar pendente."""
        sol = self.gate.requer_aprovacao(
            tipo=TipoAprovacao.DEPLOY_PRODUCAO,
            descricao="Deploy v1.0 para produção",
            solicitante="Alex (PM Central)",
        )
        assert sol.tipo == TipoAprovacao.DEPLOY_PRODUCAO
        assert sol.aprovado is None  # Pendente
        assert sol.descricao == "Deploy v1.0 para produção"

    def test_gasto_abaixo_limite_auto_aprovado(self):
        """Gasto de IA abaixo de R$50 deve ser auto-aprovado."""
        sol = self.gate.requer_aprovacao(
            tipo=TipoAprovacao.GASTO_IA,
            descricao="Chamada Claude para análise",
            solicitante="Kenji (Tech Lead)",
            valor=25.00,
        )
        assert sol.aprovado is True
        assert sol.aprovado_por == "auto_aprovado_limite"

    def test_gasto_acima_limite_fica_pendente(self):
        """Gasto de IA acima de R$50 deve ficar pendente."""
        sol = self.gate.requer_aprovacao(
            tipo=TipoAprovacao.GASTO_IA,
            descricao="Processamento batch pesado",
            solicitante="Yuki (IA)",
            valor=150.00,
        )
        assert sol.aprovado is None  # Pendente

    def test_aprovar_solicitacao(self):
        """Operations Lead deve conseguir aprovar."""
        sol = self.gate.requer_aprovacao(
            tipo=TipoAprovacao.DEPLOY_PRODUCAO,
            descricao="Deploy de teste",
            solicitante="Alex",
        )
        resultado = self.gate.aprovar(sol, aprovador="Jonatas")
        assert resultado.aprovado is True
        assert resultado.aprovado_por == "Jonatas"

    def test_rejeitar_solicitacao(self):
        """Operations Lead deve conseguir rejeitar."""
        sol = self.gate.requer_aprovacao(
            tipo=TipoAprovacao.CAMPANHA_MARKETING,
            descricao="Campanha Black Friday",
            solicitante="Marco (PM)",
        )
        resultado = self.gate.rejeitar(sol, aprovador="Jonatas")
        assert resultado.aprovado is False
        assert resultado.aprovado_por == "Jonatas"

    def test_listar_pendentes(self):
        """Deve listar apenas solicitações pendentes."""
        # Criar 3 solicitações — 1 auto-aprovada, 2 pendentes
        self.gate.requer_aprovacao(
            tipo=TipoAprovacao.GASTO_IA,
            descricao="Gasto pequeno",
            solicitante="Kenji",
            valor=10.00,  # Auto-aprovado
        )
        self.gate.requer_aprovacao(
            tipo=TipoAprovacao.DEPLOY_PRODUCAO,
            descricao="Deploy 1",
            solicitante="Hans",
        )
        self.gate.requer_aprovacao(
            tipo=TipoAprovacao.MUDANCA_ARQUITETURA,
            descricao="Migração banco",
            solicitante="Kenji",
        )

        pendentes = self.gate.listar_pendentes()
        assert len(pendentes) == 2

    def test_historico_completo(self):
        """Histórico deve conter todas as solicitações."""
        for i in range(5):
            self.gate.requer_aprovacao(
                tipo=TipoAprovacao.GASTO_IA,
                descricao=f"Gasto {i}",
                solicitante="Teste",
                valor=10.00,
            )
        assert len(self.gate.historico) == 5

    def test_tipos_de_aprovacao(self):
        """Todos os tipos de aprovação devem existir."""
        tipos = [t.value for t in TipoAprovacao]
        assert "deploy_producao" in tipos
        assert "gasto_ia" in tipos
        assert "mudanca_arquitetura" in tipos
        assert "campanha_marketing" in tipos
        assert "outreach_massa" in tipos
