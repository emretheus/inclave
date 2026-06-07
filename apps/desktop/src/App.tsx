import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { UploadCloud } from "lucide-react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { Toaster } from "sonner";
import { Titlebar } from "@/components/Titlebar";
import { Sidebar } from "@/components/Sidebar";
import { StatusBar } from "@/components/StatusBar";
import { Transcript } from "@/features/chat/Transcript";
import { Composer } from "@/features/chat/Composer";
import { Settings } from "@/features/settings/Settings";
import { Onboarding } from "@/features/onboarding/Onboarding";
import { CommandPalette } from "@/features/palette/CommandPalette";
import { ScrollArea, TooltipProvider } from "@/components/ui/primitives";
import { useSystem } from "@/stores/system";
import { useModels } from "@/stores/models";
import { useChat } from "@/stores/chat";
import { useWorkspace } from "@/stores/workspace";
import { useFileDrop } from "@/hooks/useFileDrop";
import { isTauri } from "@/lib/ipc";

const ONBOARDED_KEY = "inclave.onboarded";

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [onboarded, setOnboarded] = useState(() => {
    // ?onboarded=1 forces past the first-run flow (handy for dev/screenshots).
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search).get("onboarded");
      if (p === "1") return true;
      if (p === "0") return false;
    }
    return localStorage.getItem(ONBOARDED_KEY) === "1";
  });

  const { refresh: refreshSystem, watch: watchSystem } = useSystem();
  const watchModels = useModels((s) => s.watch);
  const { newSession, runLast } = useChat();
  const addPaths = useWorkspace((s) => s.addPaths);
  const { dragging } = useFileDrop();

  useEffect(() => {
    watchSystem();
    watchModels();
    void refreshSystem();
  }, [refreshSystem, watchSystem, watchModels]);

  const pickFiles = useCallback(async () => {
    if (!isTauri()) {
      await addPaths(["/mock/example.csv"]);
      return;
    }
    const selected = await openDialog({ multiple: true });
    if (!selected) return;
    const paths = Array.isArray(selected) ? selected : [selected];
    await addPaths(paths);
  }, [addPaths]);

  // Global keyboard shortcuts (mirror the native menu accelerators).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      } else if (mod && e.key === "n") {
        e.preventDefault();
        newSession();
      } else if (mod && e.key === "o") {
        e.preventDefault();
        void pickFiles();
      } else if (mod && e.key === ",") {
        e.preventDefault();
        setSettingsOpen(true);
      } else if (mod && e.key === "Enter") {
        e.preventDefault();
        void runLast();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [newSession, pickFiles, runLast]);

  const finishOnboarding = () => {
    localStorage.setItem(ONBOARDED_KEY, "1");
    setOnboarded(true);
  };

  if (!onboarded) {
    return (
      <TooltipProvider delayDuration={300}>
        <div className="flex h-full flex-col">
          <div className="titlebar-drag h-11 shrink-0" />
          <Onboarding onDone={finishOnboarding} />
        </div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider delayDuration={300}>
      <div className="relative flex h-full flex-col overflow-hidden">
        <Titlebar onOpenSettings={() => setSettingsOpen(true)} />
        <div className="flex min-h-0 flex-1">
          <Sidebar onAddFiles={() => void pickFiles()} />
          <main className="flex min-w-0 flex-1 flex-col bg-background">
            <ScrollArea className="flex-1">
              <Transcript />
            </ScrollArea>
            <Composer />
          </main>
        </div>
        <StatusBar onPalette={() => setPaletteOpen(true)} />

        <AnimatePresence>
          {dragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="pointer-events-none absolute inset-0 z-40 flex items-center justify-center bg-primary/10 backdrop-blur-sm"
            >
              <div className="flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed border-primary bg-surface/90 px-10 py-8">
                <UploadCloud className="size-10 text-primary" />
                <p className="text-sm font-medium">Drop files to add them to your workspace</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <Settings open={settingsOpen} onOpenChange={setSettingsOpen} />
        <CommandPalette
          open={paletteOpen}
          onOpenChange={setPaletteOpen}
          onOpenSettings={() => setSettingsOpen(true)}
          onAddFiles={() => void pickFiles()}
        />
        <Toaster position="bottom-right" theme="dark" richColors />
      </div>
    </TooltipProvider>
  );
}
