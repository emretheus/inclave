import { useState } from "react";
import { motion } from "framer-motion";
import { ChevronDown, Loader2, ShieldCheck, Terminal } from "lucide-react";
import type { RunCard } from "@/stores/chat";
import { Badge } from "@/components/ui/primitives";
import { cn, formatDuration } from "@/lib/utils";

// The sandbox output card — the desktop reimagining of the CLI's ╭ stdout ╮ panel.
export function SandboxCard({ card }: { card: RunCard }) {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState<"stdout" | "stderr">("stdout");
  const running = card.status === "running";
  const failed = !running && (card.exitCode !== 0 || card.timedOut);

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="my-2 overflow-hidden rounded-lg border border-border bg-surface-2"
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        {running ? (
          <Loader2 className="size-3.5 animate-spin text-primary" />
        ) : (
          <ShieldCheck className="size-3.5 text-[var(--color-success)]" />
        )}
        <span className="flex items-center gap-1.5 text-xs font-medium">
          <Terminal className="size-3.5 text-muted-foreground" />
          Sandbox
        </span>
        <div className="flex-1" />
        {running ? (
          <Badge variant="secondary">running…</Badge>
        ) : card.timedOut ? (
          <Badge variant="warning">timed out</Badge>
        ) : (
          <Badge variant={failed ? "destructive" : "success"}>exit {card.exitCode}</Badge>
        )}
        {!running && (
          <span className="text-[11px] text-muted-foreground">{formatDuration(card.durationMs)}</span>
        )}
        <ChevronDown
          className={cn("size-4 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>

      {open && !running && (
        <div className="border-t border-border">
          {card.stderr && (
            <div className="flex gap-1 px-3 pt-2">
              {(["stdout", "stderr"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "rounded-md px-2 py-0.5 font-mono text-[11px] transition-colors",
                    tab === t ? "bg-muted text-foreground" : "text-muted-foreground",
                  )}
                >
                  {t}
                  {t === "stderr" && <span className="ml-1 text-destructive">●</span>}
                </button>
              ))}
            </div>
          )}
          <pre className="max-h-72 overflow-auto px-3 py-2 font-mono text-[12px] leading-relaxed">
            {(tab === "stderr" ? card.stderr : card.stdout) || (
              <span className="text-muted-foreground italic">no output</span>
            )}
          </pre>
        </div>
      )}
    </motion.div>
  );
}
