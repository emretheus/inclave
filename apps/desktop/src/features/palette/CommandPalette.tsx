import { useEffect } from "react";
import { Cpu, FileText, MessageSquarePlus, Play, Settings } from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { useChat } from "@/stores/chat";
import { useModels } from "@/stores/models";
import { useSystem } from "@/stores/system";

export function CommandPalette({
  open,
  onOpenChange,
  onOpenSettings,
  onAddFiles,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onOpenSettings: () => void;
  onAddFiles: () => void;
}) {
  const newSession = useChat((s) => s.newSession);
  const runLast = useChat((s) => s.runLast);
  const { list, refresh, setDefault } = useModels();
  const setActiveModel = useSystem((s) => s.setActiveModel);

  useEffect(() => {
    if (open) void refresh();
  }, [open, refresh]);

  const run = (fn: () => void) => {
    onOpenChange(false);
    fn();
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>
        <CommandGroup heading="Actions">
          <CommandItem onSelect={() => run(newSession)}>
            <MessageSquarePlus /> New chat
          </CommandItem>
          <CommandItem onSelect={() => run(() => void runLast())}>
            <Play /> Re-run last code block
          </CommandItem>
          <CommandItem onSelect={() => run(onAddFiles)}>
            <FileText /> Add files
          </CommandItem>
          <CommandItem onSelect={() => run(onOpenSettings)}>
            <Settings /> Settings
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Switch model">
          {list.map((m) => (
            <CommandItem
              key={m.name}
              onSelect={() =>
                run(() => {
                  setActiveModel(m.name);
                  void setDefault(m.name);
                })
              }
            >
              <Cpu /> {m.name}
            </CommandItem>
          ))}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
