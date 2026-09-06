"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { isEditableTarget } from "@/lib/shortcuts";

interface CameraPanelProps {
  busy: boolean;
  locked: boolean;
  imageUrl: string | null;
  onCapture: (image: Blob, previewUrl: string, mockText?: string) => Promise<void>;
}

export function CameraPanel({ busy, locked, imageUrl, onCapture }: CameraPanelProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [deviceId, setDeviceId] = useState("");
  const [cameraState, setCameraState] = useState<"idle" | "starting" | "ready" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }, []);

  const startCamera = useCallback(
    async (requestedDeviceId?: string) => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraState("error");
        setMessage("This browser does not support camera capture. You can still try a sample card.");
        return;
      }
      setCameraState("starting");
      setMessage("");
      stopCamera();
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: requestedDeviceId
            ? { deviceId: { exact: requestedDeviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } }
            : { width: { ideal: 1920 }, height: { ideal: 1080 } },
        });
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        const cameras = (await navigator.mediaDevices.enumerateDevices()).filter(
          (device) => device.kind === "videoinput",
        );
        setDevices(cameras);
        const activeId = stream.getVideoTracks()[0]?.getSettings().deviceId ?? requestedDeviceId ?? "";
        setDeviceId(activeId);
        if (activeId) localStorage.setItem("career-card-camera", activeId);
        setCameraState("ready");
      } catch (error) {
        setCameraState("error");
        setMessage(
          error instanceof DOMException && error.name === "NotAllowedError"
            ? "Camera access is blocked. Allow camera permission in the browser, then try again."
            : "The camera could not start. Check that another app is not using it.",
        );
      }
    },
    [stopCamera],
  );

  useEffect(() => stopCamera, [stopCamera]);

  const captureVideo = useCallback(async () => {
    const video = videoRef.current;
    if (!video || cameraState !== "ready" || locked || busy) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth || 1920;
    canvas.height = video.videoHeight || 1080;
    canvas.getContext("2d")?.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92),
    );
    if (!blob) return;
    await onCapture(blob, URL.createObjectURL(blob));
  }, [busy, cameraState, locked, onCapture]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (
        event.code === "Space" &&
        !isEditableTarget(event.target) &&
        cameraState === "ready" &&
        !locked &&
        !busy
      ) {
        event.preventDefault();
        void captureVideo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [busy, cameraState, captureVideo, locked]);

  const captureSample = async () => {
    if (locked || busy) return;
    const canvas = document.createElement("canvas");
    canvas.width = 1280;
    canvas.height = 800;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.fillStyle = "#dad4c8";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.save();
    context.translate(640, 400);
    context.rotate(-0.035);
    context.shadowColor = "rgba(28, 23, 35, .22)";
    context.shadowBlur = 28;
    context.fillStyle = "#fffdf8";
    context.fillRect(-460, -250, 920, 500);
    context.shadowColor = "transparent";
    context.fillStyle = "#702541";
    context.fillRect(-460, 175, 920, 75);
    context.fillStyle = "#302b35";
    context.font = "italic 48px cursive";
    context.fillText("Fox Sportz", -300, 20);
    context.restore();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.92),
    );
    if (!blob) return;
    await onCapture(blob, URL.createObjectURL(blob), "Fox Sportz");
  };

  const selectCamera = (nextDeviceId: string) => {
    setDeviceId(nextDeviceId);
    void startCamera(nextDeviceId);
  };

  return (
    <section className="camera-panel" aria-label="Card camera">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Capture</p>
          <h2>{locked ? "Card ready to review" : "Place a card in the guide"}</h2>
        </div>
        <span className={`live-pill ${cameraState === "ready" ? "is-live" : ""}`}>
          <span aria-hidden="true" />
          {cameraState === "ready" ? "Camera live" : "Camera off"}
        </span>
      </div>

      <div className={`camera-stage ${locked ? "has-capture" : ""}`}>
        <video ref={videoRef} muted playsInline aria-label="Live webcam preview" />
        {locked && imageUrl ? (
          // Dynamic authenticated image is intentionally rendered directly.
          // eslint-disable-next-line @next/next/no-img-element
          <img className="captured-image" src={imageUrl} alt="Captured response card" />
        ) : (
          <>
            <div className="card-guide" aria-hidden="true">
              <span className="corner corner-tl" />
              <span className="corner corner-tr" />
              <span className="corner corner-bl" />
              <span className="corner corner-br" />
              <p>Align the white card inside this frame</p>
            </div>
            {cameraState !== "ready" && (
              <div className="camera-empty">
                <div className="camera-mark" aria-hidden="true">◎</div>
                <strong>Camera preview</strong>
                <span>Request access when you are ready to capture.</span>
              </div>
            )}
          </>
        )}
      </div>

      {message && <p className="inline-alert" role="alert">{message}</p>}

      <div className="camera-controls">
        {cameraState !== "ready" ? (
          <button className="button secondary" onClick={() => void startCamera(localStorage.getItem("career-card-camera") ?? undefined)} disabled={busy || locked}>
            {cameraState === "starting" ? "Starting camera…" : "Enable camera"}
          </button>
        ) : (
          <button className="button capture-button" onClick={() => void captureVideo()} disabled={busy || locked}>
            <span aria-hidden="true" className="shutter" />
            {busy ? "Processing…" : "Capture card"}
            <kbd>Space</kbd>
          </button>
        )}

        {devices.length > 1 && !locked && (
          <label className="camera-select">
            <span>Camera</span>
            <select value={deviceId} onChange={(event) => selectCamera(event.target.value)}>
              {devices.map((device, index) => (
                <option value={device.deviceId} key={device.deviceId}>
                  {device.label || `Camera ${index + 1}`}
                </option>
              ))}
            </select>
          </label>
        )}

        {cameraState !== "ready" && !locked && (
          <button className="text-button" onClick={() => void captureSample()} disabled={busy}>
            Try a sample card
          </button>
        )}
      </div>
    </section>
  );
}
