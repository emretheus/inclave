import { useEffect, useState } from "react";
import { isTauri } from "@/lib/ipc";
import { useWorkspace } from "@/stores/workspace";

// Native Tauri file-drop gives us real filesystem paths (richer than the CLI's
// drop detection). When dropped, files are added to the workspace + attached.
export function useFileDrop() {
  const [dragging, setDragging] = useState(false);
  const addPaths = useWorkspace((s) => s.addPaths);

  useEffect(() => {
    if (!isTauri()) {
      // Browser dev: accept HTML5 drops for layout testing (no real paths).
      const over = (e: DragEvent) => {
        e.preventDefault();
        setDragging(true);
      };
      const leave = () => setDragging(false);
      const drop = (e: DragEvent) => {
        e.preventDefault();
        setDragging(false);
      };
      window.addEventListener("dragover", over);
      window.addEventListener("dragleave", leave);
      window.addEventListener("drop", drop);
      return () => {
        window.removeEventListener("dragover", over);
        window.removeEventListener("dragleave", leave);
        window.removeEventListener("drop", drop);
      };
    }

    let unlisten: (() => void) | undefined;
    void (async () => {
      const { getCurrentWebview } = await import("@tauri-apps/api/webview");
      unlisten = await getCurrentWebview().onDragDropEvent((event) => {
        if (event.payload.type === "over") setDragging(true);
        else if (event.payload.type === "drop") {
          setDragging(false);
          void addPaths(event.payload.paths);
        } else setDragging(false);
      });
    })();

    return () => unlisten?.();
  }, [addPaths]);

  return { dragging };
}
