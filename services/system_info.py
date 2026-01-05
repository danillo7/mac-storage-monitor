"""
NERD SPACE V5.0 - System Info Service
AI FIRST Edition

Coleta de informações do sistema usando comandos nativos do macOS.
Corrige bugs de storage e adiciona dados completos.
"""

import subprocess
import re
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path


class SystemInfoService:
    """Serviço de coleta de informações do sistema"""

    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}

    def _run_cmd(self, cmd: str, timeout: int = 10) -> str:
        """Executa comando shell com timeout"""
        try:
            # Garantir PATH completo para comandos do sistema
            env = os.environ.copy()
            env["PATH"] = "/usr/sbin:/usr/bin:/bin:/opt/homebrew/bin:" + env.get("PATH", "")
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return ""
        except Exception as e:
            print(f"Command error: {e}")
            return ""

    def _is_cache_valid(self, key: str, ttl_seconds: int) -> bool:
        """Verifica se cache é válido"""
        if key not in self._cache_timestamps:
            return False
        elapsed = (datetime.now() - self._cache_timestamps[key]).total_seconds()
        return elapsed < ttl_seconds

    def get_macos_version(self) -> Dict[str, Any]:
        """Obtém versão completa do macOS"""
        cache_key = "macos_version"
        if self._is_cache_valid(cache_key, 3600):  # 1 hora
            return self._cache[cache_key]

        # sw_vers para nome e versão
        product_name = self._run_cmd("sw_vers -productName")
        product_version = self._run_cmd("sw_vers -productVersion")
        build_version = self._run_cmd("sw_vers -buildVersion")

        # Nome do codinome (Tahoe para macOS 26)
        codename = self._get_macos_codename(product_version)

        # Kernel version
        kernel = self._run_cmd("uname -r")

        result = {
            "product_name": product_name,
            "version": product_version,
            "build": build_version,
            "codename": codename,
            "kernel": kernel,
            "full_name": f"{product_name} {codename} {product_version}",
            "formatted": f"{codename} {product_version} (Build {build_version})"
        }

        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        return result

    def _get_macos_codename(self, version: str) -> str:
        """Retorna codinome do macOS baseado na versão"""
        major = int(version.split('.')[0]) if version else 0
        codenames = {
            26: "Tahoe",
            15: "Sequoia",
            14: "Sonoma",
            13: "Ventura",
            12: "Monterey",
            11: "Big Sur",
            10: "Catalina"  # Para versões 10.x
        }
        return codenames.get(major, f"macOS {major}")

    def get_storage_real(self) -> Dict[str, Any]:
        """
        Obtém dados REAIS de storage usando diskutil apfs list.
        FIX: df mostra dados do snapshot, não do container APFS real.
        """
        cache_key = "storage_real"
        if self._is_cache_valid(cache_key, 60):  # 1 minuto
            return self._cache[cache_key]

        # Usar diskutil apfs list para dados REAIS do container
        apfs_output = self._run_cmd("diskutil apfs list", timeout=15)

        total_gb = 0.0
        used_gb = 0.0
        free_gb = 0.0
        percent_used = 0.0

        # Parse APFS container data
        for line in apfs_output.split('\n'):
            if 'Capacity Ceiling' in line or 'Size (Capacity Ceiling)' in line:
                # Total capacity
                match = re.search(r'\((\d+(?:\.\d+)?)\s*GB\)', line)
                if match:
                    total_gb = float(match.group(1))
            elif 'Capacity In Use By Volumes' in line:
                # Used space
                match = re.search(r'\((\d+(?:\.\d+)?)\s*GB\)', line)
                if match:
                    used_gb = float(match.group(1))
            elif 'Capacity Not Allocated' in line:
                # Free space
                match = re.search(r'\((\d+(?:\.\d+)?)\s*GB\)', line)
                if match:
                    free_gb = float(match.group(1))

        # Calculate percentage
        if total_gb > 0:
            percent_used = (used_gb / total_gb) * 100

        # Fallback to df if APFS parsing failed
        if total_gb == 0:
            df_output = self._run_cmd("df -h /")
            lines = df_output.split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                total_gb = self._parse_size(parts[1]) if len(parts) > 1 else 0
                used_gb = self._parse_size(parts[2]) if len(parts) > 2 else 0
                free_gb = self._parse_size(parts[3]) if len(parts) > 3 else 0
                percent_used = float(parts[4].replace('%', '')) if len(parts) > 4 else 0

        # Categorias de uso (como o macOS mostra)
        categories = self._get_storage_categories()

        # Dados do Sistema = Total usado - Soma das categorias conhecidas
        known_used = sum(categories.values())
        system_data = max(0, used_gb - known_used)

        result = {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": round(percent_used, 1),
            "categories": {
                "apps": round(categories.get("apps", 0), 2),
                "documents": round(categories.get("documents", 0), 2),
                "developer": round(categories.get("developer", 0), 2),
                "photos": round(categories.get("photos", 0), 2),
                "icloud": round(categories.get("icloud", 0), 2),
                "messages": round(categories.get("messages", 0), 2),
                "macos": round(categories.get("macos", 0), 2),
                "system_data": round(system_data, 2),
                "other": round(categories.get("other", 0), 2)
            },
            "formatted": {
                "total": f"{total_gb:.1f} GB",
                "used": f"{used_gb:.1f} GB",
                "free": f"{free_gb:.1f} GB"
            }
        }

        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        return result

    def _parse_size(self, s: str) -> float:
        """Converte string de tamanho (11Gi, 500M, 1.5T) para GB"""
        s = s.upper()
        if 'T' in s:
            return float(s.replace('TI', '').replace('T', '').replace('B', '')) * 1024
        elif 'G' in s:
            return float(s.replace('GI', '').replace('G', '').replace('B', ''))
        elif 'M' in s:
            return float(s.replace('MI', '').replace('M', '').replace('B', '')) / 1024
        return 0

    def _get_storage_categories(self) -> Dict[str, float]:
        """Calcula tamanho de cada categoria de storage"""
        home = os.path.expanduser("~")

        def get_dir_size_gb(path: str) -> float:
            """Obtém tamanho de diretório em GB"""
            if not os.path.exists(path):
                return 0
            try:
                output = self._run_cmd(f'du -sk "{path}" 2>/dev/null')
                if output:
                    kb = int(output.split()[0])
                    return kb / (1024 * 1024)  # KB -> GB
            except:
                pass
            return 0

        categories = {
            "apps": get_dir_size_gb("/Applications") + get_dir_size_gb(f"{home}/Applications"),
            "documents": get_dir_size_gb(f"{home}/Documents"),
            "developer": get_dir_size_gb(f"{home}/Developer") + get_dir_size_gb(f"{home}/Projects"),
            "photos": get_dir_size_gb(f"{home}/Pictures"),
            "icloud": get_dir_size_gb(f"{home}/Library/Mobile Documents"),
            "messages": get_dir_size_gb(f"{home}/Library/Messages"),
            "macos": get_dir_size_gb("/System"),
            "other": get_dir_size_gb(f"{home}/Downloads") + get_dir_size_gb(f"{home}/Desktop")
        }

        return categories

    def get_monitors(self) -> List[Dict[str, Any]]:
        """Obtém informações dos monitores conectados"""
        cache_key = "monitors"
        if self._is_cache_valid(cache_key, 300):  # 5 minutos
            return self._cache[cache_key]

        output = self._run_cmd("system_profiler SPDisplaysDataType -json")
        monitors = []

        try:
            data = json.loads(output)
            displays = data.get("SPDisplaysDataType", [])

            for gpu in displays:
                gpu_displays = gpu.get("spdisplays_ndrvs", [])
                for display in gpu_displays:
                    resolution = display.get("_spdisplays_resolution", "")
                    res_match = re.search(r'(\d+)\s*x\s*(\d+)', resolution)

                    monitor = {
                        "name": display.get("_name", "Unknown"),
                        "vendor": display.get("_spdisplays_display-vendor-id", ""),
                        "resolution": {
                            "width": int(res_match.group(1)) if res_match else 0,
                            "height": int(res_match.group(2)) if res_match else 0,
                            "formatted": resolution
                        },
                        "refresh_rate": self._extract_refresh_rate(resolution),
                        "is_main": display.get("spdisplays_main", "") == "spdisplays_yes",
                        "is_retina": "Retina" in resolution,
                        "connection": display.get("spdisplays_connection_type", "")
                    }
                    monitors.append(monitor)
        except Exception as e:
            print(f"Monitor info error: {e}")

        # Ordenar: principal primeiro, depois por nome
        monitors.sort(key=lambda m: (not m.get("is_main", False), m.get("name", "")))

        self._cache[cache_key] = monitors
        self._cache_timestamps[cache_key] = datetime.now()
        return monitors

    def _extract_refresh_rate(self, resolution_str: str) -> int:
        """Extrai taxa de atualização da string de resolução"""
        match = re.search(r'@\s*(\d+)\s*Hz', resolution_str)
        if match:
            return int(match.group(1))
        # Padrão para monitores sem info
        return 60

    def get_hardware_info(self) -> Dict[str, Any]:
        """Obtém informações de hardware"""
        cache_key = "hardware"
        if self._is_cache_valid(cache_key, 300):  # 5 minutos
            return self._cache[cache_key]

        # Model
        model = self._run_cmd("sysctl -n hw.model")
        model_name = self._run_cmd("system_profiler SPHardwareDataType | grep 'Model Name' | cut -d':' -f2")

        # Chip
        chip = self._run_cmd("sysctl -n machdep.cpu.brand_string")
        if not chip or "Apple" not in chip:
            chip = self._run_cmd("system_profiler SPHardwareDataType | grep 'Chip' | cut -d':' -f2")

        # RAM
        ram_bytes = int(self._run_cmd("sysctl -n hw.memsize") or 0)
        ram_gb = ram_bytes / (1024**3)

        # Serial
        serial = self._run_cmd("system_profiler SPHardwareDataType | grep 'Serial Number' | cut -d':' -f2")

        result = {
            "model": model.strip(),
            "model_name": model_name.strip(),
            "chip": chip.strip(),
            "ram_gb": round(ram_gb),
            "serial": serial.strip()[-4:] + "..." if serial else "",  # Só últimos 4 chars
            "cpu_cores": int(self._run_cmd("sysctl -n hw.ncpu") or 0),
            "cpu_physical_cores": int(self._run_cmd("sysctl -n hw.physicalcpu") or 0)
        }

        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        return result

    def get_uptime(self) -> Dict[str, Any]:
        """Obtém uptime do sistema"""
        boot_time = self._run_cmd("sysctl -n kern.boottime")
        # Formato: { sec = 1735725735, usec = 0 } Thu Jan  1 04:32:15 2026
        match = re.search(r'sec = (\d+)', boot_time)

        if match:
            boot_timestamp = int(match.group(1))
            boot_dt = datetime.fromtimestamp(boot_timestamp)
            now = datetime.now()
            uptime = now - boot_dt

            days = uptime.days
            hours = uptime.seconds // 3600
            minutes = (uptime.seconds % 3600) // 60

            return {
                "boot_time": boot_dt.isoformat(),
                "boot_formatted": boot_dt.strftime("%Y-%m-%d %H:%M:%S"),
                "uptime_seconds": int(uptime.total_seconds()),
                "uptime_formatted": f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m",
                "days": days,
                "hours": hours,
                "minutes": minutes
            }

        return {
            "boot_time": None,
            "uptime_seconds": 0,
            "uptime_formatted": "Unknown"
        }

    def get_dev_tools(self) -> Dict[str, Any]:
        """Obtém versões de ferramentas de desenvolvimento"""
        cache_key = "dev_tools"
        if self._is_cache_valid(cache_key, 300):  # 5 minutos
            return self._cache[cache_key]

        def get_version(cmd: str) -> str:
            output = self._run_cmd(cmd)
            # Extrair versão do output
            match = re.search(r'(\d+\.\d+(?:\.\d+)?)', output)
            return match.group(1) if match else ""

        result = {
            "shell": self._run_cmd("echo $SHELL").split('/')[-1],
            "shell_version": get_version("$SHELL --version 2>/dev/null || echo ''"),
            "python": get_version("python3 --version"),
            "node": get_version("node --version"),
            "npm": get_version("npm --version"),
            "homebrew": get_version("brew --version"),
            "homebrew_packages": int(self._run_cmd("brew list | wc -l") or 0),
            "git": get_version("git --version"),
            "docker": get_version("docker --version 2>/dev/null || echo ''"),
            "claude_code": "Available" if self._run_cmd("which claude") else "Not installed"
        }

        self._cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        return result

    def get_quick_links(self) -> List[Dict[str, Any]]:
        """Retorna lista de quick links para ferramentas dev"""
        return [
            {"name": "Terminal", "icon": "terminal", "shortcut": "⌘T", "action": "open -a Terminal"},
            {"name": "Warp", "icon": "terminal", "shortcut": "⌘W", "action": "open -a Warp"},
            {"name": "VS Code", "icon": "code", "shortcut": "⌘V", "action": "open -a 'Visual Studio Code'"},
            {"name": "GitHub", "icon": "github", "shortcut": "⌘H", "action": "open https://github.com"},
            {"name": "Claude Code", "icon": "bot", "shortcut": "⌘C", "action": "open -a Terminal && claude"},
            {"name": "Comet", "icon": "activity", "shortcut": "⌘O", "action": "open -a Comet"},
            {"name": "Python", "icon": "code", "shortcut": "⌘P", "action": "open -a Terminal && python3"},
            {"name": "Node", "icon": "code", "shortcut": "⌘N", "action": "open -a Terminal && node"}
        ]


# Singleton
_service: Optional[SystemInfoService] = None

def get_system_info_service() -> SystemInfoService:
    """Retorna instância singleton do serviço"""
    global _service
    if _service is None:
        _service = SystemInfoService()
    return _service
