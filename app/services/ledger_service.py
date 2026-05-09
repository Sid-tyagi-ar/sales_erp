from typing import List, Dict, Any
from app.models.ledger import StockLedgerEntry
from app.schemas.ledger import StockLedgerResponse

class LedgerService:
    async def append(self, tenant_id: str, entry: StockLedgerEntry) -> None:
        """
        TODO: always called inside a batch, never standalone
        """
        pass

    async def list(self, tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> List[StockLedgerResponse]:
        """
        TODO: Implement DB logic to list stock ledger entries.
        """
        return []
