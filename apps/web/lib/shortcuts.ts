export type ShortcutAction = "approve" | "employer" | "question" | "unknown" | null;

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    target.tagName === "INPUT" ||
    target.tagName === "TEXTAREA" ||
    target.tagName === "SELECT"
  );
}

export function reviewShortcut(event: KeyboardEvent): ShortcutAction {
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && key === "enter") return "approve";
  if (isEditableTarget(event.target)) return null;
  if (!event.altKey) return null;
  if (key === "e") return "employer";
  if (key === "q") return "question";
  if (key === "u") return "unknown";
  return null;
}
