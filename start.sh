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
echo "🚀 Iniciando Mac Storage Monitor..."
echo "📊 Dashboard: http://localhost:8080"
echo ""
echo "Pressione Ctrl+C para encerrar"
echo ""

python app.py
