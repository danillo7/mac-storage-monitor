#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        NERD SPACE V5.0 - AI FIRST Edition                     ║
║                 Enterprise-Grade System Intelligence Platform                 ║
║                                                                              ║
║  Features:                                                                   ║
║  • Hardware Dashboard (CPU, GPU, Memory, Battery, Displays)                  ║
║  • Software Intelligence (macOS, Updates, Services)                          ║
║  • Storage Analysis with Drill-Down (like Apple but 1000x better)            ║
║  • AI Insights - Proactive System Intelligence                               ║
║  • Speed Test embedado com histórico                                         ║
║  • Real-time Performance Monitoring                                          ║
║  • Weather & Network Status                                                  ║
║                                                                              ║
║  Created for: Dr. Danillo Costa                                              ║
║  By: Claude Code (Anthropic) - TOP 1% Engineering Standards                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import subprocess
import asyncio
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from functools import lru_cache
import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# NERD SPACE V5.0 Services
from services.claude_usage import get_claude_usage_service
from services.speed_test import get_speed_test_service
from services.weather import get_weather_service
from services.history_db import get_history_db
from services.system_info import get_system_info_service
from services.ai_insights import get_ai_insights_service

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APP_NAME = "NERD SPACE"
APP_VERSION = "5.0.0 - AI FIRST Edition"
PORT = 8888
ICLOUD_DIR = Path.home() / "Library/Mobile Documents/com~apple~CloudDocs"

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HardwareInfo:
    model_name: str
    model_identifier: str
    chip: str
    total_cores: int
    performance_cores: int
    efficiency_cores: int
    gpu_cores: int
    memory_gb: int
    serial_number: str
    hardware_uuid: str
    warranty_expiry: str
    uptime: str
    uptime_seconds: int

@dataclass
class DisplayInfo:
    name: str
    resolution: str
    ui_resolution: str
    refresh_rate: str
    is_main: bool
    rotation: str
    connection: str

@dataclass
class BatteryInfo:
    percentage: int
    is_charging: bool
    power_source: str
    cycle_count: int
    condition: str
    max_capacity: str
    time_remaining: str
    serial_number: str

@dataclass
class StorageCategory:
    name: str
    size_bytes: int
    size_human: str
    icon: str
    color: str
    percentage: float
    items: List[Dict[str, Any]]
    expandable: bool

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (use absolute path)
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def run_cmd(cmd: str, timeout: int = 5) -> str:
    """Execute shell command safely with short timeout"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""

# Smart cache system with different TTLs
import time as time_module
import threading

class SmartCache:
    """Cache with different TTLs for different data types"""
    def __init__(self):
        self._cache = {}
        self._locks = {}

    def get(self, key: str, ttl: int = 60):
        """Get cached value if not expired"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time_module.time() - timestamp < ttl:
                return data
        return None

    def set(self, key: str, data):
        """Set cache value"""
        self._cache[key] = (data, time_module.time())

    def clear(self, key: str = None):
        """Clear cache"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

_cache = SmartCache()

# Cache TTLs (in seconds)
CACHE_TTL = {
    "hardware": 300,      # 5 min - rarely changes
    "storage": 60,        # 1 min - can change
    "applications": 300,  # 5 min - apps don't change often
    "battery": 30,        # 30s - changes with usage
    "processes": 10,      # 10s - changes frequently
    "network": 15,        # 15s - changes frequently
    "icloud": 120,        # 2 min - large, slow to compute
    "trash": 30,          # 30s - can change
}

# Legacy cache for backward compatibility
_storage_cache = {"data": None, "timestamp": 0}

def parse_size(size_str: str) -> int:
    """Parse human-readable size to bytes"""
    size_str = size_str.strip().upper().replace(",", ".")
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    for suffix, mult in multipliers.items():
        if suffix in size_str:
            try:
                return int(float(size_str.replace(suffix, "").strip()) * mult)
            except:
                return 0
    try:
        return int(float(size_str))
    except:
        return 0

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_val) < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"

def format_uptime(seconds: int) -> str:
    """Format seconds to human-readable uptime"""
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    parts = []
    if days > 0:
        parts.append(f"{days} dia{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hora{'s' if hours > 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} min")
    return " ".join(parts) if parts else "< 1 min"

# ═══════════════════════════════════════════════════════════════════════════════
# NERD SPACE - PREMIUM FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

OWNER_NAME = "Danillo Costa"
SAO_PAULO_TZ = "America/Sao_Paulo"

def get_personalized_greeting() -> Dict[str, Any]:
    """Get personalized greeting for Danillo Costa based on São Paulo time"""
    from datetime import datetime
    import random

    # Get São Paulo time
    try:
        from zoneinfo import ZoneInfo
        sp_tz = ZoneInfo(SAO_PAULO_TZ)
        now = datetime.now(sp_tz)
    except:
        now = datetime.now()

    hour = now.hour

    # Motivational phrases for a NERD/Tech enthusiast
    morning_greetings = [
        f"Bom dia, {OWNER_NAME}! ☀️ Que tal começar com um café e um código limpo?",
        f"Ótima manhã, Dr. {OWNER_NAME.split()[1]}! 🌅 Seu Mac está pronto para conquistar o mundo.",
        f"Bom dia, {OWNER_NAME}! 💪 Hoje é dia de fazer acontecer!",
        f"Rise and shine, {OWNER_NAME}! 🚀 Sua estação de comando está operacional.",
        f"Bom dia, mestre! ☕ O café está chamando e os bits aguardam.",
    ]

    afternoon_greetings = [
        f"Boa tarde, {OWNER_NAME}! 🌤️ Produtividade em alta!",
        f"Olá, Dr. {OWNER_NAME.split()[1]}! 💼 Como está o progresso hoje?",
        f"Boa tarde, comandante! 🎯 Missões sendo cumpridas?",
        f"Hey {OWNER_NAME}! 🔥 A tarde está quente e os projetos também!",
        f"Boa tarde! 🧠 Hora de transformar café em código.",
    ]

    evening_greetings = [
        f"Boa noite, {OWNER_NAME}! 🌆 Finalizando com excelência?",
        f"Boa noite, Dr. {OWNER_NAME.split()[1]}! 🌙 Hora de revisar os logs do dia.",
        f"Hey {OWNER_NAME}! 🌃 Os nerds dominam a noite.",
        f"Boa noite, mestre! ✨ Deploy finalizado ou sessão de debug?",
        f"Boa noite! 🎮 Trabalho concluído, hora de relaxar?",
    ]

    night_greetings = [
        f"Ainda acordado, {OWNER_NAME}? 🦉 Os melhores códigos nascem à noite!",
        f"Madrugada, Dr. {OWNER_NAME.split()[1]}! 🌌 Modo noturno ativado.",
        f"Olá, coruja! 🌙 Debugando o universo?",
        f"{OWNER_NAME}, lembre-se: dormir também é importante! 😴",
        f"Madrugada ninja! 🥷 Que os bugs fujam de você.",
    ]

    if 5 <= hour < 12:
        period = "morning"
        greeting = random.choice(morning_greetings)
        emoji = "☀️"
    elif 12 <= hour < 18:
        period = "afternoon"
        greeting = random.choice(afternoon_greetings)
        emoji = "🌤️"
    elif 18 <= hour < 22:
        period = "evening"
        greeting = random.choice(evening_greetings)
        emoji = "🌆"
    else:
        period = "night"
        greeting = random.choice(night_greetings)
        emoji = "🌙"

    return {
        "greeting": greeting,
        "period": period,
        "emoji": emoji,
        "name": OWNER_NAME,
        "hour": hour,
        "time_sp": now.strftime("%H:%M:%S"),
        "date_sp": now.strftime("%d/%m/%Y"),
        "day_name": now.strftime("%A").replace("Monday", "Segunda").replace("Tuesday", "Terça").replace("Wednesday", "Quarta").replace("Thursday", "Quinta").replace("Friday", "Sexta").replace("Saturday", "Sábado").replace("Sunday", "Domingo"),
    }

def get_weather_sao_paulo() -> Dict[str, Any]:
    """Get weather for São Paulo using wttr.in (free, no API key needed)"""
    import urllib.request
    import json
    import ssl

    try:
        # SSL context para evitar erro de certificado no Python 3.14
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # wttr.in free weather API
        url = "https://wttr.in/Sao_Paulo?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
            data = json.loads(response.read().decode())

        current = data["current_condition"][0]
        weather_desc = current.get("lang_pt", [{}])[0].get("value", current.get("weatherDesc", [{}])[0].get("value", "N/A"))

        # Get forecast for rain probability
        today_forecast = data.get("weather", [{}])[0]
        hourly = today_forecast.get("hourly", [])

        # Find current hour's rain chance
        from datetime import datetime
        current_hour = datetime.now().hour
        rain_chance = 0
        for h in hourly:
            h_time = int(h.get("time", "0")) // 100
            if h_time == current_hour:
                rain_chance = int(h.get("chanceofrain", 0))
                break

        return {
            "success": True,
            "city": "São Paulo",
            "temperature": int(current.get("temp_C", 0)),
            "feels_like": int(current.get("FeelsLikeC", 0)),
            "humidity": int(current.get("humidity", 0)),
            "wind_speed": int(current.get("windspeedKmph", 0)),
            "wind_direction": current.get("winddir16Point", "N/A"),
            "description": weather_desc,
            "rain_chance": rain_chance,
            "uv_index": int(current.get("uvIndex", 0)),
            "visibility": int(current.get("visibility", 0)),
            "cloud_cover": int(current.get("cloudcover", 0)),
            "pressure": int(current.get("pressure", 0)),
            "weather_code": current.get("weatherCode", "113"),
            "is_day": 6 <= datetime.now().hour <= 18,
            "sunrise": today_forecast.get("astronomy", [{}])[0].get("sunrise", "N/A"),
            "sunset": today_forecast.get("astronomy", [{}])[0].get("sunset", "N/A"),
            "max_temp": int(today_forecast.get("maxtempC", 0)),
            "min_temp": int(today_forecast.get("mintempC", 0)),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "city": "São Paulo",
            "temperature": None,
        }

def get_power_info() -> Dict[str, Any]:
    """Get detailed power and energy information"""
    battery = psutil.sensors_battery()
    pmset_output = run_cmd("pmset -g batt")
    pmset_ps = run_cmd("pmset -g ps")

    # Parse detailed battery info
    cycle_count = 0
    max_capacity = 100
    condition = "Normal"

    sp_battery = run_cmd("system_profiler SPPowerDataType")
    for line in sp_battery.split("\n"):
        if "Cycle Count:" in line:
            try:
                cycle_count = int(re.search(r"(\d+)", line).group(1))
            except:
                pass
        elif "Maximum Capacity:" in line:
            try:
                max_capacity = int(re.search(r"(\d+)", line).group(1))
            except:
                pass
        elif "Condition:" in line:
            condition = line.split(":")[1].strip()

    # Get power consumption
    power_info = run_cmd("pmset -g thermlog 2>/dev/null | head -5")

    return {
        "battery_percent": battery.percent if battery else None,
        "is_charging": battery.power_plugged if battery else None,
        "time_remaining_mins": int(battery.secsleft / 60) if battery and battery.secsleft > 0 else None,
        "power_source": "AC Power" if (battery and battery.power_plugged) else "Battery",
        "cycle_count": cycle_count,
        "max_capacity_percent": max_capacity,
        "condition": condition,
        "pmset_status": pmset_output,
        "is_optimized_charging": "optimized" in sp_battery.lower(),
        "adapter_info": run_cmd("system_profiler SPPowerDataType | grep -A5 'AC Charger'"),
    }

def run_speed_test() -> Dict[str, Any]:
    """Run internet speed test using fast.com via curl"""
    try:
        # Simple download speed test using a small file
        import time
        import urllib.request

        # Test download speed with a 1MB file
        test_url = "http://speedtest.tele2.net/1MB.zip"

        start_time = time.time()
        req = urllib.request.Request(test_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
        end_time = time.time()

        download_time = end_time - start_time
        file_size_mb = len(data) / (1024 * 1024)
        download_speed_mbps = (file_size_mb * 8) / download_time  # Convert to Mbps

        # Get ping to Google DNS
        ping_output = run_cmd("ping -c 3 8.8.8.8 2>/dev/null | tail -1")
        ping_ms = None
        if ping_output:
            match = re.search(r"(\d+\.\d+)/", ping_output)
            if match:
                ping_ms = float(match.group(1))

        return {
            "success": True,
            "download_mbps": round(download_speed_mbps, 2),
            "ping_ms": ping_ms,
            "test_file_mb": round(file_size_mb, 2),
            "test_duration_sec": round(download_time, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }

def get_trash_info() -> Dict[str, Any]:
    """Get detailed information about the Trash folder using macOS commands"""
    import os

    try:
        # Use du command to get total size (works with permissions)
        du_output = run_cmd("du -sk ~/.Trash 2>/dev/null || echo '0'")
        total_size_kb = 0
        try:
            total_size_kb = int(du_output.split()[0])
        except:
            pass
        total_size = total_size_kb * 1024

        # Use ls to count items (with error handling for permissions)
        ls_output = run_cmd("ls -la ~/.Trash 2>/dev/null | tail -n +4")
        items = []
        file_count = 0
        folder_count = 0

        if ls_output.strip():
            for line in ls_output.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    is_folder = permissions.startswith('d')
                    name = ' '.join(parts[8:])

                    if name in ['.', '..', '.DS_Store']:
                        continue

                    if is_folder:
                        folder_count += 1
                    else:
                        file_count += 1

                    # Get size for this specific item
                    item_size_output = run_cmd(f"du -sk ~/.Trash/'{name}' 2>/dev/null || echo '0'")
                    item_size_kb = 0
                    try:
                        item_size_kb = int(item_size_output.split()[0])
                    except:
                        pass
                    item_size = item_size_kb * 1024

                    # Get modification date
                    stat_output = run_cmd(f"stat -f '%m' ~/.Trash/'{name}' 2>/dev/null")
                    days_old = 0
                    deleted_date = "Desconhecido"
                    try:
                        mod_timestamp = int(stat_output.strip())
                        mod_date = datetime.fromtimestamp(mod_timestamp)
                        days_old = (datetime.now() - mod_date).days
                        deleted_date = mod_date.strftime("%d/%m/%Y %H:%M")
                    except:
                        pass

                    items.append({
                        "name": name,
                        "is_folder": is_folder,
                        "size_bytes": item_size,
                        "size_human": format_bytes(item_size),
                        "deleted_date": deleted_date,
                        "days_old": days_old,
                    })

        # Sort by size (largest first)
        items.sort(key=lambda x: x["size_bytes"], reverse=True)
        top_items = items[:10]

        return {
            "total_size_bytes": total_size,
            "total_size_human": format_bytes(total_size),
            "file_count": file_count,
            "folder_count": folder_count,
            "total_items": file_count + folder_count,
            "is_empty": (file_count + folder_count) == 0,
            "top_items": top_items,
            "can_recover_space": total_size > 0,
            "recommendation": "🗑️ Esvaziar lixeira para recuperar espaço" if total_size > 100*1024*1024 else None,
        }
    except Exception as e:
        return {
            "error": str(e),
            "total_size_bytes": 0,
            "total_size_human": "0 B",
            "is_empty": True,
            "total_items": 0,
            "top_items": [],
        }

def get_mac_tips() -> List[Dict[str, str]]:
    """Get useful Mac tips and shortcuts - Expanded for NERD SPACE V5.0"""
    tips = [
        # ═══════════════════════════════════════════════════════════════════
        # SISTEMA - Essenciais (10 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Force Quit Apps", "shortcut": "⌘ + ⌥ + Esc", "description": "Abre o menu Force Quit para fechar apps travados", "category": "Sistema"},
        {"title": "Spotlight", "shortcut": "⌘ + Space", "description": "Abre a busca universal do Mac", "category": "Sistema"},
        {"title": "Lock Screen", "shortcut": "⌃ + ⌘ + Q", "description": "Bloqueia a tela imediatamente", "category": "Sistema"},
        {"title": "Mission Control", "shortcut": "⌃ + ↑ ou F3", "description": "Visão geral de todas as janelas", "category": "Sistema"},
        {"title": "Mostrar Desktop", "shortcut": "F11 ou ⌘ + F3", "description": "Mostra a área de trabalho instantaneamente", "category": "Sistema"},
        {"title": "Reiniciar Finder", "shortcut": "⌥ + clique no Finder", "description": "Menu escondido para relançar o Finder", "category": "Sistema"},
        {"title": "System Preferences", "shortcut": "⌘ + Space → System", "description": "Acesso rápido às Preferências", "category": "Sistema"},
        {"title": "Sleep Rápido", "shortcut": "⌥ + ⌘ + Eject", "description": "Coloca o Mac para dormir instantaneamente", "category": "Sistema"},
        {"title": "Info do Sistema", "shortcut": "⌥ + Menu Apple", "description": "Abre Info do Sistema diretamente", "category": "Sistema"},
        {"title": "Safe Boot", "shortcut": "⇧ na inicialização", "description": "Inicia em modo seguro para diagnóstico", "category": "Sistema"},

        # ═══════════════════════════════════════════════════════════════════
        # SCREENSHOT (6 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Screenshot Área", "shortcut": "⌘ + ⇧ + 4", "description": "Captura uma área selecionada da tela", "category": "Screenshot"},
        {"title": "Screenshot Janela", "shortcut": "⌘ + ⇧ + 4 + Space", "description": "Captura uma janela específica", "category": "Screenshot"},
        {"title": "Screenshot Tela", "shortcut": "⌘ + ⇧ + 3", "description": "Captura a tela inteira", "category": "Screenshot"},
        {"title": "Gravar Tela", "shortcut": "⌘ + ⇧ + 5", "description": "Abre opções de screenshot e gravação", "category": "Screenshot"},
        {"title": "Screenshot Touch Bar", "shortcut": "⌘ + ⇧ + 6", "description": "Captura a Touch Bar (se disponível)", "category": "Screenshot"},
        {"title": "Clipboard Copy", "shortcut": "+ ⌃ em qualquer screenshot", "description": "Copia screenshot para clipboard ao invés de salvar", "category": "Screenshot"},

        # ═══════════════════════════════════════════════════════════════════
        # FINDER (10 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Finder Path", "shortcut": "⌘ + ⇧ + G", "description": "Ir para pasta específica no Finder", "category": "Finder"},
        {"title": "Limpar Lixeira", "shortcut": "⌘ + ⇧ + Delete", "description": "Esvazia a lixeira permanentemente", "category": "Finder"},
        {"title": "Arquivos Ocultos", "shortcut": "⌘ + ⇧ + .", "description": "Mostra/oculta arquivos escondidos", "category": "Finder"},
        {"title": "Nova Pasta", "shortcut": "⌘ + ⇧ + N", "description": "Cria nova pasta no Finder", "category": "Finder"},
        {"title": "Info do Arquivo", "shortcut": "⌘ + I", "description": "Mostra informações do arquivo/pasta", "category": "Finder"},
        {"title": "Quick Look", "shortcut": "Space", "description": "Preview rápido de qualquer arquivo", "category": "Finder"},
        {"title": "Abrir com...", "shortcut": "⌥ + clique direito", "description": "Mostra 'Abrir com...' como padrão", "category": "Finder"},
        {"title": "Duplicar Arquivo", "shortcut": "⌘ + D", "description": "Duplica arquivo selecionado", "category": "Finder"},
        {"title": "Mover para Lixeira", "shortcut": "⌘ + Delete", "description": "Move arquivo para a lixeira", "category": "Finder"},
        {"title": "AirDrop", "shortcut": "⌘ + ⇧ + R", "description": "Abre AirDrop no Finder", "category": "Finder"},

        # ═══════════════════════════════════════════════════════════════════
        # NAVEGAÇÃO (8 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Switch Apps", "shortcut": "⌘ + Tab", "description": "Alterna entre aplicativos abertos", "category": "Navegação"},
        {"title": "Switch Windows", "shortcut": "⌘ + `", "description": "Alterna janelas do mesmo app", "category": "Navegação"},
        {"title": "Minimize", "shortcut": "⌘ + M", "description": "Minimiza a janela atual", "category": "Navegação"},
        {"title": "Full Screen", "shortcut": "⌃ + ⌘ + F", "description": "Entra/sai do modo tela cheia", "category": "Navegação"},
        {"title": "Nova Janela", "shortcut": "⌘ + N", "description": "Abre nova janela do app atual", "category": "Navegação"},
        {"title": "Fechar Janela", "shortcut": "⌘ + W", "description": "Fecha a janela atual", "category": "Navegação"},
        {"title": "Fechar App", "shortcut": "⌘ + Q", "description": "Fecha completamente o aplicativo", "category": "Navegação"},
        {"title": "Split View", "shortcut": "⌃ + ⌘ + F → arrastar", "description": "Divide a tela entre dois apps", "category": "Navegação"},

        # ═══════════════════════════════════════════════════════════════════
        # TEXTO & EDIÇÃO (10 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Emoji Picker", "shortcut": "⌃ + ⌘ + Space", "description": "Abre o seletor de emojis", "category": "Texto"},
        {"title": "Selecionar Tudo", "shortcut": "⌘ + A", "description": "Seleciona todo o conteúdo", "category": "Texto"},
        {"title": "Buscar/Substituir", "shortcut": "⌘ + F / ⌘ + ⌥ + F", "description": "Busca ou busca e substitui texto", "category": "Texto"},
        {"title": "Desfazer", "shortcut": "⌘ + Z", "description": "Desfaz última ação", "category": "Texto"},
        {"title": "Refazer", "shortcut": "⌘ + ⇧ + Z", "description": "Refaz ação desfeita", "category": "Texto"},
        {"title": "Deletar Palavra", "shortcut": "⌥ + Delete", "description": "Deleta palavra anterior inteira", "category": "Texto"},
        {"title": "Início da Linha", "shortcut": "⌘ + ←", "description": "Move cursor para início da linha", "category": "Texto"},
        {"title": "Fim da Linha", "shortcut": "⌘ + →", "description": "Move cursor para fim da linha", "category": "Texto"},
        {"title": "Pular Palavra", "shortcut": "⌥ + ← / →", "description": "Move cursor entre palavras", "category": "Texto"},
        {"title": "Selecionar Palavra", "shortcut": "Double-click", "description": "Seleciona palavra inteira", "category": "Texto"},

        # ═══════════════════════════════════════════════════════════════════
        # DEV TOOLS - NERD (12 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Terminal Rápido", "shortcut": "⌘ + Space → Term", "description": "Acesso rápido ao Terminal via Spotlight", "category": "Dev"},
        {"title": "Activity Monitor", "shortcut": "⌘ + Space → Activity", "description": "Monitore CPU, memória e rede", "category": "Dev"},
        {"title": "Console Logs", "shortcut": "⌘ + Space → Console", "description": "Ver logs do sistema em tempo real", "category": "Dev"},
        {"title": "Inspecionar (Safari)", "shortcut": "⌘ + ⌥ + I", "description": "Abre Developer Tools no Safari", "category": "Dev"},
        {"title": "Inspecionar (Chrome)", "shortcut": "⌘ + ⌥ + J", "description": "Abre Console no Chrome", "category": "Dev"},
        {"title": "Disk Utility", "shortcut": "⌘ + Space → Disk", "description": "Gerenciar discos e partições", "category": "Dev"},
        {"title": "Network Utility", "shortcut": "⌘ + Space → Network", "description": "Ferramentas de diagnóstico de rede", "category": "Dev"},
        {"title": "Keychain Access", "shortcut": "⌘ + Space → Keychain", "description": "Gerenciar senhas e certificados", "category": "Dev"},
        {"title": "Terminal: Clear", "shortcut": "⌘ + K", "description": "Limpa o buffer do Terminal", "category": "Dev"},
        {"title": "Terminal: Cancelar", "shortcut": "⌃ + C", "description": "Cancela comando em execução", "category": "Dev"},
        {"title": "Git GUI", "shortcut": "gitk ou git gui", "description": "Interfaces gráficas para Git", "category": "Dev"},
        {"title": "Xcode Tools", "shortcut": "xcode-select --install", "description": "Instala ferramentas de linha de comando", "category": "Dev"},

        # ═══════════════════════════════════════════════════════════════════
        # PRODUTIVIDADE - Power User (8 tips)
        # ═══════════════════════════════════════════════════════════════════
        {"title": "Hot Corners", "shortcut": "System Prefs → Desktop", "description": "Configure ações nos cantos da tela", "category": "Produtividade"},
        {"title": "Stage Manager", "shortcut": "⌃ + ⌘ + S", "description": "Organiza janelas automaticamente", "category": "Produtividade"},
        {"title": "Focus Mode", "shortcut": "⌃ + ⌘ + D", "description": "Ativa modo Não Perturbe", "category": "Produtividade"},
        {"title": "Dictation", "shortcut": "Fn Fn (2x)", "description": "Ativa ditado por voz", "category": "Produtividade"},
        {"title": "Text Replacement", "shortcut": "System Prefs → Keyboard", "description": "Configure atalhos de texto personalizados", "category": "Produtividade"},
        {"title": "Siri", "shortcut": "⌘ + Space (segurar)", "description": "Ativa Siri para comandos de voz", "category": "Produtividade"},
        {"title": "Handoff", "shortcut": "Dock → ícone app", "description": "Continue trabalho de outro dispositivo", "category": "Produtividade"},
        {"title": "Universal Clipboard", "shortcut": "⌘ + C no iPhone", "description": "Cola texto copiado de outro device Apple", "category": "Produtividade"},
    ]
    return tips

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM DATA COLLECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def get_hardware_info() -> Dict[str, Any]:
    """Get comprehensive hardware information"""
    output = run_cmd("system_profiler SPHardwareDataType SPSoftwareDataType")

    def extract(pattern: str, text: str) -> str:
        match = re.search(pattern + r":\s*(.+)", text)
        return match.group(1).strip() if match else "N/A"

    # Parse cores
    cores_str = extract("Total Number of Cores", output)
    total_cores = 14
    perf_cores = 10
    eff_cores = 4
    if "performance" in cores_str.lower():
        match = re.search(r"(\d+)\s*\((\d+)\s*performance\s*and\s*(\d+)\s*efficiency", cores_str)
        if match:
            total_cores, perf_cores, eff_cores = int(match.group(1)), int(match.group(2)), int(match.group(3))

    # Get GPU cores
    gpu_output = run_cmd("system_profiler SPDisplaysDataType | grep 'Total Number of Cores'")
    gpu_cores = 30
    if gpu_output:
        try:
            gpu_cores = int(re.search(r"(\d+)", gpu_output).group(1))
        except:
            pass

    # Get memory
    memory_str = extract("Memory", output)
    memory_gb = 36
    try:
        memory_gb = int(re.search(r"(\d+)", memory_str).group(1))
    except:
        pass

    # Calculate uptime
    boot_time = psutil.boot_time()
    uptime_seconds = int(datetime.now().timestamp() - boot_time)

    return {
        "model_name": extract("Model Name", output),
        "model_identifier": extract("Model Identifier", output),
        "model_number": extract("Model Number", output),
        "chip": extract("Chip", output),
        "total_cores": total_cores,
        "performance_cores": perf_cores,
        "efficiency_cores": eff_cores,
        "gpu_cores": gpu_cores,
        "metal_support": "Metal 4",
        "memory_gb": memory_gb,
        "serial_number": extract("Serial Number \\(system\\)", output) or (run_cmd("ioreg -l | grep IOPlatformSerialNumber").split('"')[-2] if "IOPlatformSerialNumber" in run_cmd("ioreg -l | grep IOPlatformSerialNumber") else "H4H2PMGF32"),
        "hardware_uuid": extract("Hardware UUID", output),
        "warranty_expiry": "23 de dezembro de 2026",
        "warranty_status": "Ativa",
        "uptime": format_uptime(uptime_seconds),
        "uptime_seconds": uptime_seconds,
        "boot_time": datetime.fromtimestamp(boot_time).isoformat(),
        "system_version": extract("System Version", output),
        "kernel_version": extract("Kernel Version", output),
        "computer_name": extract("Computer Name", output),
        "user_name": extract("User Name", output),
        "sip_status": extract("System Integrity Protection", output),
        "activation_lock": extract("Activation Lock Status", output),
    }

def get_displays_info() -> List[Dict[str, Any]]:
    """Get information about all connected displays"""
    output = run_cmd("system_profiler SPDisplaysDataType")
    displays = []

    # Parse display sections
    display_sections = re.split(r"\n\s{8}(\w[^:]+):", output)

    current_display = None
    for i, section in enumerate(display_sections):
        if i == 0:
            continue
        if i % 2 == 1:  # Display name
            if any(skip in section.lower() for skip in ["apple m", "chipset", "type", "bus", "vendor", "metal"]):
                continue
            current_display = {"name": section.strip()}
        elif current_display:  # Display properties
            lines = section.strip().split("\n")
            for line in lines:
                if "Resolution:" in line:
                    current_display["resolution"] = line.split(":", 1)[1].strip()
                elif "UI Looks like:" in line:
                    ui_info = line.split(":", 1)[1].strip()
                    current_display["ui_resolution"] = ui_info
                    if "@" in ui_info:
                        current_display["refresh_rate"] = ui_info.split("@")[1].strip()
                elif "Main Display:" in line:
                    current_display["is_main"] = "Yes" in line
                elif "Rotation:" in line:
                    rot = line.split(":", 1)[1].strip()
                    current_display["rotation"] = rot if rot != "Supported" else "0°"
                elif "Online:" in line:
                    current_display["online"] = "Yes" in line

            if "resolution" in current_display:
                # Determine display type icon
                name_lower = current_display["name"].lower()
                if "odyssey" in name_lower or "samsung" in name_lower:
                    current_display["icon"] = "🎮"
                    current_display["type"] = "Gaming Monitor"
                elif "dell" in name_lower:
                    current_display["icon"] = "🖥️"
                    current_display["type"] = "Professional Monitor"
                else:
                    current_display["icon"] = "📺"
                    current_display["type"] = "External Display"

                displays.append(current_display)
            current_display = None

    return displays

def get_battery_info() -> Dict[str, Any]:
    """Get detailed battery information"""
    pmset_output = run_cmd("pmset -g batt")
    power_output = run_cmd("system_profiler SPPowerDataType")

    # Parse pmset
    percentage = 0
    is_charging = False
    power_source = "Unknown"
    time_remaining = "N/A"

    if "AC Power" in pmset_output:
        power_source = "AC Power"
    elif "Battery Power" in pmset_output:
        power_source = "Battery"

    match = re.search(r"(\d+)%", pmset_output)
    if match:
        percentage = int(match.group(1))

    is_charging = "charging" in pmset_output.lower() and "not charging" not in pmset_output.lower()

    match = re.search(r"(\d+:\d+)\s*remaining", pmset_output)
    if match:
        time_remaining = match.group(1)
    elif "charged" in pmset_output.lower():
        time_remaining = "Carregada"

    # Parse system profiler for detailed info
    def extract_power(pattern: str) -> str:
        match = re.search(pattern + r":\s*(.+)", power_output)
        return match.group(1).strip() if match else "N/A"

    cycle_count = 0
    match = re.search(r"Cycle Count:\s*(\d+)", power_output)
    if match:
        cycle_count = int(match.group(1))

    return {
        "percentage": percentage,
        "is_charging": is_charging,
        "power_source": power_source,
        "time_remaining": time_remaining,
        "cycle_count": cycle_count,
        "condition": extract_power("Condition"),
        "max_capacity": extract_power("Maximum Capacity"),
        "serial_number": extract_power("Serial Number"),
        "health_status": "Excelente" if cycle_count < 100 else "Bom" if cycle_count < 500 else "Regular",
        "health_percentage": max(0, 100 - (cycle_count * 0.1)),
    }

def get_storage_categories() -> Dict[str, Any]:
    """Get categorized storage analysis with drill-down capability"""
    import time

    # Check cache first
    now = time.time()
    if _storage_cache["data"] and (now - _storage_cache["timestamp"]) < CACHE_TTL["storage"]:
        return _storage_cache["data"]

    # FIX: Usar dados REAIS do APFS container, não do psutil
    # psutil.disk_usage("/") retorna dados do snapshot, não do container real
    system_info = get_system_info_service()
    storage_real = system_info.get_storage_real()

    total_bytes = int(storage_real["total_gb"] * 1024 * 1024 * 1024)
    used_bytes = int(storage_real["used_gb"] * 1024 * 1024 * 1024)
    free_bytes = int(storage_real["free_gb"] * 1024 * 1024 * 1024)

    categories = []

    # Define category analysis
    category_definitions = [
        {
            "name": "Aplicativos",
            "icon": "package",
            "color": "#ef4444",
            "paths": ["/Applications"],
            "get_items": lambda: get_applications_list()
        },
        {
            "name": "Desenvolvedor",
            "icon": "code",
            "color": "#f97316",
            "paths": [str(Path.home() / "Developer"), "/opt/homebrew", "/usr/local"],
            "get_items": lambda: get_developer_breakdown()
        },
        {
            "name": "Documentos",
            "icon": "file-text",
            "color": "#eab308",
            "paths": [str(Path.home() / "Documents")],
            "get_items": lambda: get_folder_breakdown(Path.home() / "Documents")
        },
        {
            "name": "Fotos",
            "icon": "image",
            "color": "#84cc16",
            "paths": [str(Path.home() / "Pictures"), str(Path.home() / "Library/Photos")],
            "get_items": lambda: []
        },
        {
            "name": "iCloud Drive",
            "icon": "cloud",
            "color": "#06b6d4",
            "paths": [str(ICLOUD_DIR)],
            "get_items": lambda: get_icloud_breakdown()
        },
        {
            "name": "Mensagens",
            "icon": "message-square",
            "color": "#22c55e",
            "paths": [str(Path.home() / "Library/Messages")],
            "get_items": lambda: []
        },
        {
            "name": "Mail",
            "icon": "mail",
            "color": "#3b82f6",
            "paths": [str(Path.home() / "Library/Mail")],
            "get_items": lambda: []
        },
        {
            "name": "Música",
            "icon": "music",
            "color": "#ec4899",
            "paths": [str(Path.home() / "Music")],
            "get_items": lambda: []
        },
        {
            "name": "Podcasts",
            "icon": "mic",
            "color": "#8b5cf6",
            "paths": [str(Path.home() / "Library/Group Containers/243LU875E5.groups.com.apple.podcasts")],
            "get_items": lambda: []
        },
        {
            "name": "macOS",
            "icon": "laptop",
            "color": "#6366f1",
            "paths": ["/System"],
            "get_items": lambda: []
        },
        {
            "name": "Dados do Sistema",
            "icon": "database",
            "color": "#64748b",
            "paths": [str(Path.home() / "Library")],
            "get_items": lambda: get_system_data_breakdown()
        },
    ]

    for cat_def in category_definitions:
        size_bytes = 0
        for path in cat_def["paths"]:
            if os.path.exists(path):
                try:
                    result = run_cmd(f'du -sk "{path}" 2>/dev/null | cut -f1', timeout=3)
                    if result:
                        size_bytes += int(result) * 1024
                except:
                    pass

        if size_bytes > 0:
            categories.append({
                "name": cat_def["name"],
                "icon": cat_def["icon"],
                "color": cat_def["color"],
                "size_bytes": size_bytes,
                "size_human": format_bytes(size_bytes),
                "percentage": round((size_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0,
                "expandable": True,
                "paths": cat_def["paths"],
            })

    # Sort by size
    categories.sort(key=lambda x: x["size_bytes"], reverse=True)

    result = {
        "total_bytes": total_bytes,
        "total_human": format_bytes(total_bytes),
        "used_bytes": used_bytes,
        "used_human": format_bytes(used_bytes),
        "free_bytes": free_bytes,
        "free_human": format_bytes(free_bytes),
        "used_percentage": round((used_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0,
        "free_percentage": round((free_bytes / total_bytes) * 100, 1) if total_bytes > 0 else 0,
        "categories": categories,
        "disk_name": "Macintosh HD",
        "file_system": "APFS",
        "device": "APPLE SSD AP1024Z",
        "smart_status": "Verified",
    }

    # Update cache
    _storage_cache["data"] = result
    _storage_cache["timestamp"] = now

    return result

def get_applications_list() -> List[Dict[str, Any]]:
    """Get list of applications with sizes"""
    apps = []
    apps_dir = Path("/Applications")

    for app_path in apps_dir.glob("*.app"):
        try:
            result = run_cmd(f'du -sk "{app_path}" 2>/dev/null | cut -f1', timeout=5)
            size_bytes = int(result) * 1024 if result else 0

            # Get app info
            info_plist = app_path / "Contents" / "Info.plist"
            version = "N/A"
            if info_plist.exists():
                ver_result = run_cmd(f'defaults read "{info_plist}" CFBundleShortVersionString 2>/dev/null')
                if ver_result:
                    version = ver_result

            apps.append({
                "name": app_path.stem,
                "path": str(app_path),
                "size_bytes": size_bytes,
                "size_human": format_bytes(size_bytes),
                "version": version,
                "icon": "app-window"
            })
        except:
            pass

    apps.sort(key=lambda x: x["size_bytes"], reverse=True)
    return apps[:50]  # Top 50 apps

def get_developer_breakdown() -> List[Dict[str, Any]]:
    """Get breakdown of developer-related storage"""
    items = []
    dev_paths = [
        (Path.home() / "Developer", "Projetos", "folder-git"),
        (Path("/opt/homebrew"), "Homebrew", "beer"),
        (Path.home() / ".npm", "NPM Cache", "package"),
        (Path.home() / ".cache", "Caches Dev", "archive"),
        (Path.home() / "Library/Developer", "Xcode/Tools", "hammer"),
    ]

    for path, name, icon in dev_paths:
        if path.exists():
            try:
                result = run_cmd(f'du -sk "{path}" 2>/dev/null | cut -f1', timeout=10)
                size_bytes = int(result) * 1024 if result else 0
                if size_bytes > 0:
                    items.append({
                        "name": name,
                        "path": str(path),
                        "size_bytes": size_bytes,
                        "size_human": format_bytes(size_bytes),
                        "icon": icon
                    })
            except:
                pass

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    return items

def get_icloud_breakdown() -> List[Dict[str, Any]]:
    """Get breakdown of iCloud Drive storage"""
    items = []
    if ICLOUD_DIR.exists():
        for subdir in ICLOUD_DIR.iterdir():
            if subdir.is_dir():
                try:
                    result = run_cmd(f'du -sk "{subdir}" 2>/dev/null | cut -f1', timeout=10)
                    size_bytes = int(result) * 1024 if result else 0
                    if size_bytes > 1024 * 1024:  # > 1MB
                        items.append({
                            "name": subdir.name,
                            "path": str(subdir),
                            "size_bytes": size_bytes,
                            "size_human": format_bytes(size_bytes),
                            "icon": "cloud"
                        })
                except:
                    pass

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    return items[:20]

def get_folder_breakdown(folder: Path) -> List[Dict[str, Any]]:
    """Get breakdown of a folder"""
    items = []
    if folder.exists():
        for subdir in folder.iterdir():
            try:
                result = run_cmd(f'du -sk "{subdir}" 2>/dev/null | cut -f1', timeout=5)
                size_bytes = int(result) * 1024 if result else 0
                if size_bytes > 1024 * 1024:  # > 1MB
                    items.append({
                        "name": subdir.name,
                        "path": str(subdir),
                        "size_bytes": size_bytes,
                        "size_human": format_bytes(size_bytes),
                        "icon": "folder" if subdir.is_dir() else "file"
                    })
            except:
                pass

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    return items[:20]

def get_system_data_breakdown() -> List[Dict[str, Any]]:
    """Get breakdown of system data"""
    items = []
    lib_paths = [
        ("Application Support", "app-window"),
        ("Caches", "archive"),
        ("Containers", "box"),
        ("Logs", "file-text"),
        ("Preferences", "settings"),
    ]

    lib = Path.home() / "Library"
    for name, icon in lib_paths:
        path = lib / name
        if path.exists():
            try:
                result = run_cmd(f'du -sk "{path}" 2>/dev/null | cut -f1', timeout=10)
                size_bytes = int(result) * 1024 if result else 0
                if size_bytes > 0:
                    items.append({
                        "name": name,
                        "path": str(path),
                        "size_bytes": size_bytes,
                        "size_human": format_bytes(size_bytes),
                        "icon": icon
                    })
            except:
                pass

    items.sort(key=lambda x: x["size_bytes"], reverse=True)
    return items

def get_processes_info() -> Dict[str, Any]:
    """Get top processes by CPU and Memory"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 0.1:
                processes.append({
                    'pid': pinfo['pid'],
                    'name': pinfo['name'][:30],
                    'cpu_percent': round(pinfo['cpu_percent'], 1),
                    'memory_percent': round(pinfo['memory_percent'], 1),
                    'memory_mb': round(pinfo['memory_info'].rss / (1024*1024), 1) if pinfo['memory_info'] else 0
                })
        except:
            pass

    by_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:10]
    by_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:10]

    return {
        "by_cpu": by_cpu,
        "by_memory": by_memory,
        "total_processes": len(list(psutil.process_iter()))
    }

# Process categories for intelligent classification
PROCESS_CATEGORIES = {
    "icloud": {
        "patterns": ["cloudd", "bird", "nsurlsessiond", "CloudKeychainProxy", "cloudphotod", "cloudpaird"],
        "icon": "cloud", "color": "blue", "name": "iCloud Services"
    },
    "browsers": {
        "patterns": ["Safari", "Chrome", "Firefox", "Arc", "Brave", "Edge", "Opera"],
        "icon": "globe", "color": "purple", "name": "Navegadores"
    },
    "creative": {
        "patterns": ["Adobe", "Photoshop", "Illustrator", "Premiere", "Figma", "Sketch", "Final Cut"],
        "icon": "palette", "color": "pink", "name": "Apps Criativos"
    },
    "development": {
        "patterns": ["node", "python", "ruby", "java", "docker", "Code", "Xcode", "Terminal", "zsh", "bash"],
        "icon": "code", "color": "green", "name": "Desenvolvimento"
    },
    "communication": {
        "patterns": ["Slack", "Zoom", "Teams", "Discord", "Telegram", "WhatsApp", "Messages", "Mail"],
        "icon": "message-circle", "color": "cyan", "name": "Comunicação"
    },
    "system": {
        "patterns": ["kernel_task", "WindowServer", "launchd", "mds", "Spotlight", "Finder", "Dock"],
        "icon": "settings", "color": "zinc", "name": "Sistema macOS"
    },
    "security": {
        "patterns": ["1Password", "Keychain", "securityd", "trustd", "biomed"],
        "icon": "shield", "color": "amber", "name": "Segurança"
    },
}

def categorize_process(name: str) -> Dict[str, Any]:
    """Categorize a process based on its name"""
    name_lower = name.lower()
    for cat_id, cat_info in PROCESS_CATEGORIES.items():
        for pattern in cat_info["patterns"]:
            if pattern.lower() in name_lower:
                return {"id": cat_id, **cat_info}
    return {"id": "other", "icon": "circle", "color": "gray", "name": "Outros", "patterns": []}

def get_process_insights(proc: Dict) -> List[Dict[str, Any]]:
    """Generate intelligent insights about a process"""
    insights = []

    # High CPU usage alert
    if proc.get('cpu_percent', 0) > 80:
        insights.append({
            "type": "critical",
            "icon": "alert-triangle",
            "message": f"CPU muito alto ({proc['cpu_percent']}%) - pode estar travado ou em loop"
        })
    elif proc.get('cpu_percent', 0) > 50:
        insights.append({
            "type": "warning",
            "icon": "alert-circle",
            "message": f"CPU elevado ({proc['cpu_percent']}%) - processo intensivo"
        })

    # High memory usage alert
    if proc.get('memory_mb', 0) > 4000:
        insights.append({
            "type": "critical",
            "icon": "memory-stick",
            "message": f"Memória muito alta ({proc['memory_mb']:.0f} MB) - pode causar lentidão"
        })
    elif proc.get('memory_mb', 0) > 2000:
        insights.append({
            "type": "warning",
            "icon": "memory-stick",
            "message": f"Memória elevada ({proc['memory_mb']:.0f} MB)"
        })

    # iCloud specific insights
    name_lower = proc.get('name', '').lower()
    if any(p in name_lower for p in ['cloudd', 'bird', 'nsurlsessiond']):
        if proc.get('cpu_percent', 0) > 20 or proc.get('memory_mb', 0) > 500:
            insights.append({
                "type": "info",
                "icon": "cloud",
                "message": "iCloud sincronizando - pode usar disco/rede intensivamente"
            })

    # Spotlight/indexing insights
    if 'mds' in name_lower or 'spotlight' in name_lower:
        if proc.get('cpu_percent', 0) > 30:
            insights.append({
                "type": "info",
                "icon": "search",
                "message": "Spotlight indexando - aguarde ou configure exclusões"
            })

    return insights

def get_processes_detailed() -> Dict[str, Any]:
    """Get detailed process analysis with intelligence - TOP 1% implementation"""
    processes = []

    # Get disk I/O counters if available
    try:
        disk_io = psutil.disk_io_counters()
        initial_read = disk_io.read_bytes
        initial_write = disk_io.write_bytes
    except:
        initial_read = initial_write = 0

    # Collect detailed process info
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info',
                                      'create_time', 'status', 'username', 'num_threads']):
        try:
            pinfo = proc.info
            cpu_pct = pinfo.get('cpu_percent') or 0
            mem_pct = pinfo.get('memory_percent') or 0
            if cpu_pct > 0 or mem_pct > 0.1:
                # Calculate uptime
                try:
                    create_time = datetime.fromtimestamp(pinfo['create_time'])
                    uptime = datetime.now() - create_time
                    uptime_str = str(uptime).split('.')[0]
                except:
                    uptime_str = "N/A"

                # Try to get I/O counters per process
                try:
                    io = proc.io_counters()
                    read_mb = round(io.read_bytes / (1024*1024), 1)
                    write_mb = round(io.write_bytes / (1024*1024), 1)
                except:
                    read_mb = write_mb = 0

                proc_data = {
                    'pid': pinfo['pid'],
                    'name': (pinfo.get('name') or 'Unknown')[:35],
                    'cpu_percent': round(cpu_pct, 1),
                    'memory_percent': round(mem_pct, 1),
                    'memory_mb': round(pinfo['memory_info'].rss / (1024*1024), 1) if pinfo['memory_info'] else 0,
                    'threads': pinfo.get('num_threads', 0),
                    'status': pinfo.get('status', 'N/A'),
                    'user': pinfo.get('username', 'N/A'),
                    'uptime': uptime_str,
                    'disk_read_mb': read_mb,
                    'disk_write_mb': write_mb,
                    'category': categorize_process(pinfo['name']),
                }

                # Add intelligent insights
                proc_data['insights'] = get_process_insights(proc_data)

                processes.append(proc_data)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Sort by different metrics
    by_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:15]
    by_memory = sorted(processes, key=lambda x: x['memory_mb'], reverse=True)[:15]
    by_disk = sorted(processes, key=lambda x: x['disk_read_mb'] + x['disk_write_mb'], reverse=True)[:15]

    # Group by category
    categories = {}
    for proc in processes:
        cat_id = proc['category']['id']
        if cat_id not in categories:
            categories[cat_id] = {
                **proc['category'],
                'processes': [],
                'total_cpu': 0,
                'total_memory': 0,
                'count': 0
            }
        categories[cat_id]['processes'].append(proc)
        categories[cat_id]['total_cpu'] += proc['cpu_percent']
        categories[cat_id]['total_memory'] += proc['memory_mb']
        categories[cat_id]['count'] += 1

    # Get all insights/alerts
    all_insights = []
    for proc in processes:
        for insight in proc.get('insights', []):
            all_insights.append({
                **insight,
                'process': proc['name'],
                'pid': proc['pid']
            })

    # Sort insights by severity
    severity_order = {'critical': 0, 'warning': 1, 'info': 2}
    all_insights.sort(key=lambda x: severity_order.get(x['type'], 3))

    # System summary
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.1)

    return {
        "by_cpu": by_cpu,
        "by_memory": by_memory,
        "by_disk": by_disk,
        "categories": categories,
        "insights": all_insights[:10],  # Top 10 insights
        "summary": {
            "total_processes": len(processes),
            "cpu_percent": cpu_percent,
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_percent": memory.percent,
            "critical_alerts": len([i for i in all_insights if i['type'] == 'critical']),
            "warning_alerts": len([i for i in all_insights if i['type'] == 'warning']),
        }
    }

def get_network_info() -> Dict[str, Any]:
    """Get network and connectivity info"""
    # Local IP
    local_ip = run_cmd("ipconfig getifaddr en0") or "N/A"

    # Tailscale
    tailscale_status = run_cmd("tailscale status --json 2>/dev/null")
    tailscale_info = {"connected": False}
    if tailscale_status:
        try:
            ts_data = json.loads(tailscale_status)
            tailscale_info = {
                "connected": True,
                "hostname": ts_data.get("Self", {}).get("DNSName", "").rstrip("."),
                "ip": ts_data.get("Self", {}).get("TailscaleIPs", [""])[0],
                "online": ts_data.get("Self", {}).get("Online", False),
            }
        except:
            pass

    # WiFi
    wifi_info = run_cmd("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I 2>/dev/null | grep ' SSID'")
    wifi_ssid = wifi_info.split(":")[1].strip() if ":" in wifi_info else "N/A"

    return {
        "local_ip": local_ip,
        "wifi_ssid": wifi_ssid,
        "tailscale": tailscale_info,
    }

def get_realtime_metrics() -> Dict[str, Any]:
    """Get real-time system metrics"""
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    # CPU frequency
    cpu_freq = psutil.cpu_freq()

    return {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "percent": cpu_percent,
            "per_core": cpu_per_core,
            "frequency_mhz": cpu_freq.current if cpu_freq else 0,
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
        },
        "memory": {
            "percent": memory.percent,
            "used_gb": round(memory.used / (1024**3), 2),
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "pressure": "Normal" if memory.percent < 70 else "Alto" if memory.percent < 90 else "Crítico",
        },
        "disk": {
            "percent": round((disk.used / disk.total) * 100, 1),
            "used_gb": round(disk.used / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "total_gb": round(disk.total / (1024**3), 2),
        },
    }

# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard"""
    return get_dashboard_html()

@app.get("/nerdspace", response_class=HTMLResponse)
async def nerdspace():
    """Serve the NERD SPACE V5.0 dashboard"""
    template_path = Path(__file__).parent / "templates" / "nerdspace.html"
    if template_path.exists():
        return template_path.read_text()
    return "<h1>Template not found</h1>"

@app.get("/api/hardware")
async def api_hardware():
    """Get hardware information"""
    return get_hardware_info()

@app.get("/api/displays")
async def api_displays():
    """Get displays information"""
    return get_displays_info()

@app.get("/api/battery")
async def api_battery():
    """Get battery information"""
    return get_battery_info()

@app.get("/api/storage")
async def api_storage():
    """Get storage categories"""
    return get_storage_categories()

@app.get("/api/storage/category/{category_name}")
async def api_storage_category(category_name: str):
    """Get detailed breakdown of a storage category"""
    category_handlers = {
        "Aplicativos": get_applications_list,
        "Desenvolvedor": get_developer_breakdown,
        "iCloud Drive": get_icloud_breakdown,
        "Dados do Sistema": get_system_data_breakdown,
    }

    handler = category_handlers.get(category_name)
    if handler:
        return {"items": handler()}

    # For other categories, try to get folder breakdown
    storage = get_storage_categories()
    for cat in storage["categories"]:
        if cat["name"] == category_name and cat.get("paths"):
            return {"items": get_folder_breakdown(Path(cat["paths"][0]))}

    return {"items": []}

@app.get("/api/applications")
async def api_applications():
    """Get applications list"""
    return {"applications": get_applications_list()}

@app.get("/api/processes")
async def api_processes():
    """Get processes information"""
    return get_processes_info()

@app.get("/api/network")
async def api_network():
    """Get network information"""
    return get_network_info()

@app.get("/api/metrics")
async def api_metrics():
    """Get real-time metrics"""
    return get_realtime_metrics()

@app.get("/api/full")
async def api_full():
    """Get all system information"""
    return {
        "hardware": get_hardware_info(),
        "displays": get_displays_info(),
        "battery": get_battery_info(),
        "storage": get_storage_categories(),
        "processes": get_processes_info(),
        "network": get_network_info(),
        "metrics": get_realtime_metrics(),
    }

@app.post("/api/open-folder")
async def api_open_folder(data: dict):
    """Open a folder in Finder"""
    path = data.get("path", "")
    if path and os.path.exists(path):
        run_cmd(f'open "{path}"')
        return {"success": True}
    return {"success": False, "error": "Path not found"}

@app.post("/api/evict-icloud")
async def api_evict_icloud(data: dict):
    """Evict iCloud files to free space"""
    path = data.get("path", str(ICLOUD_DIR))
    if os.path.exists(path):
        # Count files first
        count = run_cmd(f'find "{path}" -type f ! -name "*.icloud" 2>/dev/null | wc -l')
        # Run evict in background
        run_cmd(f'find "{path}" -type f ! -name "*.icloud" -exec brctl evict {{}} \\; 2>/dev/null &')
        return {"success": True, "files_count": int(count.strip()) if count.strip() else 0}
    return {"success": False, "error": "Path not found"}

@app.post("/api/open-system-report")
async def api_open_system_report():
    """Open macOS System Report (Relatório do Sistema)"""
    run_cmd('open -a "System Information"')
    return {"success": True, "message": "System Report opened"}

@app.post("/api/open-activity-monitor")
async def api_open_activity_monitor():
    """Open Activity Monitor"""
    run_cmd('open -a "Activity Monitor"')
    return {"success": True, "message": "Activity Monitor opened"}

@app.post("/api/open-about-mac")
async def api_open_about_mac():
    """Open About This Mac"""
    run_cmd('open "x-apple.systempreferences:com.apple.SystemProfiler.AboutExtension"')
    return {"success": True, "message": "About This Mac opened"}

@app.get("/api/processes/detailed")
async def api_processes_detailed():
    """Get detailed process analysis with intelligence"""
    return get_processes_detailed()

# ═══════════════════════════════════════════════════════════════════════════════
# NERD SPACE API ENDPOINTS - Premium Features
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/greeting")
async def api_greeting():
    """Get personalized greeting for Danillo Costa"""
    return get_personalized_greeting()

@app.get("/api/weather")
async def api_weather():
    """Get São Paulo weather information"""
    return get_weather_sao_paulo()

@app.get("/api/power")
async def api_power():
    """Get detailed power/energy information"""
    return get_power_info()

@app.get("/api/tips")
async def api_tips():
    """Get Mac tips and shortcuts"""
    return {"tips": get_mac_tips()}

@app.get("/api/trash")
async def api_trash():
    """Get Trash folder information"""
    return get_trash_info()

@app.post("/api/empty-trash")
async def api_empty_trash():
    """Empty the Trash folder (requires user confirmation in Finder)"""
    try:
        # Open Finder and trigger empty trash with AppleScript
        result = run_cmd('''osascript -e 'tell application "Finder" to empty the trash' 2>&1''')
        if "error" in result.lower():
            return {"success": False, "error": result}
        return {"success": True, "message": "Lixeira esvaziada com sucesso!"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/open-trash")
async def api_open_trash():
    """Open Trash folder in Finder"""
    run_cmd('open ~/.Trash')
    return {"success": True, "message": "Lixeira aberta no Finder"}

@app.get("/api/nerdspace")
async def api_nerdspace():
    """Get all NERD SPACE data in one call"""
    return {
        "greeting": get_personalized_greeting(),
        "weather": get_weather_sao_paulo(),
        "power": get_power_info(),
        "tips": get_mac_tips()[:4],  # Top 4 tips
        "trash": get_trash_info(),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# NERD SPACE V5.0 - AI FIRST ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/claude-usage")
async def api_claude_usage():
    """Get Claude Max 20x usage statistics"""
    service = get_claude_usage_service()
    return service.get_usage_stats()

@app.post("/api/claude-usage/log")
async def api_claude_log(data: dict):
    """Log a message to Claude usage tracker"""
    service = get_claude_usage_service()
    service.log_message(
        tokens_in=data.get("tokens_in", 0),
        tokens_out=data.get("tokens_out", 0),
        model=data.get("model", "claude-3-sonnet"),
        extended_thinking=data.get("extended_thinking", False)
    )
    return {"success": True}

@app.get("/api/speedtest/last")
async def api_speedtest_last():
    """Get last speed test result"""
    service = get_speed_test_service()
    result = service.get_last_test()
    return result if result else {"status": "no_data"}

@app.post("/api/speedtest")
async def api_speedtest_run():
    """Run a new speed test"""
    service = get_speed_test_service()
    result = await service.run_test(full=True)
    return result

@app.get("/api/speedtest/history")
async def api_speedtest_history():
    """Get speed test history"""
    service = get_speed_test_service()
    return {"tests": service.get_history(limit=10)}

@app.get("/api/weather/v2")
async def api_weather_v2(city: str = "Sao Paulo"):
    """Get weather with new service (wttr.in fallback)"""
    service = get_weather_service()
    return await service.get_weather(city)

@app.get("/api/monitors")
async def api_monitors():
    """Get connected monitors information"""
    service = get_system_info_service()
    return service.get_monitors()

@app.get("/api/macos")
async def api_macos():
    """Get macOS version info (including codename like Tahoe)"""
    service = get_system_info_service()
    return service.get_macos_version()

@app.get("/api/storage/v2")
async def api_storage_v2():
    """Get accurate storage info using diskutil (fixes 135GB difference bug)"""
    service = get_system_info_service()
    return service.get_storage_real()

@app.get("/api/uptime")
async def api_uptime():
    """Get system uptime"""
    service = get_system_info_service()
    return service.get_uptime()

@app.get("/api/dev-tools")
async def api_dev_tools():
    """Get development tools versions"""
    service = get_system_info_service()
    return service.get_dev_tools()

@app.get("/api/quick-links")
async def api_quick_links():
    """Get quick links for dev tools"""
    service = get_system_info_service()
    return {"links": service.get_quick_links()}

@app.get("/api/history/recent")
async def api_history_recent():
    """Get recent metrics from history"""
    db = get_history_db()
    return {"metrics": db.get_recent_metrics(minutes=60)}

@app.get("/api/history/hourly")
async def api_history_hourly():
    """Get hourly aggregated metrics"""
    db = get_history_db()
    return {"metrics": db.get_hourly_metrics(hours=24)}

@app.get("/api/history/events")
async def api_history_events():
    """Get recent events/alerts"""
    db = get_history_db()
    return {"events": db.get_recent_events(limit=20)}

@app.get("/api/history/stats")
async def api_history_stats():
    """Get history database stats"""
    db = get_history_db()
    return db.get_db_stats()

@app.post("/api/open-app")
async def api_open_app(data: dict):
    """Open a Mac application"""
    app_name = data.get("app", "")
    allowed_apps = [
        "Terminal", "Finder", "Safari", "System Preferences", "Activity Monitor",
        "Disk Utility", "Console", "Keychain Access", "Network Utility",
        "System Information", "Automator", "Script Editor", "Font Book",
        "Digital Color Meter", "Screenshot", "Preview", "TextEdit", "Calculator",
        "Notes", "Reminders", "Calendar", "Mail", "Messages", "FaceTime",
        "Music", "Photos", "Podcasts", "Books", "News", "Stocks", "Home",
        "Shortcuts", "Clock", "Weather", "Maps", "Contacts", "App Store",
        "Xcode", "Visual Studio Code", "Warp", "iTerm", "Docker", "Postman"
    ]
    if app_name in allowed_apps:
        run_cmd(f'open -a "{app_name}"')
        return {"success": True, "message": f"{app_name} opened"}
    return {"success": False, "error": "App not allowed or not found"}

@app.post("/api/open-url")
async def api_open_url(data: dict):
    """Open a system URL (settings, etc)"""
    url = data.get("url", "")
    allowed_urls = {
        "storage": "x-apple.systempreferences:com.apple.settings.Storage",
        "battery": "x-apple.systempreferences:com.apple.Battery-Settings.extension",
        "network": "x-apple.systempreferences:com.apple.Network-Settings.extension",
        "bluetooth": "x-apple.systempreferences:com.apple.BluetoothSettings",
        "wifi": "x-apple.systempreferences:com.apple.wifi-settings-extension",
        "displays": "x-apple.systempreferences:com.apple.Displays-Settings.extension",
        "sound": "x-apple.systempreferences:com.apple.Sound-Settings.extension",
        "keyboard": "x-apple.systempreferences:com.apple.Keyboard-Settings.extension",
        "trackpad": "x-apple.systempreferences:com.apple.Trackpad-Settings.extension",
        "about": "x-apple.systempreferences:com.apple.SystemProfiler.AboutExtension",
        "security": "x-apple.systempreferences:com.apple.preference.security",
        "timemachine": "x-apple.systempreferences:com.apple.Time-Machine-Settings.extension",
        "icloud": "x-apple.systempreferences:com.apple.preferences.AppleIDPrefPane",
    }
    if url in allowed_urls:
        run_cmd(f'open "{allowed_urls[url]}"')
        return {"success": True, "message": f"Settings {url} opened"}
    return {"success": False, "error": "URL not allowed"}


@app.get("/api/insights")
async def api_insights():
    """Get AI-powered insights about system health"""
    service = get_ai_insights_service()

    # Verificar cache primeiro
    cached = service.get_cached_insights()
    if cached:
        return {
            "insights": cached,
            "summary": service.get_quick_summary(cached),
            "cached": True
        }

    # Coletar dados para análise
    storage_data = get_storage_categories()
    battery_data = get_battery_info()
    network_data = get_network_info()
    power_data = get_power_info()

    # Histórico de speed tests
    speed_service = get_speed_test_service()
    speed_history = speed_service.get_history(limit=5)

    # Gerar insights
    insights = service.generate_insights(
        storage_data=storage_data,
        battery_data=battery_data,
        network_data=network_data,
        speed_history=speed_history,
        power_data=power_data
    )

    return {
        "insights": insights,
        "summary": service.get_quick_summary(insights),
        "cached": False
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET FOR REAL-TIME UPDATES
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            metrics = get_realtime_metrics()
            await websocket.send_json(metrics)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD HTML - WORLD-CLASS UI
# ═══════════════════════════════════════════════════════════════════════════════

def get_dashboard_html() -> str:
    return '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NERD SPACE V5.0</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        /* ═══════════════════════════════════════════════════════════════════════
           PREMIUM THEME SYSTEM - Light/Dark/Auto
           ═══════════════════════════════════════════════════════════════════════ */

        :root {
            /* Dark Theme (Default) */
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a24;
            --bg-hover: rgba(255,255,255,0.05);
            --border-color: rgba(255,255,255,0.08);
            --border-hover: rgba(255,255,255,0.15);
            --text-primary: #ffffff;
            --text-secondary: #a1a1aa;
            --text-muted: #71717a;
            --accent-blue: #3b82f6;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-orange: #f97316;
            --accent-purple: #8b5cf6;
            --accent-cyan: #06b6d4;
            --glass-bg: rgba(26, 26, 36, 0.8);
            --glass-border: rgba(255,255,255,0.08);
            --shadow-color: rgba(0,0,0,0.4);
            --gradient-primary: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --gradient-success: linear-gradient(135deg, #22c55e, #06b6d4);
            --gradient-danger: linear-gradient(135deg, #ef4444, #f97316);
        }

        /* Light Theme */
        [data-theme="light"] {
            --bg-primary: #f8fafc;
            --bg-secondary: #f1f5f9;
            --bg-card: #ffffff;
            --bg-hover: rgba(0,0,0,0.03);
            --border-color: rgba(0,0,0,0.08);
            --border-hover: rgba(0,0,0,0.15);
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --glass-bg: rgba(255, 255, 255, 0.9);
            --glass-border: rgba(0,0,0,0.08);
            --shadow-color: rgba(0,0,0,0.1);
        }

        /* Auto (System) Theme */
        @media (prefers-color-scheme: light) {
            [data-theme="auto"] {
                --bg-primary: #f8fafc;
                --bg-secondary: #f1f5f9;
                --bg-card: #ffffff;
                --bg-hover: rgba(0,0,0,0.03);
                --border-color: rgba(0,0,0,0.08);
                --border-hover: rgba(0,0,0,0.15);
                --text-primary: #0f172a;
                --text-secondary: #475569;
                --text-muted: #94a3b8;
                --glass-bg: rgba(255, 255, 255, 0.9);
                --glass-border: rgba(0,0,0,0.08);
                --shadow-color: rgba(0,0,0,0.1);
            }
        }

        * { box-sizing: border-box; }

        body {
            background: var(--bg-primary);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
            margin: 0;
            min-height: 100vh;
        }

        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            border-radius: 20px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 30px var(--shadow-color);
        }

        .glass-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-3px);
            box-shadow: 0 12px 40px var(--shadow-color);
        }

        /* Premium Theme Toggle */
        .theme-toggle {
            display: flex;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 4px;
            gap: 2px;
            border: 1px solid var(--border-color);
        }

        .theme-btn {
            padding: 8px 12px;
            border-radius: 8px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 500;
        }

        .theme-btn:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }

        .theme-btn.active {
            background: var(--accent-blue);
            color: white;
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
        }

        .theme-btn i {
            width: 14px;
            height: 14px;
        }

        /* Premium Gradient Text */
        .gradient-text {
            background: var(--gradient-primary);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* Premium Badge */
        .premium-badge {
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            color: #000;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        .storage-bar {
            height: 24px;
            border-radius: 6px;
            overflow: hidden;
            display: flex;
            background: var(--bg-secondary);
        }

        .storage-segment {
            height: 100%;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }

        .storage-segment:hover {
            filter: brightness(1.2);
            transform: scaleY(1.1);
        }

        .category-item {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }

        .category-item:hover {
            background: rgba(255,255,255,0.05);
            border-color: var(--border-color);
        }

        .category-item.expanded {
            background: rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.3);
        }

        .sub-items {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
        }

        .sub-items.expanded {
            max-height: 500px;
        }

        .sub-item {
            display: flex;
            align-items: center;
            padding: 8px 16px 8px 48px;
            font-size: 13px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .sub-item:hover {
            background: rgba(255,255,255,0.03);
            color: var(--text-primary);
        }

        /* Quick Action Buttons for NERD SPACE */
        .quick-action-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 16px 12px;
            border-radius: 16px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 12px;
            font-weight: 500;
        }

        .quick-action-btn:hover {
            background: var(--bg-hover);
            border-color: var(--accent-blue);
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.2);
        }

        .quick-action-btn:active {
            transform: translateY(0);
        }

        /* NERD Tab Special Styling */
        .nerd-tab {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1));
            border: 1px solid rgba(139, 92, 246, 0.3);
        }

        .nerd-tab:hover {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.2));
        }

        .metric-ring {
            width: 120px;
            height: 120px;
            position: relative;
        }

        .metric-ring svg {
            transform: rotate(-90deg);
        }

        .metric-ring-bg {
            stroke: var(--bg-secondary);
        }

        .metric-ring-progress {
            stroke-linecap: round;
            transition: stroke-dashoffset 0.5s ease;
        }

        .tab-button {
            padding: 10px 20px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
            cursor: pointer;
            border: none;
            background: transparent;
            color: var(--text-secondary);
        }

        .tab-button:hover {
            background: rgba(255,255,255,0.05);
            color: var(--text-primary);
        }

        .tab-button.active {
            background: var(--accent-blue);
            color: white;
        }

        .badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .badge-green { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
        .badge-blue { background: rgba(59, 130, 246, 0.2); color: #3b82f6; }
        .badge-orange { background: rgba(249, 115, 22, 0.2); color: #f97316; }
        .badge-red { background: rgba(239, 68, 68, 0.2); color: #ef4444; }

        .glow-effect {
            box-shadow: 0 0 40px rgba(59, 130, 246, 0.15);
        }

        .pulse {
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* ═══════════════════════════════════════════════════════════════════
           ULTRA PREMIUM ENHANCEMENTS - NERD ELITE DESIGN SYSTEM
           ═══════════════════════════════════════════════════════════════════ */

        /* Animated Background Gradient */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background:
                radial-gradient(ellipse at 20% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(236, 72, 153, 0.05) 0%, transparent 50%);
            pointer-events: none;
            z-index: -1;
            animation: bgShift 20s ease-in-out infinite;
        }

        @keyframes bgShift {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(1.1); }
        }

        /* Floating Orbs */
        .floating-orbs {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
            overflow: hidden;
        }

        .orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(60px);
            animation: float 15s ease-in-out infinite;
        }

        .orb-1 {
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
            top: 10%;
            left: 10%;
            animation-delay: 0s;
        }

        .orb-2 {
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%);
            top: 60%;
            right: 10%;
            animation-delay: -5s;
        }

        .orb-3 {
            width: 350px;
            height: 350px;
            background: radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, transparent 70%);
            bottom: 10%;
            left: 30%;
            animation-delay: -10s;
        }

        @keyframes float {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            25% { transform: translate(30px, -30px) rotate(5deg); }
            50% { transform: translate(-20px, 20px) rotate(-5deg); }
            75% { transform: translate(40px, 10px) rotate(3deg); }
        }

        /* Premium Glass Card - Enhanced */
        .glass-card {
            background: linear-gradient(135deg, var(--glass-bg), rgba(255,255,255,0.02));
            backdrop-filter: blur(24px) saturate(180%);
            -webkit-backdrop-filter: blur(24px) saturate(180%);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow:
                0 4px 30px var(--shadow-color),
                inset 0 1px 0 rgba(255,255,255,0.05);
            position: relative;
            overflow: hidden;
        }

        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        }

        .glass-card:hover {
            border-color: rgba(139, 92, 246, 0.3);
            transform: translateY(-4px) scale(1.01);
            box-shadow:
                0 20px 60px var(--shadow-color),
                0 0 30px rgba(139, 92, 246, 0.1),
                inset 0 1px 0 rgba(255,255,255,0.1);
        }

        /* Premium Card with Glow */
        .premium-card {
            position: relative;
        }

        .premium-card::after {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 26px;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.3), rgba(139, 92, 246, 0.3), rgba(236, 72, 153, 0.3));
            z-index: -1;
            opacity: 0;
            transition: opacity 0.4s ease;
        }

        .premium-card:hover::after {
            opacity: 1;
        }

        /* Shimmer Effect */
        .shimmer {
            position: relative;
            overflow: hidden;
        }

        .shimmer::after {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 50%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 3s infinite;
        }

        @keyframes shimmer {
            100% { left: 200%; }
        }

        /* Ultra Premium Gradient Text */
        .ultra-gradient-text {
            background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899, #f97316);
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientFlow 5s ease infinite;
        }

        @keyframes gradientFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Neon Glow Effects */
        .neon-blue {
            text-shadow: 0 0 10px rgba(59, 130, 246, 0.5), 0 0 20px rgba(59, 130, 246, 0.3), 0 0 30px rgba(59, 130, 246, 0.2);
        }
        .neon-purple {
            text-shadow: 0 0 10px rgba(139, 92, 246, 0.5), 0 0 20px rgba(139, 92, 246, 0.3), 0 0 30px rgba(139, 92, 246, 0.2);
        }
        .neon-pink {
            text-shadow: 0 0 10px rgba(236, 72, 153, 0.5), 0 0 20px rgba(236, 72, 153, 0.3), 0 0 30px rgba(236, 72, 153, 0.2);
        }

        /* Premium Button */
        .btn-premium {
            position: relative;
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: white;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }

        .btn-premium::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
            transition: left 0.5s ease;
        }

        .btn-premium:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5);
        }

        .btn-premium:hover::before {
            left: 100%;
        }

        .btn-premium:active {
            transform: translateY(0);
        }

        /* Enhanced Quick Action Buttons */
        .quick-action-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 20px 16px;
            border-radius: 20px;
            background: linear-gradient(145deg, var(--bg-secondary), var(--bg-card));
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-size: 12px;
            font-weight: 600;
            position: relative;
            overflow: hidden;
        }

        .quick-action-btn::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .quick-action-btn:hover {
            border-color: rgba(139, 92, 246, 0.5);
            transform: translateY(-4px) scale(1.02);
            box-shadow:
                0 12px 30px rgba(139, 92, 246, 0.2),
                0 0 20px rgba(139, 92, 246, 0.1);
        }

        .quick-action-btn:hover::before {
            opacity: 1;
        }

        .quick-action-btn:active {
            transform: translateY(-2px) scale(1);
        }

        .quick-action-btn .icon-wrapper {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .quick-action-btn:hover .icon-wrapper {
            transform: scale(1.1) rotate(5deg);
        }

        /* Premium Tab Button */
        .tab-button {
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-secondary);
            position: relative;
            overflow: hidden;
        }

        .tab-button::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            width: 0;
            height: 3px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            border-radius: 3px;
            transition: all 0.3s ease;
            transform: translateX(-50%);
        }

        .tab-button:hover {
            background: rgba(139, 92, 246, 0.1);
            color: var(--text-primary);
            border-color: rgba(139, 92, 246, 0.2);
        }

        .tab-button:hover::after {
            width: 30px;
        }

        .tab-button.active {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2));
            color: white;
            border-color: rgba(139, 92, 246, 0.4);
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.3);
        }

        .tab-button.active::after {
            width: 50%;
        }

        /* NERD Tab Special - Enhanced */
        .nerd-tab {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(236, 72, 153, 0.15));
            border: 1px solid rgba(139, 92, 246, 0.4) !important;
            position: relative;
        }

        .nerd-tab::before {
            content: '';
            position: absolute;
            inset: -1px;
            border-radius: 13px;
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.5), rgba(236, 72, 153, 0.5));
            z-index: -1;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .nerd-tab:hover::before {
            opacity: 0.5;
        }

        .nerd-tab.active {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.3), rgba(236, 72, 153, 0.3));
            border-color: transparent !important;
        }

        .nerd-tab.active::before {
            opacity: 1;
        }

        /* ═══════════════════════════════════════════════════════════════════
           UX BEST PRACTICES - Navigation Tabs (Apple HIG + WCAG 2.1 AA)
           Min 44px height, clear selection, grouped, keyboard accessible
           ═══════════════════════════════════════════════════════════════════ */

        .nav-tab {
            display: flex;
            align-items: center;
            gap: 10px;
            min-height: 44px;
            padding: 8px 16px 8px 10px;
            border-radius: 12px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-secondary);
            position: relative;
            white-space: nowrap;
        }

        .nav-tab-icon {
            width: 28px;
            height: 28px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            transition: transform 0.25s ease, box-shadow 0.25s ease;
            flex-shrink: 0;
        }

        .nav-tab:hover {
            background: var(--glass-bg);
            color: var(--text-primary);
            border-color: rgba(255, 255, 255, 0.1);
        }

        .nav-tab:hover .nav-tab-icon {
            transform: scale(1.1);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .nav-tab:focus-visible {
            outline: 2px solid #3b82f6;
            outline-offset: 2px;
        }

        .nav-tab.active {
            background: linear-gradient(135deg, var(--glass-bg), rgba(139, 92, 246, 0.15));
            color: white;
            font-weight: 600;
            border-color: rgba(139, 92, 246, 0.4);
            box-shadow: 0 4px 20px rgba(139, 92, 246, 0.25),
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
        }

        .nav-tab.active::before {
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 3px;
            height: 60%;
            background: linear-gradient(180deg, #3b82f6, #8b5cf6);
            border-radius: 0 3px 3px 0;
        }

        .nav-tab.active .nav-tab-icon {
            box-shadow: 0 4px 16px rgba(139, 92, 246, 0.5);
        }

        .nav-badge-new {
            font-size: 9px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            background: linear-gradient(135deg, #8b5cf6, #ec4899);
            color: white;
            letter-spacing: 0.5px;
            animation: badgePulse 2s ease-in-out infinite;
        }

        @keyframes badgePulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.9; transform: scale(1.05); }
        }

        /* Scrollbar for nav */
        .scrollbar-thin::-webkit-scrollbar {
            height: 4px;
        }

        .scrollbar-thin::-webkit-scrollbar-track {
            background: transparent;
        }

        .scrollbar-thin::-webkit-scrollbar-thumb {
            background: rgba(139, 92, 246, 0.3);
            border-radius: 4px;
        }

        .scrollbar-thin::-webkit-scrollbar-thumb:hover {
            background: rgba(139, 92, 246, 0.5);
        }

        /* Premium Metric Ring */
        .metric-ring {
            width: 140px;
            height: 140px;
            position: relative;
            filter: drop-shadow(0 0 10px var(--ring-color, rgba(59, 130, 246, 0.3)));
        }

        .metric-ring svg {
            transform: rotate(-90deg);
        }

        .metric-ring-bg {
            stroke: var(--bg-secondary);
        }

        .metric-ring-progress {
            stroke-linecap: round;
            transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* Weather Card Premium */
        .weather-premium {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(6, 182, 212, 0.15));
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .weather-premium:hover {
            border-color: rgba(6, 182, 212, 0.5);
            box-shadow: 0 20px 60px rgba(6, 182, 212, 0.15);
        }

        /* Stats Number Animation */
        .stat-number {
            font-size: 3rem;
            font-weight: 800;
            letter-spacing: -2px;
            line-height: 1;
            transition: all 0.3s ease;
        }

        .stat-number:hover {
            transform: scale(1.05);
        }

        /* Premium Header */
        header {
            background: linear-gradient(180deg, var(--glass-bg) 0%, rgba(0,0,0,0) 100%) !important;
        }

        /* Scrollbar Premium */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.5), rgba(139, 92, 246, 0.5));
            border-radius: 5px;
            border: 2px solid var(--bg-secondary);
        }

        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.7), rgba(139, 92, 246, 0.7));
        }

        /* Selection Premium */
        ::selection {
            background: rgba(139, 92, 246, 0.3);
            color: white;
        }

        /* Tooltip Premium */
        [data-tooltip] {
            position: relative;
        }

        [data-tooltip]::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%) translateY(-5px);
            padding: 8px 12px;
            background: rgba(0,0,0,0.9);
            color: white;
            font-size: 12px;
            border-radius: 8px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: all 0.3s ease;
        }

        [data-tooltip]:hover::after {
            opacity: 1;
            transform: translateX(-50%) translateY(-10px);
        }

        /* Hero Section Premium */
        .hero-section {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.05));
            border-radius: 32px;
            padding: 40px;
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(139, 92, 246, 0.2);
        }

        .hero-section::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 50%);
            animation: heroGlow 10s ease-in-out infinite;
        }

        @keyframes heroGlow {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(-20%, 20%); }
        }

        /* Card Grid Animation */
        .card-grid > * {
            animation: cardFadeIn 0.5s ease forwards;
            opacity: 0;
        }

        .card-grid > *:nth-child(1) { animation-delay: 0.1s; }
        .card-grid > *:nth-child(2) { animation-delay: 0.2s; }
        .card-grid > *:nth-child(3) { animation-delay: 0.3s; }
        .card-grid > *:nth-child(4) { animation-delay: 0.4s; }
        .card-grid > *:nth-child(5) { animation-delay: 0.5s; }
        .card-grid > *:nth-child(6) { animation-delay: 0.6s; }

        @keyframes cardFadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Breathing Animation for Important Elements */
        .breathing {
            animation: breathing 3s ease-in-out infinite;
        }

        @keyframes breathing {
            0%, 100% { box-shadow: 0 0 20px rgba(139, 92, 246, 0.2); }
            50% { box-shadow: 0 0 40px rgba(139, 92, 246, 0.4); }
        }

        /* Number Counter Animation */
        @keyframes countUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .count-up {
            animation: countUp 0.5s ease forwards;
        }

        /* Apple-style Blur Effect */
        .apple-blur {
            backdrop-filter: blur(40px) saturate(200%);
            -webkit-backdrop-filter: blur(40px) saturate(200%);
        }

        /* Status Indicator Premium */
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            position: relative;
        }

        .status-dot::after {
            content: '';
            position: absolute;
            inset: -3px;
            border-radius: 50%;
            background: inherit;
            opacity: 0.3;
            animation: statusPulse 2s ease-in-out infinite;
        }

        @keyframes statusPulse {
            0%, 100% { transform: scale(1); opacity: 0.3; }
            50% { transform: scale(1.5); opacity: 0; }
        }

        /* Premium Link Style */
        .premium-link {
            color: var(--accent-blue);
            text-decoration: none;
            position: relative;
            transition: all 0.3s ease;
        }

        .premium-link::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 0;
            height: 2px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            transition: width 0.3s ease;
        }

        .premium-link:hover {
            color: var(--accent-purple);
        }

        .premium-link:hover::after {
            width: 100%;
        }

        .loading-skeleton {
            background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-card) 50%, var(--bg-secondary) 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }

        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .macbook-image {
            width: 200px;
            height: auto;
            filter: drop-shadow(0 20px 40px rgba(0,0,0,0.4));
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-secondary);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.2);
        }

        /* ═══════════════════════════════════════════════════════════════════
           PHASE 2 - ULTRA PREMIUM ENHANCEMENTS
           ═══════════════════════════════════════════════════════════════════ */

        /* Breathing Animation - Subtle pulse for important elements */
        .breathing {
            animation: breathing 4s ease-in-out infinite;
        }

        @keyframes breathing {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 4px 30px var(--shadow-color);
            }
            50% {
                transform: scale(1.01);
                box-shadow: 0 8px 40px rgba(139, 92, 246, 0.2);
            }
        }

        /* Premium Clock Card - Special Styling */
        .premium-clock-card {
            background: linear-gradient(145deg, rgba(139, 92, 246, 0.12), rgba(59, 130, 246, 0.08)) !important;
            border: 1px solid rgba(139, 92, 246, 0.35) !important;
            position: relative;
            overflow: hidden;
        }

        .premium-clock-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(
                from 0deg,
                transparent,
                rgba(139, 92, 246, 0.1),
                transparent,
                rgba(59, 130, 246, 0.1),
                transparent
            );
            animation: rotateGlow 10s linear infinite;
            opacity: 0.5;
        }

        @keyframes rotateGlow {
            100% { transform: rotate(360deg); }
        }

        /* Enhanced Stat Numbers with Counter Animation */
        .stat-number {
            font-size: 3.5rem;
            font-weight: 900;
            font-family: 'SF Pro Display', -apple-system, sans-serif;
            letter-spacing: -2px;
            line-height: 1;
            background: linear-gradient(135deg, currentColor, rgba(255,255,255,0.8));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
        }

        /* Skeleton Loading Animation */
        .skeleton {
            background: linear-gradient(
                90deg,
                rgba(255,255,255,0.05) 0%,
                rgba(255,255,255,0.1) 50%,
                rgba(255,255,255,0.05) 100%
            );
            background-size: 200% 100%;
            animation: skeleton-loading 1.5s ease-in-out infinite;
            border-radius: 8px;
        }

        @keyframes skeleton-loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        /* Glassmorphism Enhanced */
        .glass-ultra {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(30px) saturate(200%);
            -webkit-backdrop-filter: blur(30px) saturate(200%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow:
                0 8px 32px rgba(0, 0, 0, 0.3),
                inset 0 1px 0 rgba(255, 255, 255, 0.1),
                inset 0 -1px 0 rgba(0, 0, 0, 0.1);
        }

        /* Hover Lift Effect */
        .hover-lift {
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        .hover-lift:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.4),
                0 0 40px rgba(139, 92, 246, 0.15);
        }

        /* Ripple Click Effect */
        .ripple {
            position: relative;
            overflow: hidden;
        }

        .ripple::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: translate(-50%, -50%);
            transition: width 0.6s ease, height 0.6s ease, opacity 0.6s ease;
            opacity: 0;
        }

        .ripple:active::after {
            width: 300px;
            height: 300px;
            opacity: 1;
            transition: 0s;
        }

        /* Glow Border on Focus */
        .glow-focus:focus-within {
            border-color: rgba(139, 92, 246, 0.6) !important;
            box-shadow:
                0 0 0 3px rgba(139, 92, 246, 0.2),
                0 8px 30px rgba(139, 92, 246, 0.15);
        }

        /* Animated Gradient Border */
        .gradient-border {
            position: relative;
            background: var(--bg-card);
            border-radius: 20px;
        }

        .gradient-border::before {
            content: '';
            position: absolute;
            inset: -2px;
            border-radius: 22px;
            background: linear-gradient(
                135deg,
                #3b82f6,
                #8b5cf6,
                #ec4899,
                #f97316,
                #3b82f6
            );
            background-size: 400% 400%;
            animation: gradientBorderFlow 6s ease infinite;
            z-index: -1;
            opacity: 0.6;
        }

        @keyframes gradientBorderFlow {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }

        /* Card Grid Stagger Animation */
        .card-grid > * {
            opacity: 0;
            transform: translateY(20px);
            animation: cardFadeIn 0.5s ease forwards;
        }

        .card-grid > *:nth-child(1) { animation-delay: 0.1s; }
        .card-grid > *:nth-child(2) { animation-delay: 0.2s; }
        .card-grid > *:nth-child(3) { animation-delay: 0.3s; }
        .card-grid > *:nth-child(4) { animation-delay: 0.4s; }
        .card-grid > *:nth-child(5) { animation-delay: 0.5s; }
        .card-grid > *:nth-child(6) { animation-delay: 0.6s; }

        @keyframes cardFadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        /* Weather Card Premium */
        .weather-premium {
            background: linear-gradient(145deg, rgba(250, 204, 21, 0.08), rgba(249, 115, 22, 0.05)) !important;
            border-color: rgba(250, 204, 21, 0.2) !important;
        }

        .weather-premium:hover {
            border-color: rgba(250, 204, 21, 0.4) !important;
            box-shadow:
                0 20px 60px rgba(0, 0, 0, 0.3),
                0 0 40px rgba(250, 204, 21, 0.1);
        }

        /* Interactive Cursor Trail */
        .cursor-glow {
            position: fixed;
            width: 300px;
            height: 300px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.15), transparent 70%);
            pointer-events: none;
            z-index: 9999;
            transform: translate(-50%, -50%);
            transition: opacity 0.3s ease;
            opacity: 0;
        }

        body:hover .cursor-glow {
            opacity: 1;
        }

        /* Status Indicator Pulse */
        .status-pulse {
            position: relative;
        }

        .status-pulse::before {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            background: inherit;
            animation: statusPulse 2s ease-out infinite;
        }

        @keyframes statusPulse {
            0% { transform: scale(1); opacity: 0.8; }
            100% { transform: scale(2.5); opacity: 0; }
        }

        /* Text Gradient Shine */
        .text-shine {
            background: linear-gradient(
                120deg,
                rgba(255,255,255,0) 0%,
                rgba(255,255,255,0.8) 50%,
                rgba(255,255,255,0) 100%
            );
            background-size: 200% 100%;
            -webkit-background-clip: text;
            animation: textShine 3s linear infinite;
        }

        @keyframes textShine {
            100% { background-position: -200% 0; }
        }
    </style>
</head>
<body>
    <!-- Floating Orbs Background -->
    <div class="floating-orbs">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
    </div>

    <div id="app" class="min-h-screen" data-theme="dark">
        <!-- Ultra Premium Header -->
        <header class="sticky top-0 z-50 apple-blur border-b" style="background: linear-gradient(180deg, var(--glass-bg), transparent); border-color: var(--border-color);">
            <div class="max-w-[1800px] mx-auto px-6 py-4">
                <div class="flex items-center justify-between">
                    <!-- Logo & Brand - Enhanced -->
                    <div class="flex items-center gap-4">
                        <div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/30 breathing shimmer">
                            <i data-lucide="cpu" class="w-7 h-7 text-white"></i>
                        </div>
                        <div>
                            <div class="flex items-center gap-3">
                                <h1 class="text-2xl font-bold ultra-gradient-text">NERD SPACE</h1>
                                <span class="px-3 py-1 rounded-lg text-[11px] font-bold tracking-wider bg-gradient-to-r from-violet-400 to-purple-500 text-white shadow-lg shadow-purple-500/30">V5.0</span>
                                <span class="px-2 py-0.5 rounded text-[9px] font-bold tracking-widest bg-gradient-to-r from-cyan-400 to-blue-500 text-white animate-pulse">AI FIRST</span>
                            </div>
                            <p class="text-sm mt-0.5 flex items-center gap-2" style="color: var(--text-muted);">
                                <span class="status-dot bg-green-400"></span>
                                Enterprise System Intelligence Platform
                            </p>
                        </div>
                    </div>

                    <!-- Center: Theme Toggle -->
                    <div class="theme-toggle">
                        <button class="theme-btn" data-theme-value="light" title="Modo Claro">
                            <i data-lucide="sun" class="w-4 h-4"></i>
                            <span class="hidden sm:inline">Claro</span>
                        </button>
                        <button class="theme-btn active" data-theme-value="dark" title="Modo Escuro">
                            <i data-lucide="moon" class="w-4 h-4"></i>
                            <span class="hidden sm:inline">Escuro</span>
                        </button>
                        <button class="theme-btn" data-theme-value="auto" title="Acompanhar Sistema">
                            <i data-lucide="monitor" class="w-4 h-4"></i>
                            <span class="hidden sm:inline">Auto</span>
                        </button>
                    </div>

                    <!-- Right: Status -->
                    <div class="flex items-center gap-4">
                        <div id="connection-status" class="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 text-sm font-medium">
                            <span class="w-2 h-2 rounded-full bg-green-400 pulse"></span>
                            <span>Ao Vivo</span>
                        </div>
                        <div id="clock" class="text-sm font-mono px-4 py-2 rounded-xl" style="background: var(--bg-secondary); color: var(--text-secondary);"></div>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="max-w-[1800px] mx-auto px-6 py-6">
            <!-- Navigation Tabs - UX Best Practices: 44px height, grouped, clear selection -->
            <nav class="flex items-center gap-1 mb-8 overflow-x-auto pb-2 scrollbar-thin" role="tablist" aria-label="Navegação principal">
                <!-- Primary Group: Dashboard -->
                <div class="flex gap-1 pr-3 border-r border-zinc-700/50">
                    <button class="nav-tab" data-tab="overview" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-blue-500 to-cyan-500">
                            <i data-lucide="layout-dashboard" class="w-4 h-4"></i>
                        </div>
                        <span>Visão Geral</span>
                    </button>
                    <button class="nav-tab active" data-tab="nerdspace" role="tab" aria-selected="true">
                        <div class="nav-tab-icon bg-gradient-to-br from-purple-500 to-pink-500">
                            <i data-lucide="rocket" class="w-4 h-4"></i>
                        </div>
                        <span>NERD SPACE</span>
                        <span class="nav-badge-new">PRO</span>
                    </button>
                </div>

                <!-- System Group: Hardware & Storage -->
                <div class="flex gap-1 px-3 border-r border-zinc-700/50">
                    <button class="nav-tab" data-tab="hardware" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-green-500 to-emerald-500">
                            <i data-lucide="cpu" class="w-4 h-4"></i>
                        </div>
                        <span>Hardware</span>
                    </button>
                    <button class="nav-tab" data-tab="storage" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-amber-500 to-orange-500">
                            <i data-lucide="hard-drive" class="w-4 h-4"></i>
                        </div>
                        <span>Storage</span>
                    </button>
                </div>

                <!-- Activity Group: Apps, Processes, Network -->
                <div class="flex gap-1 pl-3">
                    <button class="nav-tab" data-tab="apps" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-pink-500 to-rose-500">
                            <i data-lucide="grid-3x3" class="w-4 h-4"></i>
                        </div>
                        <span>Apps</span>
                    </button>
                    <button class="nav-tab" data-tab="processes" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-red-500 to-orange-500">
                            <i data-lucide="activity" class="w-4 h-4"></i>
                        </div>
                        <span>Processos</span>
                    </button>
                    <button class="nav-tab" data-tab="network" role="tab" aria-selected="false">
                        <div class="nav-tab-icon bg-gradient-to-br from-cyan-500 to-blue-500">
                            <i data-lucide="wifi" class="w-4 h-4"></i>
                        </div>
                        <span>Rede</span>
                    </button>
                </div>
            </nav>

            <!-- Tab Content -->
            <div id="tab-content">
                <!-- Content will be loaded dynamically -->
            </div>
        </main>
    </div>

    <script>
    // ═══════════════════════════════════════════════════════════════════════════
    // PREMIUM THEME SYSTEM
    // ═══════════════════════════════════════════════════════════════════════════

    const ThemeManager = {
        init() {
            const saved = localStorage.getItem('theme') || 'dark';
            this.setTheme(saved);
            this.bindEvents();
        },

        setTheme(theme) {
            const app = document.getElementById('app');
            if (app) {
                app.setAttribute('data-theme', theme);
            }
            localStorage.setItem('theme', theme);
            this.updateButtons(theme);
        },

        updateButtons(activeTheme) {
            document.querySelectorAll('.theme-btn').forEach(btn => {
                const isActive = btn.dataset.themeValue === activeTheme;
                btn.classList.toggle('active', isActive);
            });
        },

        bindEvents() {
            document.querySelectorAll('.theme-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const theme = btn.dataset.themeValue;
                    this.setTheme(theme);
                    showToast('Tema alterado para ' + (theme === 'dark' ? 'Escuro' : theme === 'light' ? 'Claro' : 'Automático'), 'success');
                });
            });

            // Listen to system preference changes
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
                if (localStorage.getItem('theme') === 'auto') {
                    this.setTheme('auto');
                }
            });
        }
    };

    // ═══════════════════════════════════════════════════════════════════════════
    // STATE MANAGEMENT
    // ═══════════════════════════════════════════════════════════════════════════

    const state = {
        hardware: null,
        displays: null,
        battery: null,
        storage: null,
        applications: null,
        processes: null,
        network: null,
        metrics: null,
        greeting: null,
        weather: null,
        power: null,
        tips: null,
        expandedCategories: new Set(),
        currentTab: 'nerdspace',
    };

    // ═══════════════════════════════════════════════════════════════════════════
    // API FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════════

    async function fetchAPI(endpoint, timeoutMs = 30000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

        try {
            const res = await fetch(`/api/${endpoint}`, { signal: controller.signal });
            clearTimeout(timeoutId);
            if (!res.ok) {
                console.error(`API ${endpoint} returned ${res.status}`);
                return null;
            }
            return await res.json();
        } catch (e) {
            clearTimeout(timeoutId);
            if (e.name === 'AbortError') {
                console.error(`Timeout fetching ${endpoint} after ${timeoutMs}ms`);
            } else {
                console.error(`Error fetching ${endpoint}:`, e);
            }
            return null;
        }
    }

    async function loadAllData() {
        const [hardware, displays, battery, storage, processes, network] = await Promise.all([
            fetchAPI('hardware'),
            fetchAPI('displays'),
            fetchAPI('battery'),
            fetchAPI('storage'),  // Dados APFS já corrigidos no endpoint original
            fetchAPI('processes'),
            fetchAPI('network'),
        ]);

        state.hardware = hardware;
        state.displays = displays;
        state.battery = battery;
        state.storage = storage;
        state.processes = processes;
        state.network = network;

        renderCurrentTab();
    }

    async function loadCategoryItems(categoryName) {
        const res = await fetchAPI(`storage/category/${encodeURIComponent(categoryName)}`);
        return res?.items || [];
    }

    async function loadNerdSpace() {
        const [greeting, weather, power, tipsData, trash] = await Promise.all([
            fetchAPI('greeting'),
            fetchAPI('weather'),  // Formato compatível com frontend
            fetchAPI('power'),
            fetchAPI('tips'),
            fetchAPI('trash'),
        ]);

        state.greeting = greeting;
        state.weather = weather;
        state.power = power;
        state.tips = tipsData?.tips || [];
        state.trash = trash;

        // Update header greeting
        updateHeaderGreeting();
    }

    // Alias for compatibility
    async function loadNerdSpaceData() {
        await loadNerdSpace();
        renderCurrentTab();
    }

    function updateHeaderGreeting() {
        const greetingEl = document.getElementById('header-greeting');
        if (greetingEl && state.greeting) {
            greetingEl.innerHTML = `
                <span class="text-lg">${state.greeting.emoji}</span>
                <span class="font-medium">${state.greeting.greeting}</span>
            `;
        }
    }

    async function runSpeedTest() {
        const btn = document.getElementById('speedtest-btn');
        const result = document.getElementById('speedtest-result');
        if (btn) btn.disabled = true;

        // Animação premium durante o teste
        if (result) {
            result.innerHTML = `
                <div class="text-center">
                    <div class="relative w-24 h-24 mx-auto mb-4">
                        <div class="absolute inset-0 rounded-full border-4 border-cyan-500/20"></div>
                        <div class="absolute inset-0 rounded-full border-4 border-t-cyan-400 border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
                        <div class="absolute inset-2 rounded-full border-4 border-t-blue-400 border-r-transparent border-b-transparent border-l-transparent animate-spin" style="animation-duration: 1.5s; animation-direction: reverse;"></div>
                        <div class="absolute inset-0 flex items-center justify-center">
                            <i data-lucide="wifi" class="w-8 h-8 text-cyan-400 animate-pulse"></i>
                        </div>
                    </div>
                    <p class="text-cyan-400 font-medium animate-pulse">Medindo velocidade...</p>
                    <p class="text-zinc-500 text-xs mt-1">Download • Upload • Latência</p>
                </div>
            `;
            lucide.createIcons();
        }
        if (btn) btn.innerHTML = '<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> Testando...';

        try {
            const res = await fetch('/api/speedtest', { method: 'POST' });
            const data = await res.json();

            if (result && data.status === 'completed') {
                const providerName = data.provider?.provider_name || 'Unknown';
                result.innerHTML = `
                    <div class="w-full">
                        <!-- Métricas principais -->
                        <div class="grid grid-cols-3 gap-4 mb-4">
                            <div class="text-center p-3 rounded-xl bg-gradient-to-br from-green-500/10 to-emerald-500/10 border border-green-500/20">
                                <div class="text-2xl font-black text-green-400">${data.download_mbps || 0}</div>
                                <div class="text-xs text-zinc-500 flex items-center justify-center gap-1">
                                    <i data-lucide="arrow-down" class="w-3 h-3"></i> Mbps
                                </div>
                            </div>
                            <div class="text-center p-3 rounded-xl bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border border-blue-500/20">
                                <div class="text-2xl font-black text-blue-400">${data.upload_mbps || 0}</div>
                                <div class="text-xs text-zinc-500 flex items-center justify-center gap-1">
                                    <i data-lucide="arrow-up" class="w-3 h-3"></i> Mbps
                                </div>
                            </div>
                            <div class="text-center p-3 rounded-xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-purple-500/20">
                                <div class="text-2xl font-black text-purple-400">${data.latency_ms || 0}</div>
                                <div class="text-xs text-zinc-500">ms ping</div>
                            </div>
                        </div>
                        <!-- Info do provedor -->
                        <div class="flex items-center justify-between text-xs text-zinc-500 px-1">
                            <span class="flex items-center gap-1">
                                <i data-lucide="radio-tower" class="w-3 h-3"></i>
                                ${providerName}
                            </span>
                            <span class="flex items-center gap-1">
                                <i data-lucide="activity" class="w-3 h-3"></i>
                                Jitter: ${data.jitter_ms || 0}ms
                            </span>
                        </div>
                    </div>
                `;
            } else if (result) {
                result.innerHTML = `
                    <div class="text-center text-red-400">
                        <i data-lucide="alert-circle" class="w-10 h-10 mx-auto mb-2 opacity-60"></i>
                        <p>Erro no teste</p>
                        <p class="text-xs text-zinc-500 mt-1">${data.error || 'Tente novamente'}</p>
                    </div>
                `;
            }
            lucide.createIcons();
        } catch (err) {
            if (result) {
                result.innerHTML = `
                    <div class="text-center text-red-400">
                        <i data-lucide="wifi-off" class="w-10 h-10 mx-auto mb-2 opacity-60"></i>
                        <p>Falha na conexão</p>
                    </div>
                `;
                lucide.createIcons();
            }
        }

        if (btn) btn.disabled = false;
        if (btn) btn.innerHTML = '<i data-lucide="gauge" class="w-4 h-4"></i> Testar Novamente';
        lucide.createIcons();

        // Carregar histórico
        loadSpeedHistory();
    }

    async function loadSpeedHistory() {
        try {
            const res = await fetch('/api/speedtest/history');
            const data = await res.json();
            const historyEl = document.getElementById('speedtest-history');

            if (historyEl && data.tests && data.tests.length > 0) {
                const lastTests = data.tests.slice(-5).reverse();
                historyEl.innerHTML = `
                    <div class="mt-4 pt-4 border-t border-white/10">
                        <div class="text-xs text-zinc-500 mb-2 flex items-center gap-1">
                            <i data-lucide="history" class="w-3 h-3"></i>
                            Últimos testes
                        </div>
                        <div class="flex gap-2">
                            ${lastTests.map(t => {
                                const date = new Date(t.timestamp);
                                const time = date.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'});
                                return `
                                    <div class="flex-1 text-center p-2 rounded-lg bg-zinc-800/50 hover:bg-zinc-700/50 transition-colors cursor-default" title="${date.toLocaleDateString('pt-BR')} ${time}">
                                        <div class="text-sm font-bold text-green-400">${t.download_mbps}</div>
                                        <div class="text-[10px] text-zinc-600">${time}</div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
                lucide.createIcons();
            }
        } catch (e) {}
    }

    // ═══════════════════════════════════════════════════════════════════
    // AI INSIGHTS - PROACTIVE INTELLIGENCE
    // ═══════════════════════════════════════════════════════════════════

    async function loadInsights() {
        const container = document.getElementById('insights-container');
        const statusEl = document.getElementById('insights-status');

        // Show loading state
        container.innerHTML = `
            <div class="col-span-full flex items-center justify-center py-8">
                <div class="flex items-center gap-3 text-zinc-400">
                    <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analisando sistema...
                </div>
            </div>
        `;

        try {
            const res = await fetch('/api/insights');
            const data = await res.json();

            // Update status badge
            if (data.summary) {
                const statusColors = {
                    critical: 'from-red-400 to-red-600',
                    warning: 'from-amber-400 to-orange-500',
                    healthy: 'from-emerald-400 to-green-500'
                };
                statusEl.className = `px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-wider bg-gradient-to-r ${statusColors[data.summary.status] || statusColors.healthy} text-black shadow-lg`;
                statusEl.innerHTML = `${data.summary.icon} ${data.summary.message.toUpperCase()}`;
            }

            // Render insights
            if (data.insights && data.insights.length > 0) {
                container.innerHTML = data.insights.map((insight, i) => {
                    const severityColors = {
                        critical: 'border-red-500/40 from-red-500/10 to-red-600/5',
                        warning: 'border-amber-500/40 from-amber-500/10 to-orange-600/5',
                        info: 'border-blue-500/40 from-blue-500/10 to-sky-600/5',
                        success: 'border-emerald-500/40 from-emerald-500/10 to-green-600/5'
                    };

                    const severityBadge = {
                        critical: 'bg-red-500/20 text-red-400 border-red-500/30',
                        warning: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
                        info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
                        success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                    };

                    const actionButton = insight.action ? `
                        <button onclick="handleInsightAction('${insight.action}', '${insight.action_type}')"
                            class="mt-3 w-full py-2 px-3 rounded-xl text-xs font-medium bg-white/5 hover:bg-white/10 border border-white/10 hover:border-purple-500/50 transition-all duration-300 flex items-center justify-center gap-2">
                            <i data-lucide="${insight.action_type === 'url' ? 'external-link' : insight.action_type === 'app' ? 'app-window' : 'settings'}" class="w-3 h-3"></i>
                            ${insight.action_type === 'settings' ? 'Abrir Configurações' : insight.action_type === 'app' ? 'Abrir App' : 'Ver Detalhes'}
                        </button>
                    ` : '';

                    return `
                        <div class="group p-5 rounded-2xl bg-gradient-to-br ${severityColors[insight.severity] || severityColors.info} border transition-all duration-300 hover:transform hover:scale-[1.02] hover:shadow-xl" style="animation-delay: ${i * 0.1}s;">
                            <div class="flex items-start gap-4">
                                <div class="w-12 h-12 rounded-xl bg-white/10 border border-white/10 flex items-center justify-center text-2xl flex-shrink-0">
                                    ${insight.icon}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 mb-1">
                                        <h4 class="font-semibold text-white">${insight.title}</h4>
                                        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${severityBadge[insight.severity] || severityBadge.info}">${insight.severity}</span>
                                    </div>
                                    <p class="text-sm text-zinc-400 leading-relaxed">${insight.description}</p>
                                    ${insight.metric_value ? `
                                        <div class="mt-2 flex items-center gap-2">
                                            <span class="text-lg font-bold text-white">${insight.metric_value}</span>
                                            <span class="text-xs text-zinc-500">${insight.metric_label || ''}</span>
                                        </div>
                                    ` : ''}
                                    ${actionButton}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');

                lucide.createIcons();
            } else {
                container.innerHTML = `
                    <div class="col-span-full text-center py-8">
                        <div class="text-4xl mb-3">🎉</div>
                        <div class="text-zinc-400">Nenhum insight no momento. Sistema funcionando perfeitamente!</div>
                    </div>
                `;
            }
        } catch (e) {
            container.innerHTML = `
                <div class="col-span-full text-center py-8 text-red-400">
                    Erro ao carregar insights: ${e.message}
                </div>
            `;
        }
    }

    function handleInsightAction(action, actionType) {
        switch (actionType) {
            case 'url':
                window.open(action, '_blank');
                break;
            case 'app':
                openApp(action);
                break;
            case 'settings':
                // Handle system preferences URLs
                if (action.startsWith('x-apple.')) {
                    // Extract the setting key from the URL
                    const settingKey = action.includes('storage') ? 'storage' :
                                       action.includes('icloud') ? 'icloud' :
                                       action.includes('Battery') ? 'battery' :
                                       action.includes('wifi') ? 'wifi' :
                                       action.includes('security') ? 'security' : null;
                    if (settingKey) {
                        openSettings(settingKey);
                    } else {
                        window.open(action);
                    }
                }
                break;
            case 'function':
                if (action === 'speedtest') {
                    runSpeedTest();
                }
                break;
        }
    }

    async function openApp(appName) {
        const res = await fetch('/api/open-app', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app: appName })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`${appName} aberto!`, 'success');
        } else {
            showToast(`Erro ao abrir ${appName}`, 'error');
        }
    }

    async function openSettings(setting) {
        const res = await fetch('/api/open-url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: setting })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Configurações abertas!`, 'success');
        }
    }

    async function openTrash() {
        const res = await fetch('/api/open-trash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            showToast('Lixeira aberta no Finder!', 'success');
        }
    }

    async function emptyTrash() {
        if (!confirm('Tem certeza que deseja esvaziar a lixeira? Esta ação é irreversível!')) {
            return;
        }

        showToast('Esvaziando lixeira...', 'info');

        const res = await fetch('/api/empty-trash', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();

        if (data.success) {
            showToast('🎉 Lixeira esvaziada com sucesso!', 'success');
            // Refresh trash data
            setTimeout(() => loadNerdSpaceData(), 500);
        } else {
            showToast('Erro ao esvaziar lixeira: ' + (data.error || 'Erro desconhecido'), 'error');
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // RENDER FUNCTIONS
    // ═══════════════════════════════════════════════════════════════════════════

    function renderCurrentTab() {
        const content = document.getElementById('tab-content');

        switch(state.currentTab) {
            case 'overview':
                content.innerHTML = renderOverviewTab();
                break;
            case 'hardware':
                content.innerHTML = renderHardwareTab();
                break;
            case 'storage':
                content.innerHTML = renderStorageTab();
                break;
            case 'apps':
                content.innerHTML = renderAppsTab();
                break;
            case 'processes':
                content.innerHTML = renderProcessesTab();
                break;
            case 'network':
                content.innerHTML = renderNetworkTab();
                break;
            case 'nerdspace':
                content.innerHTML = renderNerdSpaceTab();
                break;
        }

        lucide.createIcons();
        attachEventListeners();
    }

    function renderOverviewTab() {
        if (!state.hardware || !state.storage || !state.battery) {
            return '<div class="text-center py-20 text-zinc-500">Carregando...</div>';
        }

        const h = state.hardware;
        const s = state.storage;
        const b = state.battery;
        const d = state.displays || [];

        return `
        <div class="grid grid-cols-12 gap-6">
            <!-- About This Mac Card -->
            <div class="col-span-12 lg:col-span-5 glass-card p-6 glow-effect">
                <div class="text-center mb-6">
                    <svg class="macbook-image mx-auto mb-4" viewBox="0 0 200 130" fill="none">
                        <rect x="20" y="10" width="160" height="100" rx="8" fill="#1a1a24" stroke="#3b82f6" stroke-width="2"/>
                        <rect x="30" y="20" width="140" height="80" rx="4" fill="#3b82f6" opacity="0.3"/>
                        <path d="M40 115 H160 L170 125 H30 Z" fill="#2a2a34"/>
                        <ellipse cx="100" cy="118" rx="30" ry="3" fill="#1a1a24"/>
                    </svg>
                    <h2 class="text-2xl font-semibold">${h.model_name}</h2>
                    <p class="text-zinc-500 text-sm">14 polegadas, nov. 2023</p>
                </div>

                <div class="space-y-4">
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Nome</span>
                        <span class="font-medium">${h.computer_name}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Chip</span>
                        <span class="font-medium">${h.chip}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Memória</span>
                        <span class="font-medium">${h.memory_gb} GB</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Número de Série</span>
                        <span class="font-mono text-sm">${h.serial_number}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Garantia</span>
                        <div class="flex items-center gap-2">
                            <span class="badge badge-green">Ativa</span>
                            <span class="text-sm">até ${h.warranty_expiry}</span>
                        </div>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">macOS</span>
                        <span class="font-medium">${h.system_version?.split(' ')[1] || 'Tahoe'} ${h.system_version?.match(/\\d+\\.\\d+/)?.[0] || '26.2'}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Uptime</span>
                        <span class="font-medium">${h.uptime}</span>
                    </div>
                </div>
            </div>

            <!-- Displays & Storage -->
            <div class="col-span-12 lg:col-span-7 space-y-6">
                <!-- Displays -->
                <div class="glass-card p-6">
                    <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                        <i data-lucide="monitor" class="w-5 h-5 text-blue-400"></i>
                        Telas (${d.length})
                    </h3>
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        ${d.map(display => `
                        <div class="p-4 rounded-xl bg-white/5 border border-white/5">
                            <div class="flex items-center gap-3 mb-3">
                                <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400">
                                    ${display.icon || '🖥️'}
                                </div>
                                <div>
                                    <div class="font-medium text-sm">${display.name}</div>
                                    <div class="text-xs text-zinc-500">${display.type || 'Monitor'}</div>
                                </div>
                            </div>
                            <div class="text-xs text-zinc-400 space-y-1">
                                <div>${display.resolution}</div>
                                <div>${display.refresh_rate || '60Hz'}</div>
                                ${display.is_main ? '<span class="badge badge-blue">Principal</span>' : ''}
                                ${display.rotation && display.rotation !== '0°' && display.rotation !== 'Supported' ? `<span class="badge badge-orange">Rotacionado ${display.rotation}</span>` : ''}
                            </div>
                        </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Storage Summary -->
                <div class="glass-card p-6">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-semibold flex items-center gap-2">
                            <i data-lucide="hard-drive" class="w-5 h-5 text-purple-400"></i>
                            Armazenamento
                        </h3>
                        <button onclick="switchTab('storage')" class="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1">
                            Ver detalhes <i data-lucide="chevron-right" class="w-4 h-4"></i>
                        </button>
                    </div>

                    <div class="mb-4">
                        <div class="flex justify-between text-sm mb-2">
                            <span class="text-zinc-400">Macintosh HD</span>
                            <span>${s.free_human} livres de ${s.total_human}</span>
                        </div>
                        <div class="storage-bar">
                            ${s.categories.map(cat => `
                            <div class="storage-segment" style="width: ${cat.percentage}%; background: ${cat.color};"
                                 title="${cat.name}: ${cat.size_human}"></div>
                            `).join('')}
                        </div>
                    </div>

                    <div class="flex flex-wrap gap-3 text-xs">
                        ${s.categories.slice(0, 6).map(cat => `
                        <div class="flex items-center gap-1.5">
                            <span class="w-2.5 h-2.5 rounded-full" style="background: ${cat.color}"></span>
                            <span class="text-zinc-400">${cat.name}</span>
                        </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Battery & Performance -->
                <div class="grid grid-cols-2 gap-6">
                    <!-- Battery -->
                    <div class="glass-card p-6">
                        <h3 class="text-sm font-medium text-zinc-400 mb-4">Bateria</h3>
                        <div class="flex items-center gap-4">
                            <div class="relative">
                                <svg class="w-16 h-16" viewBox="0 0 64 64">
                                    <circle cx="32" cy="32" r="28" fill="none" stroke="#1a1a24" stroke-width="6"/>
                                    <circle cx="32" cy="32" r="28" fill="none"
                                            stroke="${b.percentage > 20 ? '#22c55e' : '#ef4444'}"
                                            stroke-width="6"
                                            stroke-dasharray="${b.percentage * 1.76} 176"
                                            stroke-linecap="round"
                                            transform="rotate(-90 32 32)"/>
                                </svg>
                                <div class="absolute inset-0 flex items-center justify-center">
                                    <span class="text-lg font-bold">${b.percentage}%</span>
                                </div>
                            </div>
                            <div class="text-sm">
                                <div class="flex items-center gap-2 mb-1">
                                    ${b.is_charging ? '<i data-lucide="zap" class="w-4 h-4 text-yellow-400"></i>' : ''}
                                    <span class="${b.is_charging ? 'text-yellow-400' : 'text-zinc-400'}">
                                        ${b.is_charging ? 'Carregando' : b.power_source}
                                    </span>
                                </div>
                                <div class="text-zinc-500">${b.time_remaining}</div>
                                <div class="text-zinc-500">${b.cycle_count} ciclos</div>
                            </div>
                        </div>
                    </div>

                    <!-- Quick Stats -->
                    <div class="glass-card p-6">
                        <h3 class="text-sm font-medium text-zinc-400 mb-4">Performance</h3>
                        <div class="space-y-3">
                            <div>
                                <div class="flex justify-between text-xs mb-1">
                                    <span>CPU</span>
                                    <span id="cpu-value">--</span>
                                </div>
                                <div class="h-2 rounded-full bg-white/5 overflow-hidden">
                                    <div id="cpu-bar" class="h-full bg-blue-500 transition-all duration-300" style="width: 0%"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-xs mb-1">
                                    <span>Memória</span>
                                    <span id="mem-value">--</span>
                                </div>
                                <div class="h-2 rounded-full bg-white/5 overflow-hidden">
                                    <div id="mem-bar" class="h-full bg-purple-500 transition-all duration-300" style="width: 0%"></div>
                                </div>
                            </div>
                            <div>
                                <div class="flex justify-between text-xs mb-1">
                                    <span>Disco</span>
                                    <span id="disk-value">--</span>
                                </div>
                                <div class="h-2 rounded-full bg-white/5 overflow-hidden">
                                    <div id="disk-bar" class="h-full bg-green-500 transition-all duration-300" style="width: 0%"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `;
    }

    function renderHardwareTab() {
        if (!state.hardware) return '<div class="text-center py-20 text-zinc-500">Carregando...</div>';

        const h = state.hardware;
        const b = state.battery || {};
        const d = state.displays || [];

        return `
        <!-- Quick Actions -->
        <div class="flex flex-wrap gap-3 mb-6">
            <button onclick="openSystemReport()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium flex items-center gap-2 hover:opacity-90 transition-all">
                <i data-lucide="file-text" class="w-4 h-4"></i>
                Relatório do Sistema
            </button>
            <button onclick="openActivityMonitor()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 text-white font-medium flex items-center gap-2 hover:opacity-90 transition-all">
                <i data-lucide="activity" class="w-4 h-4"></i>
                Activity Monitor
            </button>
            <button onclick="openAboutMac()" class="px-4 py-2 rounded-xl bg-white/10 text-white font-medium flex items-center gap-2 hover:bg-white/20 transition-all">
                <i data-lucide="apple" class="w-4 h-4"></i>
                Sobre Este Mac
            </button>
        </div>

        <div class="grid grid-cols-12 gap-6">
            <!-- Chip Info -->
            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="cpu" class="w-5 h-5 text-blue-400"></i>
                    Processador
                </h3>

                <div class="flex items-center gap-6 mb-6">
                    <div class="w-20 h-20 rounded-2xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
                        <span class="text-3xl">🔮</span>
                    </div>
                    <div>
                        <h4 class="text-2xl font-bold">${h.chip}</h4>
                        <p class="text-zinc-400">Apple Silicon</p>
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-4 mb-6">
                    <div class="p-4 rounded-xl bg-white/5 text-center">
                        <div class="text-2xl font-bold text-blue-400">${h.total_cores}</div>
                        <div class="text-xs text-zinc-500">Núcleos CPU</div>
                    </div>
                    <div class="p-4 rounded-xl bg-white/5 text-center">
                        <div class="text-2xl font-bold text-purple-400">${h.gpu_cores}</div>
                        <div class="text-xs text-zinc-500">Núcleos GPU</div>
                    </div>
                    <div class="p-4 rounded-xl bg-white/5 text-center">
                        <div class="text-2xl font-bold text-green-400">${h.memory_gb}</div>
                        <div class="text-xs text-zinc-500">GB RAM</div>
                    </div>
                </div>

                <div class="space-y-3 text-sm">
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Performance Cores</span>
                        <span>${h.performance_cores} cores</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Efficiency Cores</span>
                        <span>${h.efficiency_cores} cores</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Metal Support</span>
                        <span class="badge badge-blue">${h.metal_support}</span>
                    </div>
                    <div class="flex justify-between py-2">
                        <span class="text-zinc-400">Neural Engine</span>
                        <span>16 cores</span>
                    </div>
                </div>
            </div>

            <!-- System Info -->
            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="laptop" class="w-5 h-5 text-green-400"></i>
                    Sistema
                </h3>

                <div class="space-y-3 text-sm">
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Model Identifier</span>
                        <span class="font-mono">${h.model_identifier}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Model Number</span>
                        <span class="font-mono">${h.model_number}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Serial Number</span>
                        <span class="font-mono">${h.serial_number}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Hardware UUID</span>
                        <span class="font-mono text-xs">${h.hardware_uuid?.substring(0, 20)}...</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">macOS Version</span>
                        <span>${h.system_version}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">Kernel</span>
                        <span class="font-mono">${h.kernel_version}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-white/5">
                        <span class="text-zinc-400">System Integrity</span>
                        <span class="badge badge-green">${h.sip_status}</span>
                    </div>
                    <div class="flex justify-between py-2">
                        <span class="text-zinc-400">Activation Lock</span>
                        <span class="badge badge-green">${h.activation_lock}</span>
                    </div>
                </div>
            </div>

            <!-- Battery Details -->
            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="battery-charging" class="w-5 h-5 text-yellow-400"></i>
                    Bateria
                </h3>

                <div class="flex items-center gap-6 mb-6">
                    <div class="relative">
                        <svg class="w-24 h-24" viewBox="0 0 96 96">
                            <circle cx="48" cy="48" r="42" fill="none" stroke="#1a1a24" stroke-width="8"/>
                            <circle cx="48" cy="48" r="42" fill="none"
                                    stroke="${b.percentage > 20 ? '#22c55e' : '#ef4444'}"
                                    stroke-width="8"
                                    stroke-dasharray="${b.percentage * 2.64} 264"
                                    stroke-linecap="round"
                                    transform="rotate(-90 48 48)"/>
                        </svg>
                        <div class="absolute inset-0 flex flex-col items-center justify-center">
                            <span class="text-2xl font-bold">${b.percentage}%</span>
                            <span class="text-xs text-zinc-500">${b.is_charging ? 'Carregando' : 'Bateria'}</span>
                        </div>
                    </div>
                    <div class="space-y-2">
                        <div class="text-sm">
                            <span class="text-zinc-400">Status:</span>
                            <span class="ml-2 badge ${b.condition === 'Normal' ? 'badge-green' : 'badge-orange'}">${b.condition}</span>
                        </div>
                        <div class="text-sm">
                            <span class="text-zinc-400">Capacidade:</span>
                            <span class="ml-2">${b.max_capacity}</span>
                        </div>
                        <div class="text-sm">
                            <span class="text-zinc-400">Ciclos:</span>
                            <span class="ml-2">${b.cycle_count} de 1000</span>
                        </div>
                    </div>
                </div>

                <div class="p-4 rounded-xl bg-green-500/10 border border-green-500/20">
                    <div class="flex items-center gap-2 text-green-400 text-sm">
                        <i data-lucide="shield-check" class="w-4 h-4"></i>
                        <span>Saúde da bateria: ${b.health_status || 'Excelente'}</span>
                    </div>
                    <p class="text-xs text-zinc-500 mt-1">
                        Com ${b.cycle_count} ciclos, sua bateria ainda tem ${Math.round(b.health_percentage || 100)}% de capacidade original.
                    </p>
                </div>
            </div>

            <!-- Displays -->
            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="monitor" class="w-5 h-5 text-cyan-400"></i>
                    Monitores (${d.length})
                </h3>

                <div class="space-y-4">
                    ${d.map((display, i) => `
                    <div class="p-4 rounded-xl bg-white/5 border border-white/5">
                        <div class="flex items-center justify-between mb-3">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                                    <i data-lucide="monitor" class="w-5 h-5"></i>
                                </div>
                                <div>
                                    <div class="font-medium">${display.name}</div>
                                    <div class="text-xs text-zinc-500">${display.type || 'Monitor Externo'}</div>
                                </div>
                            </div>
                            ${display.is_main ? '<span class="badge badge-blue">Principal</span>' : ''}
                        </div>
                        <div class="grid grid-cols-2 gap-4 text-sm">
                            <div>
                                <span class="text-zinc-500">Resolução:</span>
                                <span class="ml-2">${display.resolution}</span>
                            </div>
                            <div>
                                <span class="text-zinc-500">Refresh:</span>
                                <span class="ml-2">${display.refresh_rate || '60Hz'}</span>
                            </div>
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>
        </div>
        `;
    }

    function renderStorageTab() {
        if (!state.storage) return '<div class="text-center py-20 text-zinc-500">Carregando...</div>';

        const s = state.storage;

        return `
        <div class="glass-card p-6">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h3 class="text-xl font-semibold flex items-center gap-2">
                        <i data-lucide="hard-drive" class="w-6 h-6 text-purple-400"></i>
                        ${s.disk_name}
                    </h3>
                    <p class="text-zinc-500 text-sm mt-1">${s.device} • ${s.file_system} • SMART: ${s.smart_status}</p>
                </div>
                <div class="text-right">
                    <div class="text-2xl font-bold">${s.free_human}</div>
                    <div class="text-sm text-zinc-500">livres de ${s.total_human}</div>
                </div>
            </div>

            <!-- Storage Bar -->
            <div class="mb-8">
                <div class="storage-bar h-8 mb-4">
                    ${s.categories.map(cat => `
                    <div class="storage-segment"
                         style="width: ${cat.percentage}%; background: ${cat.color};"
                         title="${cat.name}: ${cat.size_human} (${cat.percentage}%)"
                         onclick="toggleCategory('${cat.name}')">
                    </div>
                    `).join('')}
                    <div class="storage-segment" style="flex: 1; background: #27272a;" title="Livre: ${s.free_human}"></div>
                </div>

                <!-- Legend -->
                <div class="flex flex-wrap gap-4 text-sm">
                    ${s.categories.map(cat => `
                    <div class="flex items-center gap-2 cursor-pointer hover:opacity-80" onclick="toggleCategory('${cat.name}')">
                        <span class="w-3 h-3 rounded-full" style="background: ${cat.color}"></span>
                        <span class="text-zinc-400">${cat.name}</span>
                        <span class="text-zinc-600">${cat.size_human}</span>
                    </div>
                    `).join('')}
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full bg-zinc-700"></span>
                        <span class="text-zinc-400">Livre</span>
                        <span class="text-zinc-600">${s.free_human}</span>
                    </div>
                </div>
            </div>

            <!-- Categories List -->
            <div class="space-y-2">
                ${s.categories.map(cat => `
                <div class="category-wrapper">
                    <div class="category-item ${state.expandedCategories.has(cat.name) ? 'expanded' : ''}"
                         onclick="toggleCategory('${cat.name}')">
                        <div class="w-10 h-10 rounded-xl flex items-center justify-center mr-4" style="background: ${cat.color}20">
                            <i data-lucide="${cat.icon}" class="w-5 h-5" style="color: ${cat.color}"></i>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium">${cat.name}</div>
                            <div class="text-sm text-zinc-500">${cat.percentage}% do disco</div>
                        </div>
                        <div class="text-right mr-4">
                            <div class="font-medium">${cat.size_human}</div>
                        </div>
                        <i data-lucide="chevron-${state.expandedCategories.has(cat.name) ? 'down' : 'right'}"
                           class="w-5 h-5 text-zinc-500 transition-transform"></i>
                    </div>
                    <div class="sub-items ${state.expandedCategories.has(cat.name) ? 'expanded' : ''}"
                         id="sub-${cat.name.replace(/\\s/g, '-')}">
                        <div class="py-2 text-center text-zinc-500 text-sm">
                            <i data-lucide="loader" class="w-4 h-4 inline animate-spin"></i>
                            Carregando...
                        </div>
                    </div>
                </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    function renderAppsTab() {
        return `
        <div class="glass-card p-6">
            <div class="flex items-center justify-between mb-6">
                <h3 class="text-xl font-semibold flex items-center gap-2">
                    <i data-lucide="grid-3x3" class="w-6 h-6 text-red-400"></i>
                    Aplicativos
                </h3>
                <div class="flex items-center gap-2">
                    <input type="text" id="app-search" placeholder="Buscar..."
                           class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-sm focus:outline-none focus:border-blue-500"
                           onkeyup="filterApps(this.value)">
                </div>
            </div>

            <div id="apps-list" class="space-y-2">
                <div class="text-center py-10 text-zinc-500">
                    <i data-lucide="loader" class="w-6 h-6 inline animate-spin"></i>
                    <p class="mt-2">Carregando aplicativos...</p>
                </div>
            </div>
        </div>
        `;
    }

    function renderProcessesTab() {
        if (!state.processesDetailed) {
            // Load detailed processes
            fetch('/api/processes/detailed')
                .then(r => r.json())
                .then(data => {
                    state.processesDetailed = data;
                    renderTab('processes');
                });
            return '<div class="text-center py-20 text-zinc-500"><i data-lucide="loader" class="w-6 h-6 inline animate-spin"></i> Carregando análise inteligente...</div>';
        }

        const p = state.processesDetailed;
        const colorMap = {
            blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
            purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
            pink: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
            green: 'bg-green-500/20 text-green-400 border-green-500/30',
            cyan: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
            zinc: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
            amber: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
            gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
            red: 'bg-red-500/20 text-red-400 border-red-500/30',
        };

        return `
        <!-- Action Buttons -->
        <div class="flex flex-wrap gap-3 mb-6">
            <button onclick="openSystemReport()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 text-white font-medium flex items-center gap-2 hover:opacity-90 transition-all">
                <i data-lucide="file-text" class="w-4 h-4"></i>
                Relatório do Sistema
            </button>
            <button onclick="openActivityMonitor()" class="px-4 py-2 rounded-xl bg-gradient-to-r from-purple-500 to-purple-600 text-white font-medium flex items-center gap-2 hover:opacity-90 transition-all">
                <i data-lucide="activity" class="w-4 h-4"></i>
                Activity Monitor
            </button>
            <button onclick="refreshProcesses()" class="px-4 py-2 rounded-xl bg-white/10 text-white font-medium flex items-center gap-2 hover:bg-white/20 transition-all">
                <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                Atualizar
            </button>
        </div>

        <!-- Summary Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="glass-card p-4">
                <div class="text-sm text-zinc-400">Processos</div>
                <div class="text-2xl font-bold">${p.summary.total_processes}</div>
            </div>
            <div class="glass-card p-4">
                <div class="text-sm text-zinc-400">CPU Total</div>
                <div class="text-2xl font-bold ${p.summary.cpu_percent > 80 ? 'text-red-400' : p.summary.cpu_percent > 50 ? 'text-amber-400' : 'text-green-400'}">${p.summary.cpu_percent.toFixed(1)}%</div>
            </div>
            <div class="glass-card p-4">
                <div class="text-sm text-zinc-400">Memória</div>
                <div class="text-2xl font-bold ${p.summary.memory_percent > 85 ? 'text-red-400' : p.summary.memory_percent > 70 ? 'text-amber-400' : 'text-green-400'}">${p.summary.memory_used_gb}/${p.summary.memory_total_gb} GB</div>
            </div>
            <div class="glass-card p-4">
                <div class="text-sm text-zinc-400">Alertas</div>
                <div class="text-2xl font-bold">
                    ${p.summary.critical_alerts > 0 ? `<span class="text-red-400">${p.summary.critical_alerts} críticos</span>` : ''}
                    ${p.summary.warning_alerts > 0 ? `<span class="text-amber-400">${p.summary.warning_alerts} avisos</span>` : ''}
                    ${p.summary.critical_alerts === 0 && p.summary.warning_alerts === 0 ? '<span class="text-green-400">Tudo OK</span>' : ''}
                </div>
            </div>
        </div>

        <!-- Insights/Alerts Panel -->
        ${p.insights && p.insights.length > 0 ? `
        <div class="glass-card p-6 mb-6 border-l-4 ${p.insights[0].type === 'critical' ? 'border-red-500' : p.insights[0].type === 'warning' ? 'border-amber-500' : 'border-blue-500'}">
            <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                <i data-lucide="brain" class="w-5 h-5 text-purple-400"></i>
                Insights Inteligentes
            </h3>
            <div class="space-y-3">
                ${p.insights.slice(0, 5).map(insight => `
                <div class="flex items-start gap-3 p-3 rounded-lg ${insight.type === 'critical' ? 'bg-red-500/10 border border-red-500/20' : insight.type === 'warning' ? 'bg-amber-500/10 border border-amber-500/20' : 'bg-blue-500/10 border border-blue-500/20'}">
                    <i data-lucide="${insight.icon}" class="w-5 h-5 mt-0.5 ${insight.type === 'critical' ? 'text-red-400' : insight.type === 'warning' ? 'text-amber-400' : 'text-blue-400'}"></i>
                    <div class="flex-1">
                        <div class="font-medium ${insight.type === 'critical' ? 'text-red-400' : insight.type === 'warning' ? 'text-amber-400' : 'text-blue-400'}">${insight.process} (PID: ${insight.pid})</div>
                        <div class="text-sm text-zinc-400">${insight.message}</div>
                    </div>
                </div>
                `).join('')}
            </div>
        </div>
        ` : ''}

        <!-- Main Process Grid -->
        <div class="grid grid-cols-12 gap-6">
            <!-- Top CPU -->
            <div class="col-span-12 lg:col-span-4 glass-card p-6">
                <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                    <i data-lucide="cpu" class="w-5 h-5 text-blue-400"></i>
                    Top CPU
                </h3>
                <div class="space-y-2">
                    ${p.by_cpu.slice(0, 10).map(proc => `
                    <div class="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all cursor-pointer group" title="Categoria: ${proc.category.name}">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg ${colorMap[proc.category.color] || colorMap.gray} flex items-center justify-center">
                                <i data-lucide="${proc.category.icon}" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="font-mono text-sm">${proc.name}</div>
                                <div class="text-xs text-zinc-500">${proc.threads} threads</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="font-medium ${proc.cpu_percent > 50 ? 'text-red-400' : proc.cpu_percent > 20 ? 'text-amber-400' : 'text-blue-400'}">${proc.cpu_percent}%</div>
                            <div class="text-xs text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity">PID: ${proc.pid}</div>
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>

            <!-- Top Memória -->
            <div class="col-span-12 lg:col-span-4 glass-card p-6">
                <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                    <i data-lucide="memory-stick" class="w-5 h-5 text-purple-400"></i>
                    Top Memória
                </h3>
                <div class="space-y-2">
                    ${p.by_memory.slice(0, 10).map(proc => `
                    <div class="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all cursor-pointer group" title="Categoria: ${proc.category.name}">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg ${colorMap[proc.category.color] || colorMap.gray} flex items-center justify-center">
                                <i data-lucide="${proc.category.icon}" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="font-mono text-sm">${proc.name}</div>
                                <div class="text-xs text-zinc-500">${proc.uptime}</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="font-medium ${proc.memory_mb > 2000 ? 'text-red-400' : proc.memory_mb > 500 ? 'text-amber-400' : 'text-purple-400'}">${proc.memory_mb.toFixed(0)} MB</div>
                            <div class="text-xs text-zinc-500">${proc.memory_percent.toFixed(1)}%</div>
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>

            <!-- Top Disco I/O -->
            <div class="col-span-12 lg:col-span-4 glass-card p-6">
                <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                    <i data-lucide="hard-drive" class="w-5 h-5 text-green-400"></i>
                    Top Disco I/O
                </h3>
                <div class="space-y-2">
                    ${p.by_disk.slice(0, 10).map(proc => `
                    <div class="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all cursor-pointer group" title="Categoria: ${proc.category.name}">
                        <div class="flex items-center gap-3">
                            <div class="w-8 h-8 rounded-lg ${colorMap[proc.category.color] || colorMap.gray} flex items-center justify-center">
                                <i data-lucide="${proc.category.icon}" class="w-4 h-4"></i>
                            </div>
                            <div>
                                <div class="font-mono text-sm">${proc.name}</div>
                                <div class="text-xs text-zinc-500">${proc.status}</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="font-medium text-green-400">
                                <span class="text-emerald-400">↓${proc.disk_read_mb}</span>
                                <span class="text-orange-400">↑${proc.disk_write_mb}</span>
                            </div>
                            <div class="text-xs text-zinc-500">MB</div>
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>
        </div>

        <!-- Categories Overview -->
        <div class="glass-card p-6 mt-6">
            <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
                <i data-lucide="layers" class="w-5 h-5 text-cyan-400"></i>
                Por Categoria
            </h3>
            <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
                ${Object.entries(p.categories).map(([id, cat]) => `
                <div class="p-4 rounded-xl ${colorMap[cat.color] || colorMap.gray} border text-center hover:scale-105 transition-transform cursor-pointer" title="Clique para ver processos">
                    <i data-lucide="${cat.icon}" class="w-6 h-6 mx-auto mb-2"></i>
                    <div class="font-medium text-sm">${cat.name}</div>
                    <div class="text-xs opacity-75">${cat.count} processos</div>
                    <div class="text-xs mt-1">CPU: ${cat.total_cpu.toFixed(1)}%</div>
                    <div class="text-xs">RAM: ${(cat.total_memory/1024).toFixed(1)} GB</div>
                </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    async function openSystemReport() {
        await fetch('/api/open-system-report', { method: 'POST' });
        showToast('Abrindo Relatório do Sistema...', 'success');
    }

    async function openActivityMonitor() {
        await fetch('/api/open-activity-monitor', { method: 'POST' });
        showToast('Abrindo Activity Monitor...', 'success');
    }

    async function openAboutMac() {
        await fetch('/api/open-about-mac', { method: 'POST' });
        showToast('Abrindo Sobre Este Mac...', 'success');
    }

    function refreshProcesses() {
        state.processesDetailed = null;
        renderTab('processes');
        showToast('Atualizando processos...', 'info');
    }

    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        const colors = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            info: 'bg-blue-500',
            warning: 'bg-amber-500'
        };
        toast.className = 'fixed bottom-4 right-4 px-6 py-3 rounded-xl ' + colors[type] + ' text-white font-medium shadow-2xl z-50 animate-pulse';
        toast.innerHTML = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    function renderNetworkTab() {
        if (!state.network) return '<div class="text-center py-20 text-zinc-500">Carregando...</div>';

        const n = state.network;

        return `
        <div class="grid grid-cols-12 gap-6">
            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="wifi" class="w-5 h-5 text-green-400"></i>
                    Conectividade
                </h3>

                <div class="space-y-4">
                    <div class="p-4 rounded-xl bg-white/5">
                        <div class="flex items-center gap-3 mb-2">
                            <i data-lucide="wifi" class="w-5 h-5 text-green-400"></i>
                            <span class="font-medium">Wi-Fi</span>
                        </div>
                        <div class="text-sm text-zinc-400">
                            <div>SSID: ${n.wifi_ssid}</div>
                            <div>IP Local: ${n.local_ip}</div>
                        </div>
                    </div>

                    ${n.tailscale?.connected ? `
                    <div class="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                        <div class="flex items-center gap-3 mb-2">
                            <svg class="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                            <span class="font-medium text-blue-400">Tailscale Conectado</span>
                        </div>
                        <div class="text-sm space-y-1">
                            <div class="text-zinc-400">IP: <span class="font-mono">${n.tailscale.ip}</span></div>
                            <div class="text-zinc-400">Hostname:</div>
                            <div class="font-mono text-xs text-blue-300 break-all">${n.tailscale.hostname}</div>
                        </div>
                    </div>
                    ` : `
                    <div class="p-4 rounded-xl bg-white/5">
                        <div class="flex items-center gap-3 text-zinc-500">
                            <i data-lucide="cloud-off" class="w-5 h-5"></i>
                            <span>Tailscale não conectado</span>
                        </div>
                    </div>
                    `}
                </div>
            </div>

            <div class="col-span-12 lg:col-span-6 glass-card p-6">
                <h3 class="text-lg font-semibold mb-6 flex items-center gap-2">
                    <i data-lucide="link" class="w-5 h-5 text-purple-400"></i>
                    Links de Acesso
                </h3>

                <div class="space-y-3">
                    <div class="p-4 rounded-xl bg-white/5">
                        <div class="text-sm text-zinc-400 mb-1">Local</div>
                        <a href="http://localhost:8888" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono text-sm">
                            http://localhost:8888
                        </a>
                    </div>
                    <div class="p-4 rounded-xl bg-white/5">
                        <div class="text-sm text-zinc-400 mb-1">Rede Local</div>
                        <a href="http://${n.local_ip}:8888" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono text-sm">
                            http://${n.local_ip}:8888
                        </a>
                    </div>
                    ${n.tailscale?.connected ? `
                    <div class="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                        <div class="text-sm text-zinc-400 mb-1">Tailscale (Qualquer lugar)</div>
                        <a href="http://${n.tailscale.hostname}:8888" target="_blank" class="text-blue-400 hover:text-blue-300 font-mono text-sm break-all">
                            http://${n.tailscale.hostname}:8888
                        </a>
                    </div>
                    ` : ''}
                </div>
            </div>
        </div>
        `;
    }

    function renderNerdSpaceTab() {
        const g = state.greeting || {};
        const w = state.weather || {};
        const p = state.power || {};
        const tips = state.tips || [];

        return `
        <div class="space-y-8 card-grid">
            <!-- ULTRA PREMIUM Hero Section -->
            <div class="hero-section relative overflow-hidden">
                <!-- Animated Background Elements -->
                <div class="absolute top-0 right-0 w-[500px] h-[500px] bg-gradient-to-bl from-purple-500/30 via-pink-500/20 to-transparent rounded-full blur-3xl animate-pulse"></div>
                <div class="absolute bottom-0 left-0 w-[400px] h-[400px] bg-gradient-to-tr from-blue-500/30 via-cyan-500/20 to-transparent rounded-full blur-3xl" style="animation: float 15s ease-in-out infinite;"></div>
                <div class="absolute top-1/2 left-1/2 w-[300px] h-[300px] bg-gradient-to-r from-violet-500/15 to-fuchsia-500/15 rounded-full blur-3xl" style="animation: float 20s ease-in-out infinite reverse;"></div>

                <div class="relative z-10">
                    <div class="flex items-center justify-between flex-wrap gap-8">
                        <!-- Left: Greeting -->
                        <div class="flex-1">
                            <div class="flex items-center gap-4 mb-4">
                                <div class="text-6xl animate-bounce" style="animation-duration: 3s;">${g.emoji || '🚀'}</div>
                                <div>
                                    <p class="text-sm uppercase tracking-widest text-purple-400 font-semibold mb-1">Bem-vindo de volta</p>
                                    <h1 class="text-4xl lg:text-5xl font-black ultra-gradient-text">${g.greeting || 'Olá, Danillo!'}</h1>
                                    <p class="text-zinc-400 mt-1 flex items-center gap-2">
                                        <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
                                        ${g.period || 'Pronto para dominar o dia'}
                                    </p>
                                </div>
                            </div>
                            <p class="text-xl text-zinc-300 mt-6 max-w-xl leading-relaxed">
                                Seu <span class="text-purple-400 font-semibold">hub de comando premium</span> para controle total do seu MacBook Pro.
                            </p>
                            <div class="flex gap-3 mt-6">
                                <span class="px-3 py-1.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">M3 Max</span>
                                <span class="px-3 py-1.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">36GB RAM</span>
                                <span class="px-3 py-1.5 rounded-full text-xs font-semibold bg-pink-500/20 text-pink-400 border border-pink-500/30">macOS Tahoe</span>
                            </div>
                        </div>

                        <!-- Right: Premium Clock + Weather Integrated -->
                        <div class="glass-card p-6 text-center min-w-[260px] breathing premium-clock-card" style="background: rgba(139, 92, 246, 0.1); border-color: rgba(139, 92, 246, 0.3);">
                            <!-- Location & Timezone -->
                            <div class="flex items-center justify-center gap-2 mb-3">
                                <span class="text-xs uppercase tracking-widest text-purple-400 font-semibold">São Paulo</span>
                                <span class="text-zinc-600">•</span>
                                <span class="text-xs text-zinc-500">GMT-3</span>
                            </div>

                            <!-- Main Time -->
                            <div class="text-5xl font-mono font-black ultra-gradient-text mb-1">${g.time_sp || '--:--'}</div>

                            <!-- Date -->
                            <div class="text-sm text-zinc-400 font-medium">${g.day_name || ''}, ${g.date_sp || ''}</div>

                            <!-- Weather & Battery Integration (Discrete) -->
                            <div class="mt-4 pt-4 border-t border-white/10 flex items-center justify-center gap-3">
                                ${w.temperature ? `
                                <div class="flex items-center gap-2">
                                    <span class="text-xl">${w.is_day !== false ? '☀️' : '🌙'}</span>
                                    <div class="text-left">
                                        <div class="text-lg font-bold text-yellow-400">${w.temperature}°C</div>
                                        <div class="text-[10px] text-zinc-500">${w.description || ''}</div>
                                    </div>
                                </div>
                                ` : `
                                <div class="text-zinc-500 text-xs">☁️</div>
                                `}
                                <div class="w-px h-8 bg-white/10"></div>
                                <!-- Battery Mini Widget -->
                                <div class="flex items-center gap-2">
                                    <span class="text-xl">${p.is_charging ? '⚡' : '🔋'}</span>
                                    <div class="text-left">
                                        <div class="text-lg font-bold ${(p.battery_percent || 0) > 20 ? 'text-green-400' : 'text-red-400'}">${p.battery_percent || '--'}%</div>
                                        <div class="text-[10px] text-zinc-500">${p.is_charging ? 'Carregando' : p.time_remaining_mins ? p.time_remaining_mins + 'min' : 'Bateria'}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- AI INSIGHTS - PROACTIVE INTELLIGENCE (TOP PRIORITY) -->
            <div class="glass-card p-6 premium-card mb-6" id="insights-section">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold flex items-center gap-2">
                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-400 via-purple-500 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-purple-500/30 shimmer pulse-glow">
                            <i data-lucide="brain" class="w-5 h-5 text-white"></i>
                        </div>
                        <div>
                            <span class="ultra-gradient-text">AI Insights</span>
                            <p class="text-[10px] text-zinc-500 font-normal">Análise proativa do sistema</p>
                        </div>
                    </h3>
                    <div class="flex items-center gap-2">
                        <span id="insights-status" class="px-2 py-1 rounded-lg text-[10px] font-bold tracking-wider bg-gradient-to-r from-emerald-400 to-green-500 text-black">🟢 HEALTHY</span>
                        <button onclick="loadInsights()" class="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition-all border border-white/10 hover:border-purple-500/50">
                            <i data-lucide="refresh-cw" class="w-3.5 h-3.5 text-zinc-400 hover:text-purple-400"></i>
                        </button>
                    </div>
                </div>
                <div id="insights-container" class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div class="p-4 rounded-xl bg-white/5 border border-white/10 animate-pulse">
                        <div class="flex items-center gap-2">
                            <div class="w-8 h-8 rounded-lg bg-zinc-700"></div>
                            <div class="flex-1">
                                <div class="h-3 bg-zinc-700 rounded w-3/4 mb-1.5"></div>
                                <div class="h-2 bg-zinc-800 rounded w-full"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Stats Grid: Speed Test + Battery Details -->
            <div class="grid grid-cols-12 gap-6">
                <!-- Speed Test - Premium -->
                <div class="col-span-12 lg:col-span-4 glass-card p-6">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="text-lg font-bold flex items-center gap-2">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                                <i data-lucide="gauge" class="w-5 h-5 text-white"></i>
                            </div>
                            <span>Velocidade</span>
                        </h3>
                        <span class="px-2 py-1 rounded-lg text-xs bg-cyan-500/20 text-cyan-400 font-semibold">Internet</span>
                    </div>
                    <div id="speedtest-result" class="min-h-[160px] flex items-center justify-center mb-6">
                        <div class="text-center">
                            <div class="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-2 border-dashed border-cyan-500/30 flex items-center justify-center mb-4">
                                <i data-lucide="wifi" class="w-10 h-10 text-cyan-400 opacity-60"></i>
                            </div>
                            <p class="text-zinc-400 text-sm">Clique para medir sua conexão</p>
                            <p class="text-zinc-500 text-xs mt-1">Teste rápido de download</p>
                        </div>
                    </div>
                    <button id="speedtest-btn" onclick="runSpeedTest()" class="btn-premium w-full flex items-center justify-center gap-3" style="background: linear-gradient(135deg, #06b6d4, #3b82f6);">
                        <i data-lucide="gauge" class="w-5 h-5"></i>
                        <span>Iniciar Speed Test</span>
                    </button>
                    <!-- Histórico de testes -->
                    <div id="speedtest-history"></div>
                </div>
            </div>

            <!-- Trash Widget - Premium Card -->
            <div class="glass-card p-6 premium-card" style="background: linear-gradient(135deg, rgba(239,68,68,0.05), rgba(251,146,60,0.05));">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold flex items-center gap-3">
                        <div class="w-11 h-11 rounded-xl bg-gradient-to-br from-red-500 to-orange-600 flex items-center justify-center shadow-lg shadow-red-500/30 ${state.trash?.total_items > 0 ? 'breathing' : ''}">
                            <i data-lucide="trash-2" class="w-5 h-5 text-white"></i>
                        </div>
                        <div>
                            <span class="text-white">Lixeira</span>
                            <p class="text-xs text-zinc-500 font-normal mt-0.5">Gerencie arquivos deletados</p>
                        </div>
                    </h3>
                    ${state.trash?.total_items > 0 ? `
                        <span class="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse">
                            ${state.trash.total_items} ${state.trash.total_items === 1 ? 'item' : 'itens'}
                        </span>
                    ` : `
                        <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-500/20 text-green-400 border border-green-500/30">
                            ✓ Vazia
                        </span>
                    `}
                </div>

                ${state.trash?.is_empty ? `
                    <div class="text-center py-8">
                        <div class="w-20 h-20 mx-auto rounded-full bg-green-500/10 border-2 border-dashed border-green-500/30 flex items-center justify-center mb-4">
                            <span class="text-4xl">🎉</span>
                        </div>
                        <p class="text-green-400 font-semibold">Lixeira vazia</p>
                        <p class="text-zinc-500 text-sm mt-1">Nenhum arquivo para recuperar</p>
                    </div>
                ` : `
                    <div class="grid grid-cols-3 gap-3 mb-4">
                        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
                            <div class="text-2xl mb-1">📁</div>
                            <div class="text-xs text-zinc-500">Pastas</div>
                            <div class="font-bold text-white">${state.trash?.folder_count || 0}</div>
                        </div>
                        <div class="p-3 rounded-xl bg-white/5 border border-white/10 text-center">
                            <div class="text-2xl mb-1">📄</div>
                            <div class="text-xs text-zinc-500">Arquivos</div>
                            <div class="font-bold text-white">${state.trash?.file_count || 0}</div>
                        </div>
                        <div class="p-3 rounded-xl bg-gradient-to-br from-red-500/10 to-orange-500/10 border border-red-500/20 text-center">
                            <div class="text-2xl mb-1">💾</div>
                            <div class="text-xs text-zinc-500">Ocupado</div>
                            <div class="font-bold text-red-400">${state.trash?.total_size_human || '0 B'}</div>
                        </div>
                    </div>

                    ${state.trash?.top_items?.length > 0 ? `
                        <div class="mb-4">
                            <p class="text-xs uppercase tracking-widest text-zinc-500 mb-2 font-semibold">📦 Maiores Itens</p>
                            <div class="space-y-2 max-h-[120px] overflow-y-auto pr-2 scrollbar-thin">
                                ${state.trash.top_items.slice(0, 5).map(item => `
                                    <div class="flex items-center justify-between p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
                                        <div class="flex items-center gap-2 min-w-0">
                                            <span class="text-lg flex-shrink-0">${item.is_folder ? '📁' : '📄'}</span>
                                            <span class="text-sm text-zinc-300 truncate">${item.name}</span>
                                        </div>
                                        <div class="flex items-center gap-2 flex-shrink-0">
                                            <span class="text-xs text-zinc-500">${item.days_old}d</span>
                                            <span class="text-xs font-semibold text-orange-400">${item.size_human}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    ` : ''}

                    <div class="flex gap-3">
                        <button onclick="openTrash()" class="flex-1 btn-premium py-2.5 text-sm" style="background: linear-gradient(135deg, #6366f1, #8b5cf6);">
                            <i data-lucide="folder-open" class="w-4 h-4 mr-2"></i>
                            Abrir Lixeira
                        </button>
                        <button onclick="emptyTrash()" class="flex-1 btn-premium py-2.5 text-sm" style="background: linear-gradient(135deg, #ef4444, #f97316);">
                            <i data-lucide="trash" class="w-4 h-4 mr-2"></i>
                            Esvaziar
                        </button>
                    </div>

                    ${state.trash?.recommendation ? `
                        <div class="mt-4 p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center gap-3">
                            <span class="text-xl">💡</span>
                            <p class="text-xs text-amber-400">${state.trash.recommendation}</p>
                        </div>
                    ` : ''}
                `}
            </div>

            <!-- Quick Actions - ULTRA PREMIUM -->
            <div class="glass-card p-8 premium-card">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-xl font-bold flex items-center gap-3">
                        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-yellow-400 via-orange-500 to-red-500 flex items-center justify-center shadow-lg shadow-orange-500/30 breathing">
                            <i data-lucide="zap" class="w-6 h-6 text-white"></i>
                        </div>
                        <div>
                            <span class="ultra-gradient-text">Quick Actions</span>
                            <p class="text-xs text-zinc-500 font-normal mt-0.5">Acesso rápido ao sistema</p>
                        </div>
                    </h3>
                    <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-yellow-500/20 to-orange-500/20 text-yellow-400 border border-yellow-500/30">⚡ Instant</span>
                </div>

                <!-- System Apps Section -->
                <div class="mb-6">
                    <p class="text-xs uppercase tracking-widest text-zinc-500 mb-4 font-semibold">🖥️ Aplicativos do Sistema</p>
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                        <button onclick="openApp('Terminal')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-zinc-700 to-zinc-900 text-2xl shadow-lg">💻</div>
                            <span class="group-hover:text-purple-400 transition-colors text-xs">Terminal</span>
                        </button>
                        <button onclick="openApp('Activity Monitor')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-green-600 to-green-800 text-2xl shadow-lg">📊</div>
                            <span class="group-hover:text-green-400 transition-colors text-xs">Monitor</span>
                        </button>
                        <button onclick="openApp('System Information')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-blue-600 to-blue-800 text-2xl shadow-lg">🖥️</div>
                            <span class="group-hover:text-blue-400 transition-colors text-xs">Sistema</span>
                        </button>
                        <button onclick="openApp('Disk Utility')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-purple-600 to-purple-800 text-2xl shadow-lg">💿</div>
                            <span class="group-hover:text-purple-400 transition-colors text-xs">Disco</span>
                        </button>
                        <button onclick="openApp('Console')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-orange-600 to-orange-800 text-2xl shadow-lg">📜</div>
                            <span class="group-hover:text-orange-400 transition-colors text-xs">Console</span>
                        </button>
                        <button onclick="openApp('Finder')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-cyan-600 to-cyan-800 text-2xl shadow-lg">📁</div>
                            <span class="group-hover:text-cyan-400 transition-colors text-xs">Finder</span>
                        </button>
                        <button onclick="openApp('Keychain Access')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-amber-600 to-yellow-800 text-2xl shadow-lg">🔑</div>
                            <span class="group-hover:text-amber-400 transition-colors text-xs">Keychain</span>
                        </button>
                        <button onclick="openApp('Preview')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-sky-600 to-blue-800 text-2xl shadow-lg">🖼️</div>
                            <span class="group-hover:text-sky-400 transition-colors text-xs">Preview</span>
                        </button>
                        <button onclick="openApp('Screenshot')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-pink-600 to-rose-800 text-2xl shadow-lg">📸</div>
                            <span class="group-hover:text-pink-400 transition-colors text-xs">Screenshot</span>
                        </button>
                        <button onclick="openApp('Notes')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-yellow-500 to-orange-600 text-2xl shadow-lg">📝</div>
                            <span class="group-hover:text-yellow-400 transition-colors text-xs">Notes</span>
                        </button>
                        <button onclick="openApp('Calculator')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-gray-600 to-gray-800 text-2xl shadow-lg">🧮</div>
                            <span class="group-hover:text-gray-300 transition-colors text-xs">Calculadora</span>
                        </button>
                        <button onclick="openApp('Shortcuts')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-indigo-500 to-violet-700 text-2xl shadow-lg">⚡</div>
                            <span class="group-hover:text-indigo-400 transition-colors text-xs">Atalhos</span>
                        </button>
                    </div>
                </div>

                <!-- Dev Tools Section - NEW! -->
                <div class="mb-6">
                    <p class="text-xs uppercase tracking-widest text-zinc-500 mb-4 font-semibold">🛠️ Dev Tools <span class="text-[10px] px-2 py-0.5 rounded bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-cyan-400 ml-2">NERD</span></p>
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                        <button onclick="openApp('Visual Studio Code')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-blue-600 to-blue-900 text-2xl shadow-lg shadow-blue-500/20">💎</div>
                            <span class="group-hover:text-blue-400 transition-colors text-xs">VS Code</span>
                        </button>
                        <button onclick="openApp('Xcode')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-cyan-500 to-blue-700 text-2xl shadow-lg shadow-cyan-500/20">🔨</div>
                            <span class="group-hover:text-cyan-400 transition-colors text-xs">Xcode</span>
                        </button>
                        <button onclick="openApp('Warp')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-purple-600 to-violet-900 text-2xl shadow-lg shadow-purple-500/20">🚀</div>
                            <span class="group-hover:text-purple-400 transition-colors text-xs">Warp</span>
                        </button>
                        <button onclick="openApp('iTerm')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-emerald-600 to-green-900 text-2xl shadow-lg shadow-emerald-500/20">⌨️</div>
                            <span class="group-hover:text-emerald-400 transition-colors text-xs">iTerm</span>
                        </button>
                        <button onclick="openApp('Docker')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-sky-500 to-blue-800 text-2xl shadow-lg shadow-sky-500/20">🐳</div>
                            <span class="group-hover:text-sky-400 transition-colors text-xs">Docker</span>
                        </button>
                        <button onclick="openApp('Postman')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-orange-500 to-red-700 text-2xl shadow-lg shadow-orange-500/20">📮</div>
                            <span class="group-hover:text-orange-400 transition-colors text-xs">Postman</span>
                        </button>
                        <button onclick="openApp('Script Editor')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-gray-500 to-zinc-800 text-2xl shadow-lg">📜</div>
                            <span class="group-hover:text-gray-300 transition-colors text-xs">Scripts</span>
                        </button>
                        <button onclick="openApp('Automator')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-zinc-500 to-gray-800 text-2xl shadow-lg">🤖</div>
                            <span class="group-hover:text-zinc-300 transition-colors text-xs">Automator</span>
                        </button>
                    </div>
                </div>

                <!-- Settings Section - EXPANDED -->
                <div>
                    <p class="text-xs uppercase tracking-widest text-zinc-500 mb-4 font-semibold">⚙️ Ajustes do Sistema</p>
                    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                        <button onclick="openSettings('storage')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-pink-600 to-rose-800 text-2xl shadow-lg">💾</div>
                            <span class="group-hover:text-pink-400 transition-colors text-xs">Storage</span>
                        </button>
                        <button onclick="openSettings('battery')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-green-500 to-emerald-700 text-2xl shadow-lg">🔋</div>
                            <span class="group-hover:text-green-400 transition-colors text-xs">Bateria</span>
                        </button>
                        <button onclick="openSettings('network')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-blue-500 to-indigo-700 text-2xl shadow-lg">🌐</div>
                            <span class="group-hover:text-blue-400 transition-colors text-xs">Rede</span>
                        </button>
                        <button onclick="openSettings('bluetooth')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-blue-400 to-blue-600 text-2xl shadow-lg">📶</div>
                            <span class="group-hover:text-blue-400 transition-colors text-xs">Bluetooth</span>
                        </button>
                        <button onclick="openSettings('displays')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-violet-600 to-purple-800 text-2xl shadow-lg">🖥️</div>
                            <span class="group-hover:text-violet-400 transition-colors text-xs">Telas</span>
                        </button>
                        <button onclick="openSettings('sound')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-red-500 to-rose-700 text-2xl shadow-lg">🔊</div>
                            <span class="group-hover:text-red-400 transition-colors text-xs">Som</span>
                        </button>
                        <button onclick="openSettings('keyboard')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-gray-500 to-zinc-700 text-2xl shadow-lg">⌨️</div>
                            <span class="group-hover:text-gray-300 transition-colors text-xs">Teclado</span>
                        </button>
                        <button onclick="openSettings('trackpad')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-slate-500 to-gray-700 text-2xl shadow-lg">👆</div>
                            <span class="group-hover:text-slate-300 transition-colors text-xs">Trackpad</span>
                        </button>
                        <button onclick="openSettings('security')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-amber-500 to-orange-700 text-2xl shadow-lg">🛡️</div>
                            <span class="group-hover:text-amber-400 transition-colors text-xs">Segurança</span>
                        </button>
                        <button onclick="openSettings('timemachine')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-teal-500 to-cyan-700 text-2xl shadow-lg">⏰</div>
                            <span class="group-hover:text-teal-400 transition-colors text-xs">Time Machine</span>
                        </button>
                        <button onclick="openSettings('icloud')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-sky-400 to-blue-600 text-2xl shadow-lg">☁️</div>
                            <span class="group-hover:text-sky-400 transition-colors text-xs">iCloud</span>
                        </button>
                        <button onclick="openSettings('about')" class="quick-action-btn group">
                            <div class="icon-wrapper bg-gradient-to-br from-zinc-600 to-zinc-800 text-2xl shadow-lg">ℹ️</div>
                            <span class="group-hover:text-zinc-300 transition-colors text-xs">Sobre</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Apple Links - PREMIUM EXPANDED -->
            <div class="glass-card p-8" style="background: linear-gradient(135deg, rgba(0,0,0,0.3), rgba(59,130,246,0.05)); border-color: rgba(255,255,255,0.1);">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-xl font-bold flex items-center gap-3">
                        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center shadow-lg border border-white/10">
                            <span class="text-2xl"></span>
                        </div>
                        <div>
                            <span class="text-white">Apple Resources</span>
                            <p class="text-xs text-zinc-500 font-normal mt-0.5">Links oficiais para seu MacBook Pro</p>
                        </div>
                    </h3>
                    <span class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800 text-zinc-300 border border-zinc-700">SN: H4H2PMGF32</span>
                </div>

                <!-- Main Apple Links -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <a href="https://checkcoverage.apple.com/br/pt/?sn=H4H2PMGF32" target="_blank" class="group p-5 rounded-2xl bg-gradient-to-br from-zinc-800/50 to-zinc-900/50 border border-white/10 hover:border-green-500/50 transition-all duration-300 flex items-center gap-4 hover:transform hover:scale-[1.02]">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/30">
                            <span class="text-2xl">🛡️</span>
                        </div>
                        <div>
                            <div class="font-semibold text-white group-hover:text-green-400 transition-colors">Verificar Cobertura</div>
                            <div class="text-xs text-zinc-500">AppleCare & Garantia</div>
                        </div>
                        <i data-lucide="external-link" class="w-4 h-4 text-zinc-600 group-hover:text-green-400 ml-auto transition-colors"></i>
                    </a>
                    <a href="https://support.apple.com/kb/SP898" target="_blank" class="group p-5 rounded-2xl bg-gradient-to-br from-zinc-800/50 to-zinc-900/50 border border-white/10 hover:border-blue-500/50 transition-all duration-300 flex items-center gap-4 hover:transform hover:scale-[1.02]">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30">
                            <span class="text-2xl">📋</span>
                        </div>
                        <div>
                            <div class="font-semibold text-white group-hover:text-blue-400 transition-colors">Tech Specs M3</div>
                            <div class="text-xs text-zinc-500">Especificações oficiais</div>
                        </div>
                        <i data-lucide="external-link" class="w-4 h-4 text-zinc-600 group-hover:text-blue-400 ml-auto transition-colors"></i>
                    </a>
                    <a href="https://support.apple.com/macos" target="_blank" class="group p-5 rounded-2xl bg-gradient-to-br from-zinc-800/50 to-zinc-900/50 border border-white/10 hover:border-purple-500/50 transition-all duration-300 flex items-center gap-4 hover:transform hover:scale-[1.02]">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-violet-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                            <span class="text-2xl">💻</span>
                        </div>
                        <div>
                            <div class="font-semibold text-white group-hover:text-purple-400 transition-colors">macOS Tahoe</div>
                            <div class="text-xs text-zinc-500">Documentação oficial</div>
                        </div>
                        <i data-lucide="external-link" class="w-4 h-4 text-zinc-600 group-hover:text-purple-400 ml-auto transition-colors"></i>
                    </a>
                    <a href="https://locate.apple.com/" target="_blank" class="group p-5 rounded-2xl bg-gradient-to-br from-zinc-800/50 to-zinc-900/50 border border-white/10 hover:border-orange-500/50 transition-all duration-300 flex items-center gap-4 hover:transform hover:scale-[1.02]">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center shadow-lg shadow-orange-500/30">
                            <span class="text-2xl">🗺️</span>
                        </div>
                        <div>
                            <div class="font-semibold text-white group-hover:text-orange-400 transition-colors">Apple Store</div>
                            <div class="text-xs text-zinc-500">Encontrar loja</div>
                        </div>
                        <i data-lucide="external-link" class="w-4 h-4 text-zinc-600 group-hover:text-orange-400 ml-auto transition-colors"></i>
                    </a>
                </div>

                <!-- Extra Apple Links Row -->
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <a href="https://developer.apple.com/" target="_blank" class="group p-4 rounded-2xl bg-gradient-to-br from-zinc-800/30 to-zinc-900/30 border border-white/5 hover:border-cyan-500/50 transition-all duration-300 flex items-center gap-3 hover:transform hover:scale-[1.02]">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                            <span class="text-xl">🔧</span>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium text-sm text-white group-hover:text-cyan-400 transition-colors">Developer Portal</div>
                            <div class="text-[10px] text-zinc-500">APIs & SDKs</div>
                        </div>
                        <i data-lucide="external-link" class="w-3 h-3 text-zinc-600 group-hover:text-cyan-400 transition-colors"></i>
                    </a>
                    <a href="https://support.apple.com/downloads" target="_blank" class="group p-4 rounded-2xl bg-gradient-to-br from-zinc-800/30 to-zinc-900/30 border border-white/5 hover:border-teal-500/50 transition-all duration-300 flex items-center gap-3 hover:transform hover:scale-[1.02]">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-teal-500/20">
                            <span class="text-xl">⬇️</span>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium text-sm text-white group-hover:text-teal-400 transition-colors">Downloads</div>
                            <div class="text-[10px] text-zinc-500">Drivers & Updates</div>
                        </div>
                        <i data-lucide="external-link" class="w-3 h-3 text-zinc-600 group-hover:text-teal-400 transition-colors"></i>
                    </a>
                    <a href="https://www.apple.com/shop/trade-in" target="_blank" class="group p-4 rounded-2xl bg-gradient-to-br from-zinc-800/30 to-zinc-900/30 border border-white/5 hover:border-amber-500/50 transition-all duration-300 flex items-center gap-3 hover:transform hover:scale-[1.02]">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
                            <span class="text-xl">♻️</span>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium text-sm text-white group-hover:text-amber-400 transition-colors">Trade In</div>
                            <div class="text-[10px] text-zinc-500">Trocar seu Mac</div>
                        </div>
                        <i data-lucide="external-link" class="w-3 h-3 text-zinc-600 group-hover:text-amber-400 transition-colors"></i>
                    </a>
                    <a href="https://www.apple.com/br/icloud/icloud-status/" target="_blank" class="group p-4 rounded-2xl bg-gradient-to-br from-zinc-800/30 to-zinc-900/30 border border-white/5 hover:border-sky-500/50 transition-all duration-300 flex items-center gap-3 hover:transform hover:scale-[1.02]">
                        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center shadow-lg shadow-sky-500/20">
                            <span class="text-xl">☁️</span>
                        </div>
                        <div class="flex-1">
                            <div class="font-medium text-sm text-white group-hover:text-sky-400 transition-colors">iCloud Status</div>
                            <div class="text-[10px] text-zinc-500">System Status</div>
                        </div>
                        <i data-lucide="external-link" class="w-3 h-3 text-zinc-600 group-hover:text-sky-400 transition-colors"></i>
                    </a>
                </div>
            </div>

            <!-- Tips & Shortcuts - ULTRA PREMIUM -->
            <div class="glass-card p-8 premium-card">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-xl font-bold flex items-center gap-3">
                        <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/30 shimmer">
                            <i data-lucide="lightbulb" class="w-6 h-6 text-white"></i>
                        </div>
                        <div>
                            <span class="ultra-gradient-text">Mac Tips & Atalhos</span>
                            <p class="text-xs text-zinc-500 font-normal mt-0.5">Domine seu MacBook como um PRO</p>
                        </div>
                    </h3>
                    <span class="px-3 py-1.5 rounded-lg text-[11px] font-bold tracking-wider bg-gradient-to-r from-amber-400 to-orange-500 text-black shadow-lg shadow-amber-500/30">🧠 NERD</span>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    ${tips.map((tip, i) => `
                    <div class="group p-4 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 hover:border-amber-500/40 transition-all duration-300 hover:transform hover:scale-[1.02] hover:shadow-lg hover:shadow-amber-500/10" style="animation-delay: ${i * 0.05}s;">
                        <div class="flex items-start gap-3">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br ${
                                tip.category === 'Navegação' ? 'from-blue-500/20 to-blue-600/20 border-blue-500/30' :
                                tip.category === 'Sistema' ? 'from-purple-500/20 to-purple-600/20 border-purple-500/30' :
                                tip.category === 'Screenshot' ? 'from-pink-500/20 to-pink-600/20 border-pink-500/30' :
                                tip.category === 'Finder' ? 'from-cyan-500/20 to-cyan-600/20 border-cyan-500/30' :
                                tip.category === 'Texto' ? 'from-green-500/20 to-green-600/20 border-green-500/30' :
                                tip.category === 'Dev' ? 'from-orange-500/20 to-red-600/20 border-orange-500/30' :
                                tip.category === 'Produtividade' ? 'from-indigo-500/20 to-violet-600/20 border-indigo-500/30' :
                                'from-amber-500/20 to-amber-600/20 border-amber-500/30'
                            } border flex items-center justify-center text-lg flex-shrink-0">
                                ${tip.category === 'Navegação' ? '🧭' : tip.category === 'Sistema' ? '⚙️' : tip.category === 'Screenshot' ? '📸' : tip.category === 'Finder' ? '📁' : tip.category === 'Texto' ? '✏️' : tip.category === 'Dev' ? '🛠️' : tip.category === 'Produtividade' ? '⚡' : '💡'}
                            </div>
                            <div class="flex-1 min-w-0">
                                <div class="font-mono text-xs px-2 py-1 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 inline-block mb-1.5 group-hover:bg-blue-500/20 transition-colors">${tip.shortcut}</div>
                                <div class="text-xs text-zinc-300 group-hover:text-white transition-colors leading-relaxed">${tip.description}</div>
                                <div class="text-[10px] text-zinc-600 mt-1.5 flex items-center gap-1">
                                    <span class="w-1.5 h-1.5 rounded-full ${
                                        tip.category === 'Dev' ? 'bg-orange-500' : tip.category === 'Produtividade' ? 'bg-indigo-500' : 'bg-amber-500'
                                    }"></span>
                                    ${tip.category}${tip.category === 'Dev' ? ' <span class="text-orange-400 font-semibold ml-1">NERD</span>' : tip.category === 'Produtividade' ? ' <span class="text-indigo-400 font-semibold ml-1">PRO</span>' : ''}
                                </div>
                            </div>
                        </div>
                    </div>
                    `).join('')}
                </div>
            </div>

            <!-- Footer Branding -->
            <div class="text-center py-8 opacity-60">
                <p class="text-xs text-zinc-500">
                    <span class="ultra-gradient-text font-bold">NERD SPACE V5.0</span> • AI FIRST Edition • Crafted with 💜 for Power Users
                </p>
                <p class="text-[10px] text-zinc-600 mt-1">Enterprise System Intelligence Platform • MacBook Pro 14" M3 Max</p>
            </div>
        </div>
        `;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // EVENT HANDLERS
    // ═══════════════════════════════════════════════════════════════════════════

    function attachEventListeners() {
        // Navigation tabs (UX Best Practice: use nav-tab class)
        document.querySelectorAll('.nav-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                switchTab(tab);
            });
            // Keyboard accessibility
            btn.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    switchTab(btn.dataset.tab);
                }
            });
        });
    }

    function switchTab(tab) {
        state.currentTab = tab;

        // Update active tab button with ARIA support
        document.querySelectorAll('.nav-tab').forEach(btn => {
            const isActive = btn.dataset.tab === tab;
            btn.classList.toggle('active', isActive);
            btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });

        renderCurrentTab();

        // Load apps if needed
        if (tab === 'apps' && !state.applications) {
            loadApplications();
        }
    }

    async function toggleCategory(categoryName) {
        const wasExpanded = state.expandedCategories.has(categoryName);

        if (wasExpanded) {
            state.expandedCategories.delete(categoryName);
        } else {
            state.expandedCategories.add(categoryName);
        }

        renderCurrentTab();

        // Load items if expanding
        if (!wasExpanded) {
            const subContainer = document.getElementById(`sub-${categoryName.replace(/\\s/g, '-')}`);
            if (subContainer) {
                try {
                    const items = await loadCategoryItems(categoryName);

                    if (items && items.length > 0) {
                        subContainer.innerHTML = items.map(item => `
                            <div class="sub-item" onclick="openFolder('${item.path}')">
                                <i data-lucide="${item.icon || 'folder'}" class="w-4 h-4 mr-3 text-zinc-500"></i>
                                <span class="flex-1 truncate">${item.name}</span>
                                <span class="text-zinc-500 ml-2">${item.size_human}</span>
                            </div>
                        `).join('');
                    } else if (items) {
                        subContainer.innerHTML = '<div class="py-2 px-12 text-zinc-500 text-sm">Nenhum item encontrado</div>';
                    } else {
                        subContainer.innerHTML = '<div class="py-2 px-12 text-red-400 text-sm">⚠️ Erro ao carregar - tente novamente</div>';
                    }
                    lucide.createIcons();
                } catch (err) {
                    console.error('Error loading category:', err);
                    subContainer.innerHTML = '<div class="py-2 px-12 text-red-400 text-sm">⚠️ Erro ao carregar - tente novamente</div>';
                }
            }
        }
    }

    async function loadApplications() {
        const data = await fetchAPI('applications');
        state.applications = data?.applications || [];

        const container = document.getElementById('apps-list');
        if (container && state.applications.length > 0) {
            renderAppsList(state.applications);
        }
    }

    function renderAppsList(apps) {
        const container = document.getElementById('apps-list');
        if (!container) return;

        container.innerHTML = apps.map(app => `
            <div class="app-item flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 cursor-pointer"
                 onclick="openFolder('${app.path}')">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500/20 to-orange-500/20 flex items-center justify-center">
                        <i data-lucide="app-window" class="w-5 h-5 text-red-400"></i>
                    </div>
                    <div>
                        <div class="font-medium">${app.name}</div>
                        <div class="text-xs text-zinc-500">v${app.version}</div>
                    </div>
                </div>
                <div class="text-right">
                    <div class="font-medium">${app.size_human}</div>
                </div>
            </div>
        `).join('');

        lucide.createIcons();
    }

    function filterApps(query) {
        if (!state.applications) return;

        const filtered = state.applications.filter(app =>
            app.name.toLowerCase().includes(query.toLowerCase())
        );
        renderAppsList(filtered);
    }

    async function openFolder(path) {
        await fetch('/api/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        });
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // WEBSOCKET & REAL-TIME
    // ═══════════════════════════════════════════════════════════════════════════

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateRealtimeMetrics(data);
        };

        ws.onclose = () => {
            setTimeout(connectWebSocket, 3000);
        };
    }

    function updateRealtimeMetrics(data) {
        // Update CPU
        const cpuBar = document.getElementById('cpu-bar');
        const cpuValue = document.getElementById('cpu-value');
        if (cpuBar && cpuValue) {
            cpuBar.style.width = `${data.cpu.percent}%`;
            cpuValue.textContent = `${data.cpu.percent.toFixed(1)}%`;
        }

        // Update Memory
        const memBar = document.getElementById('mem-bar');
        const memValue = document.getElementById('mem-value');
        if (memBar && memValue) {
            memBar.style.width = `${data.memory.percent}%`;
            memValue.textContent = `${data.memory.used_gb}/${data.memory.total_gb} GB`;
        }

        // Update Disk
        const diskBar = document.getElementById('disk-bar');
        const diskValue = document.getElementById('disk-value');
        if (diskBar && diskValue) {
            diskBar.style.width = `${data.disk.percent}%`;
            diskValue.textContent = `${data.disk.percent}%`;
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // CLOCK
    // ═══════════════════════════════════════════════════════════════════════════

    function updateClock() {
        const clock = document.getElementById('clock');
        if (clock) {
            const now = new Date();
            clock.textContent = now.toLocaleTimeString('pt-BR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // INITIALIZATION
    // ═══════════════════════════════════════════════════════════════════════════

    document.addEventListener('DOMContentLoaded', () => {
        // Initialize Premium Theme System
        ThemeManager.init();

        lucide.createIcons();
        loadAllData();
        loadNerdSpace();  // Load NERD SPACE data
        loadSpeedHistory();  // Load speed test history
        loadInsights();  // Load AI Insights
        connectWebSocket();
        updateClock();
        setInterval(updateClock, 1000);

        // Refresh data every 30 seconds
        setInterval(loadAllData, 30000);
        setInterval(loadNerdSpace, 60000);  // Refresh NERD SPACE every 60s
        setInterval(loadInsights, 300000);  // Refresh AI Insights every 5 minutes
    });
    </script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  Enterprise-Grade System Monitor & Control")
    print("=" * 70)
    print()
    print("  🌐 Local:     http://localhost:8888")
    print("  🌐 Network:   http://$(hostname):8888")
    print("  🌐 Tailscale: http://macbook-pro-de-danillo.tail556dd0.ts.net:8888")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 70)

    uvicorn.run(app, host="0.0.0.0", port=PORT)
