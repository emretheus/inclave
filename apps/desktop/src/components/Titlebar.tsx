import { ChevronDown, Cog, Cpu } from "lucide-react";
import { Logo } from "@/components/Logo";
import { useSystem } from "@/stores/system";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ModelMenu } from "@/features/models/ModelMenu";
import { Button } from "@/components/ui/button";

// Custom macOS titlebar: draggable, leaves room for the traffic lights on the
// left (inset via tauri.conf), shows the active model + settings on the right.
export function Titlebar({ onOpenSettings }: { onOpenSettings: () => void }) {
  const activeModel = useSystem((s) => s.activeModel);

  return (
    <div className="titlebar-drag flex h-12 items-center justify-between border-b border-border bg-surface/70 pl-20 pr-2.5 backdrop-blur-xl">
      <div className="flex items-center gap-2">
        <Logo variant="badge" className="size-[18px] rounded-[6px] shadow-xs" />
        <span className="text-[13px] font-semibold tracking-tight">InClave</span>
      </div>

      <div className="titlebar-no-drag flex items-center gap-1">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1.5 rounded-lg border border-border/60 bg-surface-2/60 px-2.5 text-xs font-medium hover:bg-surface-3"
            >
              <Cpu className="size-3.5 text-accent" />
              <span className="max-w-40 truncate">{activeModel ?? "no model"}</span>
              <ChevronDown className="size-3 text-subtle-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <ModelMenu />
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="ghost"
          size="icon"
          className="size-7 text-subtle-foreground hover:text-foreground"
          onClick={onOpenSettings}
        >
          <Cog className="size-4" />
        </Button>
      </div>
    </div>
  );
}
