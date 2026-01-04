"""
NERD SPACE V5.0 - Weather Service
AI FIRST Edition

Serviço de clima com fallback para wttr.in (gratuito, sem API key)
Cache de 30 minutos para evitar rate limit.
"""

import asyncio
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Cache file
CACHE_FILE = Path(__file__).parent.parent / "data" / "weather_cache.json"

# TTL do cache em segundos (30 minutos)
CACHE_TTL = 30 * 60


class WeatherService:
    """Serviço de clima com cache e fallback"""

    def __init__(self):
        self.cache_file = CACHE_FILE
        self._ensure_cache_file()

    def _ensure_cache_file(self):
        """Garante que o arquivo de cache existe"""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.cache_file.exists():
            self._save_cache({})

    def _load_cache(self) -> dict:
        """Carrega cache"""
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_cache(self, data: dict):
        """Salva cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _is_cache_valid(self, cache_data: dict) -> bool:
        """Verifica se cache ainda é válido"""
        if not cache_data or "timestamp" not in cache_data:
            return False

        cached_time = datetime.fromisoformat(cache_data["timestamp"])
        return (datetime.now() - cached_time).total_seconds() < CACHE_TTL

    async def get_weather(self, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtém dados do clima

        Args:
            city: Nome da cidade. Se None, usa localização por IP.
        """
        # Verificar cache primeiro
        cache = self._load_cache()
        cache_key = city or "auto"

        if cache_key in cache and self._is_cache_valid(cache[cache_key]):
            return cache[cache_key]["data"]

        # Buscar dados frescos
        try:
            # Tentar wttr.in primeiro (mais confiável)
            weather_data = await self._fetch_wttr(city)

            if weather_data:
                # Salvar no cache
                cache[cache_key] = {
                    "timestamp": datetime.now().isoformat(),
                    "data": weather_data
                }
                self._save_cache(cache)
                return weather_data

        except Exception as e:
            print(f"Weather fetch error: {e}")

        # Retornar dados de fallback
        return self._get_fallback_data()

    async def _fetch_wttr(self, city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca clima via wttr.in (gratuito)"""
        try:
            # Formato JSON do wttr.in
            location = city if city else ""
            url = f"https://wttr.in/{location}?format=j1"

            # SSL context para evitar erro de certificado no Python 3.14
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    # Extrair dados relevantes
                    current = data.get("current_condition", [{}])[0]
                    location_info = data.get("nearest_area", [{}])[0]

                    return {
                        "temperature_c": int(current.get("temp_C", 0)),
                        "temperature_f": int(current.get("temp_F", 32)),
                        "feels_like_c": int(current.get("FeelsLikeC", 0)),
                        "humidity": int(current.get("humidity", 0)),
                        "description": current.get("weatherDesc", [{}])[0].get("value", ""),
                        "description_pt": self._translate_condition(
                            current.get("weatherDesc", [{}])[0].get("value", "")
                        ),
                        "wind_kph": float(current.get("windspeedKmph", 0)),
                        "wind_dir": current.get("winddir16Point", "N"),
                        "pressure_mb": int(current.get("pressure", 1013)),
                        "uv_index": int(current.get("uvIndex", 0)),
                        "visibility_km": int(current.get("visibility", 10)),
                        "cloud_cover": int(current.get("cloudcover", 0)),
                        "icon": self._get_weather_icon(current.get("weatherCode", "113")),
                        "location": {
                            "city": location_info.get("areaName", [{}])[0].get("value", "Unknown"),
                            "region": location_info.get("region", [{}])[0].get("value", ""),
                            "country": location_info.get("country", [{}])[0].get("value", "")
                        },
                        "last_updated": datetime.now().isoformat(),
                        "source": "wttr.in"
                    }
        except Exception as e:
            print(f"wttr.in error: {e}")
            return None

    def _translate_condition(self, condition: str) -> str:
        """Traduz condição do tempo para português"""
        translations = {
            "Sunny": "Ensolarado",
            "Clear": "Limpo",
            "Partly cloudy": "Parcialmente nublado",
            "Cloudy": "Nublado",
            "Overcast": "Encoberto",
            "Mist": "Névoa",
            "Fog": "Neblina",
            "Light rain": "Chuva leve",
            "Rain": "Chuva",
            "Heavy rain": "Chuva forte",
            "Thunderstorm": "Tempestade",
            "Snow": "Neve",
            "Light snow": "Neve leve",
            "Heavy snow": "Neve forte",
            "Sleet": "Granizo",
            "Patchy rain possible": "Possibilidade de chuva",
            "Patchy light rain": "Chuva leve isolada",
            "Moderate rain": "Chuva moderada",
            "Heavy rain at times": "Chuva forte por vezes",
        }
        return translations.get(condition, condition)

    def _get_weather_icon(self, code: str) -> str:
        """Retorna emoji/ícone baseado no código do tempo"""
        code_to_icon = {
            "113": "☀️",   # Sunny
            "116": "⛅",   # Partly cloudy
            "119": "☁️",   # Cloudy
            "122": "☁️",   # Overcast
            "143": "🌫️",  # Mist
            "176": "🌧️",  # Patchy rain
            "179": "🌨️",  # Patchy snow
            "182": "🌧️",  # Patchy sleet
            "185": "🌧️",  # Patchy freezing drizzle
            "200": "⛈️",  # Thundery outbreaks
            "227": "❄️",   # Blowing snow
            "230": "❄️",   # Blizzard
            "248": "🌫️",  # Fog
            "260": "🌫️",  # Freezing fog
            "263": "🌧️",  # Light drizzle
            "266": "🌧️",  # Light drizzle
            "281": "🌧️",  # Freezing drizzle
            "284": "🌧️",  # Heavy freezing drizzle
            "293": "🌧️",  # Light rain
            "296": "🌧️",  # Light rain
            "299": "🌧️",  # Moderate rain
            "302": "🌧️",  # Moderate rain
            "305": "🌧️",  # Heavy rain
            "308": "🌧️",  # Heavy rain
            "311": "🌧️",  # Light freezing rain
            "314": "🌧️",  # Moderate freezing rain
            "317": "🌧️",  # Light sleet
            "320": "🌨️",  # Moderate sleet
            "323": "🌨️",  # Light snow
            "326": "🌨️",  # Light snow
            "329": "❄️",   # Moderate snow
            "332": "❄️",   # Moderate snow
            "335": "❄️",   # Heavy snow
            "338": "❄️",   # Heavy snow
            "350": "🌧️",  # Ice pellets
            "353": "🌧️",  # Light rain shower
            "356": "🌧️",  # Moderate rain shower
            "359": "🌧️",  # Heavy rain shower
            "362": "🌧️",  # Light sleet showers
            "365": "🌨️",  # Moderate sleet showers
            "368": "🌨️",  # Light snow showers
            "371": "❄️",   # Moderate snow showers
            "374": "🌧️",  # Light ice pellets
            "377": "🌧️",  # Moderate ice pellets
            "386": "⛈️",  # Thundery with light rain
            "389": "⛈️",  # Thundery with heavy rain
            "392": "⛈️",  # Thundery with light snow
            "395": "⛈️",  # Thundery with heavy snow
        }
        return code_to_icon.get(code, "🌡️")

    def _get_fallback_data(self) -> Dict[str, Any]:
        """Dados de fallback quando não consegue buscar"""
        return {
            "temperature_c": 25,
            "temperature_f": 77,
            "feels_like_c": 26,
            "humidity": 60,
            "description": "Unknown",
            "description_pt": "Indisponível",
            "wind_kph": 0,
            "wind_dir": "N",
            "pressure_mb": 1013,
            "uv_index": 5,
            "visibility_km": 10,
            "cloud_cover": 0,
            "icon": "🌡️",
            "location": {
                "city": "Unknown",
                "region": "",
                "country": ""
            },
            "last_updated": datetime.now().isoformat(),
            "source": "fallback",
            "error": "Não foi possível obter dados do clima"
        }

    async def get_forecast(self, city: Optional[str] = None, days: int = 3) -> list:
        """Obtém previsão para os próximos dias"""
        try:
            location = city if city else ""
            url = f"https://wttr.in/{location}?format=j1"

            # SSL context para evitar erro de certificado no Python 3.14
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_context)

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return []

                    data = await response.json()
                    weather_data = data.get("weather", [])

                    forecast = []
                    for day in weather_data[:days]:
                        forecast.append({
                            "date": day.get("date", ""),
                            "max_temp_c": int(day.get("maxtempC", 0)),
                            "min_temp_c": int(day.get("mintempC", 0)),
                            "avg_temp_c": int(day.get("avgtempC", 0)),
                            "description": day.get("hourly", [{}])[4].get(
                                "weatherDesc", [{}])[0].get("value", ""),
                            "icon": self._get_weather_icon(
                                day.get("hourly", [{}])[4].get("weatherCode", "113")
                            ),
                            "uv_index": int(day.get("uvIndex", 0)),
                            "sunrise": day.get("astronomy", [{}])[0].get("sunrise", ""),
                            "sunset": day.get("astronomy", [{}])[0].get("sunset", "")
                        })

                    return forecast
        except Exception as e:
            print(f"Forecast error: {e}")
            return []


# Singleton
_service: Optional[WeatherService] = None

def get_weather_service() -> WeatherService:
    """Retorna instância singleton do serviço"""
    global _service
    if _service is None:
        _service = WeatherService()
    return _service
