"""
NERD SPACE V5.0 - Speed Test Nativo
AI FIRST Edition

Speed test embedado sem dependências externas.
Usa servidores públicos para medir download, upload e latência.
"""

import asyncio
import aiohttp
import time
import socket
from typing import Optional, Dict, Any
from datetime import datetime
import json
from pathlib import Path

# Servidores de teste (CDNs públicos e confiáveis) - 1MB para teste rápido
TEST_SERVERS = [
    {
        "name": "OVH",
        "download_url": "https://proof.ovh.net/files/1Mb.dat",  # 1MB (rápido)
        "ping_host": "1.1.1.1"  # Cloudflare DNS
    },
    {
        "name": "Tele2",
        "download_url": "http://speedtest.tele2.net/1MB.zip",  # 1MB
        "ping_host": "8.8.8.8"  # Google DNS
    }
]

# Arquivo para histórico de testes
HISTORY_FILE = Path(__file__).parent.parent / "data" / "speed_history.json"


class SpeedTestService:
    """Serviço de speed test nativo"""

    def __init__(self):
        self.history_file = HISTORY_FILE
        self._ensure_history_file()

    def _ensure_history_file(self):
        """Garante que o arquivo de histórico existe"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history({"tests": []})

    def _load_history(self) -> dict:
        """Carrega histórico"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return {"tests": []}

    def _save_history(self, data: dict):
        """Salva histórico"""
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)

    async def run_test(self, full: bool = True) -> Dict[str, Any]:
        """
        Executa speed test completo

        Args:
            full: Se True, faz download+upload. Se False, só ping.
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "download_mbps": 0,
            "upload_mbps": 0,
            "latency_ms": 0,
            "jitter_ms": 0,
            "server": "Cloudflare",
            "provider": await self._get_isp_info(),
            "status": "running"
        }

        try:
            # 1. Teste de latência (ping)
            latency, jitter = await self._measure_latency()
            result["latency_ms"] = latency
            result["jitter_ms"] = jitter

            if full:
                # 2. Teste de download
                result["download_mbps"] = await self._measure_download()

                # 3. Teste de upload
                result["upload_mbps"] = await self._measure_upload()

            result["status"] = "completed"

            # Salvar no histórico
            self._add_to_history(result)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    async def _measure_latency(self) -> tuple:
        """Mede latência e jitter"""
        latencies = []
        host = TEST_SERVERS[0]["ping_host"]

        for _ in range(5):
            try:
                start = time.perf_counter()

                # Usando socket TCP para ping (mais confiável que ICMP)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((host, 80))
                sock.close()

                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)

                await asyncio.sleep(0.1)
            except:
                pass

        if not latencies:
            return 0, 0

        avg_latency = sum(latencies) / len(latencies)

        # Jitter = variação entre pings consecutivos
        if len(latencies) > 1:
            diffs = [abs(latencies[i] - latencies[i-1]) for i in range(1, len(latencies))]
            jitter = sum(diffs) / len(diffs)
        else:
            jitter = 0

        return round(avg_latency, 1), round(jitter, 1)

    async def _measure_download(self) -> float:
        """Mede velocidade de download"""
        import ssl

        # Tentar múltiplos servidores
        for server in TEST_SERVERS:
            url = server["download_url"]
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)

                async with aiohttp.ClientSession(connector=connector) as session:
                    start = time.perf_counter()
                    total_bytes = 0

                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                        if response.status != 200:
                            continue
                        async for chunk in response.content.iter_chunked(8192):
                            total_bytes += len(chunk)

                    elapsed = time.perf_counter() - start

                    if total_bytes > 0 and elapsed > 0:
                        # Calcular Mbps
                        mbps = (total_bytes * 8) / (elapsed * 1_000_000)
                        return round(mbps, 1)
            except Exception as e:
                print(f"Download test error ({server['name']}): {e}")
                continue

        return 0

    async def _measure_upload(self) -> float:
        """Mede velocidade de upload usando httpbin.org"""
        url = "https://httpbin.org/post"

        try:
            # Gerar dados para upload (100KB para teste rápido)
            data = b'0' * 100_000

            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(connector=connector) as session:
                start = time.perf_counter()

                async with session.post(url, data=data,
                                        timeout=aiohttp.ClientTimeout(total=10)) as response:
                    await response.read()

                elapsed = time.perf_counter() - start

                # Calcular Mbps
                mbps = (len(data) * 8) / (elapsed * 1_000_000)
                return round(mbps, 1)
        except Exception as e:
            print(f"Upload test error: {e}")
            return 0

    async def _get_isp_info(self) -> Dict[str, str]:
        """Obtém informações do provedor via IP"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://ipinfo.io/json",
                                       timeout=aiohttp.ClientTimeout(total=5)) as response:
                    data = await response.json()

                    return {
                        "ip": data.get("ip", ""),
                        "city": data.get("city", ""),
                        "region": data.get("region", ""),
                        "country": data.get("country", ""),
                        "org": data.get("org", ""),
                        "provider_name": self._parse_provider_name(data.get("org", ""))
                    }
        except:
            return {
                "ip": "",
                "city": "Unknown",
                "region": "",
                "country": "BR",
                "org": "",
                "provider_name": "Unknown"
            }

    def _parse_provider_name(self, org: str) -> str:
        """Extrai nome do provedor do campo org"""
        if not org:
            return "Unknown"

        # Remover AS number (ex: "AS18881 Vivo" -> "Vivo")
        parts = org.split()
        if parts and parts[0].startswith("AS"):
            return " ".join(parts[1:])
        return org

    def _add_to_history(self, result: dict):
        """Adiciona resultado ao histórico"""
        history = self._load_history()
        history["tests"].append(result)

        # Manter apenas últimos 50 testes
        history["tests"] = history["tests"][-50:]

        self._save_history(history)

    def get_history(self, limit: int = 10) -> list:
        """Retorna histórico de testes"""
        history = self._load_history()
        return history["tests"][-limit:]

    def get_last_test(self) -> Optional[dict]:
        """Retorna último teste realizado"""
        history = self._load_history()
        tests = history.get("tests", [])
        return tests[-1] if tests else None


# Singleton
_service: Optional[SpeedTestService] = None

def get_speed_test_service() -> SpeedTestService:
    """Retorna instância singleton do serviço"""
    global _service
    if _service is None:
        _service = SpeedTestService()
    return _service
