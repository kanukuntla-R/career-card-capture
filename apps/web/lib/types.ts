export type EventType = "TABLING" | "CLASSROOM_PRESENTATION" | "OTHER";
export type SessionStatus = "IN_PROGRESS" | "COMPLETED" | "ARCHIVED";
export type CardType = "EMPLOYER" | "QUESTION" | "UNKNOWN";
export type CardStatus =
  | "CAPTURED"
  | "PROCESSING"
  | "NEEDS_REVIEW"
  | "APPROVED"
  | "SKIPPED"
  | "OCR_FAILED"
  | "REMOVED";
export type SheetSyncState = "NOT_REQUIRED" | "PENDING" | "SYNCED" | "ERROR";

export interface CareerEvent {
  id: string;
  title: string;
  event_type: EventType;
  event_date: string | null;
  location: string | null;
  course: string | null;
  topic: string | null;
  notes: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface CaptureSession {
  id: string;
  event_id: string;
  name: string;
  status: SessionStatus;
  started_at: string;
  completed_at: string | null;
  archived_at: string | null;
  last_activity_at: string;
  created_at: string;
  updated_at: string;
  event_title: string;
  event_type: EventType;
  total_cards: number;
  review_cards: number;
  approved_cards: number;
  skipped_cards: number;
}

export interface CardRecord {
  id: string;
  event_id: string;
  session_id: string;
  sequence_number: number;
  status: CardStatus;
  suggested_type: CardType | null;
  final_type: CardType | null;
  raw_ocr: string | null;
  final_text: string | null;
  ocr_confidence: number | null;
  ocr_provider: string | null;
  ocr_model: string | null;
  was_edited: boolean;
  has_image: boolean;
  captured_at: string;
  approved_at: string | null;
  removed_at: string | null;
  removed_reason: string | null;
  sync_status: SheetSyncState;
  created_at: string;
  updated_at: string;
}

export interface CardRevision {
  id: string;
  card_id: string;
  revision_number: number;
  previous_final_type: CardType;
  previous_final_text: string;
  new_final_type: CardType;
  new_final_text: string;
  reason: string | null;
  changed_at: string;
  changed_by: string | null;
}

export interface OCRProviderInfo {
  id: "mock" | "hunyuan";
  enabled: boolean;
  ready: boolean;
  model: string | null;
  detail?: string | null;
}

export interface GoogleSheetsStatus {
  enabled: boolean;
  configured: boolean;
  tab_name: string;
  spreadsheet_url: string | null;
  eligible_cards: number;
  pending: number;
  synced: number;
  errors: number;
  last_error: string | null;
}

export interface GoogleSheetsSyncResult extends GoogleSheetsStatus {
  attempted: number;
  succeeded: number;
  failed: number;
}

export interface EventDraft {
  title: string;
  event_type: EventType;
  event_date?: string;
  location?: string;
  course?: string;
  topic?: string;
  notes?: string;
}
