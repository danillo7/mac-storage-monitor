# NERD SPACE V5.0 - AI FIRST EDITION
## Plano de Implementação Completo

**Data:** 2026-01-03 | **Versão:** 4.0.0 | **Codinome:** AI FIRST

---

## ANÁLISE DOS PRINTS

### Print 1 - Monitores
- **3 Monitores detectados:**
  - DELL P2719H (2) - Esquerda
  - Odyssey G5 - Centro (Principal)
  - DELL P2719H (1) - Direita
- **Ação:** Criar representação visual SVG da disposição real

### Print 2 - Storage Incorreto
- **macOS mostra:** 354,95 GB usados
- **Site mostra:** 219,31 GB
- **Diferença:** ~135 GB
- **Causa:** Falta incluir "Dados do Sistema" (246,3 GB) que o macOS conta
- **Solução:** Usar `diskutil info` para pegar o uso REAL do disco

### Print 3 - Site Travado
- **Modal:** "Página sem resposta"
- **Causa provável:** Requests sem timeout, WebSocket bloqueando, loops infinitos
- **Processos pesados:** ApplicationsStorageExtension (80.3% CPU)
- **Solução:** Debounce, lazy loading, request queue, timeouts agressivos

---

## FASE 1: CORREÇÕES CRÍTICAS (BUGS)

### 1.1 Storage Incorreto
```
ATUAL: du -sk /Users/* (só conta arquivos do usuário)
NOVO: diskutil info / | grep "Used" → pega uso REAL incluindo sistema
```
- Usar `df -h /` para espaço total/usado/livre
- Incluir "Dados do Sistema" como categoria
- Mostrar breakdown igual ao macOS

### 1.2 Clima Não Funciona
- Endpoint atual depende de API externa que pode estar falhando
- Implementar fallback com wttr.in (gratuito, sem API key)
- Cache de 30 minutos para evitar rate limit
- Mostrar localização baseada em IP

### 1.3 Rede Não Abre
- Bug no toggleCategory() causando loop
- Adicionar debounce de 300ms
- Verificar se já está carregando antes de fazer nova request

### 1.4 Apps Sumindo/Reaparecendo
- Cache de apps muito curto (provavelmente 10s)
- Aumentar cache para 5 minutos (apps não mudam frequentemente)
- Adicionar loading skeleton enquanto carrega

### 1.5 Site Travando
- Implementar Request Queue (máximo 3 requests simultâneas)
- Abort Controller com timeout de 5s
- Lazy loading para seções não visíveis

---

## FASE 2: AI FIRST FEATURES

### 2.1 Insights Inteligentes Proativos
- **Análise preditiva:** "Seu disco ficará cheio em ~15 dias no ritmo atual"
- **Sugestões contextuais:** "Você tem 12GB em Downloads com mais de 30 dias"
- **Alertas inteligentes:** "CPU alta detectada - ApplicationsStorageExtension pode ser fechado"
- **Dicas personalizadas:** Baseadas no uso real do sistema

### 2.2 AI Assistant Embarcado
- Chat flutuante para perguntas rápidas
- Comandos naturais: "Libere espaço no disco", "Por que está lento?"
- Execução de ações com confirmação

### 2.3 Histórico Compacto (SQLite)
- Banco SQLite local (~1KB por registro)
- Agregação automática: dados por hora → dia → semana → mês
- Retenção: 7 dias detalhado, 30 dias agregado, 1 ano resumido
- Gráficos de tendência para CPU, RAM, Disco, Rede

### 2.4 Anomaly Detection
- Baseline de uso normal calculado automaticamente
- Alertas quando métricas fogem do padrão
- Correlação: "CPU alta começou junto com processo X"

---

## FASE 3: PREMIUM UI/UX

### 3.1 Menu Sticky (Acompanha Scroll)
```css
.nav-tabs {
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(20px);
}
```

### 3.2 Links Externos Identificados
- Ícone ↗ para links externos
- Tooltip: "Abre em nova aba"
- Cor diferenciada (azul para interno, cinza+ícone para externo)

### 3.3 Ordem dos Menus (Nova)
1. **NERD SPACE** (Primeiro - Principal)
2. **Visão Geral** (Dashboard resumido)
3. **Hardware**
4. **Storage**
5. **Processos**
6. **Rede**
7. **Bateria**
8. **Configurações**

### 3.4 macOS Version Completa
```
ATUAL: macOS 26.2
NOVO: macOS Tahoe 26.2 (Build 26C5xx)
```

### 3.5 Ordenação em Apps
- Alfabética (A-Z / Z-A)
- Por tamanho (Maior → Menor / Menor → Maior)
- Por data de modificação
- Por categoria (System, User, Developer)
- Filtro de busca

### 3.6 Filtros em Processos
- Por severidade: Crítico / Aviso / Normal
- Por consumo: CPU > 50%, RAM > 1GB
- Por tipo: System / User / Background
- Ação rápida: Encerrar processo (com confirmação)

---

## FASE 4: NERD SPACE TURBINADO

### 4.1 Speed Test Embedado (Sem Programas Externos)
```python
# Implementação nativa com requests/aiohttp
async def speed_test():
    # Download: baixar arquivo de servidor conhecido
    # Upload: enviar dados para servidor
    # Latência: ping para múltiplos servidores
    return {
        "download_mbps": 245.8,
        "upload_mbps": 123.4,
        "latency_ms": 12,
        "provider": "Vivo Fibra",  # via IP lookup
        "location": "São Paulo, BR",
        "timestamp": "2026-01-03 18:45:00",
        "server": "speedtest-sp.vivo.com.br"
    }
```
- Teste automático ao abrir o site
- Histórico dos últimos 10 testes
- Gráfico de evolução

### 4.2 Monitores - Visual Real
```
┌─────────────┐  ┌─────────────────────┐  ┌─────────────┐
│             │  │                     │  │             │
│ DELL P2719H │  │    Odyssey G5       │  │ DELL P2719H │
│    (2)      │  │     (Principal)     │  │    (1)      │
│  1920x1080  │  │     2560x1440       │  │  1920x1080  │
│    60Hz     │  │       144Hz         │  │    60Hz     │
└─────────────┘  └─────────────────────┘  └─────────────┘
```
- SVG interativo com escala proporcional
- Click para ver detalhes de cada monitor
- Indicador de monitor principal (★)

### 4.3 Quick Links (Ferramentas Dev)
| App | Atalho | Ação |
|-----|--------|------|
| Terminal | ⌘T | Abre Terminal.app |
| Warp | ⌘W | Abre Warp.app |
| Claude Code | ⌘C | Abre no Terminal |
| Gemini CLI | ⌘G | Abre no Terminal |
| VS Code | ⌘V | Abre VS Code |
| GitHub | ⌘H | Abre github.com |
| Comet | ⌘O | Abre Comet.app |
| Python REPL | ⌘P | python3 no Terminal |
| Node REPL | ⌘N | node no Terminal |

### 4.4 System Info Expandido
- **macOS:** Tahoe 26.2 (Build 26C5xx)
- **Uptime:** 3 dias, 14 horas
- **Last Boot:** 2026-01-01 04:32:15
- **Kernel:** Darwin 26.2.0
- **Shell:** zsh 5.9
- **Homebrew:** 4.2.0 (45 packages)
- **Python:** 3.14.0
- **Node:** 22.0.0

---

## FASE 5: DADOS CORRETOS

### 5.1 Storage Real (Como o macOS Calcula)
```python
def get_storage_real():
    # Usar diskutil para dados REAIS
    total = run_cmd("diskutil info / | grep 'Container Total' | awk '{print $4}'")
    used = run_cmd("diskutil info / | grep 'Container Used' | awk '{print $4}'")

    # Categorias como o macOS
    categories = {
        "Aplicativos": get_apps_size(),      # /Applications + ~/Applications
        "Documentos": get_docs_size(),        # ~/Documents
        "Desenvolvedor": get_dev_size(),      # ~/Developer + Xcode
        "Fotos": get_photos_size(),           # ~/Pictures + Photos Library
        "iCloud Drive": get_icloud_size(),    # ~/Library/Mobile Documents
        "Mensagens": get_messages_size(),     # ~/Library/Messages
        "macOS": get_macos_size(),            # /System
        "Dados do Sistema": calculated,       # Total - soma das categorias
        "Outros Usuários": get_other_users(), # /Users (exceto current)
    }
    return categories
```

### 5.2 Provedor de Internet via IP
```python
def get_isp_info():
    # Via ipinfo.io (gratuito até 50k/mês)
    data = requests.get("https://ipinfo.io/json").json()
    return {
        "ip": data["ip"],
        "city": data["city"],
        "region": data["region"],
        "country": data["country"],
        "isp": data["org"],  # "AS18881 Vivo"
        "provider_name": "Vivo Fibra"  # Parsed
    }
```

---

## FASE 6: PERFORMANCE & ESTABILIDADE

### 6.1 Request Queue System
```javascript
class RequestQueue {
    constructor(maxConcurrent = 3) {
        this.queue = [];
        this.running = 0;
        this.maxConcurrent = maxConcurrent;
    }

    async add(request) {
        if (this.running >= this.maxConcurrent) {
            await new Promise(resolve => this.queue.push(resolve));
        }
        this.running++;
        try {
            return await request();
        } finally {
            this.running--;
            if (this.queue.length > 0) {
                this.queue.shift()();
            }
        }
    }
}
```

### 6.2 Debounce para Clicks
```javascript
function debounce(func, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Uso
const toggleCategoryDebounced = debounce(toggleCategory, 300);
```

### 6.3 Cache Inteligente por Tipo
| Dado | TTL | Justificativa |
|------|-----|---------------|
| Hardware | 5 min | Não muda |
| macOS Version | 1 hora | Só muda com update |
| Apps | 5 min | Raramente muda |
| Storage | 1 min | Pode mudar |
| Processos | 5 seg | Muda frequentemente |
| Rede | 15 seg | Muda frequentemente |
| Clima | 30 min | API rate limit |
| Speed Test | Manual | Sob demanda |

---

## FASE 7: MICROINTERAÇÕES PREMIUM

### 7.1 Animações
- Cards com hover lift (translateY -2px + shadow)
- Transições suaves (300ms ease-out)
- Loading skeletons em vez de spinners
- Progress bars animadas
- Números com contagem animada

### 7.2 Feedback Visual
- Toast notifications para ações
- Shake animation para erros
- Pulse para alertas críticos
- Checkmark animation para sucesso

### 7.3 Acessibilidade
- Contraste WCAG AAA
- Focus indicators visíveis
- Keyboard navigation completa
- Screen reader friendly
- Reduced motion support

---

## ARQUITETURA FINAL

```
mac-storage-monitor/
├── app.py                    # FastAPI principal
├── services/
│   ├── ai_insights.py        # Motor de insights AI
│   ├── speed_test.py         # Speed test nativo
│   ├── history_db.py         # SQLite para histórico
│   └── system_info.py        # Coleta de dados do sistema
├── static/
│   ├── app.js                # Frontend JS
│   └── styles.css            # CSS customizado
├── data/
│   └── history.db            # SQLite compacto
└── templates/
    └── dashboard.html        # Template HTML
```

---

## ESTIMATIVA DE TAMANHO

| Componente | Tamanho |
|------------|---------|
| app.py (atualizado) | ~150 KB |
| history.db (1 mês) | ~500 KB |
| Total instalação | < 1 MB |

---

## RESUMO EXECUTIVO

### Correções Imediatas (BUGS)
1. ✅ Storage: usar `diskutil` para dados reais
2. ✅ Clima: fallback para wttr.in
3. ✅ Rede: debounce + timeout
4. ✅ Apps: cache de 5 min
5. ✅ Site travando: request queue + abort controller

### Melhorias AI FIRST
1. ✅ Insights preditivos e proativos
2. ✅ Histórico compacto em SQLite
3. ✅ Anomaly detection
4. ✅ Sugestões contextuais

### Premium UI/UX
1. ✅ Menu sticky (acompanha scroll)
2. ✅ Links externos identificados com ↗
3. ✅ NERD SPACE como primeiro menu
4. ✅ macOS Tahoe 26.2 completo
5. ✅ Ordenação em Apps
6. ✅ Filtros em Processos
7. ✅ Monitores com layout visual real
8. ✅ Speed test embedado
9. ✅ Quick links para ferramentas dev

---

## APROVAÇÃO

**Aguardando aprovação para iniciar implementação.**

- [ ] Aprovado para execução
- [ ] Modificações necessárias: ________________

---

*Plano criado por: Equipe 360° (Arquiteto, UX Designer, Backend Engineer, Frontend Engineer, QA, Security)*
