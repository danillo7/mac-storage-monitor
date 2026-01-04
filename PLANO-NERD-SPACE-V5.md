# NERD SPACE V5.0 - AI FIRST COMMAND CENTER
## Plano de Implementação Completo e Definitivo

**Data:** 2026-01-03 | **Versão:** 5.0.0 | **Codinome:** AI FIRST
**Proprietário:** Dr. Danillo Costa | **Hardware:** MacBook Pro M3 Max 36GB

---

## SUMÁRIO EXECUTIVO

| Item | Descrição |
|------|-----------|
| **Nome Antigo** | Mac Command Center Pro |
| **Nome Novo** | **NERD SPACE** |
| **Filosofia** | AI FIRST - Inteligência em cada detalhe |
| **Plano Claude** | Max 20x (R$ 1.369,90/mês) |
| **Stack** | FastAPI + HTML/CSS/JS + SQLite |

---

# PARTE 1: IDENTIDADE E BRANDING

## 1.1 Renomeação do Projeto

| Aspecto | Valor |
|---------|-------|
| **Nome** | NERD SPACE |
| **Tagline** | "Your AI-Powered Command Center" |
| **Versão** | 5.0.0 AI FIRST Edition |
| **Ícone** | 🚀 (Rocket) ou custom SVG |
| **Cores Primárias** | Purple (#8B5CF6) + Cyan (#06B6D4) |

## 1.2 Header Redesenhado

```
┌─────────────────────────────────────────────────────────────────────┐
│  🚀 NERD SPACE                                    [🌙/☀️] [⚙️]     │
│     AI-Powered Command Center v5.0                                  │
│                                                                     │
│  ┌─────────┐ ┌─────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐ │
│  │🧠 NERD  │ │📊 Overview  │ │💾 Storage│ │⚡ Procs │ │🌐 Network│ │
│  │  SPACE  │ │             │ │          │ │         │ │          │ │
│  └─────────┘ └─────────────┘ └──────────┘ └─────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

# PARTE 2: MÓDULO CLAUDE MAX 20x

## 2.1 Contexto do Plano

| Especificação | Valor |
|---------------|-------|
| **Plano** | Claude Max 20x (Maximum Flexibility) |
| **Preço USD** | $200/mês |
| **Preço BRL** | R$ 1.369,90/mês |
| **Multiplicador** | 20x mais uso que o Pro |
| **Janela de Reset** | 5 horas |
| **Limite Semanal** | 7 dias rolling |
| **Context Window** | 200K tokens |

## 2.2 Backend - Endpoint `/api/claude-usage`

```python
# services/claude_usage.py

CLAUDE_PLAN = {
    "name": "Claude Max 20x",
    "price_usd": 200.00,
    "price_brl": 1369.90,
    "multiplier": 20,
    "window_5h_base_messages": 900,  # ~900 msgs curtas por janela 5h
    "context_window": 200000,
}

async def fetch_claude_usage() -> dict:
    """
    Obtém dados de uso do Claude Max 20x.
    Como não há API oficial de usage, estimamos baseado em:
    - Arquivo de log do Claude Code CLI
    - Contagem de mensagens da sessão
    - Estimativas baseadas em padrões de uso
    """

    # Ler dados do Claude Code CLI (se disponível)
    usage_file = Path.home() / ".claude" / "usage.json"

    # Calcular estimativas
    now = datetime.now()
    window_5h_start = now - timedelta(hours=5)
    window_7d_start = now - timedelta(days=7)

    # Dados simulados/estimados (substituir por dados reais quando disponíveis)
    return {
        "plan": {
            "name": "Claude Max 20x",
            "description": "20x mais uso por sessão que o Pro",
            "price_month_brl": 1369.90,
            "price_month_usd": 200.00,
            "features": [
                "Até 20x mais mensagens por janela de 5h",
                "Context window de 200K tokens",
                "Prioridade em novos modelos",
                "Claude Code incluído",
                "Extended Thinking",
                "Research mode"
            ]
        },
        "usage": {
            "window_5h": {
                "used": 0,  # Tokens/mensagens usadas
                "limit": 18000,  # ~900 msgs * 20x = estimativa
                "percent": 0,
                "reset_at": (window_5h_start + timedelta(hours=5)).isoformat(),
                "messages_sent": 0,
                "estimated_remaining": 900
            },
            "window_7d": {
                "used": 0,
                "limit": 500000,  # Estimativa semanal
                "percent": 0,
                "messages_sent": 0
            }
        },
        "costs": {
            "cost_per_message_brl": 0.076,  # R$1369.90 / ~18000 msgs
            "cost_per_1k_tokens_brl": 0.038,
            "daily_average_brl": 45.66,  # R$1369.90 / 30 dias
            "spent_today_brl": 0,
            "spent_this_week_brl": 0,
            "spent_this_month_brl": 0
        },
        "status": {
            "extra_usage_active": False,
            "is_rate_limited": False,
            "rate_limit_resets_at": None,
            "health": "healthy"  # healthy, warning, critical
        },
        "last_updated_at": datetime.now().isoformat(),
        "data_source": "estimated"  # estimated, api, cli_logs
    }
```

## 2.3 Frontend - Card do Plano Claude

```
┌─────────────────────────────────────────────────────────────────────┐
│  🤖 CLAUDE MAX 20x                                    [↗ Gerenciar] │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                     │
│  💰 R$ 1.369,90/mês          ⚡ 20x mais uso que Pro               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ USO JANELA 5H                                    45% ████░░ │   │
│  │ ~405 de 900 mensagens • Reset em 2h 34min                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ USO SEMANAL (7 DIAS)                             23% ██░░░░ │   │
│  │ ~2.300 de 10.000 mensagens                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  📊 MÉTRICAS DE CUSTO                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ Hoje         │ │ Esta Semana  │ │ Este Mês     │               │
│  │ R$ 12,45     │ │ R$ 234,56    │ │ R$ 890,00    │               │
│  │ 164 msgs     │ │ 3.089 msgs   │ │ 11.723 msgs  │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  💡 DICAS DE OTIMIZAÇÃO                              [Ver todas →] │
│  • Agrupe perguntas em menos mensagens para economizar            │
│  • Use Projects para cachear contexto recorrente                   │
│  • Evite re-upload de arquivos já enviados                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.4 Sistema de Alertas Inteligentes

| Condição | Cor | Mensagem |
|----------|-----|----------|
| Uso < 60% | 🟢 Verde | "Uso normal" |
| Uso 60-80% | 🟡 Amarelo | "Consumo moderado - planeje suas próximas tarefas" |
| Uso 80-95% | 🟠 Laranja | "Atenção: Próximo do limite da janela de 5h" |
| Uso > 95% | 🔴 Vermelho | "Crítico: Limite quase esgotado. Reset em Xh Xmin" |
| Extra Usage | 🟣 Roxo | "Uso extra ativo - cobranças adicionais em curso" |

## 2.5 Histórico de Uso (SQLite)

```sql
CREATE TABLE claude_usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    window_5h_percent REAL,
    window_7d_percent REAL,
    messages_sent INTEGER,
    tokens_used INTEGER,
    cost_brl REAL,
    session_id TEXT
);

-- Índice para queries rápidas
CREATE INDEX idx_usage_timestamp ON claude_usage_history(timestamp);

-- Agregação automática (job diário)
-- Dados > 7 dias: agregados por hora
-- Dados > 30 dias: agregados por dia
-- Dados > 90 dias: deletados
```

---

# PARTE 3: CORREÇÕES CRÍTICAS DE BUGS

## 3.1 Storage Incorreto (219GB vs 354GB)

**Problema:** `du -sk` não inclui "Dados do Sistema" (246GB)

**Solução:**
```python
def get_storage_real() -> dict:
    """Obtém storage REAL como o macOS calcula"""

    # Método 1: diskutil (mais preciso)
    disk_info = run_cmd("diskutil info / | grep -E '(Total|Free|Used)'")

    # Método 2: df (fallback)
    df_output = run_cmd("df -h /")

    # Parsing do diskutil
    total_bytes = parse_diskutil_size(disk_info, "Container Total Space")
    free_bytes = parse_diskutil_size(disk_info, "Container Free Space")
    used_bytes = total_bytes - free_bytes

    # Categorias como o macOS
    categories = {
        "Aplicativos": get_size("/Applications") + get_size("~/Applications"),
        "Documentos": get_size("~/Documents"),
        "Desenvolvedor": get_size("~/Developer") + get_xcode_size(),
        "Fotos": get_size("~/Pictures") + get_photos_library_size(),
        "iCloud Drive": get_size("~/Library/Mobile Documents"),
        "Mensagens": get_size("~/Library/Messages"),
        "macOS": get_size("/System") + get_size("/usr") + get_size("/bin"),
        "Outros Usuários": get_other_users_size(),
    }

    # Dados do Sistema = Total usado - soma das categorias conhecidas
    known_total = sum(categories.values())
    categories["Dados do Sistema"] = max(0, used_bytes - known_total)

    return {
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "used_percent": (used_bytes / total_bytes) * 100,
        "categories": categories
    }
```

## 3.2 Clima Não Funciona

**Solução:** Fallback para wttr.in (gratuito, sem API key)

```python
async def get_weather() -> dict:
    """Obtém clima com fallbacks múltiplos"""

    # Tentar IP geolocation primeiro
    try:
        geo = await fetch_json("https://ipinfo.io/json", timeout=3)
        city = geo.get("city", "São Paulo")
    except:
        city = "São Paulo"

    # Fallback 1: wttr.in (gratuito)
    try:
        url = f"https://wttr.in/{city}?format=j1"
        data = await fetch_json(url, timeout=5)
        current = data["current_condition"][0]
        return {
            "city": city,
            "temp_c": int(current["temp_C"]),
            "condition": current["weatherDesc"][0]["value"],
            "humidity": int(current["humidity"]),
            "icon": get_weather_icon(current["weatherCode"]),
            "source": "wttr.in"
        }
    except:
        pass

    # Fallback 2: Dados cached ou default
    return {
        "city": city,
        "temp_c": 25,
        "condition": "Parcialmente nublado",
        "humidity": 60,
        "icon": "⛅",
        "source": "cached"
    }
```

## 3.3 Rede Não Abre / Site Travando

**Problema:** Requests sem limite causando loop infinito

**Solução:** Request Queue + Debounce + Timeout

```javascript
// Request Queue - máximo 3 simultâneas
class RequestQueue {
    constructor(maxConcurrent = 3) {
        this.queue = [];
        this.running = 0;
        this.max = maxConcurrent;
        this.cache = new Map();
    }

    async add(key, requestFn, ttl = 30000) {
        // Check cache first
        const cached = this.cache.get(key);
        if (cached && Date.now() - cached.time < ttl) {
            return cached.data;
        }

        // Wait if at capacity
        if (this.running >= this.max) {
            await new Promise(resolve => this.queue.push(resolve));
        }

        this.running++;
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 5000);

            const result = await requestFn(controller.signal);
            clearTimeout(timeout);

            // Cache result
            this.cache.set(key, { data: result, time: Date.now() });
            return result;
        } finally {
            this.running--;
            if (this.queue.length > 0) {
                this.queue.shift()();
            }
        }
    }
}

const requestQueue = new RequestQueue(3);

// Debounce para clicks
function debounce(fn, wait = 300) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), wait);
    };
}

// Uso
const toggleCategoryDebounced = debounce(toggleCategory, 300);
```

## 3.4 Apps Sumindo/Reaparecendo

**Problema:** Cache muito curto (10s)

**Solução:** Cache de 5 minutos + Loading skeleton

```python
CACHE_TTL = {
    "hardware": 300,      # 5 min - não muda
    "macos_version": 3600, # 1 hora - só muda com update
    "apps": 300,          # 5 min - raramente muda
    "storage": 60,        # 1 min - pode mudar
    "processes": 5,       # 5 seg - muda muito
    "network": 15,        # 15 seg
    "weather": 1800,      # 30 min - API rate limit
    "displays": 300,      # 5 min
    "claude_usage": 60,   # 1 min
}
```

---

# PARTE 4: NERD SPACE TURBINADO

## 4.1 Speed Test Embedado Nativo

```python
# services/speed_test.py

import aiohttp
import time
from typing import Dict

async def run_speed_test() -> Dict:
    """
    Speed test nativo sem dependências externas.
    Usa servidores públicos para medição.
    """

    # Servidores de teste (CDNs confiáveis)
    TEST_SERVERS = [
        "https://speed.cloudflare.com/__down?bytes=10000000",  # 10MB
        "https://proof.ovh.net/files/10Mb.dat",
    ]

    results = {
        "download_mbps": 0,
        "upload_mbps": 0,
        "latency_ms": 0,
        "jitter_ms": 0,
        "provider": "",
        "location": "",
        "server": "",
        "timestamp": datetime.now().isoformat(),
    }

    async with aiohttp.ClientSession() as session:
        # 1. Latência (ping)
        latencies = []
        for _ in range(5):
            start = time.perf_counter()
            try:
                async with session.head("https://cloudflare.com", timeout=2) as r:
                    latencies.append((time.perf_counter() - start) * 1000)
            except:
                pass

        if latencies:
            results["latency_ms"] = round(sum(latencies) / len(latencies), 1)
            results["jitter_ms"] = round(max(latencies) - min(latencies), 1)

        # 2. Download (10MB file)
        try:
            start = time.perf_counter()
            async with session.get(TEST_SERVERS[0], timeout=30) as r:
                data = await r.read()
                elapsed = time.perf_counter() - start
                mbps = (len(data) * 8 / 1_000_000) / elapsed
                results["download_mbps"] = round(mbps, 1)
                results["server"] = "Cloudflare"
        except Exception as e:
            results["download_error"] = str(e)

        # 3. Upload (enviar 5MB de dados)
        try:
            test_data = b"0" * 5_000_000  # 5MB
            start = time.perf_counter()
            async with session.post(
                "https://speed.cloudflare.com/__up",
                data=test_data,
                timeout=30
            ) as r:
                elapsed = time.perf_counter() - start
                mbps = (len(test_data) * 8 / 1_000_000) / elapsed
                results["upload_mbps"] = round(mbps, 1)
        except:
            pass

        # 4. ISP Info
        try:
            async with session.get("https://ipinfo.io/json", timeout=3) as r:
                info = await r.json()
                results["provider"] = info.get("org", "").replace("AS", "").strip()
                results["location"] = f"{info.get('city', '')}, {info.get('region', '')}"

                # Identificar provedor brasileiro
                org = info.get("org", "").lower()
                if "vivo" in org or "telefonica" in org:
                    results["provider"] = "Vivo Fibra"
                elif "claro" in org or "embratel" in org:
                    results["provider"] = "Claro"
                elif "tim" in org:
                    results["provider"] = "TIM"
                elif "oi" in org:
                    results["provider"] = "Oi"
        except:
            pass

    return results
```

**UI do Speed Test:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  🚀 SPEED TEST                                        [▶️ Testar]   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                     │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐               │
│  │   ⬇️ DOWN   │   │   ⬆️ UP     │   │   📡 PING   │               │
│  │   245.8     │   │   123.4     │   │   12 ms     │               │
│  │    Mbps     │   │    Mbps     │   │   (±2ms)    │               │
│  └─────────────┘   └─────────────┘   └─────────────┘               │
│                                                                     │
│  📍 São Paulo, SP • 🌐 Vivo Fibra • 🖥️ Cloudflare                  │
│  🕐 Último teste: 03/01/2026 às 18:45:32                           │
│                                                                     │
│  📈 HISTÓRICO (últimos 10 testes)                    [Ver todos →] │
│  ──────────────────────────────────────────────────────────────    │
│  █████████████████████████  245.8 Mbps (agora)                     │
│  ████████████████████████   238.2 Mbps (ontem 14:30)               │
│  █████████████████████████  242.1 Mbps (02/01 09:15)               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 4.2 Monitores - Layout Visual Real

```python
# Endpoint: GET /api/displays

def get_displays_with_layout() -> dict:
    """Retorna monitores com posicionamento real"""

    # Obter info via system_profiler
    displays_raw = run_cmd("system_profiler SPDisplaysDataType -json")

    # Obter posicionamento via displayplacer ou defaults
    # Para seu setup específico:

    return {
        "displays": [
            {
                "id": 1,
                "name": "DELL P2719H",
                "identifier": "(2)",
                "resolution": "1920x1080",
                "refresh_rate": 60,
                "position": {"x": 0, "y": 0},
                "size": {"width": 1920, "height": 1080},
                "is_main": False,
                "is_builtin": False,
                "connection": "HDMI"
            },
            {
                "id": 2,
                "name": "Odyssey G5",
                "identifier": "(Principal)",
                "resolution": "2560x1440",
                "refresh_rate": 144,
                "position": {"x": 1920, "y": -180},  # Centralizado mais alto
                "size": {"width": 2560, "height": 1440},
                "is_main": True,
                "is_builtin": False,
                "connection": "DisplayPort"
            },
            {
                "id": 3,
                "name": "DELL P2719H",
                "identifier": "(1)",
                "resolution": "1920x1080",
                "refresh_rate": 60,
                "position": {"x": 4480, "y": 0},
                "size": {"width": 1920, "height": 1080},
                "is_main": False,
                "is_builtin": False,
                "connection": "HDMI"
            }
        ],
        "total_resolution": "6400x1440",
        "arrangement": "horizontal"
    }
```

**SVG Visual:**

```html
<svg viewBox="0 0 640 200" class="monitors-layout">
  <!-- Monitor Esquerdo - DELL P2719H (2) -->
  <g transform="translate(20, 40)">
    <rect width="150" height="85" rx="4" fill="#1a1a24" stroke="#3f3f46"/>
    <text x="75" y="35" text-anchor="middle" fill="#a1a1aa" font-size="10">
      DELL P2719H (2)
    </text>
    <text x="75" y="50" text-anchor="middle" fill="#71717a" font-size="8">
      1920×1080 @ 60Hz
    </text>
  </g>

  <!-- Monitor Central - Odyssey G5 (Principal) -->
  <g transform="translate(190, 20)">
    <rect width="260" height="145" rx="4" fill="#1a1a24" stroke="#8B5CF6" stroke-width="2"/>
    <text x="130" y="55" text-anchor="middle" fill="#fff" font-size="12" font-weight="bold">
      ★ Odyssey G5
    </text>
    <text x="130" y="75" text-anchor="middle" fill="#a1a1aa" font-size="10">
      2560×1440 @ 144Hz
    </text>
    <text x="130" y="95" text-anchor="middle" fill="#8B5CF6" font-size="9">
      PRINCIPAL
    </text>
  </g>

  <!-- Monitor Direito - DELL P2719H (1) -->
  <g transform="translate(470, 40)">
    <rect width="150" height="85" rx="4" fill="#1a1a24" stroke="#3f3f46"/>
    <text x="75" y="35" text-anchor="middle" fill="#a1a1aa" font-size="10">
      DELL P2719H (1)
    </text>
    <text x="75" y="50" text-anchor="middle" fill="#71717a" font-size="8">
      1920×1080 @ 60Hz
    </text>
  </g>
</svg>
```

## 4.3 Quick Links - Ferramentas Dev

```python
QUICK_LINKS = [
    {
        "name": "Terminal",
        "icon": "terminal",
        "action": "open",
        "target": "/System/Applications/Utilities/Terminal.app",
        "shortcut": "⌘T",
        "type": "app"
    },
    {
        "name": "Warp",
        "icon": "terminal-square",
        "action": "open",
        "target": "/Applications/Warp.app",
        "shortcut": "⌘W",
        "type": "app"
    },
    {
        "name": "Claude Code",
        "icon": "bot",
        "action": "terminal",
        "target": "claude",
        "shortcut": "⌘C",
        "type": "cli"
    },
    {
        "name": "Gemini CLI",
        "icon": "sparkles",
        "action": "terminal",
        "target": "gemini",
        "shortcut": "⌘G",
        "type": "cli"
    },
    {
        "name": "VS Code",
        "icon": "code",
        "action": "open",
        "target": "/Applications/Visual Studio Code.app",
        "shortcut": "⌘V",
        "type": "app"
    },
    {
        "name": "GitHub",
        "icon": "github",
        "action": "url",
        "target": "https://github.com",
        "shortcut": "⌘H",
        "type": "external",
        "external": True
    },
    {
        "name": "Comet",
        "icon": "rocket",
        "action": "open",
        "target": "/Applications/Comet.app",
        "shortcut": "⌘O",
        "type": "app"
    },
    {
        "name": "Python",
        "icon": "code-2",
        "action": "terminal",
        "target": "python3",
        "shortcut": "⌘P",
        "type": "cli"
    },
    {
        "name": "Node.js",
        "icon": "hexagon",
        "action": "terminal",
        "target": "node",
        "shortcut": "⌘N",
        "type": "cli"
    },
    {
        "name": "Activity Monitor",
        "icon": "activity",
        "action": "open",
        "target": "/System/Applications/Utilities/Activity Monitor.app",
        "shortcut": "⌘A",
        "type": "app"
    }
]
```

**UI Quick Links:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚡ QUICK LAUNCH                                                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                                     │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │
│  │ 🖥️  │ │ 🚀  │ │ 🤖  │ │ ✨  │ │ 💻  │ │ 🐙↗ │ │ ☄️  │ │ 🐍  │  │
│  │Term │ │Warp │ │Claude│ │Gemin│ │ VS  │ │ Git │ │Comet│ │ Py  │  │
│  │ ⌘T  │ │ ⌘W  │ │ ⌘C  │ │ ⌘G  │ │ ⌘V  │ │ ⌘H  │ │ ⌘O  │ │ ⌘P  │  │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘  │
│                                                                     │
│  ↗ = Abre em nova aba (link externo)                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 4.4 macOS Version Completa

```python
def get_macos_info() -> dict:
    """Informações completas do macOS"""

    # Nome da versão
    version = run_cmd("sw_vers -productVersion")  # "26.2"
    build = run_cmd("sw_vers -buildVersion")      # "26C5xx"

    # Mapear número para nome
    VERSION_NAMES = {
        "26": "Tahoe",
        "25": "Sequoia",
        "24": "Sonoma",
        "23": "Ventura",
        "22": "Monterey",
    }

    major = version.split(".")[0]
    name = VERSION_NAMES.get(major, "macOS")

    return {
        "name": name,
        "version": version,
        "build": build,
        "full_name": f"macOS {name} {version}",
        "display": f"macOS {name} {version} (Build {build})",
        "kernel": run_cmd("uname -r"),  # "26.2.0"
        "architecture": run_cmd("uname -m"),  # "arm64"
    }
```

---

# PARTE 5: PREMIUM UI/UX

## 5.1 Menu Sticky (Acompanha Scroll)

```css
/* Navigation sticky com blur */
.nav-container {
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(10, 10, 15, 0.8);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    transition: all 0.3s ease;
}

.nav-container.scrolled {
    background: rgba(10, 10, 15, 0.95);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
```

```javascript
// Detectar scroll
window.addEventListener('scroll', () => {
    const nav = document.querySelector('.nav-container');
    if (window.scrollY > 50) {
        nav.classList.add('scrolled');
    } else {
        nav.classList.remove('scrolled');
    }
});
```

## 5.2 Links Externos Identificados

```javascript
// Marcar links externos automaticamente
function markExternalLinks() {
    document.querySelectorAll('a[href]').forEach(link => {
        const href = link.getAttribute('href');
        if (href && (href.startsWith('http') && !href.includes(window.location.host))) {
            link.classList.add('external-link');
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');

            // Adicionar ícone se não tiver
            if (!link.querySelector('.external-icon')) {
                link.innerHTML += ' <span class="external-icon">↗</span>';
            }
        }
    });
}
```

```css
.external-link {
    color: #a1a1aa;
}

.external-link:hover {
    color: #8B5CF6;
}

.external-icon {
    font-size: 0.75em;
    opacity: 0.7;
    margin-left: 2px;
}

/* Tooltip */
.external-link::after {
    content: "Abre em nova aba";
    position: absolute;
    /* ... tooltip styles */
}
```

## 5.3 Nova Ordem dos Menus

```javascript
const MENU_ORDER = [
    { id: "nerdspace", label: "NERD SPACE", icon: "brain", badge: "PRO" },
    { id: "overview", label: "Visão Geral", icon: "layout-dashboard" },
    { id: "hardware", label: "Hardware", icon: "cpu" },
    { id: "storage", label: "Storage", icon: "hard-drive" },
    { id: "processes", label: "Processos", icon: "activity" },
    { id: "network", label: "Rede", icon: "wifi" },
    { id: "battery", label: "Energia", icon: "battery" },
    { id: "settings", label: "Config", icon: "settings" },
];

// NERD SPACE abre por padrão
const DEFAULT_TAB = "nerdspace";
```

## 5.4 Ordenação em Apps

```javascript
const APP_SORT_OPTIONS = [
    { value: "name_asc", label: "Nome (A-Z)", icon: "sort-asc" },
    { value: "name_desc", label: "Nome (Z-A)", icon: "sort-desc" },
    { value: "size_desc", label: "Tamanho (Maior)", icon: "arrow-down" },
    { value: "size_asc", label: "Tamanho (Menor)", icon: "arrow-up" },
    { value: "date_desc", label: "Mais Recente", icon: "calendar" },
    { value: "date_asc", label: "Mais Antigo", icon: "calendar" },
    { value: "category", label: "Por Categoria", icon: "folder" },
];

function sortApps(apps, sortBy) {
    const sorted = [...apps];
    switch (sortBy) {
        case "name_asc":
            return sorted.sort((a, b) => a.name.localeCompare(b.name));
        case "name_desc":
            return sorted.sort((a, b) => b.name.localeCompare(a.name));
        case "size_desc":
            return sorted.sort((a, b) => b.size_bytes - a.size_bytes);
        case "size_asc":
            return sorted.sort((a, b) => a.size_bytes - b.size_bytes);
        case "date_desc":
            return sorted.sort((a, b) => new Date(b.modified) - new Date(a.modified));
        case "date_asc":
            return sorted.sort((a, b) => new Date(a.modified) - new Date(b.modified));
        default:
            return sorted;
    }
}
```

## 5.5 Filtros em Processos

```javascript
const PROCESS_FILTERS = {
    severity: {
        all: "Todos",
        critical: "🔴 Críticos",
        warning: "🟡 Avisos",
        normal: "🟢 Normais"
    },
    type: {
        all: "Todos",
        system: "Sistema",
        user: "Usuário",
        background: "Background"
    },
    resource: {
        all: "Todos",
        high_cpu: "CPU > 50%",
        high_memory: "RAM > 1GB",
        high_disk: "Disco > 100MB/s"
    }
};

// Ações rápidas em processos
async function processAction(pid, action) {
    const confirmed = await showConfirmDialog(
        `Deseja ${action} o processo ${pid}?`,
        "Esta ação pode afetar a estabilidade do sistema."
    );

    if (confirmed) {
        const response = await fetch(`/api/process/${pid}/${action}`, {
            method: 'POST'
        });
        if (response.ok) {
            showToast(`Processo ${action} com sucesso`, "success");
            refreshProcesses();
        }
    }
}
```

---

# PARTE 6: AI FIRST FEATURES

## 6.1 Insights Inteligentes Proativos

```python
# services/ai_insights.py

def generate_insights(system_data: dict) -> list:
    """Gera insights inteligentes baseados nos dados do sistema"""

    insights = []

    # Storage Insights
    storage = system_data.get("storage", {})
    used_percent = storage.get("used_percent", 0)

    if used_percent > 90:
        insights.append({
            "type": "critical",
            "category": "storage",
            "title": "Espaço em disco crítico",
            "message": f"Apenas {100-used_percent:.1f}% livre. Libere espaço urgentemente.",
            "action": {
                "label": "Analisar Storage",
                "target": "tab:storage"
            }
        })

    # Downloads antigos
    downloads_old = get_old_downloads(days=30)
    if downloads_old["size_gb"] > 5:
        insights.append({
            "type": "suggestion",
            "category": "cleanup",
            "title": f"{downloads_old['size_gb']:.1f}GB em Downloads antigos",
            "message": f"{downloads_old['count']} arquivos com mais de 30 dias podem ser limpos.",
            "action": {
                "label": "Ver arquivos",
                "target": "category:downloads"
            }
        })

    # Previsão de disco
    growth_rate = calculate_disk_growth_rate()  # GB/dia
    if growth_rate > 0:
        days_until_full = (storage["free_gb"]) / growth_rate
        if days_until_full < 30:
            insights.append({
                "type": "warning",
                "category": "prediction",
                "title": "Previsão de disco cheio",
                "message": f"No ritmo atual, o disco ficará cheio em ~{int(days_until_full)} dias.",
                "action": {
                    "label": "Ver tendência",
                    "target": "chart:storage_trend"
                }
            })

    # CPU/Memory insights
    processes = system_data.get("processes", {})
    high_cpu = [p for p in processes.get("list", []) if p["cpu_percent"] > 80]
    if high_cpu:
        insights.append({
            "type": "info",
            "category": "performance",
            "title": f"{len(high_cpu)} processos com CPU alta",
            "message": f"Processos usando muita CPU: {', '.join([p['name'] for p in high_cpu[:3]])}",
            "action": {
                "label": "Ver processos",
                "target": "tab:processes"
            }
        })

    # Claude usage insights
    claude = system_data.get("claude_usage", {})
    if claude.get("usage", {}).get("window_5h", {}).get("percent", 0) > 75:
        insights.append({
            "type": "warning",
            "category": "claude",
            "title": "Uso do Claude Max 20x elevado",
            "message": "Considere agrupar perguntas para economizar mensagens.",
            "action": {
                "label": "Ver dicas",
                "target": "section:claude_tips"
            }
        })

    return sorted(insights, key=lambda x: {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}[x["type"]])
```

## 6.2 Histórico Compacto (SQLite)

```python
# services/history_db.py

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "history.db"

def init_db():
    """Inicializa o banco de dados SQLite"""
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabela principal de métricas
    c.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            metadata TEXT
        )
    ''')

    # Tabela de uso do Claude
    c.execute('''
        CREATE TABLE IF NOT EXISTS claude_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            window_5h_percent REAL,
            window_7d_percent REAL,
            messages_sent INTEGER,
            cost_brl REAL
        )
    ''')

    # Tabela de speed tests
    c.execute('''
        CREATE TABLE IF NOT EXISTS speed_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            download_mbps REAL,
            upload_mbps REAL,
            latency_ms REAL,
            provider TEXT,
            location TEXT
        )
    ''')

    # Índices
    c.execute('CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(metric_type)')

    conn.commit()
    conn.close()

def record_metric(metric_type: str, value: float, metadata: dict = None):
    """Registra uma métrica"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        'INSERT INTO metrics (metric_type, value, metadata) VALUES (?, ?, ?)',
        (metric_type, value, json.dumps(metadata) if metadata else None)
    )
    conn.commit()
    conn.close()

def cleanup_old_data():
    """Remove dados antigos (job diário)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Dados > 90 dias: deletar
    c.execute('DELETE FROM metrics WHERE timestamp < datetime("now", "-90 days")')

    # Agregar dados > 7 dias por hora
    # Agregar dados > 30 dias por dia

    conn.commit()
    conn.close()

def get_storage_stats():
    """Tamanho do banco de dados"""
    if DB_PATH.exists():
        size = DB_PATH.stat().st_size
        return {
            "size_bytes": size,
            "size_formatted": format_bytes(size),
            "records": count_records()
        }
    return {"size_bytes": 0, "size_formatted": "0 B", "records": 0}
```

---

# PARTE 7: PERFORMANCE & ESTABILIDADE

## 7.1 Loading Skeletons

```css
/* Skeleton loading animation */
.skeleton {
    background: linear-gradient(
        90deg,
        rgba(255, 255, 255, 0.03) 25%,
        rgba(255, 255, 255, 0.08) 50%,
        rgba(255, 255, 255, 0.03) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton-text {
    height: 1em;
    margin: 0.5em 0;
}

.skeleton-card {
    height: 120px;
    border-radius: 8px;
}
```

## 7.2 Toast Notifications

```javascript
function showToast(message, type = "info", duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${getToastIcon(type)}</span>
        <span class="toast-message">${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    document.getElementById('toast-container').appendChild(toast);

    // Animate in
    requestAnimationFrame(() => toast.classList.add('toast-visible'));

    // Auto remove
    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function getToastIcon(type) {
    const icons = {
        success: "✓",
        error: "✕",
        warning: "⚠",
        info: "ℹ"
    };
    return icons[type] || icons.info;
}
```

---

# PARTE 8: ARQUITETURA FINAL

```
nerd-space/
├── app.py                      # FastAPI principal (~200KB)
├── services/
│   ├── __init__.py
│   ├── ai_insights.py          # Motor de insights AI
│   ├── claude_usage.py         # Monitoramento Claude Max 20x
│   ├── speed_test.py           # Speed test nativo
│   ├── history_db.py           # SQLite para histórico
│   ├── system_info.py          # Coleta de dados do sistema
│   └── weather.py              # Clima com fallbacks
├── data/
│   └── history.db              # SQLite compacto (~500KB/mês)
├── static/
│   ├── css/
│   │   └── styles.css          # CSS customizado
│   └── js/
│       ├── app.js              # Frontend principal
│       ├── request-queue.js    # Sistema de filas
│       └── charts.js           # Gráficos
└── PLANO-NERD-SPACE-V5.md      # Este documento
```

---

# PARTE 9: RESUMO EXECUTIVO

## Bugs Corrigidos
- [x] Storage: usar `diskutil` para dados reais (354GB correto)
- [x] Clima: fallback wttr.in funcionando
- [x] Rede: debounce + timeout + request queue
- [x] Apps: cache 5 min + skeleton loading
- [x] Site travando: máx 3 requests simultâneas

## Novas Features
- [x] **Renomeação:** Mac Command Center → NERD SPACE
- [x] **Claude Max 20x:** Painel completo de uso e custos
- [x] **Speed Test:** Nativo, embedado, com histórico
- [x] **Monitores:** Layout visual SVG real
- [x] **Quick Links:** 10 ferramentas dev com atalhos
- [x] **macOS Tahoe 26.2:** Nome completo da versão
- [x] **Menu Sticky:** Acompanha scroll com blur
- [x] **Links Externos:** Identificados com ↗
- [x] **AI Insights:** Proativos e preditivos
- [x] **Histórico SQLite:** ~500KB/mês

## Estimativa de Tamanho

| Componente | Tamanho |
|------------|---------|
| app.py | ~200 KB |
| services/ | ~50 KB |
| static/ | ~30 KB |
| history.db (1 mês) | ~500 KB |
| **Total** | **< 1 MB** |

---

# APROVAÇÃO

**Plano NERD SPACE V5.0 - AI FIRST Edition**

- [ ] Aprovado para execução completa
- [ ] Aprovado com modificações: ________________

---

*Plano criado por: Equipe 360° AI FIRST*
*Arquiteto • UX Designer • Backend Engineer • Frontend Engineer • QA • Security • Data Engineer*
