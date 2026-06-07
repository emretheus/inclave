import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Check, Download, MemoryStick, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { Badge, Progress } from "@/components/ui/primitives";
import { useModels } from "@/stores/models";
import { useSystem } from "@/stores/system";

const RECOMMENDED = [
  { name: "llama3.2", size: "2.0 GB", note: "fast, great default" },
  { name: "llama3.1:8b", size: "4.7 GB", note: "better reasoning" },
  { name: "qwen2.5-coder:7b", size: "4.4 GB", note: "coding-tuned" },
];

// First-run flow. Mirrors the CLI's onboarding.py: welcome → Ollama → model → go.
export function Onboarding({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  const { status, refresh, ensureOllama } = useSystem();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="vibrancy flex h-full flex-col items-center justify-center px-8">
      <motion.div
        key={step}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        {step === 0 && (
          <div className="text-center">
            <Logo variant="badge" className="mx-auto mb-5 size-20 rounded-[1.25rem] shadow-md" />
            <h1 className="text-2xl font-semibold tracking-tight">Welcome to InClave</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              A local AI that reads your files and runs code — entirely on your Mac. No cloud, no
              telemetry, no API keys.
            </p>
            <div className="mt-5 flex items-center justify-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4 text-[var(--color-success)]" />
              Everything stays on 127.0.0.1
            </div>
            <Button className="mt-6 w-full" onClick={() => setStep(1)}>
              Get started
            </Button>
          </div>
        )}

        {step === 1 && (
          <div>
            <h2 className="text-xl font-semibold">Local engine</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              InClave runs models through Ollama on your machine.
            </p>
            <div className="mt-4 rounded-lg border border-border bg-surface p-4">
              <div className="flex items-center gap-2">
                <span
                  className={`size-2 rounded-full ${
                    status?.ollama_running ? "bg-[var(--color-success)]" : "bg-[var(--color-warning)]"
                  }`}
                />
                <span className="text-sm">
                  Ollama is {status?.ollama_running ? "running" : "not running"}
                </span>
              </div>
              {!status?.ollama_running && (
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-3"
                  onClick={() => void ensureOllama()}
                >
                  Start Ollama
                </Button>
              )}
              {status?.ram_gb && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Detected {status.ram_gb} GB unified memory
                </p>
              )}
            </div>
            <Button className="mt-6 w-full" disabled={!status?.ollama_running} onClick={() => setStep(2)}>
              Continue
            </Button>
          </div>
        )}

        {step === 2 && <PickModel ramGb={status?.ram_gb ?? null} onDone={onDone} />}
      </motion.div>
    </div>
  );
}

function PickModel({ ramGb, onDone }: { ramGb: number | null; onDone: () => void }) {
  const { pulling, pull, watch, setDefault } = useModels();
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    watch();
  }, [watch]);

  const fits = (sizeGb: number) => (ramGb ? ramGb * 0.7 >= sizeGb + 2 : true);

  const choose = async (name: string) => {
    await pull(name);
    await setDefault(name);
    setDone(name);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold">Pick a model</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        We'll download it once. You can add more later in Settings.
      </p>
      <div className="mt-4 flex flex-col gap-2">
        {RECOMMENDED.map((m) => {
          const sizeGb = parseFloat(m.size);
          const ok = fits(sizeGb);
          return (
            <button
              key={m.name}
              disabled={Boolean(pulling)}
              onClick={() => void choose(m.name)}
              className="flex items-center gap-3 rounded-lg border border-border bg-surface px-4 py-3 text-left transition-colors hover:border-primary/40 disabled:opacity-60"
            >
              <Download className="size-4 text-muted-foreground" />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{m.name}</span>
                  {ok ? (
                    <Badge variant="success">fits in memory</Badge>
                  ) : (
                    <Badge variant="warning">
                      <MemoryStick className="mr-1 size-2.5" /> will swap
                    </Badge>
                  )}
                </div>
                <span className="text-xs text-muted-foreground">
                  {m.size} · {m.note}
                </span>
              </div>
              {done === m.name && <Check className="size-4 text-[var(--color-success)]" />}
            </button>
          );
        })}
      </div>

      {pulling && (
        <div className="mt-4">
          <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
            <span>{pulling.status}</span>
            <span>{pulling.pct}%</span>
          </div>
          <Progress value={pulling.pct} />
        </div>
      )}

      <Button className="mt-6 w-full" disabled={!done} onClick={onDone}>
        Start using InClave
      </Button>
    </div>
  );
}
