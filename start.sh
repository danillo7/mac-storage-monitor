#!/bin/bash
# =============================================================================
# NERD SPACE V5.0 - Script de Inicialização
# =============================================================================

cd "$(dirname "$0")"

# Verificar/criar ambiente virtual
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativar ambiente
source .venv/bin/activate

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -q -r requirements.txt

# Iniciar servidor
echo ""
echo "🚀 Iniciando NERD SPACE V5.0..."
echo "════════════════════════════════════════════════════════════"
echo "📊 LOCAL:      http://localhost:8888"
echo "📊 REDE LOCAL: http://$(ipconfig getifaddr en0 2>/dev/null || echo 'N/A'):8888"
echo ""
echo "🔗 LINK ÚNICO (Tailscale - acesso de qualquer lugar):"
echo "   http://macbook-pro-de-danillo.tail556dd0.ts.net:8888"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Pressione Ctrl+C para encerrar"
echo ""

python app.py
