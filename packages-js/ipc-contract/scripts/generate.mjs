// Generate index.ts from schema.json (exported by the Python bridge).
//
//   node scripts/generate.mjs
//
// The output is a typed catalog of IPC methods + events. Rich object shapes
// (FileEntry, ModelInfo, Session, …) are declared in domain.ts by hand because
// they mirror the engine dataclasses, not the flat param/event maps.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const schema = JSON.parse(readFileSync(resolve(root, "schema.json"), "utf8"));

const banner = `// AUTO-GENERATED from schema.json by scripts/generate.mjs. DO NOT EDIT.
// Regenerate with:  pnpm gen:ipc  (after  uv run python packages/bridge/scripts/export_schema.py)
/* eslint-disable */
`;

const methodNames = schema.methods.map((m) => m.name);
const eventNames = schema.events.map((e) => e.name);

const jsType = (t) => {
  switch (t) {
    case "string":
      return "string";
    case "string[]":
      return "string[]";
    case "int":
      return "number";
    case "bool":
      return "boolean";
    case "object":
      return "Record<string, unknown>";
    case "object[]":
      return "Record<string, unknown>[]";
    case "null":
      return "null";
    default:
      return "unknown";
  }
};

const paramsType = (params) => {
  const entries = Object.entries(params);
  if (entries.length === 0) return "Record<string, never>";
  return `{ ${entries.map(([k, v]) => `${k}: ${jsType(v)}`).join("; ")} }`;
};

const payloadType = (payload) => {
  const entries = Object.entries(payload);
  return `{ ${entries.map(([k, v]) => `${k}: ${jsType(v)}`).join("; ")} }`;
};

let out = banner + "\n";

// Method-name union + params map.
out += `export const METHODS = ${JSON.stringify(methodNames, null, 2)} as const;\n`;
out += `export type Method = (typeof METHODS)[number];\n\n`;

out += `export interface MethodParams {\n`;
for (const m of schema.methods) {
  out += `  ${JSON.stringify(m.name)}: ${paramsType(m.params)};\n`;
}
out += `}\n\n`;

// Streaming method flags.
const streaming = schema.methods.filter((m) => m.streams).map((m) => m.name);
out += `export const STREAMING_METHODS = ${JSON.stringify(streaming, null, 2)} as const;\n\n`;

// Event-name union + payload map.
out += `export const EVENTS = ${JSON.stringify(eventNames, null, 2)} as const;\n`;
out += `export type EventName = (typeof EVENTS)[number];\n\n`;

out += `export interface EventPayloads {\n`;
for (const e of schema.events) {
  out += `  ${JSON.stringify(e.name)}: ${payloadType(e.payload)};\n`;
}
out += `}\n\n`;

// Error codes.
out += `export const ERROR_CODES = ${JSON.stringify(schema.errorCodes, null, 2)} as const;\n`;
out += `export const DOMAIN_ERROR_CODES = ${JSON.stringify(
  schema.domainErrorCodes,
  null,
  2,
)} as const;\n`;
out += `export type DomainErrorCode = (typeof DOMAIN_ERROR_CODES)[number];\n\n`;

out += `export * from "./domain";\n`;

writeFileSync(resolve(root, "index.ts"), out);
console.log("wrote index.ts");
