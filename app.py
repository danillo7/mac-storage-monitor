#!/usr/bin/env python3
"""
=============================================================================
MAC STORAGE MONITOR - Sistema de Monitoramento Inteligente de Disco
=============================================================================
Autor: Claude Code para Dr. Danillo Costa
Data: 2026-01-03
Descrição: Dashboard web para monitoramento de armazenamento no macOS
=============================================================================
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psutil

# =============================================================================
# Configuração
# =============================================================================

app = FastAPI(
    title="Mac Storage Monitor",
    description="Sistema de Monitoramento Inteligente de Disco",
    version="1.0.0"
)

# Diretórios importantes
HOME = Path.home()
ICLOUD_DIR = HOME / "Library/Mobile Documents/com~apple~CloudDocs"
LIBRARY_DIR = HOME / "Library"
CACHE_DIR = LIBRARY_DIR / "Caches"

# Histórico de uso (em memória - pode ser persistido em SQLite)
usage_history: list[dict] = []
MAX_HISTORY = 1000

# =============================================================================
# Funções de Análise
# =============================================================================

def get_disk_usage() -> dict:
    """Retorna uso do disco principal"""
    usage = psutil.disk_usage('/')
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "used_gb": round(usage.used / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
        "percent": usage.percent,
        "status": "critical" if usage.percent > 90 else "warning" if usage.percent > 75 else "ok"
    }

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
            return round(size_kb / (1024**2), 2)  # Converter para GB
    except Exception:
        pass
    return 0.0

def get_folder_sizes_async(paths: list[Path]) -> dict[str, float]:
    """Obtém tamanhos de várias pastas"""
    sizes = {}
    for path in paths:
        if path.exists():
            sizes[str(path)] = get_folder_size(path)
    return sizes

def analyze_icloud() -> dict:
    """Análise detalhada do iCloud"""
    if not ICLOUD_DIR.exists():
        return {"error": "iCloud Drive não encontrado"}

    result = {
        "total_size_gb": get_folder_size(ICLOUD_DIR),
        "folders": [],
        "local_files_count": 0,
        "cloud_only_count": 0
    }

    # Listar subpastas
    for item in sorted(ICLOUD_DIR.iterdir()):
        if item.is_dir():
            size = get_folder_size(item)
            result["folders"].append({
                "name": item.name,
                "size_gb": size,
                "path": str(item)
            })

    # Ordenar por tamanho
    result["folders"].sort(key=lambda x: x["size_gb"], reverse=True)

    # Contar arquivos locais vs nuvem
    try:
        local_count = subprocess.run(
            f'find "{ICLOUD_DIR}" -type f ! -name "*.icloud" 2>/dev/null | wc -l',
            shell=True, capture_output=True, text=True, timeout=60
        )
        cloud_count = subprocess.run(
            f'find "{ICLOUD_DIR}" -name "*.icloud" 2>/dev/null | wc -l',
            shell=True, capture_output=True, text=True, timeout=60
        )
        result["local_files_count"] = int(local_count.stdout.strip() or 0)
        result["cloud_only_count"] = int(cloud_count.stdout.strip() or 0)
    except Exception:
        pass

    return result

def analyze_caches() -> dict:
    """Análise de caches do sistema"""
    caches = {
        "user_caches": [],
        "system_caches": [],
        "total_gb": 0
    }

    # Caches do usuário
    if CACHE_DIR.exists():
        for item in CACHE_DIR.iterdir():
            if item.is_dir():
                size = get_folder_size(item)
                if size > 0.01:  # Só mostrar > 10MB
                    caches["user_caches"].append({
                        "name": item.name,
                        "size_gb": size,
                        "path": str(item)
                    })

    caches["user_caches"].sort(key=lambda x: x["size_gb"], reverse=True)
    caches["total_gb"] = sum(c["size_gb"] for c in caches["user_caches"])

    return caches

def analyze_docker() -> dict:
    """Análise do Docker se existir"""
    docker_dir = LIBRARY_DIR / "Containers/com.docker.docker"
    if docker_dir.exists():
        return {
            "size_gb": get_folder_size(docker_dir),
            "path": str(docker_dir)
        }
    return {"size_gb": 0, "path": None}

def get_large_files(min_size_mb: int = 100, limit: int = 20) -> list[dict]:
    """Encontra arquivos grandes no sistema"""
    files = []
    try:
        result = subprocess.run(
            f'find "{HOME}" -type f -size +{min_size_mb}M 2>/dev/null | head -{limit * 2}',
            shell=True, capture_output=True, text=True, timeout=120
        )
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    size = os.path.getsize(line)
                    files.append({
                        "path": line,
                        "size_mb": round(size / (1024**2), 2),
                        "name": os.path.basename(line)
                    })
                except Exception:
                    pass
    except Exception:
        pass

    files.sort(key=lambda x: x["size_mb"], reverse=True)
    return files[:limit]

def get_recent_large_files(days: int = 3, min_size_mb: int = 50) -> list[dict]:
    """Arquivos grandes criados/modificados recentemente"""
    files = []
    try:
        result = subprocess.run(
            f'find "{HOME}" -type f -mtime -{days} -size +{min_size_mb}M 2>/dev/null | head -30',
            shell=True, capture_output=True, text=True, timeout=120
        )
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    stat = os.stat(line)
                    files.append({
                        "path": line,
                        "size_mb": round(stat.st_size / (1024**2), 2),
                        "name": os.path.basename(line),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception:
                    pass
    except Exception:
        pass

    files.sort(key=lambda x: x["size_mb"], reverse=True)
    return files

def get_recommendations() -> list[dict]:
    """Gera recomendações baseadas na análise"""
    recommendations = []

    disk = get_disk_usage()

    # Recomendação baseada no uso do disco
    if disk["percent"] > 90:
        recommendations.append({
            "priority": "critical",
            "title": "Disco quase cheio!",
            "description": f"Apenas {disk['free_gb']}GB livres. Ação urgente necessária.",
            "action": "liberar_espaco"
        })
    elif disk["percent"] > 75:
        recommendations.append({
            "priority": "warning",
            "title": "Disco com uso elevado",
            "description": f"{disk['percent']}% do disco em uso. Considere limpar arquivos.",
            "action": "revisar_espaco"
        })

    # Verificar iCloud
    icloud = analyze_icloud()
    if icloud.get("total_size_gb", 0) > 100:
        recommendations.append({
            "priority": "warning",
            "title": "iCloud usando muito espaço local",
            "description": f"iCloud Drive está usando {icloud['total_size_gb']}GB localmente.",
            "action": "otimizar_icloud"
        })

    # Verificar Docker
    docker = analyze_docker()
    if docker["size_gb"] > 20:
        recommendations.append({
            "priority": "info",
            "title": "Docker com muito espaço",
            "description": f"Docker usando {docker['size_gb']}GB. Considere limpar imagens não usadas.",
            "action": "limpar_docker"
        })

    # Verificar caches
    caches = analyze_caches()
    if caches["total_gb"] > 5:
        recommendations.append({
            "priority": "info",
            "title": "Caches acumulados",
            "description": f"{caches['total_gb']}GB em caches. Podem ser limpos com segurança.",
            "action": "limpar_caches"
        })

    return recommendations

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal"""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/status")
async def api_status():
    """Status geral do disco"""
    disk = get_disk_usage()
    return {
        "timestamp": datetime.now().isoformat(),
        "disk": disk,
        "recommendations_count": len(get_recommendations())
    }

@app.get("/api/full-analysis")
async def api_full_analysis():
    """Análise completa do sistema"""
    return {
        "timestamp": datetime.now().isoformat(),
        "disk": get_disk_usage(),
        "icloud": analyze_icloud(),
        "caches": analyze_caches(),
        "docker": analyze_docker(),
        "recommendations": get_recommendations()
    }

@app.get("/api/icloud")
async def api_icloud():
    """Análise detalhada do iCloud"""
    return analyze_icloud()

@app.get("/api/large-files")
async def api_large_files(min_size: int = 100, limit: int = 20):
    """Lista arquivos grandes"""
    return get_large_files(min_size, limit)

@app.get("/api/recent-files")
async def api_recent_files(days: int = 3, min_size: int = 50):
    """Arquivos grandes recentes"""
    return get_recent_large_files(days, min_size)

@app.get("/api/recommendations")
async def api_recommendations():
    """Recomendações de otimização"""
    return get_recommendations()

@app.post("/api/evict-icloud")
async def api_evict_icloud(folder: str = None):
    """Remove downloads locais do iCloud"""
    target = ICLOUD_DIR / folder if folder else ICLOUD_DIR

    if not target.exists():
        return {"error": "Pasta não encontrada"}

    try:
        result = subprocess.run(
            f'find "{target}" -type f ! -name "*.icloud" -exec brctl evict {{}} \\; 2>/dev/null',
            shell=True, capture_output=True, text=True, timeout=300
        )
        return {"success": True, "message": f"Liberado espaço de {folder or 'iCloud Drive'}"}
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/clear-caches")
async def api_clear_caches():
    """Limpa caches do usuário"""
    try:
        # Apenas caches seguros
        safe_caches = [
            CACHE_DIR / "com.apple.Safari",
            CACHE_DIR / "com.spotify.client",
            CACHE_DIR / "Google",
        ]

        cleared = []
        for cache in safe_caches:
            if cache.exists():
                subprocess.run(['rm', '-rf', str(cache)], timeout=30)
                cleared.append(cache.name)

        return {"success": True, "cleared": cleared}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/history")
async def api_history():
    """Histórico de uso do disco"""
    return usage_history[-100:]

# =============================================================================
# Dashboard HTML
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mac Storage Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); }
        .card { background: rgba(30, 41, 59, 0.8); backdrop-filter: blur(10px); }
        .status-critical { color: #ef4444; }
        .status-warning { color: #f59e0b; }
        .status-ok { color: #22c55e; }
        .animate-pulse-slow { animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <div class="container mx-auto px-4 py-8">
        <!-- Header -->
        <div class="flex items-center justify-between mb-8">
            <div>
                <h1 class="text-3xl font-bold flex items-center gap-3">
                    <i data-lucide="hard-drive" class="w-8 h-8"></i>
                    Mac Storage Monitor
                </h1>
                <p class="text-slate-400 mt-1">Monitoramento inteligente de armazenamento</p>
            </div>
            <div id="last-update" class="text-slate-400 text-sm"></div>
        </div>

        <!-- Status Principal -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="card rounded-xl p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-slate-400 text-sm">Espaço Total</p>
                        <p id="total-space" class="text-2xl font-bold">--</p>
                    </div>
                    <i data-lucide="database" class="w-10 h-10 text-blue-400"></i>
                </div>
            </div>
            <div class="card rounded-xl p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-slate-400 text-sm">Espaço Usado</p>
                        <p id="used-space" class="text-2xl font-bold">--</p>
                    </div>
                    <i data-lucide="pie-chart" class="w-10 h-10 text-amber-400"></i>
                </div>
            </div>
            <div class="card rounded-xl p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-slate-400 text-sm">Espaço Livre</p>
                        <p id="free-space" class="text-2xl font-bold">--</p>
                    </div>
                    <i data-lucide="check-circle" class="w-10 h-10 text-green-400"></i>
                </div>
            </div>
            <div class="card rounded-xl p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-slate-400 text-sm">Uso do Disco</p>
                        <p id="disk-percent" class="text-2xl font-bold">--</p>
                    </div>
                    <i data-lucide="activity" class="w-10 h-10" id="status-icon"></i>
                </div>
            </div>
        </div>

        <!-- Barra de Progresso -->
        <div class="card rounded-xl p-6 mb-8">
            <div class="flex justify-between mb-2">
                <span class="text-slate-400">Uso do Disco</span>
                <span id="progress-label" class="font-mono">0%</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-4">
                <div id="progress-bar" class="h-4 rounded-full transition-all duration-500" style="width: 0%"></div>
            </div>
        </div>

        <!-- Grid Principal -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            <!-- iCloud Analysis -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                    <i data-lucide="cloud" class="w-5 h-5"></i>
                    iCloud Drive
                </h2>
                <div id="icloud-info" class="space-y-3">
                    <p class="text-slate-400">Carregando...</p>
                </div>
            </div>

            <!-- Recommendations -->
            <div class="card rounded-xl p-6">
                <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                    <i data-lucide="lightbulb" class="w-5 h-5"></i>
                    Recomendações
                </h2>
                <div id="recommendations" class="space-y-3">
                    <p class="text-slate-400">Carregando...</p>
                </div>
            </div>
        </div>

        <!-- Maiores Consumidores -->
        <div class="card rounded-xl p-6 mb-8">
            <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                <i data-lucide="folder-open" class="w-5 h-5"></i>
                Maiores Consumidores de Espaço
            </h2>
            <div id="top-folders" class="space-y-2">
                <p class="text-slate-400">Carregando...</p>
            </div>
        </div>

        <!-- Ações Rápidas -->
        <div class="card rounded-xl p-6">
            <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
                <i data-lucide="zap" class="w-5 h-5"></i>
                Ações Rápidas
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button onclick="evictICloud()" class="bg-blue-600 hover:bg-blue-700 rounded-lg p-4 transition flex flex-col items-center gap-2">
                    <i data-lucide="cloud-off" class="w-6 h-6"></i>
                    <span class="text-sm">Liberar iCloud</span>
                </button>
                <button onclick="clearCaches()" class="bg-amber-600 hover:bg-amber-700 rounded-lg p-4 transition flex flex-col items-center gap-2">
                    <i data-lucide="trash-2" class="w-6 h-6"></i>
                    <span class="text-sm">Limpar Caches</span>
                </button>
                <button onclick="openICloudSettings()" class="bg-slate-600 hover:bg-slate-700 rounded-lg p-4 transition flex flex-col items-center gap-2">
                    <i data-lucide="settings" class="w-6 h-6"></i>
                    <span class="text-sm">Config iCloud</span>
                </button>
                <button onclick="refreshData()" class="bg-green-600 hover:bg-green-700 rounded-lg p-4 transition flex flex-col items-center gap-2">
                    <i data-lucide="refresh-cw" class="w-6 h-6"></i>
                    <span class="text-sm">Atualizar</span>
                </button>
            </div>
        </div>

        <!-- Footer -->
        <div class="text-center mt-8 text-slate-500 text-sm">
            <p>Mac Storage Monitor v1.0 | Dr. Danillo Costa</p>
        </div>
    </div>

    <script>
        // Inicializar ícones Lucide
        lucide.createIcons();

        // Atualizar dados
        async function refreshData() {
            try {
                const response = await fetch('/api/full-analysis');
                const data = await response.json();
                updateUI(data);
            } catch (error) {
                console.error('Erro ao carregar dados:', error);
            }
        }

        function updateUI(data) {
            // Status do disco
            document.getElementById('total-space').textContent = data.disk.total_gb + ' GB';
            document.getElementById('used-space').textContent = data.disk.used_gb + ' GB';
            document.getElementById('free-space').textContent = data.disk.free_gb + ' GB';
            document.getElementById('disk-percent').textContent = data.disk.percent + '%';

            // Barra de progresso
            const progressBar = document.getElementById('progress-bar');
            progressBar.style.width = data.disk.percent + '%';
            document.getElementById('progress-label').textContent = data.disk.percent + '%';

            // Cor baseada no status
            if (data.disk.status === 'critical') {
                progressBar.className = 'h-4 rounded-full transition-all duration-500 bg-red-500';
                document.getElementById('status-icon').className = 'w-10 h-10 text-red-400 animate-pulse';
            } else if (data.disk.status === 'warning') {
                progressBar.className = 'h-4 rounded-full transition-all duration-500 bg-amber-500';
                document.getElementById('status-icon').className = 'w-10 h-10 text-amber-400';
            } else {
                progressBar.className = 'h-4 rounded-full transition-all duration-500 bg-green-500';
                document.getElementById('status-icon').className = 'w-10 h-10 text-green-400';
            }

            // iCloud
            if (data.icloud && !data.icloud.error) {
                let icloudHtml = `
                    <div class="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                        <span>Total Local</span>
                        <span class="font-bold text-amber-400">${data.icloud.total_size_gb} GB</span>
                    </div>
                    <div class="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                        <span>Arquivos Locais</span>
                        <span class="font-mono">${data.icloud.local_files_count?.toLocaleString() || '?'}</span>
                    </div>
                    <div class="flex justify-between items-center p-3 bg-slate-700/50 rounded-lg">
                        <span>Apenas na Nuvem</span>
                        <span class="font-mono">${data.icloud.cloud_only_count?.toLocaleString() || '?'}</span>
                    </div>
                `;

                if (data.icloud.folders && data.icloud.folders.length > 0) {
                    icloudHtml += '<div class="mt-4 space-y-2">';
                    data.icloud.folders.slice(0, 5).forEach(folder => {
                        icloudHtml += `
                            <div class="flex justify-between items-center text-sm">
                                <span class="truncate text-slate-300">${folder.name}</span>
                                <span class="font-mono text-xs">${folder.size_gb} GB</span>
                            </div>
                        `;
                    });
                    icloudHtml += '</div>';
                }
                document.getElementById('icloud-info').innerHTML = icloudHtml;
            }

            // Recomendações
            if (data.recommendations && data.recommendations.length > 0) {
                let recsHtml = '';
                data.recommendations.forEach(rec => {
                    const colorClass = rec.priority === 'critical' ? 'border-red-500 bg-red-500/10' :
                                      rec.priority === 'warning' ? 'border-amber-500 bg-amber-500/10' :
                                      'border-blue-500 bg-blue-500/10';
                    recsHtml += `
                        <div class="p-3 rounded-lg border-l-4 ${colorClass}">
                            <p class="font-semibold">${rec.title}</p>
                            <p class="text-sm text-slate-400">${rec.description}</p>
                        </div>
                    `;
                });
                document.getElementById('recommendations').innerHTML = recsHtml;
            } else {
                document.getElementById('recommendations').innerHTML = '<p class="text-green-400">✓ Nenhuma ação necessária</p>';
            }

            // Maiores pastas
            if (data.icloud && data.icloud.folders) {
                let foldersHtml = '';
                data.icloud.folders.slice(0, 8).forEach((folder, i) => {
                    const percent = (folder.size_gb / data.disk.total_gb * 100).toFixed(1);
                    foldersHtml += `
                        <div class="flex items-center gap-4">
                            <span class="w-8 text-slate-500">#${i + 1}</span>
                            <div class="flex-1">
                                <div class="flex justify-between mb-1">
                                    <span class="truncate">${folder.name}</span>
                                    <span class="font-mono text-sm">${folder.size_gb} GB</span>
                                </div>
                                <div class="w-full bg-slate-700 rounded-full h-2">
                                    <div class="bg-blue-500 h-2 rounded-full" style="width: ${Math.min(percent * 2, 100)}%"></div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                document.getElementById('top-folders').innerHTML = foldersHtml;
            }

            // Timestamp
            document.getElementById('last-update').textContent =
                'Atualizado: ' + new Date(data.timestamp).toLocaleTimeString('pt-BR');
        }

        async function evictICloud() {
            if (!confirm('Isso vai liberar o espaço local do iCloud.\\nOs arquivos continuarão na nuvem.\\nDeseja continuar?')) return;

            try {
                const response = await fetch('/api/evict-icloud', { method: 'POST' });
                const result = await response.json();
                alert(result.success ? 'Espaço liberado com sucesso!' : 'Erro: ' + result.error);
                refreshData();
            } catch (error) {
                alert('Erro ao liberar espaço: ' + error);
            }
        }

        async function clearCaches() {
            if (!confirm('Limpar caches do sistema?\\nIsso é seguro e não afeta seus dados.')) return;

            try {
                const response = await fetch('/api/clear-caches', { method: 'POST' });
                const result = await response.json();
                alert(result.success ? 'Caches limpos: ' + result.cleared.join(', ') : 'Erro: ' + result.error);
                refreshData();
            } catch (error) {
                alert('Erro ao limpar caches: ' + error);
            }
        }

        function openICloudSettings() {
            alert('Abrindo configurações do iCloud...\\nVá em: iCloud > iCloud Drive > Options > Optimize Mac Storage');
            // Isso seria feito via backend
        }

        // Carregar dados iniciais
        refreshData();

        // Atualizar a cada 30 segundos
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
"""

# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Mac Storage Monitor iniciando...")
    print("📊 Dashboard: http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
