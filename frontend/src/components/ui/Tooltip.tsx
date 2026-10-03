import * as RT from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

/** Plain-text tooltip on hover and keyboard focus. Needs the `TooltipProvider` in App. */
export function Tooltip({ text, children }: { text: string; children: ReactNode }) {
  return (
    <RT.Root>
      <RT.Trigger asChild>{children}</RT.Trigger>
      <RT.Portal>
        <RT.Content
          sideOffset={6}
          className="z-toast max-w-xs rounded bg-text px-2 py-1 text-label text-surface"
        >
          {text}
        </RT.Content>
      </RT.Portal>
    </RT.Root>
  );
}

export const TooltipProvider = RT.Provider;
