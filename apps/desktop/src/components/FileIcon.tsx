import { FileCode, FileSpreadsheet, FileText, FileType, File } from "lucide-react";
import type { FileEntry } from "@inclave/ipc-contract";

export function FileIcon({ kind, className }: { kind: FileEntry["kind"]; className?: string }) {
  switch (kind) {
    case "csv":
    case "xlsx":
      return <FileSpreadsheet className={className} />;
    case "pdf":
      return <FileType className={className} />;
    case "code":
      return <FileCode className={className} />;
    case "text":
      return <FileText className={className} />;
    default:
      return <File className={className} />;
  }
}
