#!/bin/bash
# =============================================================================
# MAC STORAGE MONITOR - Script de Inicialização
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
echo "🚀 Iniciando Mac Monitor Pro v2.0..."
echo "📊 Dashboard: http://localhost:8888"
echo "📊 Na rede:   http://$(ipconfig getifaddr en0 2>/dev/null || echo 'N/A'):8888"
echo ""
echo "Pressione Ctrl+C para encerrar"
echo ""

python app.py
