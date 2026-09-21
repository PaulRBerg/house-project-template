import { AlertDialog } from "@base-ui/react/alert-dialog";
import { useEffect, useRef } from "react";

import { AppButton } from "./AppButton.js";

type ConfirmDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  intent?: "default" | "destructive";
};

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  intent = "default",
}: ConfirmDialogProps) {
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const confirmedRef = useRef(false);
  const wasOpenRef = useRef(open);

  useEffect(() => {
    if (open && !wasOpenRef.current) confirmedRef.current = false;
    wasOpenRef.current = open;
  }, [open]);

  const confirm = (): void => {
    if (confirmedRef.current) return;
    confirmedRef.current = true;
    onConfirm();
  };

  return (
    <AlertDialog.Root onOpenChange={onOpenChange} open={open}>
      <AlertDialog.Portal>
        <AlertDialog.Backdrop
          className="fixed inset-0 z-(--z-confirm-backdrop) bg-dialog-backdrop backdrop-blur-[3px] transition-opacity data-ending-style:opacity-0 data-starting-style:opacity-0 motion-reduce:transition-none"
          data-app-dialog-backdrop=""
        />
        <AlertDialog.Viewport className="fixed inset-0 z-(--z-confirm) grid place-items-center overflow-y-auto p-6">
          <AlertDialog.Popup
            className="w-full max-w-120 rounded-xl border border-line bg-surface p-6 text-ink shadow-panel transition-[transform,opacity] data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0 motion-reduce:transition-none"
            finalFocus={true}
            initialFocus={cancelButtonRef}
          >
            <AlertDialog.Title className="text-[1.1rem] font-bold tracking-tight">
              {title}
            </AlertDialog.Title>
            <AlertDialog.Description className="mt-2 text-[0.78rem] leading-relaxed text-muted">
              {description}
            </AlertDialog.Description>
            <div className="mt-6 flex justify-end gap-2">
              <AlertDialog.Close
                render={
                  <AppButton intent="secondary" ref={cancelButtonRef} type="button">
                    {cancelLabel}
                  </AppButton>
                }
              />
              <AlertDialog.Close
                render={
                  <AppButton
                    {...(intent === "destructive"
                      ? { className: "border-danger bg-danger text-surface hover:bg-danger/90" }
                      : {})}
                    intent="primary"
                    onClick={confirm}
                    type="button"
                  >
                    {confirmLabel}
                  </AppButton>
                }
              />
            </div>
          </AlertDialog.Popup>
        </AlertDialog.Viewport>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
