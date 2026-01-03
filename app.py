#!/usr/bin/env python3
"""
=============================================================================
MAC MONITOR PRO v2.0 - Sistema Completo de Monitoramento macOS
=============================================================================
Autor: Claude Code para Dr. Danillo Costa
Data: 2026-01-03
Descrição: Dashboard web para monitoramento de armazenamento E atividades
=============================================================================

Features:
- Monitoramento de Disco (Storage)
- Monitoramento de CPU em tempo real
- Monitoramento de Memória RAM
- Top Processos por CPU e Memória
- Análise do iCloud Drive
- Histórico de métricas
- Alertas automáticos
- API REST completa
"""

import os
import json
import subprocess
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from collections import deque
import threading

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import psutil

# =============================================================================
# Configuração
# =============================================================================

app = FastAPI(
    title="Mac Monitor Pro",
    description="Sistema Completo de Monitoramento macOS",
    version="2.0.0"
)

# CORS para acesso externo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios importantes
HOME = Path.home()
ICLOUD_DIR = HOME / "Library/Mobile Documents/com~apple~CloudDocs"
LIBRARY_DIR = HOME / "Library"
CACHE_DIR = LIBRARY_DIR / "Caches"

# Histórico de métricas (últimas 100 leituras)
metrics_history: deque = deque(maxlen=100)
connected_clients: List[WebSocket] = []

# =============================================================================
# Funções de Monitoramento - Sistema
# =============================================================================

def get_cpu_info() -> Dict[str, Any]:
    """Informações detalhadas de CPU"""
    cpu_percent = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_freq = psutil.cpu_freq()
    load_avg = os.getloadavg()

    return {
        "percent_total": round(sum(cpu_percent) / len(cpu_percent), 1),
        "percent_per_core": cpu_percent,
        "core_count": psutil.cpu_count(logical=False),
        "thread_count": psutil.cpu_count(logical=True),
        "frequency_current": round(cpu_freq.current, 0) if cpu_freq else 0,
        "frequency_max": round(cpu_freq.max, 0) if cpu_freq else 0,
        "load_1min": round(load_avg[0], 2),
        "load_5min": round(load_avg[1], 2),
        "load_15min": round(load_avg[2], 2),
        "status": "critical" if sum(cpu_percent)/len(cpu_percent) > 90 else
                 "warning" if sum(cpu_percent)/len(cpu_percent) > 70 else "ok"
    }

def get_memory_info() -> Dict[str, Any]:
    """Informações detalhadas de memória"""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "percent": mem.percent,
        "swap_total_gb": round(swap.total / (1024**3), 2),
        "swap_used_gb": round(swap.used / (1024**3), 2),
        "swap_percent": swap.percent,
        "status": "critical" if mem.percent > 90 else
                 "warning" if mem.percent > 75 else "ok"
    }

def get_disk_info() -> Dict[str, Any]:
    """Informações de disco"""
    usage = psutil.disk_usage('/')

    # IO stats se disponível
    try:
        io = psutil.disk_io_counters()
        io_stats = {
            "read_bytes": io.read_bytes,
            "write_bytes": io.write_bytes,
            "read_count": io.read_count,
            "write_count": io.write_count
        }
    except:
        io_stats = None

    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "percent": usage.percent,
        "io_stats": io_stats,
        "status": "critical" if usage.percent > 90 else
                 "warning" if usage.percent > 75 else "ok"
    }

def get_network_info() -> Dict[str, Any]:
    """Informações de rede"""
    try:
        net = psutil.net_io_counters()
        return {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "bytes_sent_formatted": format_bytes(net.bytes_sent),
            "bytes_recv_formatted": format_bytes(net.bytes_recv)
        }
    except:
        return {}

def get_top_processes(by: str = "cpu", limit: int = 10) -> List[Dict]:
    """Top processos por CPU ou memória"""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'status']):
        try:
            info = proc.info
            processes.append({
                "pid": info['pid'],
                "name": info['name'][:30],  # Truncar nomes longos
                "cpu_percent": round(info['cpu_percent'] or 0, 1),
                "memory_percent": round(info['memory_percent'] or 0, 1),
                "memory_mb": round((info['memory_info'].rss if info['memory_info'] else 0) / (1024**2), 1),
                "status": info['status']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Ordenar
    key = 'cpu_percent' if by == 'cpu' else 'memory_percent'
    processes.sort(key=lambda x: x[key], reverse=True)

    return processes[:limit]

def get_battery_info() -> Optional[Dict]:
    """Informações de bateria (se disponível)"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "time_left_mins": round(battery.secsleft / 60) if battery.secsleft > 0 else None,
                "status": "charging" if battery.power_plugged else
                         "critical" if battery.percent < 20 else
                         "warning" if battery.percent < 40 else "ok"
            }
    except:
        pass
    return None

# =============================================================================
# Funções de Monitoramento - iCloud
# =============================================================================

def get_folder_size(path: Path) -> float:
    """Calcula tamanho de uma pasta em GB"""
    try:
        result = subprocess.run(
            ['du', '-sk', str(path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            size_kb = int(result.stdout.split()[0])
            return round(size_kb / (1024**2), 2)
    except:
        pass
    return 0.0

def analyze_icloud() -> Dict:
    """Análise do iCloud Drive"""
    if not ICLOUD_DIR.exists():
        return {"error": "iCloud Drive não encontrado", "total_size_gb": 0}

    result = {
        "total_size_gb": get_folder_size(ICLOUD_DIR),
        "folders": [],
        "local_files_count": 0,
        "cloud_only_count": 0
    }

    # Listar subpastas
    try:
        for item in sorted(ICLOUD_DIR.iterdir()):
            if item.is_dir():
                size = get_folder_size(item)
                result["folders"].append({
                    "name": item.name,
                    "size_gb": size,
                    "path": str(item)
                })
        result["folders"].sort(key=lambda x: x["size_gb"], reverse=True)
    except:
        pass

    return result

def analyze_caches() -> Dict:
    """Análise de caches"""
    caches = {"items": [], "total_gb": 0}

    if CACHE_DIR.exists():
        try:
            for item in CACHE_DIR.iterdir():
                if item.is_dir():
                    size = get_folder_size(item)
                    if size > 0.01:
                        caches["items"].append({
                            "name": item.name,
                            "size_gb": size
                        })
            caches["items"].sort(key=lambda x: x["size_gb"], reverse=True)
            caches["total_gb"] = round(sum(c["size_gb"] for c in caches["items"]), 2)
        except:
            pass

    return caches

# =============================================================================
# Helpers
# =============================================================================

def format_bytes(bytes_val: int) -> str:
    """Formata bytes para human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"

def get_system_info() -> Dict:
    """Informações gerais do sistema"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
    except:
        uptime_str = "N/A"

    return {
        "hostname": os.uname().nodename,
        "os": f"{os.uname().sysname} {os.uname().release}",
        "uptime": uptime_str,
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}"
    }

def get_all_metrics() -> Dict:
    """Coleta todas as métricas"""
    return {
        "timestamp": datetime.now().isoformat(),
        "system": get_system_info(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disk": get_disk_info(),
        "network": get_network_info(),
        "battery": get_battery_info(),
        "top_cpu": get_top_processes("cpu", 5),
        "top_memory": get_top_processes("memory", 5)
    }

def get_recommendations() -> List[Dict]:
    """Gera recomendações baseadas nas métricas"""
    recommendations = []

    disk = get_disk_info()
    memory = get_memory_info()
    cpu = get_cpu_info()

    if disk["percent"] > 90:
        recommendations.append({
            "priority": "critical",
            "category": "disk",
            "title": "Disco quase cheio!",
            "description": f"Apenas {disk['free_gb']}GB livres ({disk['percent']}% usado)",
            "action": "Liberar espaço urgentemente"
        })
    elif disk["percent"] > 75:
        recommendations.append({
            "priority": "warning",
            "category": "disk",
            "title": "Espaço em disco baixo",
            "description": f"{disk['free_gb']}GB livres ({disk['percent']}% usado)",
            "action": "Considere limpar arquivos desnecessários"
        })

    if memory["percent"] > 90:
        recommendations.append({
            "priority": "critical",
            "category": "memory",
            "title": "Memória crítica!",
            "description": f"Apenas {memory['available_gb']}GB disponíveis",
            "action": "Feche aplicativos não utilizados"
        })
    elif memory["percent"] > 80:
        recommendations.append({
            "priority": "warning",
            "category": "memory",
            "title": "Uso de memória elevado",
            "description": f"{memory['percent']}% da RAM em uso",
            "action": "Monitore o uso de memória"
        })

    if cpu["percent_total"] > 80:
        recommendations.append({
            "priority": "warning",
            "category": "cpu",
            "title": "CPU sob carga alta",
            "description": f"CPU em {cpu['percent_total']}%",
            "action": "Verifique processos consumindo CPU"
        })

    return recommendations

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Dashboard principal"""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/status")
async def api_status():
    """Status rápido do sistema"""
    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": get_cpu_info()["percent_total"],
        "memory_percent": get_memory_info()["percent"],
        "disk_percent": get_disk_info()["percent"],
        "status": "healthy"
    }

@app.get("/api/metrics")
async def api_metrics():
    """Todas as métricas do sistema"""
    return get_all_metrics()

@app.get("/api/cpu")
async def api_cpu():
    """Métricas de CPU"""
    return get_cpu_info()

@app.get("/api/memory")
async def api_memory():
    """Métricas de memória"""
    return get_memory_info()

@app.get("/api/disk")
async def api_disk():
    """Métricas de disco"""
    return get_disk_info()

@app.get("/api/processes")
async def api_processes(by: str = "cpu", limit: int = 15):
    """Lista de processos"""
    return get_top_processes(by, limit)

@app.get("/api/icloud")
async def api_icloud():
    """Análise do iCloud"""
    return analyze_icloud()

@app.get("/api/caches")
async def api_caches():
    """Análise de caches"""
    return analyze_caches()

@app.get("/api/recommendations")
async def api_recommendations():
    """Recomendações de otimização"""
    return get_recommendations()

@app.get("/api/history")
async def api_history():
    """Histórico de métricas"""
    return list(metrics_history)

@app.post("/api/evict-icloud")
async def api_evict_icloud(folder: str = None):
    """Remove downloads locais do iCloud"""
    target = ICLOUD_DIR / folder if folder else ICLOUD_DIR
    if not target.exists():
        return {"error": "Pasta não encontrada"}

    try:
        subprocess.run(
            f'find "{target}" -type f ! -name "*.icloud" -exec brctl evict {{}} \\; 2>/dev/null',
            shell=True, timeout=300
        )
        return {"success": True, "message": f"Liberando espaço de {folder or 'iCloud Drive'}"}
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para atualizações em tempo real"""
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            metrics = get_all_metrics()
            metrics_history.append({
                "timestamp": metrics["timestamp"],
                "cpu": metrics["cpu"]["percent_total"],
                "memory": metrics["memory"]["percent"],
                "disk": metrics["disk"]["percent"]
            })
            await websocket.send_json(metrics)
            await asyncio.sleep(2)  # Atualiza a cada 2 segundos
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# =============================================================================
# Dashboard HTML
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mac Monitor Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }
        .card { background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1); }
        .glow-green { box-shadow: 0 0 20px rgba(34, 197, 94, 0.3); }
        .glow-amber { box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); }
        .glow-red { box-shadow: 0 0 20px rgba(239, 68, 68, 0.3); }
        .animate-pulse-slow { animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .fade-in { animation: fadeIn 0.5s ease-out; }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white font-sans">
    <div class="container mx-auto px-4 py-6 max-w-7xl">
        <!-- Header -->
        <header class="flex items-center justify-between mb-8">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <i data-lucide="activity" class="w-7 h-7"></i>
                </div>
                <div>
                    <h1 class="text-2xl font-bold">Mac Monitor Pro</h1>
                    <p class="text-slate-400 text-sm" id="system-info">Carregando...</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <div id="connection-status" class="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-700">
                    <span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
                    <span class="text-xs">Conectando...</span>
                </div>
                <span id="last-update" class="text-slate-400 text-xs"></span>
            </div>
        </header>

        <!-- Status Cards -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <!-- CPU -->
            <div class="card rounded-2xl p-5 fade-in" id="cpu-card">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-slate-400 text-sm font-medium">CPU</span>
                    <i data-lucide="cpu" class="w-5 h-5 text-blue-400"></i>
                </div>
                <p id="cpu-percent" class="text-3xl font-bold">--%</p>
                <p id="cpu-cores" class="text-slate-500 text-xs mt-1">-- cores</p>
            </div>
            <!-- Memory -->
            <div class="card rounded-2xl p-5 fade-in" id="memory-card">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-slate-400 text-sm font-medium">Memória</span>
                    <i data-lucide="memory-stick" class="w-5 h-5 text-purple-400"></i>
                </div>
                <p id="memory-percent" class="text-3xl font-bold">--%</p>
                <p id="memory-detail" class="text-slate-500 text-xs mt-1">-- / -- GB</p>
            </div>
            <!-- Disk -->
            <div class="card rounded-2xl p-5 fade-in" id="disk-card">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-slate-400 text-sm font-medium">Disco</span>
                    <i data-lucide="hard-drive" class="w-5 h-5 text-green-400"></i>
                </div>
                <p id="disk-percent" class="text-3xl font-bold">--%</p>
                <p id="disk-detail" class="text-slate-500 text-xs mt-1">-- GB livres</p>
            </div>
            <!-- Battery/Network -->
            <div class="card rounded-2xl p-5 fade-in" id="extra-card">
                <div class="flex items-center justify-between mb-3">
                    <span class="text-slate-400 text-sm font-medium">Bateria</span>
                    <i data-lucide="battery" class="w-5 h-5 text-amber-400" id="battery-icon"></i>
                </div>
                <p id="battery-percent" class="text-3xl font-bold">--%</p>
                <p id="battery-detail" class="text-slate-500 text-xs mt-1">--</p>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <!-- CPU Chart -->
            <div class="card rounded-2xl p-5">
                <h3 class="text-sm font-medium text-slate-400 mb-4">CPU por Core</h3>
                <div class="h-32">
                    <canvas id="cpu-chart"></canvas>
                </div>
            </div>
            <!-- History Chart -->
            <div class="card rounded-2xl p-5">
                <h3 class="text-sm font-medium text-slate-400 mb-4">Histórico (últimos 60s)</h3>
                <div class="h-32">
                    <canvas id="history-chart"></canvas>
                </div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <!-- Top Processes -->
            <div class="card rounded-2xl p-5 lg:col-span-2">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-sm font-medium text-slate-400">Top Processos</h3>
                    <div class="flex gap-2">
                        <button onclick="sortProcesses('cpu')" id="sort-cpu" class="px-3 py-1 rounded-lg bg-blue-600 text-xs">CPU</button>
                        <button onclick="sortProcesses('memory')" id="sort-memory" class="px-3 py-1 rounded-lg bg-slate-700 text-xs">RAM</button>
                    </div>
                </div>
                <div id="processes-list" class="space-y-2 max-h-64 overflow-y-auto">
                    <p class="text-slate-500 text-sm">Carregando...</p>
                </div>
            </div>

            <!-- Recommendations -->
            <div class="card rounded-2xl p-5">
                <h3 class="text-sm font-medium text-slate-400 mb-4">Recomendações</h3>
                <div id="recommendations" class="space-y-3">
                    <p class="text-slate-500 text-sm">Analisando...</p>
                </div>
            </div>
        </div>

        <!-- iCloud Section -->
        <div class="card rounded-2xl p-5 mb-6">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-sm font-medium text-slate-400 flex items-center gap-2">
                    <i data-lucide="cloud" class="w-4 h-4"></i>
                    iCloud Drive
                </h3>
                <button onclick="evictICloud()" class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs transition">
                    Liberar Espaço
                </button>
            </div>
            <div id="icloud-info" class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <p class="text-slate-500 text-sm">Carregando...</p>
            </div>
        </div>

        <!-- Footer -->
        <footer class="text-center text-slate-500 text-xs">
            Mac Monitor Pro v2.0 | Dr. Danillo Costa |
            <a href="https://github.com/danillo7/mac-storage-monitor" target="_blank" class="text-blue-400 hover:underline">GitHub</a>
        </footer>
    </div>

    <script>
        // Estado
        let ws = null;
        let cpuChart = null;
        let historyChart = null;
        let processSort = 'cpu';
        let historyData = { labels: [], cpu: [], memory: [], disk: [] };

        // Inicializar
        document.addEventListener('DOMContentLoaded', () => {
            lucide.createIcons();
            initCharts();
            connectWebSocket();
            loadICloud();
        });

        function initCharts() {
            // CPU per core chart
            const cpuCtx = document.getElementById('cpu-chart').getContext('2d');
            cpuChart = new Chart(cpuCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        data: [],
                        backgroundColor: 'rgba(59, 130, 246, 0.7)',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { max: 100, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b' } }
                    }
                }
            });

            // History chart
            const historyCtx = document.getElementById('history-chart').getContext('2d');
            historyChart = new Chart(historyCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        { label: 'CPU', data: [], borderColor: '#3b82f6', tension: 0.4, fill: false, pointRadius: 0 },
                        { label: 'RAM', data: [], borderColor: '#a855f7', tension: 0.4, fill: false, pointRadius: 0 },
                        { label: 'Disco', data: [], borderColor: '#22c55e', tension: 0.4, fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top', labels: { boxWidth: 12, color: '#64748b' } } },
                    scales: {
                        y: { max: 100, grid: { color: 'rgba(255,255,255,0.1)' }, ticks: { color: '#64748b' } },
                        x: { display: false }
                    }
                }
            });
        }

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onopen = () => {
                document.getElementById('connection-status').innerHTML =
                    '<span class="w-2 h-2 rounded-full bg-green-500"></span><span class="text-xs">Conectado</span>';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateUI(data);
            };

            ws.onclose = () => {
                document.getElementById('connection-status').innerHTML =
                    '<span class="w-2 h-2 rounded-full bg-red-500"></span><span class="text-xs">Desconectado</span>';
                setTimeout(connectWebSocket, 3000);
            };
        }

        function updateUI(data) {
            // System info
            if (data.system) {
                document.getElementById('system-info').textContent =
                    `${data.system.hostname} | Uptime: ${data.system.uptime}`;
            }

            // CPU
            if (data.cpu) {
                document.getElementById('cpu-percent').textContent = `${data.cpu.percent_total}%`;
                document.getElementById('cpu-cores').textContent = `${data.cpu.core_count} cores | Load: ${data.cpu.load_1min}`;
                setCardStatus('cpu-card', data.cpu.status);

                // Update CPU chart
                cpuChart.data.labels = data.cpu.percent_per_core.map((_, i) => `C${i}`);
                cpuChart.data.datasets[0].data = data.cpu.percent_per_core;
                cpuChart.update('none');
            }

            // Memory
            if (data.memory) {
                document.getElementById('memory-percent').textContent = `${data.memory.percent}%`;
                document.getElementById('memory-detail').textContent =
                    `${data.memory.used_gb} / ${data.memory.total_gb} GB`;
                setCardStatus('memory-card', data.memory.status);
            }

            // Disk
            if (data.disk) {
                document.getElementById('disk-percent').textContent = `${data.disk.percent}%`;
                document.getElementById('disk-detail').textContent = `${data.disk.free_gb} GB livres`;
                setCardStatus('disk-card', data.disk.status);
            }

            // Battery
            if (data.battery) {
                document.getElementById('battery-percent').textContent = `${data.battery.percent}%`;
                document.getElementById('battery-detail').textContent =
                    data.battery.plugged ? 'Carregando' :
                    data.battery.time_left_mins ? `${data.battery.time_left_mins}min restantes` : 'Em uso';
            }

            // Processes
            const procs = processSort === 'cpu' ? data.top_cpu : data.top_memory;
            if (procs) {
                updateProcessList(procs);
            }

            // History
            updateHistory(data);

            // Timestamp
            document.getElementById('last-update').textContent =
                `Atualizado: ${new Date(data.timestamp).toLocaleTimeString('pt-BR')}`;
        }

        function setCardStatus(cardId, status) {
            const card = document.getElementById(cardId);
            card.classList.remove('glow-green', 'glow-amber', 'glow-red');
            if (status === 'critical') card.classList.add('glow-red');
            else if (status === 'warning') card.classList.add('glow-amber');
            else card.classList.add('glow-green');
        }

        function updateProcessList(processes) {
            const container = document.getElementById('processes-list');
            container.innerHTML = processes.map(p => `
                <div class="flex items-center justify-between py-2 px-3 bg-slate-800/50 rounded-lg">
                    <div class="flex-1 min-w-0">
                        <p class="text-sm truncate">${p.name}</p>
                        <p class="text-xs text-slate-500">PID: ${p.pid}</p>
                    </div>
                    <div class="flex gap-4 text-right">
                        <div>
                            <p class="text-sm font-mono ${p.cpu_percent > 50 ? 'text-amber-400' : ''}">${p.cpu_percent}%</p>
                            <p class="text-xs text-slate-500">CPU</p>
                        </div>
                        <div>
                            <p class="text-sm font-mono ${p.memory_percent > 10 ? 'text-purple-400' : ''}">${p.memory_mb}MB</p>
                            <p class="text-xs text-slate-500">RAM</p>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function updateHistory(data) {
            const now = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            historyData.labels.push(now);
            historyData.cpu.push(data.cpu?.percent_total || 0);
            historyData.memory.push(data.memory?.percent || 0);
            historyData.disk.push(data.disk?.percent || 0);

            // Manter apenas últimos 30 pontos
            if (historyData.labels.length > 30) {
                historyData.labels.shift();
                historyData.cpu.shift();
                historyData.memory.shift();
                historyData.disk.shift();
            }

            historyChart.data.labels = historyData.labels;
            historyChart.data.datasets[0].data = historyData.cpu;
            historyChart.data.datasets[1].data = historyData.memory;
            historyChart.data.datasets[2].data = historyData.disk;
            historyChart.update('none');
        }

        function sortProcesses(by) {
            processSort = by;
            document.getElementById('sort-cpu').className = by === 'cpu' ? 'px-3 py-1 rounded-lg bg-blue-600 text-xs' : 'px-3 py-1 rounded-lg bg-slate-700 text-xs';
            document.getElementById('sort-memory').className = by === 'memory' ? 'px-3 py-1 rounded-lg bg-blue-600 text-xs' : 'px-3 py-1 rounded-lg bg-slate-700 text-xs';
        }

        async function loadICloud() {
            try {
                const res = await fetch('/api/icloud');
                const data = await res.json();

                if (data.error) {
                    document.getElementById('icloud-info').innerHTML = `<p class="text-slate-500">${data.error}</p>`;
                    return;
                }

                let html = `
                    <div class="bg-slate-800/50 rounded-lg p-3">
                        <p class="text-xs text-slate-400">Total Local</p>
                        <p class="text-lg font-bold text-amber-400">${data.total_size_gb} GB</p>
                    </div>
                `;

                if (data.folders) {
                    data.folders.slice(0, 3).forEach(f => {
                        html += `
                            <div class="bg-slate-800/50 rounded-lg p-3">
                                <p class="text-xs text-slate-400 truncate">${f.name}</p>
                                <p class="text-lg font-bold">${f.size_gb} GB</p>
                            </div>
                        `;
                    });
                }

                document.getElementById('icloud-info').innerHTML = html;

                // Load recommendations
                const recsRes = await fetch('/api/recommendations');
                const recs = await recsRes.json();

                if (recs.length === 0) {
                    document.getElementById('recommendations').innerHTML =
                        '<p class="text-green-400 text-sm">✓ Sistema saudável</p>';
                } else {
                    document.getElementById('recommendations').innerHTML = recs.map(r => `
                        <div class="p-3 rounded-lg border-l-4 ${r.priority === 'critical' ? 'border-red-500 bg-red-500/10' : 'border-amber-500 bg-amber-500/10'}">
                            <p class="text-sm font-medium">${r.title}</p>
                            <p class="text-xs text-slate-400 mt-1">${r.description}</p>
                        </div>
                    `).join('');
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function evictICloud() {
            if (!confirm('Liberar espaço do iCloud? Arquivos continuarão na nuvem.')) return;
            try {
                const res = await fetch('/api/evict-icloud', { method: 'POST' });
                const data = await res.json();
                alert(data.success ? 'Liberação iniciada!' : 'Erro: ' + data.error);
                setTimeout(loadICloud, 5000);
            } catch (e) {
                alert('Erro: ' + e);
            }
        }
    </script>
</body>
</html>
"""

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("🖥️  MAC MONITOR PRO v2.0")
    print("=" * 60)
    print(f"📊 Dashboard: http://localhost:8888")
    print(f"📊 Externo:   http://0.0.0.0:8888")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8888)
