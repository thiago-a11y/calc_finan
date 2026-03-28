# Deploy em Produção — Synerium Factory

> Guia completo para colocar o Synerium Factory em `synerium-factory.objetivasolucao.com.br`

---

## Por que NÃO pode ficar no cPanel atual?

O cPanel da Objetiva é **compartilhado e só suporta PHP**. O Synerium Factory precisa de:
- Python 3.13 rodando 24/7 (FastAPI + uvicorn)
- SQLite com acesso direto ao disco
- ChromaDB (vector store) em memória
- WebSocket para LiveKit
- Process workers para agentes CrewAI

**Solução:** Servidor dedicado (VPS) apontado pelo subdomínio.

---

## Opções de Hospedagem (comparativo)

| Opção | Custo/mês | Prós | Contras |
|-------|-----------|------|---------|
| **Hetzner Cloud** | R$25 (~€4) | Mais barato, SSD rápido, EU datacenter | Não tem no Brasil |
| **DigitalOcean** | R$30 (~$6) | Fácil de usar, bom suporte | Um pouco mais caro |
| **AWS Lightsail** | R$30 (~$5) | Já tem conta AWS (SES), integrado | Interface mais complexa |
| **Contabo** | R$20 (~€3.5) | Muito barato, muito recurso | Suporte fraco |
| **Railway** | R$30 (~$5) | Deploy automático via GitHub | Menos controle |

**Recomendação:** **AWS Lightsail** — vocês já têm conta AWS (usam SES), então é integrado e familiar.

---

## Plano de Ação — Passo a Passo

### Etapa 1: Criar VPS (AWS Lightsail)

1. Acesse **https://lightsail.aws.amazon.com**
2. Clique **"Create instance"**
3. Configurações:
   - **Region:** São Paulo (sa-east-1) — mais perto de Ipatinga
   - **Platform:** Linux/Unix
   - **Blueprint:** Ubuntu 22.04 LTS
   - **Plano:** $5/mês (1 GB RAM, 1 vCPU, 40 GB SSD) — suficiente para começar
   - **Name:** `synerium-factory`
4. Clique **"Create instance"**
5. Aguarde o status ficar **"Running"**
6. Anote o **IP público** (ex: `18.231.xxx.xxx`)

### Etapa 2: DNS no Registro.br

1. Acesse o painel DNS de `objetivasolucao.com.br`
2. Adicione um **registro A**:
   - **Nome:** `synerium-factory`
   - **Tipo:** A
   - **Valor:** IP do Lightsail (o que anotou na etapa 1)
   - **TTL:** 300
3. Aguarde propagação DNS (5min a 2h)
4. Teste: `ping synerium-factory.objetivasolucao.com.br` → deve resolver para o IP

### Etapa 3: Configurar o Servidor (SSH)

Conectar via SSH:
```bash
ssh ubuntu@synerium-factory.objetivasolucao.com.br
```

Instalar dependências:
```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Python 3.13
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt install python3.13 python3.13-venv python3.13-dev -y

# Node.js 20 (para build do frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Git
sudo apt install git -y

# Nginx (reverse proxy)
sudo apt install nginx -y

# Certbot (SSL gratuito)
sudo apt install certbot python3-certbot-nginx -y
```

### Etapa 4: Clonar e Configurar o Projeto

```bash
# Clonar o repositório (criar repositório GitHub primeiro se necessário)
cd /opt
sudo mkdir synerium-factory
sudo chown ubuntu:ubuntu synerium-factory
git clone https://github.com/SineriumX/synerium-factory.git /opt/synerium-factory

# Virtualenv
cd /opt/synerium-factory
python3.13 -m venv .venv
source .venv/bin/activate

# Instalar dependências Python
pip install -r requirements.txt

# Copiar .env
cp .env.example .env
nano .env  # Editar com as chaves reais

# Build do frontend
cd dashboard
npm install
npm run build
cd ..

# Criar diretórios necessários
mkdir -p data/chromadb data/uploads/chat data/propostas_edicao data/deploys logs
```

### Etapa 5: Configurar Nginx (Reverse Proxy)

```bash
sudo nano /etc/nginx/sites-available/synerium-factory
```

Conteúdo:
```nginx
server {
    listen 80;
    server_name synerium-factory.objetivasolucao.com.br;

    # Frontend React (arquivos estáticos)
    root /opt/synerium-factory/dashboard/dist;
    index index.html;

    # SPA — todas as rotas vão para index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Python (reverse proxy para uvicorn)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Auth routes
    location /auth/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Uploads
    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
    }

    # WebSocket (para LiveKit e futuros)
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Ativar:
```bash
sudo ln -s /etc/nginx/sites-available/synerium-factory /etc/nginx/sites-enabled/
sudo nginx -t  # Testar configuração
sudo systemctl reload nginx
```

### Etapa 6: SSL (HTTPS gratuito)

```bash
sudo certbot --nginx -d synerium-factory.objetivasolucao.com.br
# Seguir as instruções (aceitar termos, email, redirect HTTP→HTTPS)
```

### Etapa 7: Systemd (API rodando permanentemente)

```bash
sudo nano /etc/systemd/system/synerium-factory.service
```

Conteúdo:
```ini
[Unit]
Description=Synerium Factory API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/synerium-factory
Environment=PATH=/opt/synerium-factory/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/opt/synerium-factory/.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ativar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable synerium-factory
sudo systemctl start synerium-factory
sudo systemctl status synerium-factory  # Verificar se está rodando
```

### Etapa 8: Testar

1. Acesse **https://synerium-factory.objetivasolucao.com.br**
2. Deve aparecer a tela de login
3. Login: `thiago@objetivasolucao.com.br` / `SyneriumFactory@2026`
4. Verificar: Painel Geral, Squads, Escritório, Deploy, etc.

---

## Deploy Automático (GitHub Actions)

Criar `.github/workflows/deploy-factory.yml`:

```yaml
name: Deploy Synerium Factory

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: synerium-factory.objetivasolucao.com.br
          username: ubuntu
          key: ${{ secrets.LIGHTSAIL_SSH_KEY }}
          script: |
            cd /opt/synerium-factory
            git pull origin main
            source .venv/bin/activate
            pip install -r requirements.txt
            cd dashboard && npm install && npm run build && cd ..
            sudo systemctl restart synerium-factory
```

---

## Checklist Final

- [ ] VPS criado (Lightsail $5/mês)
- [ ] DNS configurado (registro A no Registro.br)
- [ ] SSH funcionando
- [ ] Python + Node + Nginx instalados
- [ ] Projeto clonado e configurado
- [ ] Nginx configurado como reverse proxy
- [ ] SSL ativo (Let's Encrypt)
- [ ] Systemd rodando a API permanentemente
- [ ] Login funcionando
- [ ] GitHub Actions configurado para deploy automático

---

## Custos Mensais

| Item | Custo |
|------|-------|
| AWS Lightsail (VPS) | $5/mês (~R$25) |
| SSL (Let's Encrypt) | Grátis |
| DNS (subdomínio) | Grátis (já paga o domínio) |
| **Total** | **R$25/mês** |

---

## Migração Futura

Quando a Objetiva crescer (50+ tenants, mais produtos), migrar para:
- AWS EC2 com mais recursos
- Docker + Docker Compose
- PostgreSQL (em vez de SQLite)
- Redis para cache e filas
- CDN para assets

---

---

## Histórico de Deploys

| Data | Versão | Descrição |
|------|--------|-----------|
| 27/Mar/2026 | v0.16.0 + v0.16.1 | Luna (Assistente IA Integrada) + Soft Delete/Lixeira — Deploy completo na AWS produção |

---

> Criado em: 2026-03-26
> Última atualização: 2026-03-27
