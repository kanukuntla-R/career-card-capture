import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CareerEvent } from "@/lib/types";

import { EventForm } from "./new-event-form";

const eventRecord: CareerEvent = {
  id: "event-1",
  title: "Fall Welcome Tabling",
  event_type: "TABLING",
  event_date: "2026-08-22",
  location: "Memorial Union",
  course: null,
  topic: null,
  notes: "Original note",
  is_archived: false,
  created_at: "2026-08-22T12:00:00Z",
  updated_at: "2026-08-22T12:00:00Z",
};

describe("EventForm", () => {
  it("updates event details and confirms safe removal", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onRemove = vi.fn().mockResolvedValue(undefined);
    render(
      <EventForm
        busy={false}
        initialEvent={eventRecord}
        onCancel={vi.fn()}
        onRemove={onRemove}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Event title/), {
      target: { value: "Updated Career Fair" },
    });
    fireEvent.change(screen.getByLabelText("Location"), {
      target: { value: "Student Pavilion" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save event" }));
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Updated Career Fair",
          location: "Student Pavilion",
        }),
      ),
    );

    fireEvent.click(screen.getByRole("button", { name: "Remove event" }));
    expect(screen.getByText(/sessions and cards will be preserved/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Remove event" }));
    expect(onRemove).toHaveBeenCalledOnce();
  });
});
