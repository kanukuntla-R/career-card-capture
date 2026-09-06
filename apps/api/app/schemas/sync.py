from pydantic import BaseModel


class SheetSyncStatusRead(BaseModel):
    enabled: bool
    configured: bool
    tab_name: str
    spreadsheet_url: str | None
    eligible_cards: int
    pending: int
    synced: int
    errors: int
    last_error: str | None


class SheetSyncRunRead(SheetSyncStatusRead):
    attempted: int
    succeeded: int
    failed: int


class SheetSyncVerifyRead(BaseModel):
    ready: bool
    message: str
