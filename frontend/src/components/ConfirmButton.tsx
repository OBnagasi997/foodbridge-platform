import { useEffect, useState } from "react";
import { Button } from "./ui";

/** Action destructive en deux temps : un premier clic arme le bouton, le second confirme. */
export function ConfirmButton({
  children,
  confirmLabel = "Confirmer",
  onConfirm,
  loading,
}: {
  children: React.ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  loading?: boolean;
}) {
  const [armed, setArmed] = useState(false);
  useEffect(() => {
    if (!armed) return;
    const t = window.setTimeout(() => setArmed(false), 4000);
    return () => window.clearTimeout(t);
  }, [armed]);

  return (
    <Button
      variant={armed ? "primary" : "ghost"}
      className={armed ? "!bg-danger-700 hover:!bg-danger-700/90" : "!text-danger-700"}
      loading={loading}
      onClick={() => (armed ? (setArmed(false), onConfirm()) : setArmed(true))}
    >
      {armed ? confirmLabel : children}
    </Button>
  );
}
