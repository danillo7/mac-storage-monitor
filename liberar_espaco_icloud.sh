#!/bin/bash
# =============================================================================
# LIBERAR ESPAÇO DO ICLOUD - SCRIPT DE EMERGÊNCIA
# =============================================================================
# Este script remove downloads locais do iCloud, mantendo arquivos na nuvem
# Autor: Claude Code para Dr. Danillo Costa
# Data: 2026-01-03
# =============================================================================

set -e

ICLOUD_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
LOG_FILE="/tmp/icloud_evict_$(date +%Y%m%d_%H%M%S).log"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   LIBERADOR DE ESPAÇO ICLOUD${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Verificar espaço atual
echo -e "${YELLOW}📊 Espaço atual no disco:${NC}"
df -h / | tail -1 | awk '{printf "   Total: %s | Usado: %s | Livre: %s | Uso: %s\n", $2, $3, $4, $5}'
echo ""

# Calcular espaço do iCloud local
echo -e "${YELLOW}📁 Analisando iCloud local...${NC}"
ICLOUD_SIZE=$(du -sh "$ICLOUD_DIR" 2>/dev/null | cut -f1)
echo -e "   Tamanho atual do iCloud local: ${RED}$ICLOUD_SIZE${NC}"
echo ""

# Listar pastas grandes
echo -e "${YELLOW}📂 Maiores pastas no iCloud:${NC}"
for d in "$ICLOUD_DIR"/*; do
    if [ -d "$d" ]; then
        size=$(du -sh "$d" 2>/dev/null | cut -f1)
        name=$(basename "$d")
        echo "   $size - $name"
    fi
done | sort -hr | head -10
echo ""

# Menu de opções
echo -e "${YELLOW}Escolha uma opção:${NC}"
echo "  1) Liberar TUDO (remover todos downloads locais)"
echo "  2) Liberar apenas pasta 40-CONHECIMENTO (cursos/livros)"
echo "  3) Liberar apenas pasta 80-ARQUIVO-GERAL"
echo "  4) Liberar pasta específica"
echo "  5) Ver preview sem executar"
echo "  6) Cancelar"
echo ""
read -p "Opção [1-6]: " opcao

case $opcao in
    1)
        echo -e "${RED}⚠️  Isso vai remover TODOS os downloads locais do iCloud!${NC}"
        echo -e "${GREEN}✅ Os arquivos continuarão na nuvem e podem ser baixados quando necessário.${NC}"
        read -p "Confirma? (s/N): " confirma
        if [[ "$confirma" =~ ^[Ss]$ ]]; then
            echo -e "${BLUE}🚀 Iniciando liberação de espaço...${NC}"
            echo "Log em: $LOG_FILE"
            find "$ICLOUD_DIR" -type f ! -name "*.icloud" -print0 2>/dev/null | while IFS= read -r -d '' file; do
                echo "Liberando: $file" >> "$LOG_FILE"
                brctl evict "$file" 2>/dev/null || true
            done
            echo -e "${GREEN}✅ Concluído! Verifique o espaço livre.${NC}"
        fi
        ;;
    2)
        PASTA="$ICLOUD_DIR/40-CONHECIMENTO"
        echo -e "${YELLOW}Liberando pasta: $PASTA${NC}"
        read -p "Confirma? (s/N): " confirma
        if [[ "$confirma" =~ ^[Ss]$ ]]; then
            find "$PASTA" -type f ! -name "*.icloud" -print0 2>/dev/null | while IFS= read -r -d '' file; do
                echo "Liberando: $file" >> "$LOG_FILE"
                brctl evict "$file" 2>/dev/null || true
            done
            echo -e "${GREEN}✅ Concluído!${NC}"
        fi
        ;;
    3)
        PASTA="$ICLOUD_DIR/80-ARQUIVO-GERAL"
        echo -e "${YELLOW}Liberando pasta: $PASTA${NC}"
        read -p "Confirma? (s/N): " confirma
        if [[ "$confirma" =~ ^[Ss]$ ]]; then
            find "$PASTA" -type f ! -name "*.icloud" -print0 2>/dev/null | while IFS= read -r -d '' file; do
                echo "Liberando: $file" >> "$LOG_FILE"
                brctl evict "$file" 2>/dev/null || true
            done
            echo -e "${GREEN}✅ Concluído!${NC}"
        fi
        ;;
    4)
        echo "Pastas disponíveis:"
        ls -1 "$ICLOUD_DIR"
        echo ""
        read -p "Nome da pasta: " pasta_nome
        PASTA="$ICLOUD_DIR/$pasta_nome"
        if [ -d "$PASTA" ]; then
            SIZE=$(du -sh "$PASTA" 2>/dev/null | cut -f1)
            echo -e "Tamanho: ${RED}$SIZE${NC}"
            read -p "Confirma liberação? (s/N): " confirma
            if [[ "$confirma" =~ ^[Ss]$ ]]; then
                find "$PASTA" -type f ! -name "*.icloud" -print0 2>/dev/null | while IFS= read -r -d '' file; do
                    brctl evict "$file" 2>/dev/null || true
                done
                echo -e "${GREEN}✅ Concluído!${NC}"
            fi
        else
            echo -e "${RED}Pasta não encontrada!${NC}"
        fi
        ;;
    5)
        echo -e "${BLUE}Preview - Arquivos que seriam liberados:${NC}"
        find "$ICLOUD_DIR" -type f ! -name "*.icloud" 2>/dev/null | wc -l | xargs -I {} echo "Total de arquivos: {}"
        echo ""
        echo "Tamanho por extensão:"
        find "$ICLOUD_DIR" -type f ! -name "*.icloud" 2>/dev/null -exec basename {} \; | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15
        ;;
    6)
        echo "Cancelado."
        exit 0
        ;;
    *)
        echo -e "${RED}Opção inválida!${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${YELLOW}📊 Espaço após liberação:${NC}"
df -h / | tail -1 | awk '{printf "   Total: %s | Usado: %s | Livre: %s | Uso: %s\n", $2, $3, $4, $5}'
