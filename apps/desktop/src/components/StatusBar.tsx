import { Command } from "lucide-react";
import { useSystem } from "@/stores/system";
import { useWorkspace } from "@/stores/workspace";
import { cn } from "@/lib/utils";

export function StatusBar({ onPalette }: { onPalette: () => void }) {
  const status = useSystem((s) => s.status);
  const activeModel = useSystem((s) => s.activeModel);
  const fileCount = useWorkspace((s) => s.attachedIds.size);
  const running = status?.ollama_running ?? false;

  return (
    <div className="flex h-7 items-center gap-4 border-t border-border bg-surface/60 px-3 text-[11px] text-muted-foreground backdrop-blur">
      <span className="flex items-center gap-1.5">
        <span
          className={cn(
            "size-1.5 rounded-full",
            running ? "bg-[var(--color-success)]" : "bg-[var(--color-warning)]",
          )}
        />
        Ollama: {running ? "running" : "offline"}
      </span>
      <span className="text-border">·</span>
      <span>{activeModel ?? "no model"}</span>
      <span className="text-border">·</span>
      <span>
        {fileCount} file{fileCount === 1 ? "" : "s"} attached
      </span>
      {status?.sandbox_ok && (
        <>
          <span className="text-border">·</span>
          <span className="text-[var(--color-success)]">sandbox ready</span>
        </>
      )}
      <div className="flex-1" />
      <button
        onClick={onPalette}
        className="flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors hover:text-foreground"
      >
        <Command className="size-3" />K
      </button>
    </div>
  );
}
