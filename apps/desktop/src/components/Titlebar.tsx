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
    <div className="titlebar-drag flex h-11 items-center justify-between border-b border-border bg-surface/60 pl-20 pr-3 backdrop-blur">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Logo variant="badge" className="size-4 rounded-[5px]" />
        <span className="text-muted-foreground">InClave</span>
      </div>

      <div className="titlebar-no-drag flex items-center gap-1.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-7 gap-1.5 px-2 text-xs">
              <Cpu className="size-3.5 text-accent" />
              <span className="max-w-40 truncate">{activeModel ?? "no model"}</span>
              <ChevronDown className="size-3 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <ModelMenu />
          </DropdownMenuContent>
        </DropdownMenu>

        <Button variant="ghost" size="icon" className="size-7" onClick={onOpenSettings}>
          <Cog className="size-4 text-muted-foreground" />
        </Button>
      </div>
    </div>
  );
}
