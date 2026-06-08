// Typed IPC client. The frontend NEVER talks to Python directly — it calls Rust
// `#[tauri::command]` wrappers, which forward to the sidecar over stdio. Rust
// re-emits sidecar notifications as Tauri events, which we subscribe to here.
//
// Two Rust commands back this whole surface:
//   - `ipc_request(method, params)`  -> Promise<result>  (one-shot + streaming)
//   - a global `bridge://event` Tauri event carrying { method, params }
//
// When running under plain Vite (no Tauri), we fall back to a mock so the UI is
// developable in a browser.

import type { EventName, EventPayloads, Method, MethodParams } from "@inclave/ipc-contract";

type InvokeFn = <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
type ListenFn = (
  event: string,
  handler: (e: { payload: unknown }) => void,
) => Promise<() => void>;

interface TauriBridge {
  invoke: InvokeFn;
  listen: ListenFn;
}

let tauri: TauriBridge | null = null;

async function loadTauri(): Promise<TauriBridge | null> {
  if (tauri) return tauri;
  // @ts-expect-error injected by Tauri at runtime
  if (typeof window !== "undefined" && window.__TAURI_INTERNALS__) {
    const core = await import("@tauri-apps/api/core");
    const event = await import("@tauri-apps/api/event");
    tauri = {
      invoke: core.invoke as InvokeFn,
      listen: event.listen as unknown as ListenFn,
    };
    return tauri;
  }
  return null;
}

export const isTauri = (): boolean =>
  typeof window !== "undefined" &&
  // @ts-expect-error injected by Tauri at runtime
  Boolean(window.__TAURI_INTERNALS__);

/** Invoke an IPC method on the sidecar (via Rust). Returns the parsed result. */
export async function ipc<M extends Method>(
  method: M,
  params: MethodParams[M],
): Promise<unknown> {
  const t = await loadTauri();
  if (!t) {
    return mockInvoke(method, params);
  }
  return t.invoke("ipc_request", { method, params });
}

// Notification bus -------------------------------------------------------- //

type EventHandler<E extends EventName> = (payload: EventPayloads[E]) => void;

const handlers = new Map<EventName, Set<(p: unknown) => void>>();
let busStarted = false;

async function ensureBus(): Promise<void> {
  if (busStarted) return;
  busStarted = true;
  const t = await loadTauri();
  if (!t) return; // mock mode dispatches directly via mockEmit
  await t.listen("bridge://event", (e) => {
    const frame = e.payload as { method: EventName; params: unknown };
    dispatch(frame.method, frame.params);
  });
}

function dispatch(method: EventName, params: unknown): void {
  const set = handlers.get(method);
  if (!set) return;
  for (const h of set) h(params);
}

/** Subscribe to a streamed event. Returns an unsubscribe fn. */
export function onEvent<E extends EventName>(event: E, handler: EventHandler<E>): () => void {
  void ensureBus();
  let set = handlers.get(event);
  if (!set) {
    set = new Set();
    handlers.set(event, set);
  }
  const wrapped = handler as (p: unknown) => void;
  set.add(wrapped);
  return () => set?.delete(wrapped);
}

// Mock mode (browser dev without Tauri) ----------------------------------- //

export function mockEmit<E extends EventName>(event: E, payload: EventPayloads[E]): void {
  dispatch(event, payload);
}

async function mockInvoke(method: Method, params: unknown): Promise<unknown> {
  const { runMock } = await import("./mock");
  return runMock(method, params);
}
