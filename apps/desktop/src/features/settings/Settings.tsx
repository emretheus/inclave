import { useEffect, useState } from "react";
import { Check, Download, MemoryStick, Trash2 } from "lucide-react";
import type { InClaveConfig } from "@inclave/ipc-contract";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge, Input, Progress, Separator } from "@/components/ui/primitives";
import { useModels } from "@/stores/models";
import { useSystem } from "@/stores/system";
import { ipc } from "@/lib/ipc";
import { formatBytes } from "@/lib/utils";

const RECOMMENDED = [
  { name: "llama3.2", note: "fast, great default" },
  { name: "llama3.1:8b", note: "better reasoning" },
  { name: "qwen2.5-coder:7b", note: "coding-tuned" },
];

export function Settings({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-6">
          <ModelsSection />
          <Separator />
          <SandboxSection />
          <Separator />
          <PrivacyNote />
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ModelsSection() {
  const { list, pulling, refresh, setDefault, remove, pull, watch } = useModels();
  const { activeModel, setActiveModel } = useSystem();
  const [pullName, setPullName] = useState("");

  useEffect(() => {
    watch();
    void refresh();
  }, [watch, refresh]);

  const installed = new Set(list.map((m) => m.name.split(":")[0]));

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">Models</h3>
      <div className="flex flex-col gap-1.5">
        {list.map((m) => (
          <div
            key={m.name}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2"
          >
            <div className="flex min-w-0 flex-1 flex-col">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm font-medium">{m.name}</span>
                {m.vram_ok === true && <Badge variant="success">fits in memory</Badge>}
                {m.vram_ok === false && (
                  <Badge variant="warning">
                    <MemoryStick className="mr-1 size-2.5" /> will swap
                  </Badge>
                )}
              </div>
              <span className="text-[11px] text-muted-foreground">
                {formatBytes(m.size_bytes)} · {m.parameter_count}
              </span>
            </div>
            {activeModel === m.name ? (
              <Badge>
                <Check className="mr-1 size-3" /> active
              </Badge>
            ) : (
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setActiveModel(m.name);
                  void setDefault(m.name);
                }}
              >
                Use
              </Button>
            )}
            <Button
              size="icon"
              variant="ghost"
              className="size-7 text-muted-foreground hover:text-destructive"
              onClick={() => void remove(m.name)}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        ))}
      </div>

      {pulling && (
        <div className="mt-3 rounded-lg border border-border bg-surface px-3 py-2">
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span>
              Pulling <span className="font-medium">{pulling.name}</span> — {pulling.status}
            </span>
            <span className="text-muted-foreground">{pulling.pct}%</span>
          </div>
          <Progress value={pulling.pct} />
        </div>
      )}

      <div className="mt-3">
        <p className="mb-1.5 text-xs text-muted-foreground">Pull a recommended model</p>
        <div className="flex flex-wrap gap-1.5">
          {RECOMMENDED.filter((r) => !installed.has(r.name.split(":")[0])).map((r) => (
            <Button
              key={r.name}
              size="sm"
              variant="outline"
              className="gap-1.5"
              disabled={Boolean(pulling)}
              onClick={() => void pull(r.name)}
            >
              <Download className="size-3.5" />
              {r.name}
              <span className="text-[11px] text-muted-foreground">{r.note}</span>
            </Button>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <Input
            value={pullName}
            onChange={(e) => setPullName(e.target.value)}
            placeholder="or pull by name, e.g. mistral"
            className="h-8 text-xs"
          />
          <Button
            size="sm"
            disabled={!pullName.trim() || Boolean(pulling)}
            onClick={() => {
              void pull(pullName.trim());
              setPullName("");
            }}
          >
            Pull
          </Button>
        </div>
      </div>
    </section>
  );
}

function SandboxSection() {
  const [cfg, setCfg] = useState<InClaveConfig | null>(null);

  useEffect(() => {
    void ipc("config.get", {}).then((c) => setCfg(c as InClaveConfig));
  }, []);

  const update = async (key: string, value: string) => {
    const next = (await ipc("config.set", { key, value })) as InClaveConfig;
    setCfg(next);
  };

  if (!cfg) return null;

  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold">Sandbox limits</h3>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">CPU seconds</span>
          <Input
            type="number"
            defaultValue={cfg.sandbox_cpu_seconds}
            onBlur={(e) => void update("sandbox_cpu_seconds", e.target.value)}
            className="h-8"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="text-muted-foreground">Memory (MB)</span>
          <Input
            type="number"
            defaultValue={cfg.sandbox_memory_mb}
            onBlur={(e) => void update("sandbox_memory_mb", e.target.value)}
            className="h-8"
          />
        </label>
      </div>
    </section>
  );
}

function PrivacyNote() {
  return (
    <section className="rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
      <p className="font-medium text-foreground">Your data stays on this Mac.</p>
      <p className="mt-1">
        InClave talks only to your local Ollama daemon (127.0.0.1). Model-written Python runs in a
        Seatbelt sandbox with no network access. No telemetry, no cloud, no API keys.
      </p>
    </section>
  );
}
