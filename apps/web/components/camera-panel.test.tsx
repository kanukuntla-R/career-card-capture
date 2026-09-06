import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CameraPanel } from "./camera-panel";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("CameraPanel", () => {
  it("keeps the live stream attached across review and the next capture", async () => {
    const stop = vi.fn();
    const stream = {
      getTracks: () => [{ stop }],
      getVideoTracks: () => [{ getSettings: () => ({ deviceId: "camera-1" }) }],
    } as unknown as MediaStream;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue(stream),
        enumerateDevices: vi.fn().mockResolvedValue([]),
      },
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();

    const onCapture = vi.fn().mockResolvedValue(undefined);
    const { rerender } = render(
      <CameraPanel busy={false} locked={false} imageUrl={null} onCapture={onCapture} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Enable camera" }));
    await waitFor(() => expect(screen.getByText("Camera live")).toBeInTheDocument());
    const originalVideo = screen.getByLabelText("Live webcam preview") as HTMLVideoElement;
    expect(originalVideo.srcObject).toBe(stream);

    rerender(
      <CameraPanel
        busy={false}
        locked
        imageUrl="blob:review-card"
        onCapture={onCapture}
      />,
    );
    expect(screen.getByLabelText("Live webcam preview")).toBe(originalVideo);
    expect(screen.getByAltText("Captured response card")).toBeInTheDocument();

    rerender(
      <CameraPanel busy={false} locked={false} imageUrl={null} onCapture={onCapture} />,
    );
    expect(screen.getByLabelText("Live webcam preview")).toBe(originalVideo);
    expect(originalVideo.srcObject).toBe(stream);
    expect(stop).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /Capture card/ })).toBeEnabled();
  });
});
