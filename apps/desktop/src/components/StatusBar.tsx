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
    <div className="tabular flex h-7 items-center gap-3 border-t border-border bg-surface/70 px-3 text-[11px] font-medium text-subtle-foreground backdrop-blur-xl">
      <span className="flex items-center gap-1.5">
        <span className="relative flex size-1.5">
          {running && (
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-[var(--color-success)] opacity-60" />
          )}
          <span
            className={cn(
              "relative inline-flex size-1.5 rounded-full",
              running ? "bg-[var(--color-success)]" : "bg-[var(--color-warning)]",
            )}
          />
        </span>
        Ollama {running ? "running" : "offline"}
      </span>
      <span className="text-border-strong">·</span>
      <span className="text-muted-foreground">{activeModel ?? "no model"}</span>
      <span className="text-border-strong">·</span>
      <span>
        {fileCount} file{fileCount === 1 ? "" : "s"} attached
      </span>
      {status?.sandbox_ok && (
        <>
          <span className="text-border-strong">·</span>
          <span className="text-[var(--color-success)]">sandbox ready</span>
        </>
      )}
      <div className="flex-1" />
      <button
        onClick={onPalette}
        className="flex items-center gap-1 rounded-md border border-border/60 bg-surface-2/50 px-1.5 py-0.5 font-mono text-[10px] transition-colors hover:bg-surface-3 hover:text-foreground"
      >
        <Command className="size-3" />K
      </button>
    </div>
  );
}
