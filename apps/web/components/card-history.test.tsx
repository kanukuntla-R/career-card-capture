import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { CardRecord } from "@/lib/types";

import { CardHistory } from "./card-history";

vi.mock("@/lib/api", () => ({
  api: {
    cardRevisions: vi.fn().mockResolvedValue([]),
  },
}));

afterEach(cleanup);

const approvedCard: CardRecord = {
  id: "card-1",
  event_id: "event-1",
  session_id: "session-1",
  sequence_number: 1,
  status: "APPROVED",
  suggested_type: "EMPLOYER",
  final_type: "EMPLOYER",
  raw_ocr: "Fox Sportz",
  final_text: "Fox Sports",
  ocr_confidence: null,
  ocr_provider: "hunyuan",
  ocr_model: "HYVL",
  was_edited: true,
  has_image: false,
  captured_at: "2026-08-22T12:00:00Z",
  approved_at: "2026-08-22T12:01:00Z",
  removed_at: null,
  removed_reason: null,
  sync_status: "SYNCED",
  created_at: "2026-08-22T12:00:00Z",
  updated_at: "2026-08-22T12:01:00Z",
};

describe("CardHistory", () => {
  it("edits an approved card while showing the untouched OCR", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <CardHistory
        cards={[approvedCard]}
        busy={false}
        onSave={onSave}
        onRemove={vi.fn()}
        onRestore={vi.fn()}
        onRetrySync={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByText("Fox Sportz")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Approved response"), {
      target: { value: "FOX Sports" },
    });
    fireEvent.click(screen.getByLabelText("Question"));
    fireEvent.change(screen.getByLabelText(/Reason for change/), {
      target: { value: "Verified against the physical card" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith(
        "card-1",
        "QUESTION",
        "FOX Sports",
        "Verified against the physical card",
      ),
    );
  });

  it("confirms removal and exposes removed cards for restoration", async () => {
    const onRemove = vi.fn().mockResolvedValue(undefined);
    const onRestore = vi.fn().mockResolvedValue(undefined);
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <CardHistory
        cards={[approvedCard]}
        busy={false}
        onSave={onSave}
        onRemove={onRemove}
        onRestore={onRestore}
        onRetrySync={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove card 01" }));
    expect(screen.getByRole("alertdialog", { name: "Remove card 01?" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove card" }));
    await waitFor(() => expect(onRemove).toHaveBeenCalledWith("card-1"));

    const removedCard: CardRecord = {
      ...approvedCard,
      status: "REMOVED",
      removed_at: "2026-08-22T12:05:00Z",
      removed_reason: "Removed by operator.",
    };
    rerender(
      <CardHistory
        cards={[removedCard]}
        busy={false}
        onSave={onSave}
        onRemove={onRemove}
        onRestore={onRestore}
        onRetrySync={vi.fn()}
      />,
    );

    expect(screen.getByText("No active cards")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show removed (1)" }));
    fireEvent.click(screen.getByRole("button", { name: "Restore card 01" }));
    await waitFor(() => expect(onRestore).toHaveBeenCalledWith("card-1"));
  });
});
