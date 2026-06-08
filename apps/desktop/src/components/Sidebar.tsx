import { useEffect } from "react";
import { MessageSquarePlus, Plus, Trash2 } from "lucide-react";
import { useChat, type TranscriptItem } from "@/stores/chat";
import { useSessions } from "@/stores/sessions";
import { useWorkspace } from "@/stores/workspace";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/primitives";
import { FileIcon } from "@/components/FileIcon";
import { cn, formatBytes, relativeTime } from "@/lib/utils";

export function Sidebar({ onAddFiles }: { onAddFiles: () => void }) {
  const { list, refresh, load, remove } = useSessions();
  const { newSession, loadTranscript, sessionId } = useChat();
  const { files, attachedIds, toggleAttached, refresh: refreshFiles } = useWorkspace();

  useEffect(() => {
    void refresh();
    void refreshFiles();
  }, [refresh, refreshFiles]);

  const openSession = async (name: string) => {
    const sess = await load(name);
    newSession();
    const items: TranscriptItem[] = sess.messages
      .filter((m) => m.role !== "system")
      .map((m, i) => ({
        kind: "message" as const,
        id: `loaded-${i}`,
        role: m.role as "user" | "assistant",
        content: m.content,
        streaming: false,
      }));
    loadTranscript(items);
  };

  return (
    <aside className="vibrancy flex w-64 shrink-0 flex-col border-r border-border">
      <div className="p-2.5">
        <Button onClick={newSession} className="w-full justify-start gap-2" variant="secondary">
          <MessageSquarePlus className="size-4" />
          New chat
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-2.5 pb-2">
          <SectionLabel>Chats</SectionLabel>
          <div className="flex flex-col gap-0.5">
            {list.map((s) => (
              <div
                key={s.name}
                className={cn(
                  "group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-muted/60",
                  sessionId === s.name && "bg-muted",
                )}
              >
                <button
                  onClick={() => void openSession(s.name)}
                  className="flex min-w-0 flex-1 flex-col items-start text-left"
                >
                  <span className="w-full truncate">{s.name === "last" ? "Recent chat" : s.name}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {s.n_turns} turns · {relativeTime(s.saved_at)}
                  </span>
                </button>
                {s.name !== "last" && (
                  <button
                    onClick={() => void remove(s.name)}
                    className="opacity-0 transition-opacity hover:text-destructive group-hover:opacity-100"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                )}
              </div>
            ))}
            {list.length === 0 && (
              <p className="px-2 py-1 text-xs text-muted-foreground">No saved chats yet</p>
            )}
          </div>
        </div>

        <div className="px-2.5 pb-2">
          <div className="flex items-center justify-between">
            <SectionLabel>Workspace</SectionLabel>
            <button
              onClick={onAddFiles}
              className="mr-1 text-muted-foreground transition-colors hover:text-foreground"
            >
              <Plus className="size-3.5" />
            </button>
          </div>
          <div className="flex flex-col gap-0.5">
            {files.map((f) => (
              <button
                key={f.id}
                onClick={() => toggleAttached(f.id)}
                className={cn(
                  "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-muted/60",
                  attachedIds.has(f.id) && "bg-primary/10",
                )}
              >
                <FileIcon
                  kind={f.kind}
                  className={cn(
                    "size-4 shrink-0",
                    attachedIds.has(f.id) ? "text-primary" : "text-muted-foreground",
                  )}
                />
                <span className="min-w-0 flex-1 truncate">{f.name}</span>
                <span className="text-[11px] text-muted-foreground">{formatBytes(f.bytes)}</span>
              </button>
            ))}
            {files.length === 0 && (
              <p className="px-2 py-1 text-xs text-muted-foreground">No files yet</p>
            )}
          </div>
        </div>
      </ScrollArea>
    </aside>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-2 pb-1 pt-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </p>
  );
}
