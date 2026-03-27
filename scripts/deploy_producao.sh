#!/bin/bash
# =============================================================
# Deploy Produção — Synerium Factory
# Executa do Mac local para sincronizar e atualizar o servidor AWS
#
# Uso:
#   chmod +x scripts/deploy_producao.sh
#   ./scripts/deploy_producao.sh
#
# Pré-requisitos:
#   - SSH key configurada para ubuntu@servidor
#   - GitHub CLI autenticado (gh auth status)
# =============================================================

set -e  # Parar no primeiro erro

# Configurações
SERVER_HOST="${SYNERIUM_SERVER_HOST:-synerium-aws}"  # Alias SSH do ~/.ssh/config
SERVER_IP="3.223.92.171"
SERVER_USER="ubuntu"
SERVER_DIR="/opt/synerium-factory"
DOMAIN="synerium-factory.objetivasolucao.com.br"

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

step() {
    echo -e "\n${BLUE}=============================================================${NC}"
    echo -e "  ${GREEN}[$1/6]${NC} $2"
    echo -e "${BLUE}=============================================================${NC}\n"
}

warn() {
    echo -e "${YELLOW}[AVISO]${NC} $1"
}

error() {
    echo -e "${RED}[ERRO]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# ----- Verificações Pré-Deploy -----

echo -e "\n${GREEN}SYNERIUM FACTORY — Deploy Produção${NC}"
echo -e "Servidor: ${SERVER_HOST} (${DOMAIN})\n"

# Verificar SSH
step 1 "VERIFICAR CONEXÃO SSH"
ssh -o ConnectTimeout=5 -o BatchMode=yes ${SERVER_HOST} "echo 'SSH OK'" 2>/dev/null || error "Sem conexão SSH com ${SERVER_IP}. Verifique sua chave SSH."
success "Conexão SSH funcionando"

# ----- Sync Vaults Obsidian -----

step 2 "SINCRONIZAR VAULTS OBSIDIAN"

VAULT_SX="$HOME/Documents/SyneriumX-notes"
VAULT_SF="$HOME/Documents/SyneriumFactory-notes"
REMOTE_VAULTS="${SERVER_DIR}/data/vaults"

# Criar diretórios remotos
ssh ${SERVER_HOST} "sudo mkdir -p ${REMOTE_VAULTS}/SyneriumX-notes ${REMOTE_VAULTS}/SyneriumFactory-notes && sudo chown -R ${SERVER_USER}:${SERVER_USER} ${REMOTE_VAULTS}"

if [ -d "$VAULT_SX" ]; then
    echo "Sincronizando SyneriumX-notes..."
    rsync -avz --delete --exclude='.obsidian' --exclude='.trash' "$VAULT_SX/" "${SERVER_HOST}:${REMOTE_VAULTS}/SyneriumX-notes/"
    success "SyneriumX-notes sincronizado"
else
    warn "SyneriumX-notes não encontrado em $VAULT_SX"
fi

if [ -d "$VAULT_SF" ]; then
    echo "Sincronizando SyneriumFactory-notes..."
    rsync -avz --delete --exclude='.obsidian' --exclude='.trash' "$VAULT_SF/" "${SERVER_HOST}:${REMOTE_VAULTS}/SyneriumFactory-notes/"
    success "SyneriumFactory-notes sincronizado"
else
    warn "SyneriumFactory-notes não encontrado em $VAULT_SF"
fi

# ----- Pull Código no Servidor -----

step 3 "ATUALIZAR CÓDIGO NO SERVIDOR"

ssh ${SERVER_HOST} << 'REMOTE_PULL'
cd /opt/synerium-factory
echo "Branch atual: $(git branch --show-current)"
git pull origin main 2>&1
echo "Último commit: $(git log --oneline -1)"
REMOTE_PULL

success "Código atualizado"

# ----- Instalar Dependências -----

step 4 "INSTALAR DEPENDÊNCIAS"

ssh ${SERVER_HOST} << 'REMOTE_DEPS'
cd /opt/synerium-factory

# Python
echo "Instalando dependências Python..."
source .venv/bin/activate
pip install -r requirements.txt --quiet 2>&1 | tail -3

# Node/React
echo "Fazendo build do dashboard..."
cd dashboard
npm install --silent 2>&1 | tail -3
npm run build 2>&1 | tail -5
cd ..

echo "Dependências instaladas"
REMOTE_DEPS

success "Dependências atualizadas"

# ----- Bootstrap (Seeds + RAG + Verificações) -----

step 5 "EXECUTAR BOOTSTRAP"

ssh ${SERVER_HOST} << 'REMOTE_BOOTSTRAP'
cd /opt/synerium-factory
source .venv/bin/activate
python -m scripts.bootstrap_aws 2>&1
REMOTE_BOOTSTRAP

success "Bootstrap executado"

# ----- Reiniciar Serviço -----

step 6 "REINICIAR SERVIÇO"

ssh ${SERVER_HOST} << 'REMOTE_RESTART'
sudo systemctl restart synerium-factory 2>/dev/null || echo "Serviço não configurado ainda"
sleep 2
sudo systemctl status synerium-factory --no-pager 2>/dev/null || echo "Verificar configuração do systemd"
REMOTE_RESTART

# ----- Verificação Final -----

echo -e "\n${GREEN}=============================================================${NC}"
echo -e "  ${GREEN}DEPLOY CONCLUÍDO!${NC}"
echo -e "${GREEN}=============================================================${NC}\n"

echo "Acesse: https://${DOMAIN}"
echo "Login: thiago@objetivasolucao.com.br / SyneriumFactory@2026"
echo ""
echo "Comandos úteis:"
echo "  ssh ${SERVER_HOST}                     # Acessar servidor"
echo "  ssh ${SERVER_HOST} 'journalctl -u synerium-factory -f'  # Ver logs"
echo ""
