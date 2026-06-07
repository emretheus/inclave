import { useRef, useState } from "react";
import { ArrowUp, Paperclip, Square, X } from "lucide-react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { useChat } from "@/stores/chat";
import { useWorkspace } from "@/stores/workspace";
import { isTauri } from "@/lib/ipc";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/primitives";
import { FileIcon } from "@/components/FileIcon";

export function Composer() {
  const [text, setText] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);
  const { send, cancel, busy } = useChat();
  const { files, attachedIds, toggleAttached, addPaths } = useWorkspace();

  const attached = files.filter((f) => attachedIds.has(f.id));

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    void send(
      trimmed,
      attached.map((f) => f.id),
      attached.map((f) => f.name),
    );
    setText("");
    if (taRef.current) taRef.current.style.height = "auto";
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const pickFiles = async () => {
    if (!isTauri()) {
      await addPaths(["/mock/example.csv"]);
      return;
    }
    const selected = await openDialog({ multiple: true });
    if (!selected) return;
    const paths = Array.isArray(selected) ? selected : [selected];
    await addPaths(paths);
  };

  const autosize = () => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-6 pb-5">
      {attached.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {attached.map((f) => (
            <span
              key={f.id}
              className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-2.5 py-1 text-xs"
            >
              <FileIcon kind={f.kind} className="size-3 text-muted-foreground" />
              {f.name}
              <button
                onClick={() => toggleAttached(f.id)}
                className="text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-ring/40">
        <Button
          variant="ghost"
          size="icon"
          className="size-9 shrink-0 text-muted-foreground"
          onClick={pickFiles}
          title="Attach files (⌘O)"
        >
          <Paperclip className="size-4" />
        </Button>
        <Textarea
          ref={taRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            autosize();
          }}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Drop files or type a message…"
          className="min-h-9 flex-1 border-0 bg-transparent px-1 py-1.5 shadow-none focus-visible:ring-0"
        />
        {busy ? (
          <Button size="icon" variant="secondary" className="size-9 shrink-0" onClick={() => void cancel()}>
            <Square className="size-3.5 fill-current" />
          </Button>
        ) : (
          <Button
            size="icon"
            className="size-9 shrink-0"
            onClick={submit}
            disabled={!text.trim()}
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
      <p className="mt-1.5 text-center text-[11px] text-muted-foreground">
        Python the model writes runs automatically in a no-network sandbox.
      </p>
    </div>
  );
}
