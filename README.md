# 🖥️ Mac Storage Monitor

Sistema de monitoramento inteligente de armazenamento para macOS.

## 🚀 Instalação Rápida

```bash
cd ~/Developer/mac-storage-monitor
chmod +x start.sh liberar_espaco_icloud.sh
./start.sh
```

## 📊 Dashboard Web

Acesse: **http://localhost:8080**

### Funcionalidades:
- ✅ Monitoramento em tempo real do disco
- ✅ Análise detalhada do iCloud Drive
- ✅ Identificação de arquivos grandes
- ✅ Recomendações automáticas
- ✅ Ações rápidas (liberar iCloud, limpar caches)

## 🆘 Liberação de Emergência

Se seu disco estiver cheio, execute:

```bash
./liberar_espaco_icloud.sh
```

### Opções:
1. Liberar TODO o iCloud local
2. Liberar apenas cursos/livros (40-CONHECIMENTO)
3. Liberar apenas arquivos gerais (80-ARQUIVO-GERAL)
4. Escolher pasta específica

## 🔧 API Endpoints

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/status` | Status rápido do disco |
| `GET /api/full-analysis` | Análise completa |
| `GET /api/icloud` | Análise do iCloud |
| `GET /api/large-files` | Arquivos grandes |
| `GET /api/recommendations` | Recomendações |
| `POST /api/evict-icloud` | Liberar espaço iCloud |
| `POST /api/clear-caches` | Limpar caches |

## ⚙️ Configuração do iCloud

Para evitar que o problema se repita:

1. Abra **Ajustes do Sistema**
2. Vá em **Apple ID** → **iCloud**
3. Clique em **iCloud Drive** → **Opções**
4. Marque ✅ **Optimize Mac Storage**

Isso faz com que arquivos antigos fiquem apenas na nuvem.

## 📝 Autor

Criado para Dr. Danillo Costa por Claude Code.
