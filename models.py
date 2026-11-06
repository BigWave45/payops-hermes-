"""Normalized provider-neutral records."""
from dataclasses import asdict, dataclass
from typing import Optional

@dataclass
class Transaction:
    provider: str
    transaction_id: str
    reference: str
    amount_minor: int
    currency: str
    status: str
    paid_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class Settlement:
    provider: str
    settlement_id: str
    currency: str
    amount_minor: int
    status: str
    settled_at: Optional[str] = None

    def to_dict(self):
        return asdict(self)
