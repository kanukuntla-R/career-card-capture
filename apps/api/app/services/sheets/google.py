import re
from pathlib import Path
from typing import Any

from app.services.sheets.types import SHEET_HEADERS, SheetSyncError

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _safe_tab_name(tab_name: str) -> str:
    return "'" + tab_name.replace("'", "''") + "'"


class GoogleSheetsGateway:
    def __init__(self, spreadsheet_id: str, tab_name: str, credentials_path: str) -> None:
        self.spreadsheet_id = spreadsheet_id
        self.tab_name = tab_name
        self.credentials_path = credentials_path
        self._values_resource: Any | None = None

    @property
    def values(self):
        if self._values_resource is None:
            credentials_file = Path(self.credentials_path)
            if not credentials_file.is_file():
                raise SheetSyncError("Google service-account credentials are not available.")
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                credentials = service_account.Credentials.from_service_account_file(
                    credentials_file,
                    scopes=[SHEETS_SCOPE],
                )
                service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
                self._values_resource = service.spreadsheets().values()
            except (OSError, ValueError, KeyError) as exc:
                raise SheetSyncError("Google service-account credentials are invalid.") from exc
        return self._values_resource

    def _range(self, cells: str) -> str:
        return f"{_safe_tab_name(self.tab_name)}!{cells}"

    @staticmethod
    def _execute(request):
        try:
            return request.execute()
        except Exception as exc:
            raise SheetSyncError(
                "Google Sheets could not be reached or the service account lacks access."
            ) from exc

    def ensure_schema(self) -> None:
        result = self._execute(
            self.values.get(
                spreadsheetId=self.spreadsheet_id,
                range=self._range("A1:H1"),
            )
        )
        rows = result.get("values", [])
        current = rows[0] if rows else []
        if not current:
            self._execute(
                self.values.update(
                    spreadsheetId=self.spreadsheet_id,
                    range=self._range("A1:H1"),
                    valueInputOption="RAW",
                    body={"values": [list(SHEET_HEADERS)]},
                )
            )
            return
        if tuple(current) != SHEET_HEADERS:
            raise SheetSyncError(
                "The configured sheet tab has unexpected columns. Use the documented header row."
            )

    def find_record_row(self, record_id: str, cached_row: int | None = None) -> int | None:
        if cached_row and cached_row > 1:
            result = self._execute(
                self.values.get(
                    spreadsheetId=self.spreadsheet_id,
                    range=self._range(f"A{cached_row}"),
                )
            )
            rows = result.get("values", [])
            if rows and rows[0] and rows[0][0] == record_id:
                return cached_row

        result = self._execute(
            self.values.get(
                spreadsheetId=self.spreadsheet_id,
                range=self._range("A2:A"),
            )
        )
        for row_number, row in enumerate(result.get("values", []), start=2):
            if row and row[0] == record_id:
                return row_number
        return None

    def append_row(self, values: list[str]) -> int:
        result = self._execute(
            self.values.append(
                spreadsheetId=self.spreadsheet_id,
                range=self._range("A:H"),
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [values]},
            )
        )
        updated_range = result.get("updates", {}).get("updatedRange", "")
        match = re.search(r"![A-Z]+(\d+):", updated_range)
        if match:
            return int(match.group(1))
        row_number = self.find_record_row(values[0])
        if row_number is None:
            raise SheetSyncError("Google Sheets appended the record but did not return its row.")
        return row_number

    def update_row(self, row_number: int, values: list[str]) -> None:
        self._execute(
            self.values.update(
                spreadsheetId=self.spreadsheet_id,
                range=self._range(f"A{row_number}:H{row_number}"),
                valueInputOption="RAW",
                body={"values": [values]},
            )
        )
