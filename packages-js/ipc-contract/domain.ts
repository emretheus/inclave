// Rich domain types mirroring the engine dataclasses. Hand-written (these are
// the shapes returned inside the flat `object`/`object[]` results), kept beside
// the generated method/event catalog in index.ts.

import { z } from "zod";

export const FileEntrySchema = z.object({
  id: z.string(),
  name: z.string(),
  original_path: z.string(),
  sha256: z.string(),
  bytes: z.number(),
  added_at: z.string(),
  kind: z.enum(["text", "csv", "xlsx", "pdf", "code", "other"]),
});
export type FileEntry = z.infer<typeof FileEntrySchema>;

export const ConfigSchema = z.object({
  default_model: z.string().nullable(),
  sandbox_cpu_seconds: z.number(),
  sandbox_memory_mb: z.number(),
  auto_run: z.boolean(),
});
export type InClaveConfig = z.infer<typeof ConfigSchema>;

export const ModelInfoSchema = z.object({
  name: z.string(),
  size_bytes: z.number(),
  family: z.string(),
  parameter_count: z.string(),
  is_default: z.boolean(),
  vram_ok: z.boolean().nullable(),
});
export type ModelInfo = z.infer<typeof ModelInfoSchema>;

export const SystemStatusSchema = z.object({
  ollama_running: z.boolean(),
  default_model: z.string().nullable(),
  ram_gb: z.number().nullable(),
  sandbox_ok: z.boolean(),
});
export type SystemStatus = z.infer<typeof SystemStatusSchema>;

export const ChatMessageSchema = z.object({
  role: z.enum(["system", "user", "assistant"]),
  content: z.string(),
});
export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const SessionSchema = z.object({
  version: z.number().optional(),
  model: z.string(),
  workdir: z.string(),
  file_ids: z.array(z.string()),
  messages: z.array(ChatMessageSchema),
  saved_at: z.string().optional(),
});
export type Session = z.infer<typeof SessionSchema>;

export const SessionSummarySchema = z.object({
  name: z.string(),
  saved_at: z.string(),
  model: z.string(),
  n_turns: z.number(),
});
export type SessionSummary = z.infer<typeof SessionSummarySchema>;

// Event payload schemas (runtime-validated as notifications arrive).
export const ChatTokenSchema = z.object({ session_id: z.string(), delta: z.string() });
export const ChatMessageDoneSchema = z.object({
  session_id: z.string(),
  role: z.string(),
  content: z.string(),
});
export const ChatRunStartSchema = z.object({ session_id: z.string(), code: z.string() });
export const ChatRunOutputSchema = z.object({
  session_id: z.string(),
  stdout: z.string(),
  stderr: z.string(),
  exit_code: z.number(),
  duration_ms: z.number(),
  timed_out: z.boolean(),
});
export const ChatTurnDoneSchema = z.object({ session_id: z.string(), n_turns: z.number() });
export const ChatErrorSchema = z.object({
  session_id: z.string(),
  code: z.string(),
  message: z.string(),
});
export const ModelsPullProgressSchema = z.object({
  name: z.string(),
  status: z.string(),
  completed: z.number(),
  total: z.number(),
});
export const OllamaStateSchema = z.object({ running: z.boolean() });
