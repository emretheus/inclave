import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

// The engine embeds attached files into the user prompt as
//   <<<FILE id=… name=… kind=…>>> … <<<END FILE>>>
// blocks, separated from the question by a "---" rule. That's what the model
// needs to see, but the UI should show only the user's actual question (file
// chips carry the attachment info). This strips the blocks for display and
// returns the clean question text + the embedded file names it found.
const FILE_BLOCK_RE = /<<<FILE[^>]*>>>[\s\S]*?<<<END FILE>>>/g;
const FILE_NAME_RE = /<<<FILE[^>]*\bname=([^\s>]+)/g;

export function cleanUserText(content: string): { text: string; fileNames: string[] } {
  if (!content.includes("<<<FILE")) return { text: content, fileNames: [] };
  const fileNames: string[] = [];
  let m: RegExpExecArray | null;
  FILE_NAME_RE.lastIndex = 0;
  while ((m = FILE_NAME_RE.exec(content)) !== null) fileNames.push(m[1]);
  const text = content
    .replace(FILE_BLOCK_RE, "")
    .replace(/^\s*-{3,}\s*/m, "") // drop the leading "---" separator
    .trim();
  return { text, fileNames };
}

export function relativeTime(iso: string): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}
