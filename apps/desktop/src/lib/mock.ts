// In-browser mock of the bridge so the UI runs under plain Vite (no Tauri).
// Simulates the same JSON-RPC results + streamed events the real sidecar emits.

import type { Method } from "@inclave/ipc-contract";
import { mockEmit } from "./ipc";

const files = [
  {
    id: "a1b2c3d4",
    name: "mrr_2026.csv",
    original_path: "~/Downloads/mrr_2026.csv",
    sha256: "a1b2c3d4ef",
    bytes: 2048,
    added_at: new Date().toISOString(),
    kind: "csv",
  },
  {
    id: "e5f6a7b8",
    name: "q1_review.pdf",
    original_path: "~/Downloads/q1_review.pdf",
    sha256: "e5f6a7b8cd",
    bytes: 184320,
    added_at: new Date().toISOString(),
    kind: "pdf",
  },
];

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function simulateChat(sessionId: string, text: string): Promise<unknown> {
  const reply = `Looking at your question — "${text.slice(0, 40)}" — here's the plan:\n\n` +
    "```python\nimport pandas as pd\ndf = pd.read_csv(\"mrr_2026.csv\")\n" +
    'growth = (df["mrr_usd"].iloc[-1] - df["mrr_usd"].iloc[0]) / df["mrr_usd"].iloc[0] * 100\n' +
    'print(f"Total MRR growth: {growth:.2f}%")\n```\n';
  for (const word of reply.match(/\S+\s*/g) ?? []) {
    mockEmit("chat.token", { session_id: sessionId, delta: word });
    await sleep(18);
  }
  mockEmit("chat.message_done", { session_id: sessionId, role: "assistant", content: reply });
  await sleep(150);
  mockEmit("chat.run_start", { session_id: sessionId, code: "import pandas as pd ..." });
  await sleep(700);
  mockEmit("chat.run_output", {
    session_id: sessionId,
    stdout: "Total MRR growth: 96.06%\n",
    stderr: "",
    exit_code: 0,
    duration_ms: 1180,
    timed_out: false,
  });
  await sleep(200);
  const summary = "MRR_USD grew by approximately **96%** from September to April.";
  for (const word of summary.match(/\S+\s*/g) ?? []) {
    mockEmit("chat.token", { session_id: sessionId, delta: word });
    await sleep(20);
  }
  mockEmit("chat.message_done", { session_id: sessionId, role: "assistant", content: summary });
  mockEmit("chat.turn_done", { session_id: sessionId, n_turns: 2 });
  return { ok: true, n_turns: 2 };
}

export async function runMock(method: Method, params: unknown): Promise<unknown> {
  const p = (params ?? {}) as Record<string, unknown>;
  switch (method) {
    case "system.status":
      return { ollama_running: true, default_model: "qwen2.5-coder:7b", ram_gb: 16, sandbox_ok: true };
    case "config.get":
      return { default_model: "qwen2.5-coder:7b", sandbox_cpu_seconds: 30, sandbox_memory_mb: 512, auto_run: false };
    case "config.set":
      return { default_model: "qwen2.5-coder:7b", sandbox_cpu_seconds: 30, sandbox_memory_mb: 512, auto_run: false };
    case "models.list":
      return [
        { name: "qwen2.5-coder:7b", size_bytes: 4_400_000_000, family: "qwen2", parameter_count: "7B", is_default: true, vram_ok: true },
        { name: "llama3.2", size_bytes: 2_000_000_000, family: "llama", parameter_count: "3B", is_default: false, vram_ok: true },
        { name: "llama3.1:70b", size_bytes: 40_000_000_000, family: "llama", parameter_count: "70B", is_default: false, vram_ok: false },
      ];
    case "files.list":
      return files;
    case "files.add":
      return files.slice(0, 1);
    case "files.remove":
      return files[0];
    case "files.clear":
      return { removed: files.length };
    case "sessions.list":
      return [
        { name: "last", saved_at: new Date(Date.now() - 120000).toISOString(), model: "qwen2.5-coder:7b", n_turns: 2 },
        { name: "q1-review", saved_at: new Date(Date.now() - 86400000).toISOString(), model: "llama3.2", n_turns: 5 },
      ];
    case "sessions.load":
      return { model: "qwen2.5-coder:7b", workdir: "", file_ids: [], messages: [], saved_at: new Date().toISOString() };
    case "sessions.save":
      return { saved: true, path: "/tmp/x.json" };
    case "sessions.delete":
      return { deleted: true };
    case "ollama.ensure_running":
      return { running: true, already: true };
    case "chat.send":
      return simulateChat(String(p.session_id ?? "mock"), String(p.text ?? ""));
    case "chat.run_last":
      return { ok: true };
    case "chat.cancel":
      return { ok: true };
    default:
      return {};
  }
}
