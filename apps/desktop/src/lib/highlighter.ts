// A single shiki highlighter restricted to the languages InClave actually
// renders. Importing only these grammars keeps the bundle small (the full shiki
// language set is ~megabytes) and — like everything else — stays offline.

import { createHighlighterCore } from "shiki/core";
import { createOnigurumaEngine } from "shiki/engine/oniguruma";

import githubDark from "shiki/themes/github-dark.mjs";
import githubLight from "shiki/themes/github-light.mjs";

import python from "shiki/langs/python.mjs";
import javascript from "shiki/langs/javascript.mjs";
import typescript from "shiki/langs/typescript.mjs";
import json from "shiki/langs/json.mjs";
import bash from "shiki/langs/bash.mjs";
import sql from "shiki/langs/sql.mjs";
import yaml from "shiki/langs/yaml.mjs";
import markdown from "shiki/langs/markdown.mjs";

export type SupportedLang =
  | "python"
  | "javascript"
  | "typescript"
  | "json"
  | "bash"
  | "sql"
  | "yaml"
  | "markdown"
  | "text";

const ALIASES: Record<string, SupportedLang> = {
  py: "python",
  py3: "python",
  python3: "python",
  js: "javascript",
  ts: "typescript",
  jsx: "javascript",
  tsx: "typescript",
  sh: "bash",
  shell: "bash",
  yml: "yaml",
  md: "markdown",
};

const KNOWN = new Set<SupportedLang>([
  "python",
  "javascript",
  "typescript",
  "json",
  "bash",
  "sql",
  "yaml",
  "markdown",
]);

export function normalizeLang(lang: string): SupportedLang {
  const lower = lang.toLowerCase();
  if (KNOWN.has(lower as SupportedLang)) return lower as SupportedLang;
  return ALIASES[lower] ?? "text";
}

let highlighterPromise: ReturnType<typeof createHighlighterCore> | null = null;

export function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = createHighlighterCore({
      themes: [githubDark, githubLight],
      langs: [python, javascript, typescript, json, bash, sql, yaml, markdown],
      engine: createOnigurumaEngine(import("shiki/wasm")),
    });
  }
  return highlighterPromise;
}
