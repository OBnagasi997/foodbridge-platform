import { telUrl, whatsappUrl } from "../lib/format";

/** Numéro de l'autre partie avec appel direct et WhatsApp. Affiché uniquement pendant une réservation en cours. */
export function ContactActions({ phone, who }: { phone: string; who: string }) {
  const link =
    "inline-flex items-center rounded-lg bg-white px-3 py-1.5 text-sm font-semibold text-leaf-800 shadow-card transition-colors hover:bg-leaf-50";
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-xl bg-oat-100 px-4 py-3">
      <p className="mr-auto text-sm text-oat-700">
        Contacter {who} : <span className="font-semibold text-leaf-900">{phone}</span>
      </p>
      <a className={link} href={telUrl(phone)}>Appeler</a>
      <a className={link} href={whatsappUrl(phone)} target="_blank" rel="noopener noreferrer">
        WhatsApp
      </a>
    </div>
  );
}
