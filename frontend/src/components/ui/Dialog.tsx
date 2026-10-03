import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { ReactNode } from "react";

/** Modal dialog (UI/UX brief 6: modals for short forms). `forced` removes every way to close it
 * without completing the form (App Flow 4.2 first-login password change). */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  forced = false,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  forced?: boolean;
  children: ReactNode;
}) {
  const block = forced ? (e: Event) => e.preventDefault() : undefined;
  return (
    <D.Root open={open} onOpenChange={forced ? undefined : onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-modal bg-black/40" />
        <D.Content
          onEscapeKeyDown={block}
          onPointerDownOutside={block}
          onInteractOutside={block}
          className="fixed left-1/2 top-1/2 z-modal w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded border border-border bg-surface p-6 shadow-md"
        >
          <div className="flex items-start justify-between gap-4">
            <D.Title className="text-h2">{title}</D.Title>
            {!forced && (
              <D.Close aria-label="Close" className="rounded p-1 text-muted hover:bg-surface-2">
                <X size={16} strokeWidth={1.75} aria-hidden="true" />
              </D.Close>
            )}
          </div>
          <D.Description className="mt-1 text-body text-muted">{description}</D.Description>
          <div className="mt-4">{children}</div>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}
