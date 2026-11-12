// Client HTTP minimal : jeton Bearer, rafraîchissement automatique sur 401.
// Les jetons sont en localStorage (simple pour un MVP). Compromis assumé : exposé en cas de XSS.
// Évolution prévue : refresh token en cookie httpOnly.

export type Role = "provider" | "beneficiary" | "admin";

export type Category =
  | "boulangerie"
  | "traiteur"
  | "fruits_legumes"
  | "produits_laitiers"
  | "epicerie"
  | "autre";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  organization_name: string | null;
  phone: string | null;
  is_verified: boolean;
  created_at: string;
}

export type Unit = "kg" | "pieces" | "portions" | "barquettes" | "litres";
export type Storage = "ambient" | "chilled" | "frozen";
export type ListingStatus = "available" | "partially_claimed" | "fully_claimed" | "expired" | "cancelled";
export type ClaimStatus = "pending" | "confirmed" | "picked_up" | "cancelled" | "no_show";

export interface Listing {
  id: string;
  provider_id: string;
  title: string;
  description: string | null;
  category: Category;
  quantity: string;
  quantity_claimed: string;
  quantity_remaining: string;
  unit: Unit;
  date_type: "dlc" | "ddm";
  storage_condition: Storage;
  allergens: string[];
  pickup_start: string;
  pickup_end: string;
  expiry_at: string;
  status: ListingStatus;
  location_text: string;
  image_url: string | null;
  provider_name: string;
  provider_verified: boolean;
  created_at: string;
}

export interface ListingPage {
  items: Listing[];
  next_cursor: string | null;
}

export interface Claim {
  id: string;
  listing_id: string;
  listing_title: string;
  provider_name: string;
  location_text: string;
  pickup_start: string;
  pickup_end: string;
  unit: Unit;
  quantity_claimed: string;
  status: ClaimStatus;
  claimed_at: string;
  picked_up_at: string | null;
  notes: string | null;
  beneficiary_name: string;
  beneficiary_verified: boolean;
  pickup_code: string | null;
  contact_phone: string | null;
}

export interface ImpactSummary {
  kg_rescued: number;
  meals_estimated: number;
  co2e_avoided_kg: number;
  listings_published: number;
  pickups_completed: number;
}

interface Tokens {
  access_token: string;
  refresh_token: string;
}

const KEY = "foodbridge.tokens";

export const tokenStore = {
  get(): Tokens | null {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? (JSON.parse(raw) as Tokens) : null;
    } catch {
      return null;
    }
  },
  set(tokens: Tokens) {
    try {
      localStorage.setItem(KEY, JSON.stringify(tokens));
    } catch {
      /* stockage indisponible (navigation privée) : la session ne survivra pas au rechargement */
    }
  },
  clear() {
    try {
      localStorage.removeItem(KEY);
    } catch {
      /* rien à faire */
    }
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function messageFrom(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

let refreshing: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const current = tokenStore.get();
  if (!current) return false;
  refreshing ??= fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: current.refresh_token }),
  })
    .then(async (r) => {
      if (!r.ok) return false;
      tokenStore.set((await r.json()) as Tokens);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const tokens = tokenStore.get();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (tokens) headers.set("Authorization", `Bearer ${tokens.access_token}`);

  let res: Response;
  try {
    res = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Connexion impossible. Vérifie ton réseau et réessaie.");
  }

  if (res.status === 401 && retry && tokens && !path.startsWith("/auth/")) {
    if (await refreshTokens()) return api<T>(path, init, false);
    tokenStore.clear();
    window.dispatchEvent(new Event("foodbridge:logout"));
  }

  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, messageFrom(body, "Une erreur est survenue."));
  return body as T;
}
