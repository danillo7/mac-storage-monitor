"""
NERD SPACE V5.0 - Claude Max 20x Usage Monitoring
AI FIRST Edition

Monitora o uso do plano Claude Max 20x ($200/mês = R$ 1.369,90)
- Window 5h: ~900 msgs (reset a cada 5h)
- Window 7d: ~126K msgs (rolling)
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import asyncio

# Caminho para armazenar dados de uso
USAGE_FILE = Path(__file__).parent.parent / "data" / "claude_usage.json"

class ClaudeUsageService:
    """Serviço para monitorar uso do Claude Max 20x"""

    # Constantes do plano
    PLAN_NAME = "Claude Max 20x"
    PRICE_USD = 200.00
    PRICE_BRL = 1369.90  # ~R$ 6,85/USD
    MULTIPLIER = 20  # 20x mais que Pro

    # Limites estimados (baseado em msgs curtas)
    WINDOW_5H_LIMIT = 900  # msgs por janela de 5h
    WINDOW_7D_LIMIT = 126000  # msgs por janela de 7 dias

    # Custo por mensagem (estimativa)
    COST_PER_MSG_BRL = 0.076  # R$ 1.369,90 / ~18.000 msgs/mês

    def __init__(self):
        self.usage_file = USAGE_FILE
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Garante que o arquivo de dados existe"""
        self.usage_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.usage_file.exists():
            self._save_data({
                "messages": [],
                "created_at": datetime.now().isoformat()
            })

    def _load_data(self) -> dict:
        """Carrega dados do arquivo"""
        try:
            with open(self.usage_file, 'r') as f:
                return json.load(f)
        except:
            return {"messages": [], "created_at": datetime.now().isoformat()}

    def _save_data(self, data: dict):
        """Salva dados no arquivo"""
        with open(self.usage_file, 'w') as f:
            json.dump(data, f, indent=2)

    def log_message(self, tokens_in: int = 0, tokens_out: int = 0,
                   model: str = "claude-3-sonnet", extended_thinking: bool = False):
        """Registra uma mensagem enviada ao Claude"""
        data = self._load_data()

        msg = {
            "timestamp": datetime.now().isoformat(),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "model": model,
            "extended_thinking": extended_thinking
        }

        data["messages"].append(msg)

        # Limpar mensagens antigas (> 7 dias)
        cutoff = (datetime.now() - timedelta(days=7)).isoformat()
        data["messages"] = [m for m in data["messages"] if m["timestamp"] > cutoff]

        self._save_data(data)

    def get_usage_stats(self) -> dict:
        """Retorna estatísticas de uso atuais"""
        data = self._load_data()
        messages = data.get("messages", [])

        now = datetime.now()

        # Janela de 5 horas
        cutoff_5h = (now - timedelta(hours=5)).isoformat()
        msgs_5h = len([m for m in messages if m["timestamp"] > cutoff_5h])

        # Janela de 7 dias
        cutoff_7d = (now - timedelta(days=7)).isoformat()
        msgs_7d = len([m for m in messages if m["timestamp"] > cutoff_7d])

        # Próximo reset da janela de 5h
        # Encontrar a mensagem mais antiga na janela atual
        msgs_in_window = [m for m in messages if m["timestamp"] > cutoff_5h]
        if msgs_in_window:
            oldest = min(m["timestamp"] for m in msgs_in_window)
            oldest_dt = datetime.fromisoformat(oldest)
            next_reset = oldest_dt + timedelta(hours=5)
            time_to_reset = (next_reset - now).total_seconds()
            time_to_reset = max(0, time_to_reset)
        else:
            time_to_reset = 0
            next_reset = now

        # Tokens totais
        tokens_in_5h = sum(m.get("tokens_in", 0) for m in msgs_in_window)
        tokens_out_5h = sum(m.get("tokens_out", 0) for m in msgs_in_window)

        msgs_7d_list = [m for m in messages if m["timestamp"] > cutoff_7d]
        tokens_in_7d = sum(m.get("tokens_in", 0) for m in msgs_7d_list)
        tokens_out_7d = sum(m.get("tokens_out", 0) for m in msgs_7d_list)

        # Custo estimado
        cost_today_brl = self._estimate_cost_today(messages)
        cost_month_brl = self._estimate_cost_month(messages)

        return {
            "plan": {
                "name": self.PLAN_NAME,
                "price_usd": self.PRICE_USD,
                "price_brl": self.PRICE_BRL,
                "multiplier": self.MULTIPLIER
            },
            "usage": {
                "window_5h": {
                    "messages": msgs_5h,
                    "limit": self.WINDOW_5H_LIMIT,
                    "percent": round((msgs_5h / self.WINDOW_5H_LIMIT) * 100, 1),
                    "tokens_in": tokens_in_5h,
                    "tokens_out": tokens_out_5h,
                    "next_reset_seconds": int(time_to_reset),
                    "next_reset_formatted": self._format_time(time_to_reset)
                },
                "window_7d": {
                    "messages": msgs_7d,
                    "limit": self.WINDOW_7D_LIMIT,
                    "percent": round((msgs_7d / self.WINDOW_7D_LIMIT) * 100, 2),
                    "tokens_in": tokens_in_7d,
                    "tokens_out": tokens_out_7d
                }
            },
            "costs": {
                "per_message_brl": self.COST_PER_MSG_BRL,
                "today_brl": cost_today_brl,
                "month_brl": cost_month_brl,
                "plan_value_brl": self.PRICE_BRL
            },
            "tips": self._get_usage_tips(msgs_5h, msgs_7d),
            "status": self._get_status(msgs_5h, msgs_7d)
        }

    def _format_time(self, seconds: float) -> str:
        """Formata segundos em string legível"""
        if seconds <= 0:
            return "Disponível"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)

        if hours > 0:
            return f"{hours}h {minutes}min"
        return f"{minutes}min"

    def _estimate_cost_today(self, messages: list) -> float:
        """Estima custo do dia atual"""
        today = datetime.now().date().isoformat()
        msgs_today = [m for m in messages if m["timestamp"].startswith(today)]
        return round(len(msgs_today) * self.COST_PER_MSG_BRL, 2)

    def _estimate_cost_month(self, messages: list) -> float:
        """Estima custo do mês atual"""
        month = datetime.now().strftime("%Y-%m")
        msgs_month = [m for m in messages if m["timestamp"].startswith(month)]
        return round(len(msgs_month) * self.COST_PER_MSG_BRL, 2)

    def _get_status(self, msgs_5h: int, msgs_7d: int) -> dict:
        """Retorna status visual do uso"""
        pct_5h = (msgs_5h / self.WINDOW_5H_LIMIT) * 100

        if pct_5h < 50:
            return {"level": "healthy", "color": "green", "icon": "check-circle"}
        elif pct_5h < 80:
            return {"level": "moderate", "color": "yellow", "icon": "alert-circle"}
        elif pct_5h < 95:
            return {"level": "high", "color": "orange", "icon": "alert-triangle"}
        else:
            return {"level": "critical", "color": "red", "icon": "x-circle"}

    def _get_usage_tips(self, msgs_5h: int, msgs_7d: int) -> list:
        """Retorna dicas baseadas no uso atual"""
        tips = []
        pct_5h = (msgs_5h / self.WINDOW_5H_LIMIT) * 100

        if pct_5h > 80:
            tips.append({
                "type": "warning",
                "message": "Uso alto! Considere aguardar o reset da janela de 5h"
            })

        if pct_5h > 50:
            tips.append({
                "type": "tip",
                "message": "Use Haiku para tarefas simples (economia de 80%)"
            })

        tips.append({
            "type": "info",
            "message": f"Próximo reset em {self._format_time((5*3600) - (msgs_5h * 20))}"
        })

        return tips


# Singleton
_service: Optional[ClaudeUsageService] = None

def get_claude_usage_service() -> ClaudeUsageService:
    """Retorna instância singleton do serviço"""
    global _service
    if _service is None:
        _service = ClaudeUsageService()
    return _service
