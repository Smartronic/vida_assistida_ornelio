import { useEffect, useRef } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  variant?: "default" | "danger";
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  variant = "default",
}: ConfirmDialogProps) {
  const cancelBtnRef = useRef<HTMLButtonElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Impede scroll do body enquanto o modal estiver aberto e foca o botão de cancelar
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
      setTimeout(() => {
        cancelBtnRef.current?.focus();
      }, 50);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Trata tecla ESC para fechar o modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onCancel]);

  if (!open) return null;

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) {
      onCancel();
    }
  };

  return (
    <div
      ref={overlayRef}
      className="dialog-overlay"
      onClick={handleOverlayClick}
      id="confirm-dialog-overlay"
    >
      <div 
        className="dialog-card animate-scale-in" 
        role="dialog" 
        aria-modal="true" 
        aria-labelledby="dialog-title" 
        aria-describedby="dialog-desc"
      >
        <h3 id="dialog-title" className="dialog-title">
          {title}
        </h3>
        <p id="dialog-desc" className="dialog-description">
          {description}
        </p>
        <div className="dialog-actions">
          <button
            ref={cancelBtnRef}
            id="dialog-cancel-btn"
            className="dialog-btn cancel"
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            id="dialog-confirm-btn"
            className={`dialog-btn confirm ${variant}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
