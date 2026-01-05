"""
NERD SPACE V5.0 - Speed Test Profissional
AI FIRST Edition - World-Class Implementation

Speed test preciso baseado nas técnicas do Fast.com (Netflix) e Speedtest.net.
Utiliza:
- Downloads paralelos progressivos (aumenta conexões até saturar)
- Múltiplas medições com descarte de outliers
- Tempo mínimo de teste para precisão
- Cache warming para evitar cold-start
"""

import asyncio
import aiohttp
import time
import ssl
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
from pathlib import Path
import random

# Servidores de teste - Múltiplos para redundância e melhor roteamento
TEST_SERVERS = [
    {
        "name": "Cloudflare",
        "base_url": "https://speed.cloudflare.com",
        "download_url": "https://speed.cloudflare.com/__down?bytes=",
        "upload_url": "https://speed.cloudflare.com/__up",
    },
    {
        "name": "Cloudflare-2",
        "base_url": "https://speed.cloudflare.com",
        "download_url": "https://speed.cloudflare.com/__down?bytes=",
        "upload_url": "https://speed.cloudflare.com/__up",
    },
]

# Configurações do teste - baseado em Fast.com/Speedtest.net
CONFIG = {
    # Download
    "download_sizes": [
        100_000,        # 100KB - warm up
        1_000_000,      # 1MB - initial
        10_000_000,     # 10MB - standard
        25_000_000,     # 25MB - fast connections
        100_000_000,    # 100MB - very fast connections
    ],
    "download_parallel_min": 4,
    "download_parallel_max": 16,
    "download_duration_target": 8,  # segundos de medição

    # Upload
    "upload_sizes": [
        100_000,        # 100KB - warm up
        1_000_000,      # 1MB - initial
        5_000_000,      # 5MB - standard
        25_000_000,     # 25MB - fast connections
    ],
    "upload_parallel_min": 2,
    "upload_parallel_max": 8,
    "upload_duration_target": 6,  # segundos de medição

    # Latência
    "latency_samples": 20,
    "latency_outlier_threshold": 0.7,  # Manter 70% mais rápidos

    # Histórico
    "history_retention_days": 7,  # 1 semana
    "history_max_tests": 200,
}

# Arquivo para histórico de testes
HISTORY_FILE = Path(__file__).parent.parent / "data" / "speed_history.json"


class SpeedTestService:
    """Serviço de speed test profissional - Fast.com/Speedtest.net level"""

    def __init__(self):
        self.history_file = HISTORY_FILE
        self._ensure_history_file()
        self._ssl_context = self._create_ssl_context()

    def _create_ssl_context(self):
        """Cria SSL context otimizado"""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _ensure_history_file(self):
        """Garante que o arquivo de histórico existe"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history({"tests": [], "last_test": None})

    def _load_history(self) -> dict:
        """Carrega histórico"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except:
            return {"tests": [], "last_test": None}

    def _save_history(self, data: dict):
        """Salva histórico"""
        with open(self.history_file, 'w') as f:
            json.dump(data, f, indent=2)

    async def run_test(self, full: bool = True) -> Dict[str, Any]:
        """
        Executa speed test completo com metodologia profissional.

        1. Warm-up de conexão
        2. Teste de latência (20 amostras)
        3. Download progressivo (aumenta até saturar)
        4. Upload progressivo
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "download_mbps": 0,
            "upload_mbps": 0,
            "latency_ms": 0,
            "jitter_ms": 0,
            "server": "Cloudflare",
            "provider": await self._get_isp_info(),
            "status": "running",
            "details": {}
        }

        try:
            # 1. Teste de latência (crítico para precisão)
            print("🔄 Medindo latência...")
            latency, jitter = await self._measure_latency_professional()
            result["latency_ms"] = latency
            result["jitter_ms"] = jitter
            result["details"]["latency_samples"] = CONFIG["latency_samples"]

            if full:
                # 2. Download com metodologia Fast.com
                print("⬇️ Testando download...")
                download_result = await self._measure_download_professional()
                result["download_mbps"] = download_result["speed_mbps"]
                result["details"]["download"] = download_result

                # 3. Upload com metodologia similar
                print("⬆️ Testando upload...")
                upload_result = await self._measure_upload_professional()
                result["upload_mbps"] = upload_result["speed_mbps"]
                result["details"]["upload"] = upload_result

            result["status"] = "completed"
            print(f"✅ Teste completo: {result['download_mbps']} Mbps down / {result['upload_mbps']} Mbps up")

            # Salvar no histórico
            self._add_to_history(result)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"❌ Erro no speed test: {e}")

        return result

    async def _measure_latency_professional(self) -> tuple:
        """
        Mede latência com metodologia profissional.
        - 20 amostras HTTP HEAD
        - Descarta outliers (30% mais altos)
        - Calcula média dos 70% mais rápidos
        - Jitter = desvio médio entre amostras consecutivas
        """
        latencies = []

        connector = aiohttp.TCPConnector(
            ssl=self._ssl_context,
            limit=1,
            ttl_dns_cache=300
        )

        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm-up
            try:
                async with session.head("https://1.1.1.1/", timeout=aiohttp.ClientTimeout(total=2)):
                    pass
            except:
                pass

            # Amostras de latência
            for _ in range(CONFIG["latency_samples"]):
                try:
                    start = time.perf_counter()
                    async with session.head(
                        "https://1.1.1.1/",
                        timeout=aiohttp.ClientTimeout(total=3)
                    ) as response:
                        latency = (time.perf_counter() - start) * 1000
                        latencies.append(latency)
                except:
                    pass

                await asyncio.sleep(0.05)

        if not latencies:
            return 0, 0

        # Ordenar e remover outliers
        latencies.sort()
        keep_count = int(len(latencies) * CONFIG["latency_outlier_threshold"])
        clean_latencies = latencies[:max(keep_count, 1)]

        avg_latency = sum(clean_latencies) / len(clean_latencies)

        # Jitter = média das diferenças absolutas entre amostras consecutivas
        if len(clean_latencies) > 1:
            diffs = [abs(clean_latencies[i] - clean_latencies[i-1])
                     for i in range(1, len(clean_latencies))]
            jitter = sum(diffs) / len(diffs)
        else:
            jitter = 0

        return round(avg_latency, 1), round(jitter, 1)

    async def _download_single(self, session: aiohttp.ClientSession, size: int) -> Dict:
        """Baixa um arquivo e retorna métricas"""
        url = f"{TEST_SERVERS[0]['download_url']}{size}"

        try:
            start = time.perf_counter()
            total_bytes = 0

            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return {"bytes": 0, "time": 0, "success": False}

                async for chunk in response.content.iter_chunked(131072):  # 128KB chunks
                    total_bytes += len(chunk)

            elapsed = time.perf_counter() - start
            return {"bytes": total_bytes, "time": elapsed, "success": True}

        except Exception as e:
            return {"bytes": 0, "time": 0, "success": False, "error": str(e)}

    async def _measure_download_professional(self) -> Dict:
        """
        Metodologia de download inspirada no Fast.com:
        1. Começa com conexões mínimas
        2. Aumenta progressivamente até saturar
        3. Mede por pelo menos X segundos
        4. Calcula velocidade baseada no throughput estável
        """
        connector = aiohttp.TCPConnector(
            ssl=self._ssl_context,
            limit=CONFIG["download_parallel_max"],
            force_close=False,
            enable_cleanup_closed=True
        )

        measurements = []
        total_bytes = 0
        start_time = time.perf_counter()
        current_parallel = CONFIG["download_parallel_min"]

        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm-up com arquivo pequeno
            warmup = await self._download_single(session, CONFIG["download_sizes"][0])

            # Determinar tamanho ótimo baseado em velocidade inicial
            initial = await self._download_single(session, CONFIG["download_sizes"][2])
            if initial["success"] and initial["time"] > 0:
                initial_speed = (initial["bytes"] * 8) / (initial["time"] * 1_000_000)

                # Escolher tamanho baseado na velocidade
                if initial_speed > 500:  # > 500 Mbps
                    optimal_size = CONFIG["download_sizes"][4]  # 100MB
                elif initial_speed > 200:  # > 200 Mbps
                    optimal_size = CONFIG["download_sizes"][3]  # 25MB
                elif initial_speed > 50:  # > 50 Mbps
                    optimal_size = CONFIG["download_sizes"][2]  # 10MB
                else:
                    optimal_size = CONFIG["download_sizes"][1]  # 1MB
            else:
                optimal_size = CONFIG["download_sizes"][2]  # 10MB default

            # Loop de medição principal
            while (time.perf_counter() - start_time) < CONFIG["download_duration_target"]:
                # Criar tarefas paralelas
                tasks = [
                    self._download_single(session, optimal_size)
                    for _ in range(current_parallel)
                ]

                batch_start = time.perf_counter()
                results = await asyncio.gather(*tasks)
                batch_time = time.perf_counter() - batch_start

                batch_bytes = sum(r["bytes"] for r in results if r["success"])

                if batch_bytes > 0 and batch_time > 0:
                    batch_speed = (batch_bytes * 8) / (batch_time * 1_000_000)
                    measurements.append({
                        "speed": batch_speed,
                        "bytes": batch_bytes,
                        "time": batch_time,
                        "parallel": current_parallel
                    })
                    total_bytes += batch_bytes

                    # Aumentar paralelismo se ainda não saturou
                    if current_parallel < CONFIG["download_parallel_max"]:
                        if len(measurements) >= 2:
                            last_two = measurements[-2:]
                            if last_two[-1]["speed"] > last_two[-2]["speed"] * 0.95:
                                current_parallel = min(current_parallel + 2, CONFIG["download_parallel_max"])

        total_time = time.perf_counter() - start_time

        if not measurements:
            return {"speed_mbps": 0, "measurements": 0, "duration": total_time}

        # Calcular velocidade final: média ponderada das melhores medições
        measurements.sort(key=lambda x: x["speed"], reverse=True)
        top_measurements = measurements[:max(len(measurements) // 2, 1)]

        weighted_speed = sum(m["speed"] * m["bytes"] for m in top_measurements)
        total_weight = sum(m["bytes"] for m in top_measurements)

        final_speed = weighted_speed / total_weight if total_weight > 0 else 0

        return {
            "speed_mbps": round(final_speed, 1),
            "measurements": len(measurements),
            "duration": round(total_time, 2),
            "total_bytes": total_bytes,
            "max_parallel": current_parallel
        }

    async def _upload_single(self, session: aiohttp.ClientSession, size: int) -> Dict:
        """Faz upload e retorna métricas"""
        url = TEST_SERVERS[0]["upload_url"]

        # Gerar dados randômicos (mais realista que zeros)
        data = bytes(random.getrandbits(8) for _ in range(min(size, 1_000_000)))
        if size > 1_000_000:
            data = data * (size // 1_000_000) + data[:size % 1_000_000]

        try:
            start = time.perf_counter()

            async with session.post(
                url,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                await response.read()

            elapsed = time.perf_counter() - start
            return {"bytes": len(data), "time": elapsed, "success": True}

        except Exception as e:
            return {"bytes": 0, "time": 0, "success": False, "error": str(e)}

    async def _measure_upload_professional(self) -> Dict:
        """
        Metodologia de upload similar ao download.
        Upload geralmente é mais lento, então usamos menos conexões paralelas.
        """
        connector = aiohttp.TCPConnector(
            ssl=self._ssl_context,
            limit=CONFIG["upload_parallel_max"],
            force_close=False
        )

        measurements = []
        total_bytes = 0
        start_time = time.perf_counter()
        current_parallel = CONFIG["upload_parallel_min"]

        async with aiohttp.ClientSession(connector=connector) as session:
            # Warm-up
            await self._upload_single(session, CONFIG["upload_sizes"][0])

            # Medição inicial para determinar tamanho
            initial = await self._upload_single(session, CONFIG["upload_sizes"][1])
            if initial["success"] and initial["time"] > 0:
                initial_speed = (initial["bytes"] * 8) / (initial["time"] * 1_000_000)

                if initial_speed > 200:
                    optimal_size = CONFIG["upload_sizes"][3]  # 25MB
                elif initial_speed > 50:
                    optimal_size = CONFIG["upload_sizes"][2]  # 5MB
                else:
                    optimal_size = CONFIG["upload_sizes"][1]  # 1MB
            else:
                optimal_size = CONFIG["upload_sizes"][1]

            # Loop de medição
            while (time.perf_counter() - start_time) < CONFIG["upload_duration_target"]:
                tasks = [
                    self._upload_single(session, optimal_size)
                    for _ in range(current_parallel)
                ]

                batch_start = time.perf_counter()
                results = await asyncio.gather(*tasks)
                batch_time = time.perf_counter() - batch_start

                batch_bytes = sum(r["bytes"] for r in results if r["success"])

                if batch_bytes > 0 and batch_time > 0:
                    batch_speed = (batch_bytes * 8) / (batch_time * 1_000_000)
                    measurements.append({
                        "speed": batch_speed,
                        "bytes": batch_bytes,
                        "time": batch_time,
                        "parallel": current_parallel
                    })
                    total_bytes += batch_bytes

                    if current_parallel < CONFIG["upload_parallel_max"]:
                        if len(measurements) >= 2:
                            if measurements[-1]["speed"] > measurements[-2]["speed"] * 0.95:
                                current_parallel = min(current_parallel + 1, CONFIG["upload_parallel_max"])

        total_time = time.perf_counter() - start_time

        if not measurements:
            return {"speed_mbps": 0, "measurements": 0, "duration": total_time}

        # Velocidade final
        measurements.sort(key=lambda x: x["speed"], reverse=True)
        top_measurements = measurements[:max(len(measurements) // 2, 1)]

        weighted_speed = sum(m["speed"] * m["bytes"] for m in top_measurements)
        total_weight = sum(m["bytes"] for m in top_measurements)

        final_speed = weighted_speed / total_weight if total_weight > 0 else 0

        return {
            "speed_mbps": round(final_speed, 1),
            "measurements": len(measurements),
            "duration": round(total_time, 2),
            "total_bytes": total_bytes,
            "max_parallel": current_parallel
        }

    async def _get_isp_info(self) -> Dict[str, str]:
        """Obtém informações do provedor via IP"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://ipinfo.io/json",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
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
        """Adiciona resultado ao histórico com cleanup de testes antigos"""
        history = self._load_history()

        # Remover testes mais antigos que 1 semana
        cutoff = datetime.now() - timedelta(days=CONFIG["history_retention_days"])
        cutoff_str = cutoff.isoformat()

        history["tests"] = [
            t for t in history.get("tests", [])
            if t.get("timestamp", "") > cutoff_str
        ]

        # Adicionar novo teste
        history["tests"].append(result)

        # Manter limite máximo
        if len(history["tests"]) > CONFIG["history_max_tests"]:
            history["tests"] = history["tests"][-CONFIG["history_max_tests"]:]

        # Salvar último teste separadamente para acesso rápido
        history["last_test"] = result

        self._save_history(history)

    def get_history(self, limit: int = 10) -> list:
        """Retorna histórico de testes"""
        history = self._load_history()
        return history.get("tests", [])[-limit:]

    def get_last_test(self) -> Optional[dict]:
        """Retorna último teste realizado"""
        history = self._load_history()
        # Primeiro tenta o campo last_test para acesso rápido
        if history.get("last_test"):
            return history["last_test"]
        # Fallback para último da lista
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
