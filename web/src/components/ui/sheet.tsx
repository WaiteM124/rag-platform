import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { type ReactNode } from "react";
import { cn } from "../../lib/utils";

export function Sheet({
  open,
  onOpenChange,
  title,
  children,
  side = "right",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  side?: "right" | "left";
}) {
  const reduceMotion = useReducedMotion();

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-40 bg-black/50"
                initial={reduceMotion ? false : { opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <motion.div
                className={cn(
                  "fixed z-50 flex h-full w-full max-w-md flex-col border-border bg-card shadow-soft outline-none",
                  side === "right" ? "right-0 top-0 border-l" : "left-0 top-0 border-r",
                )}
                initial={reduceMotion ? false : { x: side === "right" ? "100%" : "-100%" }}
                animate={{ x: 0 }}
                exit={reduceMotion ? undefined : { x: side === "right" ? "100%" : "-100%" }}
                transition={{ type: "spring", damping: 28, stiffness: 320 }}
              >
                <motion.div className="flex items-center justify-between border-b border-border px-4 py-3">
                  <Dialog.Title className="text-sm font-semibold">{title}</Dialog.Title>
                  <Dialog.Close
                    className="rounded-lg p-2 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                    aria-label="Close citations"
                  >
                    <X className="h-4 w-4" />
                  </Dialog.Close>
                </motion.div>
                <div className="flex-1 overflow-y-auto p-4">{children}</div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}