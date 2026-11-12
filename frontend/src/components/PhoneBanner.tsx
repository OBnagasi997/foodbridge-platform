import { useState } from "react";
import { toast } from "sonner";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../lib/api";
import { phoneField } from "../lib/schemas";
import { Button } from "./ui";

/** Invite les comptes créés avant l'ajout du téléphone à le renseigner. */
export function PhoneBanner() {
  const { user, updateProfile } = useAuth();
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  if (!user || user.phone) return null;

  const save = async () => {
    const parsed = phoneField.safeParse(value);
    if (!parsed.success) return setError(parsed.error.issues[0].message);
    setSaving(true);
    try {
      await updateProfile({ phone: parsed.data });
      toast.success("Numéro enregistré");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Enregistrement impossible");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border-b border-honey-100 bg-honey-100/60">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
        <p className="mr-auto text-sm font-semibold text-honey-700">
          Ajoute ton numéro pour que commerçants et associations puissent se joindre au moment du retrait.
        </p>
        <label className="sr-only" htmlFor="banner-phone">Numéro de téléphone</label>
        <input
          id="banner-phone" type="tel" autoComplete="tel" value={value} placeholder="06 12 34 56 78"
          onChange={(e) => { setValue(e.target.value); setError(null); }}
          onKeyDown={(e) => e.key === "Enter" && save()}
          aria-invalid={error ? true : undefined}
          className="w-48 rounded-xl border border-oat-300 bg-white px-3 py-2 text-sm outline-none focus:border-leaf-600 focus:ring-2 focus:ring-leaf-500/40"
        />
        <Button className="!py-2" onClick={save} loading={saving}>Enregistrer</Button>
        {error && <p role="alert" className="w-full text-sm text-danger-700">{error}</p>}
      </div>
    </div>
  );
}
