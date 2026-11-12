import type { Category, ClaimStatus, ListingStatus } from "./api";

export const CATEGORY_LABEL: Record<Category, string> = {
  boulangerie: "Boulangerie",
  traiteur: "Traiteur",
  fruits_legumes: "Fruits et légumes",
  produits_laitiers: "Produits laitiers",
  epicerie: "Épicerie",
  autre: "Autre",
};

export const UNIT_LABEL: Record<string, string> = {
  kg: "kg",
  pieces: "pièces",
  portions: "portions",
  barquettes: "barquettes",
  litres: "L",
};

export const STORAGE_LABEL = { ambient: "Ambiant", chilled: "Frais", frozen: "Surgelé" } as const;

export const ALLERGEN_LABEL: Record<string, string> = {
  gluten: "Gluten",
  crustaces: "Crustacés",
  oeufs: "Œufs",
  poisson: "Poisson",
  arachides: "Arachides",
  soja: "Soja",
  lait: "Lait",
  fruits_a_coque: "Fruits à coque",
  celeri: "Céleri",
  moutarde: "Moutarde",
  sesame: "Sésame",
  sulfites: "Sulfites",
  lupin: "Lupin",
  mollusques: "Mollusques",
};

export const LISTING_STATUS_LABEL: Record<ListingStatus, string> = {
  available: "Disponible",
  partially_claimed: "Partiellement réservée",
  fully_claimed: "Entièrement réservée",
  expired: "Expirée",
  cancelled: "Retirée",
};

export const CLAIM_STATUS_LABEL: Record<ClaimStatus, string> = {
  pending: "En attente",
  confirmed: "À retirer",
  picked_up: "Retirée",
  cancelled: "Annulée",
  no_show: "Non présenté",
};

/** Temps restant avant la fin du créneau de retrait, avec un niveau d'urgence. */
export function timeLeft(end: string, now = Date.now()): { label: string; urgent: boolean } {
  const ms = new Date(end).getTime() - now;
  if (ms <= 0) return { label: "Créneau terminé", urgent: true };
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 60) return { label: `Plus que ${minutes} min`, urgent: true };
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { label: `Encore ${hours} h`, urgent: hours < 3 };
  return { label: `Encore ${Math.floor(hours / 24)} j`, urgent: false };
}

export function formatQuantity(value: string | number): string {
  const n = Number(value);
  return Number.isInteger(n) ? String(n) : n.toLocaleString("fr-FR", { maximumFractionDigits: 2 });
}

export const hm = (iso: string) =>
  new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

export const dayLabel = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });

const pad = (n: number) => String(n).padStart(2, "0");

/** Date -> valeur d'un <input type="datetime-local"> (heure locale, sans fuseau). */
export function toLocalInput(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Valeur datetime-local -> ISO 8601 avec fuseau, comme l'exige l'API. */
export const localToIso = (value: string) => new Date(value).toISOString();

export interface WindowPreset {
  start: string;
  end: string;
  expiry: string;
}

/** Créneaux prêts à l'emploi pour publier en deux clics. */
export function presetWindow(kind: "soon" | "evening", now = new Date()): WindowPreset {
  const start = new Date(now);
  const end = new Date(now);
  if (kind === "soon") {
    start.setMinutes(start.getMinutes() + 30);
    end.setHours(end.getHours() + 2, end.getMinutes() + 30);
  } else {
    start.setHours(18, 0, 0, 0);
    end.setHours(19, 30, 0, 0);
    if (end.getTime() <= now.getTime()) {
      start.setDate(start.getDate() + 1);
      end.setDate(end.getDate() + 1);
    }
  }
  const expiry = new Date(end.getTime() + 12 * 3600_000);
  return { start: toLocalInput(start), end: toLocalInput(end), expiry: toLocalInput(expiry) };
}

/** Lien d'appel : tel:+33612345678 */
export const telUrl = (phone: string) => `tel:${phone.replace(/[^\d+]/g, "")}`;

/** Lien WhatsApp (wa.me attend le numéro international sans le « + »). */
export const whatsappUrl = (phone: string) => `https://wa.me/${phone.replace(/\D/g, "")}`;
