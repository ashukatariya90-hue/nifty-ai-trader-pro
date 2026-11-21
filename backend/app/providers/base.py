"""Provider-neutral, read-only market-data contract.

Implement this interface only with a licensed provider's official SDK/API.
This package intentionally contains no broker authentication or order APIs.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass(frozen=True)
class Quote:
    symbol: str
    last_price: float
    timestamp: datetime
    source: str
    delayed: bool = False

class ReadOnlyMarketDataProvider(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def quote(self, symbol: str) -> Optional[Quote]: ...

    @abstractmethod
    def status(self) -> dict: ...
