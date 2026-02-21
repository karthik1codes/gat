from __future__ import annotations

from sqlalchemy import create_engine

from ..config import DatabaseConfig
from .base import BaseConnector, ConnectionResult


class SQLServerConnector(BaseConnector):
    def connect(self, config: DatabaseConfig) -> ConnectionResult:
        try:
            url = config.get_url()
            engine = create_engine(url, pool_pre_ping=True)
            if not self.test_connection(engine):
                return ConnectionResult(None, "Connection test failed")
            return ConnectionResult(engine)
        except Exception as e:
            return ConnectionResult(None, str(e))
