/// <reference types="node" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

// Tauri expects a fixed port and no clearing of the screen so its logs survive.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: "127.0.0.1",
    watch: {
      // Don't watch the Rust side — it has its own watcher.
      ignored: ["**/src-tauri/**"],
    },
  },
  // Produce a build Tauri can bundle.
  build: {
    target: "safari15",
    outDir: "dist",
    emptyOutDir: true,
  },
});
