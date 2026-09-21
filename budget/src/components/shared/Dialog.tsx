import { Dialog as BaseDialog } from "@base-ui/react/dialog";
import { X } from "lucide-react";
import { useRef, type ReactNode } from "react";

import { cn, eyebrowStyles, iconButtonStyles } from "./styles.js";

interface DialogProps {
  open: boolean;
  title: string;
  eyebrow?: string;
  /** Decorative tile rendered before the title, such as the item's icon. */
  leading?: ReactNode;
  wide?: boolean;
  onRequestClose: () => void;
  onExited?: () => void;
  children: ReactNode;
}

export function Dialog({
  open,
  title,
  eyebrow,
  leading,
  wide = false,
  onRequestClose,
  onExited,
  children,
}: DialogProps) {
  const closeRequestPendingRef = useRef(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  return (
    <BaseDialog.Root
      modal={!import.meta.env.DEV}
      onOpenChange={(nextOpen) => {
        if (nextOpen || !open || closeRequestPendingRef.current) return;
        closeRequestPendingRef.current = true;
        queueMicrotask(() => {
          closeRequestPendingRef.current = false;
        });
        onRequestClose();
      }}
      onOpenChangeComplete={(nextOpen) => {
        if (!nextOpen) onExited?.();
      }}
      open={open}
    >
      <BaseDialog.Portal>
        <BaseDialog.Backdrop
          className="fixed inset-0 z-(--z-backdrop) bg-dialog-backdrop backdrop-blur-[3px] data-ending-style:animate-out data-ending-style:animation-duration-150 data-ending-style:fade-out data-starting-style:animate-in data-starting-style:animation-duration-200 data-starting-style:fade-in motion-reduce:animate-none"
          data-app-dialog-backdrop=""
        />
        <BaseDialog.Viewport className="fixed inset-0 z-(--z-dialog) flex justify-end overflow-hidden">
          <BaseDialog.Popup
            className={cn(
              "flex size-full max-w-140 flex-col overflow-hidden border-l border-line bg-surface shadow-panel data-ending-style:animate-out data-ending-style:animation-duration-150 data-ending-style:slide-out-to-right data-starting-style:animate-in data-starting-style:animation-duration-200 data-starting-style:slide-in-from-right motion-reduce:animate-none",
              wide && "max-w-220",
            )}
            finalFocus={true}
            initialFocus={closeButtonRef}
          >
            <header className="flex min-h-20.5 flex-none items-start justify-between gap-4 border-b border-line px-6 py-5">
              <div className="flex min-w-0 items-start gap-3.5">
                {leading}
                <div className="min-w-0">
                  {eyebrow && <p className={cn(eyebrowStyles, "mb-1")}>{eyebrow}</p>}
                  <BaseDialog.Title className="text-[1.22rem]/[1.25] font-[680] tracking-tight text-balance">
                    {title}
                  </BaseDialog.Title>
                </div>
              </div>
              <BaseDialog.Close
                aria-label="Închide"
                className={cn(iconButtonStyles, "-mt-1 -mr-2")}
                ref={closeButtonRef}
              >
                <X aria-hidden="true" size={20} />
              </BaseDialog.Close>
            </header>
            {children}
          </BaseDialog.Popup>
        </BaseDialog.Viewport>
      </BaseDialog.Portal>
    </BaseDialog.Root>
  );
}
