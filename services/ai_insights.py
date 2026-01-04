"""
NERD SPACE V5.0 - AI Insights Service
AI FIRST Edition

Serviço de insights inteligentes que analisa dados do sistema
e gera recomendações proativas para o usuário.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

# Cache file for insights
CACHE_FILE = Path(__file__).parent.parent / "data" / "insights_cache.json"
CACHE_TTL = 5 * 60  # 5 minutos


class Insight:
    """Representa um insight individual"""

    def __init__(
        self,
        category: str,
        severity: str,  # info, warning, critical, success
        title: str,
        description: str,
        action: Optional[str] = None,
        action_type: Optional[str] = None,  # url, app, settings
        icon: str = "💡",
        metric_value: Optional[str] = None,
        metric_label: Optional[str] = None
    ):
        self.category = category
        self.severity = severity
        self.title = title
        self.description = description
        self.action = action
        self.action_type = action_type
        self.icon = icon
        self.metric_value = metric_value
        self.metric_label = metric_label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "action_type": self.action_type,
            "icon": self.icon,
            "metric_value": self.metric_value,
            "metric_label": self.metric_label
        }


class AIInsightsService:
    """Serviço de insights inteligentes"""

    def __init__(self):
        self.cache_file = CACHE_FILE
        self._ensure_cache_file()

    def _ensure_cache_file(self):
        """Garante que o arquivo de cache existe"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_file.exists():
            self._save_cache({"timestamp": None, "insights": []})

    def _load_cache(self) -> dict:
        """Carrega cache"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except:
            return {"timestamp": None, "insights": []}

    def _save_cache(self, data: dict):
        """Salva cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _is_cache_valid(self) -> bool:
        """Verifica se cache ainda é válido"""
        cache = self._load_cache()
        if not cache.get("timestamp"):
            return False

        cached_time = datetime.fromisoformat(cache["timestamp"])
        return (datetime.now() - cached_time).total_seconds() < CACHE_TTL

    def generate_insights(
        self,
        storage_data: Dict[str, Any],
        battery_data: Dict[str, Any],
        network_data: Dict[str, Any],
        speed_history: List[Dict[str, Any]],
        power_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Gera insights baseados nos dados do sistema

        Args:
            storage_data: Dados de armazenamento
            battery_data: Dados da bateria
            network_data: Dados de rede
            speed_history: Histórico de speed tests
            power_data: Dados de energia
        """
        insights = []

        # Analisar Storage
        insights.extend(self._analyze_storage(storage_data))

        # Analisar Bateria
        insights.extend(self._analyze_battery(battery_data, power_data))

        # Analisar Network
        insights.extend(self._analyze_network(network_data, speed_history))

        # Analisar Performance
        insights.extend(self._analyze_performance(power_data))

        # Ordenar por severidade
        severity_order = {"critical": 0, "warning": 1, "info": 2, "success": 3}
        insights.sort(key=lambda x: severity_order.get(x["severity"], 99))

        # Cachear resultados
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "insights": insights
        }
        self._save_cache(cache_data)

        return insights

    def _analyze_storage(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analisa dados de storage e gera insights"""
        insights = []

        # Adaptar para estrutura de get_storage_categories()
        percent_used = data.get("used_percentage", 0)
        free_bytes = data.get("free_bytes", 0)
        free_gb = free_bytes / (1024 * 1024 * 1024) if free_bytes else 0
        categories_list = data.get("categories", [])

        # Converter lista de categories para dict por nome
        categories = {}
        for cat in categories_list:
            name = cat.get("name", "").lower().replace(" ", "_")
            size_gb = cat.get("size_bytes", 0) / (1024 * 1024 * 1024)
            categories[name] = size_gb

        # Insight: Espaço crítico
        if percent_used >= 90:
            insights.append(Insight(
                category="storage",
                severity="critical",
                title="Espaço Crítico!",
                description=f"Apenas {free_gb:.1f}GB livres ({100-percent_used:.0f}%). Performance pode ser afetada.",
                action="x-apple.systempreferences:com.apple.preference.storage",
                action_type="settings",
                icon="🔴",
                metric_value=f"{percent_used:.0f}%",
                metric_label="usado"
            ).to_dict())
        elif percent_used >= 80:
            insights.append(Insight(
                category="storage",
                severity="warning",
                title="Espaço Ficando Baixo",
                description=f"Restam {free_gb:.1f}GB. Considere fazer limpeza em breve.",
                action="x-apple.systempreferences:com.apple.preference.storage",
                action_type="settings",
                icon="🟡",
                metric_value=f"{free_gb:.1f}GB",
                metric_label="livres"
            ).to_dict())
        elif percent_used < 50:
            insights.append(Insight(
                category="storage",
                severity="success",
                title="Storage Saudável",
                description=f"{free_gb:.1f}GB livres. Seu SSD está bem organizado!",
                icon="🟢",
                metric_value=f"{free_gb:.1f}GB",
                metric_label="livres"
            ).to_dict())

        # Insight: System Data grande (Dados do Sistema -> dados_do_sistema)
        system_data = categories.get("dados_do_sistema", 0)
        if system_data > 100:
            insights.append(Insight(
                category="storage",
                severity="warning",
                title="System Data Volumoso",
                description=f"{system_data:.0f}GB em dados do sistema. Cache e logs podem ser limpos.",
                action="x-apple.systempreferences:com.apple.preference.storage",
                action_type="settings",
                icon="📦",
                metric_value=f"{system_data:.0f}GB",
                metric_label="system"
            ).to_dict())

        # Insight: iCloud uso alto (iCloud Drive -> icloud_drive)
        icloud = categories.get("icloud_drive", 0)
        if icloud > 50:
            insights.append(Insight(
                category="storage",
                severity="info",
                title="iCloud Local Volumoso",
                description=f"{icloud:.1f}GB sincronizados localmente. Otimize o armazenamento.",
                action="x-apple.systempreferences:com.apple.preference.icloud",
                action_type="settings",
                icon="☁️",
                metric_value=f"{icloud:.1f}GB",
                metric_label="iCloud"
            ).to_dict())

        return insights

    def _analyze_battery(
        self,
        battery: Dict[str, Any],
        power: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analisa dados de bateria e gera insights"""
        insights = []

        percent = battery.get("percent", 100)
        is_charging = battery.get("is_charging", False)
        health = battery.get("health", 100)
        cycle_count = battery.get("cycle_count", 0)

        # Insight: Bateria baixa
        if percent <= 20 and not is_charging:
            insights.append(Insight(
                category="battery",
                severity="warning",
                title="Bateria Baixa",
                description=f"Apenas {percent}% restantes. Conecte o carregador em breve.",
                icon="🪫",
                metric_value=f"{percent}%",
                metric_label="restante"
            ).to_dict())

        # Insight: Saúde da bateria
        if health < 80:
            insights.append(Insight(
                category="battery",
                severity="warning",
                title="Bateria Degradada",
                description=f"Capacidade máxima em {health}%. Considere trocar a bateria.",
                action="https://support.apple.com/mac/repair",
                action_type="url",
                icon="🔋",
                metric_value=f"{health}%",
                metric_label="saúde"
            ).to_dict())
        elif health >= 95:
            insights.append(Insight(
                category="battery",
                severity="success",
                title="Bateria Excelente",
                description=f"Saúde em {health}% com {cycle_count} ciclos. Excelente condição!",
                icon="💚",
                metric_value=f"{health}%",
                metric_label="saúde"
            ).to_dict())

        # Insight: Alto uso de energia
        power_source = power.get("power_source", "")
        if "Battery" in power_source and percent < 50:
            time_remaining = power.get("time_remaining_formatted", "")
            if time_remaining:
                insights.append(Insight(
                    category="battery",
                    severity="info",
                    title="Tempo Restante",
                    description=f"Aproximadamente {time_remaining} de bateria disponível.",
                    icon="⏱️",
                    metric_value=time_remaining,
                    metric_label="restante"
                ).to_dict())

        return insights

    def _analyze_network(
        self,
        network: Dict[str, Any],
        speed_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Analisa dados de rede e gera insights"""
        insights = []

        # Verificar conexão WiFi
        wifi_name = network.get("wifi_ssid", "")
        if not wifi_name:
            insights.append(Insight(
                category="network",
                severity="warning",
                title="Sem WiFi",
                description="Nenhuma rede WiFi conectada. Usando ethernet ou offline.",
                action="x-apple.systempreferences:com.apple.wifi-settings-extension",
                action_type="settings",
                icon="📶",
            ).to_dict())

        # Analisar histórico de velocidade
        if speed_history:
            last_test = speed_history[-1] if speed_history else None

            if last_test:
                download = last_test.get("download_mbps", 0)
                latency = last_test.get("latency_ms", 0)

                # Insight: Velocidade lenta
                if download < 25:
                    insights.append(Insight(
                        category="network",
                        severity="warning",
                        title="Internet Lenta",
                        description=f"Último teste: {download:.0f} Mbps. Pode afetar streaming e downloads.",
                        action="speedtest",
                        action_type="function",
                        icon="🐢",
                        metric_value=f"{download:.0f}",
                        metric_label="Mbps"
                    ).to_dict())
                elif download >= 100:
                    insights.append(Insight(
                        category="network",
                        severity="success",
                        title="Internet Rápida",
                        description=f"Último teste: {download:.0f} Mbps download, {latency:.0f}ms latência.",
                        icon="🚀",
                        metric_value=f"{download:.0f}",
                        metric_label="Mbps"
                    ).to_dict())

                # Insight: Latência alta
                if latency > 100:
                    insights.append(Insight(
                        category="network",
                        severity="info",
                        title="Latência Elevada",
                        description=f"{latency:.0f}ms de latência. Pode afetar videochamadas.",
                        icon="📡",
                        metric_value=f"{latency:.0f}",
                        metric_label="ms"
                    ).to_dict())

        return insights

    def _analyze_performance(self, power: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analisa dados de performance e gera insights"""
        insights = []

        # Insight: Modo de energia
        power_mode = power.get("low_power_mode", False)
        if power_mode:
            insights.append(Insight(
                category="performance",
                severity="info",
                title="Modo Economia Ativo",
                description="Performance reduzida para economizar bateria.",
                action="x-apple.systempreferences:com.apple.preference.battery",
                action_type="settings",
                icon="🔋"
            ).to_dict())

        # Insight: Thermal throttling
        thermal = power.get("thermal_state", "nominal")
        if thermal != "nominal":
            insights.append(Insight(
                category="performance",
                severity="warning",
                title="Temperatura Elevada",
                description="Mac aquecido. Performance pode estar limitada.",
                action="Activity Monitor",
                action_type="app",
                icon="🌡️"
            ).to_dict())

        return insights

    def get_cached_insights(self) -> List[Dict[str, Any]]:
        """Retorna insights cacheados se válidos"""
        if self._is_cache_valid():
            cache = self._load_cache()
            return cache.get("insights", [])
        return []

    def get_quick_summary(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera resumo rápido dos insights"""
        critical = len([i for i in insights if i["severity"] == "critical"])
        warnings = len([i for i in insights if i["severity"] == "warning"])
        success = len([i for i in insights if i["severity"] == "success"])

        if critical > 0:
            status = "critical"
            message = f"{critical} problema(s) crítico(s) detectado(s)"
            icon = "🔴"
        elif warnings > 0:
            status = "warning"
            message = f"{warnings} alerta(s) para atenção"
            icon = "🟡"
        else:
            status = "healthy"
            message = "Sistema saudável"
            icon = "🟢"

        return {
            "status": status,
            "message": message,
            "icon": icon,
            "critical_count": critical,
            "warning_count": warnings,
            "success_count": success,
            "total": len(insights)
        }


# Singleton
_service: Optional[AIInsightsService] = None

def get_ai_insights_service() -> AIInsightsService:
    """Retorna instância singleton do serviço"""
    global _service
    if _service is None:
        _service = AIInsightsService()
    return _service
