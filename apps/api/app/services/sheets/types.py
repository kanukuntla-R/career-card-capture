from dataclasses import dataclass
from typing import Protocol

SHEET_HEADERS = (
    "Record ID",
    "Timestamp",
    "Event",
    "Event Type",
    "Session",
    "Response Type",
    "Response",
    "Last Updated",
)


class SheetSyncError(RuntimeError):
    """A safe operator-facing Google Sheets synchronization error."""


class SheetGateway(Protocol):
    def ensure_schema(self) -> None: ...

    def find_record_row(self, record_id: str, cached_row: int | None = None) -> int | None: ...

    def append_row(self, values: list[str]) -> int: ...

    def update_row(self, row_number: int, values: list[str]) -> None: ...


@dataclass(frozen=True)
class SyncRunCounts:
    attempted: int = 0
    succeeded: int = 0
    failed: int = 0
