import { useEffect } from "react";
import { Check, Cpu, MemoryStick } from "lucide-react";
import { useModels } from "@/stores/models";
import { useSystem } from "@/stores/system";
import {
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { formatBytes } from "@/lib/utils";

// The model switcher inside the titlebar dropdown.
export function ModelMenu() {
  const { list, refresh, setDefault } = useModels();
  const { activeModel, setActiveModel } = useSystem();

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <>
      <DropdownMenuLabel>Switch model</DropdownMenuLabel>
      {list.map((m) => (
        <DropdownMenuItem
          key={m.name}
          onSelect={() => {
            setActiveModel(m.name);
            void setDefault(m.name);
          }}
          className="flex items-center gap-2"
        >
          <Cpu className="size-3.5 text-muted-foreground" />
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="truncate">{m.name}</span>
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
              {formatBytes(m.size_bytes)}
              {m.vram_ok === false && (
                <span className="flex items-center gap-0.5 text-[var(--color-warning)]">
                  <MemoryStick className="size-2.5" /> swaps
                </span>
              )}
            </span>
          </div>
          {activeModel === m.name && <Check className="size-4 text-primary" />}
        </DropdownMenuItem>
      ))}
      {list.length === 0 && (
        <div className="px-2 py-2 text-xs text-muted-foreground">
          No models installed. Open Settings → Models.
        </div>
      )}
      <DropdownMenuSeparator />
      <DropdownMenuItem disabled className="text-[11px] text-muted-foreground">
        Manage models in Settings
      </DropdownMenuItem>
    </>
  );
}
