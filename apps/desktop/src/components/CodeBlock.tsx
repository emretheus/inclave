import { useEffect, useState } from "react";
import { Check, Copy, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getHighlighter, normalizeLang } from "@/lib/highlighter";
import { cn } from "@/lib/utils";

// Offline syntax highlighting via shiki. Grammars/themes are bundled with the
// app — no network fetch, keeping the privacy guarantee intact.
export function CodeBlock({
  code,
  lang = "python",
  onRun,
  running,
}: {
  code: string;
  lang?: string;
  onRun?: () => void;
  running?: boolean;
}) {
  const [html, setHtml] = useState<string>("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const normalized = normalizeLang(lang);
    getHighlighter()
      .then((hl) =>
        hl.codeToHtml(code, {
          lang: normalized === "text" ? "python" : normalized,
          themes: { light: "github-light", dark: "github-dark" },
          defaultColor: false,
        }),
      )
      .then((out) => !cancelled && setHtml(out))
      .catch(() => !cancelled && setHtml(`<pre>${escapeHtml(code)}</pre>`));
    return () => {
      cancelled = true;
    };
  }, [code, lang]);

  const copy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-border bg-surface-2">
      <div className="flex items-center justify-between border-b border-border px-3 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
          {lang}
        </span>
        <div className="flex items-center gap-1">
          {onRun && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 gap-1 px-2 text-xs"
              onClick={onRun}
              disabled={running}
            >
              <Play className="size-3" />
              {running ? "running…" : "Run"}
            </Button>
          )}
          <Button variant="ghost" size="sm" className="h-6 gap-1 px-2 text-xs" onClick={copy}>
            {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      </div>
      <div
        className={cn(
          "shiki-host overflow-x-auto p-3 text-[13px] leading-relaxed [&_pre]:!bg-transparent [&_code]:font-mono",
          running && "animate-pulse",
        )}
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c] ?? c);
}
