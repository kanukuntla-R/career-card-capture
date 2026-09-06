import { describe, expect, it } from "vitest";

import { isEditableTarget, reviewShortcut } from "./shortcuts";

function keyEvent(key: string, init: KeyboardEventInit, target?: HTMLElement): KeyboardEvent {
  const event = new KeyboardEvent("keydown", { key, ...init });
  Object.defineProperty(event, "target", { value: target ?? document.body });
  return event;
}

describe("review shortcuts", () => {
  it("allows modifier approval while editing", () => {
    const textarea = document.createElement("textarea");
    expect(reviewShortcut(keyEvent("Enter", { ctrlKey: true }, textarea))).toBe("approve");
  });

  it("does not change type while typing", () => {
    const input = document.createElement("input");
    expect(reviewShortcut(keyEvent("e", { altKey: true }, input))).toBeNull();
    expect(isEditableTarget(input)).toBe(true);
  });

  it("maps classification shortcuts outside form controls", () => {
    expect(reviewShortcut(keyEvent("q", { altKey: true }))).toBe("question");
    expect(reviewShortcut(keyEvent("u", { altKey: true }))).toBe("unknown");
  });
});
