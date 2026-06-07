import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Paperclip } from "lucide-react";
import { useChat } from "@/stores/chat";
import { Markdown } from "@/components/Markdown";
import { SandboxCard } from "@/components/SandboxCard";
import { Logo } from "@/components/Logo";
import { cn } from "@/lib/utils";

export function Transcript() {
  const items = useChat((s) => s.items);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [items]);

  if (items.length === 0) return <EmptyState />;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-1 px-6 py-6">
      {items.map((item) =>
        item.kind === "run" ? (
          <div key={item.id} className="pl-1">
            <SandboxCard card={item.card} />
          </div>
        ) : (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
              "group flex flex-col gap-1.5 py-2",
              item.role === "user" ? "items-end" : "items-start",
            )}
          >
            {item.role === "user" ? (
              <div className="flex max-w-[85%] flex-col items-end gap-1.5">
                {item.fileNames && item.fileNames.length > 0 && (
                  <div className="flex flex-wrap justify-end gap-1">
                    {item.fileNames.map((n) => (
                      <span
                        key={n}
                        className="flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[11px] text-muted-foreground"
                      >
                        <Paperclip className="size-2.5" />
                        {n}
                      </span>
                    ))}
                  </div>
                )}
                <div className="rounded-2xl rounded-br-md bg-primary px-3.5 py-2 text-sm text-primary-foreground">
                  {item.content}
                </div>
              </div>
            ) : (
              <div className="flex w-full max-w-full gap-2.5">
                <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
                  <Logo className="size-3.5" />
                </div>
                <div className={cn("min-w-0 flex-1", item.streaming && "streaming-caret")}>
                  <Markdown content={item.content} />
                </div>
              </div>
            )}
          </motion.div>
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function EmptyState() {
  const examples = [
    "Summarize the key points from q1_review.pdf",
    "What's the total MRR growth in mrr_2026.csv?",
    "Plot revenue by month and describe the trend",
  ];
  const send = useChat((s) => s.send);
  return (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <Logo variant="badge" className="mb-4 size-16 rounded-2xl shadow-sm" />
      <h2 className="text-lg font-semibold">Ask anything about your files</h2>
      <p className="mt-1 max-w-sm text-sm text-muted-foreground">
        Drop a PDF, spreadsheet, or code file and ask away. Everything runs locally — your data
        never leaves this Mac.
      </p>
      <div className="mt-6 flex flex-col gap-2">
        {examples.map((ex) => (
          <button
            key={ex}
            onClick={() => send(ex, [], [])}
            className="rounded-lg border border-border bg-surface px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
