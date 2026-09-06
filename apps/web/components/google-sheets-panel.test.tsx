import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { GoogleSheetsStatus } from "@/lib/types";

import { GoogleSheetsPanel } from "./google-sheets-panel";

afterEach(cleanup);

const connected: GoogleSheetsStatus = {
  enabled: true,
  configured: true,
  tab_name: "Responses",
  spreadsheet_url: "https://docs.google.com/spreadsheets/d/test/edit",
  eligible_cards: 12,
  pending: 2,
  synced: 10,
  errors: 0,
  last_error: null,
};

describe("GoogleSheetsPanel", () => {
  it("shows connected counts and starts a sync", async () => {
    const onSync = vi.fn().mockResolvedValue(undefined);
    render(<GoogleSheetsPanel status={connected} busy={false} onSync={onSync} />);

    expect(screen.getByText("Connected")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sync approved cards" }));
    await waitFor(() => expect(onSync).toHaveBeenCalledOnce());
    expect(screen.getByRole("link", { name: "Download CSV" })).toHaveAttribute(
      "href",
      "/backend/api/v1/export/cards.csv",
    );
  });

  it("keeps CSV available before Google is configured", () => {
    render(
      <GoogleSheetsPanel
        status={{ ...connected, enabled: false, configured: false, spreadsheet_url: null }}
        busy={false}
        onSync={vi.fn()}
      />,
    );
    expect(screen.getByText("Not connected")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sync approved cards" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download CSV" })).toBeInTheDocument();
  });
});
