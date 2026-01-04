"""
NERD SPACE V5.0 - History Database
AI FIRST Edition

SQLite compacto para histórico de métricas.
- ~1KB por registro
- Agregação automática: hora → dia → semana → mês
- Retenção: 7 dias detalhado, 30 dias agregado, 1 ano resumido
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from contextlib import contextmanager

# Database path
DB_FILE = Path(__file__).parent.parent / "data" / "history.db"


class HistoryDB:
    """Banco de dados SQLite para histórico de métricas"""

    def __init__(self):
        self.db_path = DB_FILE
        self._ensure_db()

    def _ensure_db(self):
        """Garante que o banco de dados existe e tem as tabelas necessárias"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabela de métricas detalhadas (dados a cada coleta)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics_raw (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    ram_percent REAL,
                    ram_used_gb REAL,
                    disk_percent REAL,
                    disk_used_gb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    temperature_c REAL,
                    battery_percent REAL,
                    process_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tabela de métricas agregadas por hora
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics_hourly (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour TEXT NOT NULL UNIQUE,
                    cpu_avg REAL,
                    cpu_max REAL,
                    ram_avg REAL,
                    ram_max REAL,
                    disk_avg REAL,
                    network_sent_total_mb REAL,
                    network_recv_total_mb REAL,
                    sample_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tabela de métricas agregadas por dia
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metrics_daily (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    cpu_avg REAL,
                    cpu_max REAL,
                    ram_avg REAL,
                    ram_max REAL,
                    disk_avg REAL,
                    disk_max REAL,
                    network_sent_total_mb REAL,
                    network_recv_total_mb REAL,
                    uptime_hours REAL,
                    sample_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tabela de eventos/alertas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT,
                    data TEXT,
                    acknowledged INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Índices para performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_raw_timestamp ON metrics_raw(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_metrics_hourly_hour ON metrics_hourly(hour)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)')

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Context manager para conexão com o banco"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def record_metrics(self, metrics: Dict[str, Any]):
        """Registra métricas coletadas"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO metrics_raw (
                    timestamp, cpu_percent, ram_percent, ram_used_gb,
                    disk_percent, disk_used_gb, network_sent_mb, network_recv_mb,
                    temperature_c, battery_percent, process_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                metrics.get('cpu_percent', 0),
                metrics.get('ram_percent', 0),
                metrics.get('ram_used_gb', 0),
                metrics.get('disk_percent', 0),
                metrics.get('disk_used_gb', 0),
                metrics.get('network_sent_mb', 0),
                metrics.get('network_recv_mb', 0),
                metrics.get('temperature_c'),
                metrics.get('battery_percent'),
                metrics.get('process_count', 0)
            ))
            conn.commit()

    def get_recent_metrics(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """Retorna métricas dos últimos N minutos"""
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM metrics_raw
                WHERE timestamp > ?
                ORDER BY timestamp DESC
            ''', (cutoff,))

            return [dict(row) for row in cursor.fetchall()]

    def get_hourly_metrics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Retorna métricas agregadas por hora"""
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM metrics_hourly
                WHERE hour > ?
                ORDER BY hour DESC
            ''', (cutoff,))

            return [dict(row) for row in cursor.fetchall()]

    def get_daily_metrics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Retorna métricas agregadas por dia"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM metrics_daily
                WHERE date > ?
                ORDER BY date DESC
            ''', (cutoff,))

            return [dict(row) for row in cursor.fetchall()]

    def aggregate_hourly(self):
        """Agrega métricas raw em hourly"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Pegar hora atual e anterior
            now = datetime.now()
            current_hour = now.strftime("%Y-%m-%d %H")
            prev_hour = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H")

            # Agregar dados da hora anterior
            cursor.execute('''
                SELECT
                    strftime('%Y-%m-%d %H', timestamp) as hour,
                    AVG(cpu_percent) as cpu_avg,
                    MAX(cpu_percent) as cpu_max,
                    AVG(ram_percent) as ram_avg,
                    MAX(ram_percent) as ram_max,
                    AVG(disk_percent) as disk_avg,
                    SUM(network_sent_mb) as network_sent_total_mb,
                    SUM(network_recv_mb) as network_recv_total_mb,
                    COUNT(*) as sample_count
                FROM metrics_raw
                WHERE strftime('%Y-%m-%d %H', timestamp) = ?
                GROUP BY strftime('%Y-%m-%d %H', timestamp)
            ''', (prev_hour,))

            row = cursor.fetchone()
            if row and row['sample_count'] > 0:
                cursor.execute('''
                    INSERT OR REPLACE INTO metrics_hourly
                    (hour, cpu_avg, cpu_max, ram_avg, ram_max, disk_avg,
                     network_sent_total_mb, network_recv_total_mb, sample_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['hour'], row['cpu_avg'], row['cpu_max'],
                    row['ram_avg'], row['ram_max'], row['disk_avg'],
                    row['network_sent_total_mb'], row['network_recv_total_mb'],
                    row['sample_count']
                ))

            conn.commit()

    def aggregate_daily(self):
        """Agrega métricas hourly em daily"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Pegar dia anterior
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

            cursor.execute('''
                SELECT
                    substr(hour, 1, 10) as date,
                    AVG(cpu_avg) as cpu_avg,
                    MAX(cpu_max) as cpu_max,
                    AVG(ram_avg) as ram_avg,
                    MAX(ram_max) as ram_max,
                    AVG(disk_avg) as disk_avg,
                    MAX(disk_avg) as disk_max,
                    SUM(network_sent_total_mb) as network_sent_total_mb,
                    SUM(network_recv_total_mb) as network_recv_total_mb,
                    COUNT(*) as uptime_hours,
                    SUM(sample_count) as sample_count
                FROM metrics_hourly
                WHERE substr(hour, 1, 10) = ?
                GROUP BY substr(hour, 1, 10)
            ''', (yesterday,))

            row = cursor.fetchone()
            if row and row['sample_count'] > 0:
                cursor.execute('''
                    INSERT OR REPLACE INTO metrics_daily
                    (date, cpu_avg, cpu_max, ram_avg, ram_max, disk_avg, disk_max,
                     network_sent_total_mb, network_recv_total_mb, uptime_hours, sample_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['date'], row['cpu_avg'], row['cpu_max'],
                    row['ram_avg'], row['ram_max'], row['disk_avg'], row['disk_max'],
                    row['network_sent_total_mb'], row['network_recv_total_mb'],
                    row['uptime_hours'], row['sample_count']
                ))

            conn.commit()

    def cleanup_old_data(self):
        """Remove dados antigos seguindo política de retenção"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Raw: manter 7 dias
            cutoff_raw = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute('DELETE FROM metrics_raw WHERE timestamp < ?', (cutoff_raw,))

            # Hourly: manter 30 dias
            cutoff_hourly = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H")
            cursor.execute('DELETE FROM metrics_hourly WHERE hour < ?', (cutoff_hourly,))

            # Daily: manter 365 dias
            cutoff_daily = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            cursor.execute('DELETE FROM metrics_daily WHERE date < ?', (cutoff_daily,))

            # Events: manter 30 dias
            cutoff_events = (datetime.now() - timedelta(days=30)).isoformat()
            cursor.execute('DELETE FROM events WHERE timestamp < ?', (cutoff_events,))

            conn.commit()

            # Vacuum para recuperar espaço
            cursor.execute('VACUUM')

    def log_event(self, event_type: str, severity: str, title: str,
                  message: str = "", data: Dict = None):
        """Registra um evento/alerta"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (timestamp, type, severity, title, message, data)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                event_type,
                severity,
                title,
                message,
                json.dumps(data) if data else None
            ))
            conn.commit()

    def get_recent_events(self, limit: int = 50, severity: str = None) -> List[Dict[str, Any]]:
        """Retorna eventos recentes"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if severity:
                cursor.execute('''
                    SELECT * FROM events
                    WHERE severity = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (severity, limit))
            else:
                cursor.execute('''
                    SELECT * FROM events
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))

            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event.get('data'):
                    event['data'] = json.loads(event['data'])
                events.append(event)

            return events

    def get_db_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do banco de dados"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # Contagem de registros por tabela
            for table in ['metrics_raw', 'metrics_hourly', 'metrics_daily', 'events']:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]

            # Tamanho do banco
            stats['db_size_kb'] = self.db_path.stat().st_size / 1024 if self.db_path.exists() else 0

            # Data do registro mais antigo e mais recente
            cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM metrics_raw')
            row = cursor.fetchone()
            stats['oldest_record'] = row[0]
            stats['newest_record'] = row[1]

            return stats


# Singleton
_db: Optional[HistoryDB] = None

def get_history_db() -> HistoryDB:
    """Retorna instância singleton do banco"""
    global _db
    if _db is None:
        _db = HistoryDB()
    return _db
