import * as React from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';

interface ModalOptions {
  /** Optional fixed width class (e.g. 'max-w-2xl'). */
  className?: string;
  /** Hide the default close button (caller renders its own controls). */
  hideClose?: boolean;
}

interface ModalContextValue {
  /** Open a modal with arbitrary content. */
  openModal: (content: React.ReactNode, options?: ModalOptions) => void;
  closeModal: () => void;
}

const ModalContext = React.createContext<ModalContextValue | null>(null);

/**
 * App-level modal host. Any feature can imperatively open a dialog without
 * threading dialog state through its own component tree.
 */
export function ModalProvider({ children }: { children: React.ReactNode }) {
  const [content, setContent] = React.useState<React.ReactNode>(null);
  const [options, setOptions] = React.useState<ModalOptions>({});
  const [open, setOpen] = React.useState(false);

  const openModal = React.useCallback((node: React.ReactNode, opts: ModalOptions = {}) => {
    setContent(node);
    setOptions(opts);
    setOpen(true);
  }, []);

  const closeModal = React.useCallback(() => setOpen(false), []);

  const value = React.useMemo(() => ({ openModal, closeModal }), [openModal, closeModal]);

  return (
    <ModalContext.Provider value={value}>
      {children}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className={options.className} hideClose={options.hideClose}>
          {content}
        </DialogContent>
      </Dialog>
    </ModalContext.Provider>
  );
}

export function useModal(): ModalContextValue {
  const ctx = React.useContext(ModalContext);
  if (!ctx) throw new Error('useModal must be used within a ModalProvider');
  return ctx;
}
