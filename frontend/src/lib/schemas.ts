import { z } from "zod";

export const loginSchema = z.object({
  email: z.email("Saisis une adresse email valide"),
  password: z.string().min(1, "Saisis ton mot de passe"),
});

/** Contrôle volontairement souple côté navigateur : l'API (libphonenumber) fait foi. */
export const phoneField = z
  .string()
  .trim()
  .regex(/^\+?[\d\s().-]+$/, "Utilise uniquement des chiffres, espaces et +")
  .refine((v) => {
    const digits = v.replace(/\D/g, "").length;
    return digits >= 8 && digits <= 15;
  }, "Numéro incomplet (de 8 à 15 chiffres)");

export const registerSchema = z
  .object({
    role: z.enum(["provider", "beneficiary"]),
    full_name: z.string().trim().min(2, "Indique ton nom (2 caractères minimum)"),
    organization_name: z.string().trim().optional(),
    phone: phoneField,
    email: z.email("Saisis une adresse email valide"),
    password: z.string().min(10, "10 caractères minimum").max(128, "128 caractères maximum"),
  })
  .refine((v) => v.role !== "provider" || !!v.organization_name, {
    path: ["organization_name"],
    message: "Indique le nom de ton commerce",
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;

/** Règles de créneau, identiques à celles du backend (qui reste l'autorité). */
export function windowErrors(
  v: { pickup_start: string; pickup_end: string; expiry_at: string; date_type: "dlc" | "ddm" },
  now = Date.now(),
): Partial<Record<"pickup_start" | "pickup_end" | "expiry_at", string>> {
  const errors: Partial<Record<"pickup_start" | "pickup_end" | "expiry_at", string>> = {};
  const start = new Date(v.pickup_start).getTime();
  const end = new Date(v.pickup_end).getTime();
  const expiry = new Date(v.expiry_at).getTime();
  if (!Number.isNaN(end) && end <= now) errors.pickup_end = "Le créneau doit se terminer dans le futur";
  else if (!Number.isNaN(start) && !Number.isNaN(end) && end <= start)
    errors.pickup_end = "La fin doit être après le début";
  else if (!Number.isNaN(end) && end > now + 7 * 24 * 3600_000)
    errors.pickup_end = "Le créneau doit se terminer dans les 7 jours";
  if (v.date_type === "dlc" && !Number.isNaN(expiry) && !Number.isNaN(end) && end > expiry)
    errors.expiry_at = "Avec une DLC, le retrait doit se terminer avant la date limite";
  return errors;
}

export const listingSchema = z
  .object({
    title: z.string().trim().min(3, "3 caractères minimum").max(160, "160 caractères maximum"),
    description: z.string().trim().max(2000, "2000 caractères maximum").optional(),
    category: z.enum(["boulangerie", "traiteur", "fruits_legumes", "produits_laitiers", "epicerie", "autre"]),
    quantity: z.string().refine((v) => Number(v) > 0, "Indique une quantité supérieure à 0"),
    unit: z.enum(["kg", "pieces", "portions", "barquettes", "litres"]),
    date_type: z.enum(["dlc", "ddm"]),
    storage_condition: z.enum(["ambient", "chilled", "frozen"]),
    allergens: z.array(z.string()),
    pickup_start: z.string().min(1, "Indique le début du retrait"),
    pickup_end: z.string().min(1, "Indique la fin du retrait"),
    expiry_at: z.string().min(1, "Indique la date limite"),
    location_text: z.string().trim().min(3, "Indique où retirer les denrées"),
  })
  .superRefine((v, ctx) => {
    for (const [path, message] of Object.entries(windowErrors(v))) {
      ctx.addIssue({ code: "custom", path: [path], message });
    }
  });

export type ListingValues = z.infer<typeof listingSchema>;
