"""
Risk Assessment Storage - Historical Tracking

SQLite-based storage for risk assessments to enable:
- Performance tracking over time
- Weight calibration based on outcomes
- Risk dashboard analytics
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskRecord:
    """A stored risk assessment record."""
    id: Optional[int]
    timestamp: str
    token_pair: str
    chain: str
    position_size_usd: float
    overall_score: float
    risk_level: str
    volatility_risk: float
    drawdown_risk: float
    liquidity_risk: float
    onchain_risk: float
    outcome: str  # 'approved', 'reduced', 'blocked'
    position_multiplier: float
    recommendations: str  # JSON array


class RiskStorage:
    """
    SQLite-based storage for risk assessment history.
    
    Usage:
        storage = RiskStorage()
        storage.initialize()
        
        # Store assessment
        record_id = storage.store(
            token_pair="ETH/USDT",
            chain="ethereum",
            position_size_usd=1000,
            overall_score=25.5,
            risk_level="low",
            volatility_risk=12.0,
            drawdown_risk=8.0,
            liquidity_risk=5.0,
            onchain_risk=10.0,
            outcome="approved",
            position_multiplier=1.0,
            recommendations=["Low risk profile"]
        )
        
        # Query recent assessments
        recent = storage.get_recent(limit=10)
        
        # Get statistics
        stats = storage.get_statistics()
    """
    
    def __init__(self, db_path: str = "./data/risk_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    def initialize(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                token_pair TEXT NOT NULL,
                chain TEXT NOT NULL,
                position_size_usd REAL NOT NULL,
                overall_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                volatility_risk REAL NOT NULL,
                drawdown_risk REAL NOT NULL,
                liquidity_risk REAL NOT NULL,
                onchain_risk REAL NOT NULL,
                outcome TEXT NOT NULL,
                position_multiplier REAL NOT NULL,
                recommendations TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_timestamp 
            ON risk_history(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_level 
            ON risk_history(risk_level)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_risk_outcome 
            ON risk_history(outcome)
        """)
        
        conn.commit()
        logger.info("Risk storage initialized at %s", self.db_path)
    
    def store(
        self,
        token_pair: str,
        chain: str,
        position_size_usd: float,
        overall_score: float,
        risk_level: str,
        volatility_risk: float,
        drawdown_risk: float,
        liquidity_risk: float,
        onchain_risk: float,
        outcome: str,
        position_multiplier: float,
        recommendations: list[str],
    ) -> int:
        """
        Store a risk assessment record.
        
        Returns:
            The ID of the inserted record
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO risk_history (
                timestamp, token_pair, chain, position_size_usd,
                overall_score, risk_level, volatility_risk, drawdown_risk,
                liquidity_risk, onchain_risk, outcome, position_multiplier,
                recommendations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            token_pair,
            chain,
            position_size_usd,
            overall_score,
            risk_level,
            volatility_risk,
            drawdown_risk,
            liquidity_risk,
            onchain_risk,
            outcome,
            position_multiplier,
            json.dumps(recommendations),
        ))
        
        conn.commit()
        record_id = cursor.lastrowid
        logger.debug(
            "Stored risk assessment: id=%d, level=%s, score=%.2f, outcome=%s",
            record_id, risk_level, overall_score, outcome
        )
        return record_id
    
    def get_recent(self, limit: int = 100) -> list[RiskRecord]:
        """Get the most recent risk assessments."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM risk_history 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]
    
    def get_by_token_pair(self, token_pair: str, limit: int = 50) -> list[RiskRecord]:
        """Get risk assessments for a specific token pair."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM risk_history 
            WHERE token_pair = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (token_pair, limit))
        
        rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]
    
    def get_by_risk_level(self, risk_level: str, limit: int = 50) -> list[RiskRecord]:
        """Get risk assessments for a specific risk level."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM risk_history 
            WHERE risk_level = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (risk_level.lower(), limit))
        
        rows = cursor.fetchall()
        return [self._row_to_record(row) for row in rows]
    
    def get_statistics(self) -> dict:
        """Get aggregate statistics for all stored assessments."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM risk_history")
        total_count = cursor.fetchone()[0]
        
        # Count by risk level
        cursor.execute("""
            SELECT risk_level, COUNT(*) 
            FROM risk_history 
            GROUP BY risk_level
        """)
        by_level = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count by outcome
        cursor.execute("""
            SELECT outcome, COUNT(*) 
            FROM risk_history 
            GROUP BY outcome
        """)
        by_outcome = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Average scores
        cursor.execute("""
            SELECT 
                AVG(overall_score),
                AVG(volatility_risk),
                AVG(drawdown_risk),
                AVG(liquidity_risk),
                AVG(onchain_risk)
            FROM risk_history
        """)
        row = cursor.fetchone()
        avg_scores = {
            "overall": row[0] or 0,
            "volatility": row[1] or 0,
            "drawdown": row[2] or 0,
            "liquidity": row[3] or 0,
            "onchain": row[4] or 0,
        }
        
        # Position size statistics
        cursor.execute("""
            SELECT 
                AVG(position_size_usd),
                SUM(position_size_usd * position_multiplier) / SUM(position_size_usd)
            FROM risk_history
            WHERE outcome != 'blocked'
        """)
        row = cursor.fetchone()
        position_stats = {
            "avg_position_size": row[0] or 0,
            "avg_position_multiplier": row[1] or 1.0,
        }
        
        return {
            "total_assessments": total_count,
            "by_risk_level": by_level,
            "by_outcome": by_outcome,
            "average_scores": avg_scores,
            "position_statistics": position_stats,
        }
    
    def get_trends(self, days: int = 7) -> dict:
        """Get risk trends over the past N days."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as count,
                AVG(overall_score) as avg_score,
                risk_level
            FROM risk_history
            WHERE timestamp >= DATETIME('now', ?)
            GROUP BY DATE(timestamp), risk_level
            ORDER BY date DESC
        """, (f'-{days} days',))
        
        rows = cursor.fetchall()
        
        trends = {}
        for row in rows:
            date = row[0]
            if date not in trends:
                trends[date] = {"date": date, "total": 0, "by_level": {}}
            trends[date]["total"] += row[1]
            trends[date]["by_level"][row[3]] = {
                "count": row[1],
                "avg_score": row[2],
            }
        
        return {"days": days, "trends": list(trends.values())}
    
    def _row_to_record(self, row: sqlite3.Row) -> RiskRecord:
        """Convert a database row to a RiskRecord."""
        return RiskRecord(
            id=row["id"],
            timestamp=row["timestamp"],
            token_pair=row["token_pair"],
            chain=row["chain"],
            position_size_usd=row["position_size_usd"],
            overall_score=row["overall_score"],
            risk_level=row["risk_level"],
            volatility_risk=row["volatility_risk"],
            drawdown_risk=row["drawdown_risk"],
            liquidity_risk=row["liquidity_risk"],
            onchain_risk=row["onchain_risk"],
            outcome=row["outcome"],
            position_multiplier=row["position_multiplier"],
            recommendations=row["recommendations"],
        )
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# Singleton instance
_risk_storage: Optional[RiskStorage] = None


def get_risk_storage(db_path: str = "./data/risk_history.db") -> RiskStorage:
    """Get or create the singleton RiskStorage instance."""
    global _risk_storage
    if _risk_storage is None:
        _risk_storage = RiskStorage(db_path)
        _risk_storage.initialize()
    return _risk_storage