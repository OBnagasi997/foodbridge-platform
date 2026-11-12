import { describe, expect, it } from "vitest";
import { registerSchema } from "./schemas";

const base = {
  role: "beneficiary" as const,
  full_name: "Awa Diop",
  phone: "06 12 34 56 78",
  email: "awa@example.org",
  password: "correct-horse-battery",
};

describe("registerSchema", () => {
  it("accepte un bénéficiaire sans organisation", () => {
    expect(registerSchema.safeParse(base).success).toBe(true);
  });

  it("exige le nom du commerce pour un commerçant", () => {
    const r = registerSchema.safeParse({ ...base, role: "provider" });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0].path).toEqual(["organization_name"]);
  });

  it("rejette un mot de passe trop court", () => {
    expect(registerSchema.safeParse({ ...base, password: "court" }).success).toBe(false);
  });

  it("rejette un email invalide", () => {
    expect(registerSchema.safeParse({ ...base, email: "pas-un-email" }).success).toBe(false);
  });
});

import { listingSchema, windowErrors } from "./schemas";

const NOW = new Date("2026-11-10T12:00:00").getTime();
const win = (over = {}) => ({
  pickup_start: "2026-11-10T13:00",
  pickup_end: "2026-11-10T15:00",
  expiry_at: "2026-11-10T20:00",
  date_type: "dlc" as const,
  ...over,
});

describe("windowErrors", () => {
  it("accepte un créneau cohérent", () => {
    expect(windowErrors(win(), NOW)).toEqual({});
  });
  it("refuse une fin avant le début", () => {
    expect(windowErrors(win({ pickup_end: "2026-11-10T12:30" }), NOW).pickup_end).toMatch(/après le début/);
  });
  it("refuse un créneau déjà terminé", () => {
    const e = windowErrors(win({ pickup_start: "2026-11-10T08:00", pickup_end: "2026-11-10T10:00" }), NOW);
    expect(e.pickup_end).toMatch(/futur/);
  });
  it("refuse un créneau au-delà de 7 jours", () => {
    expect(windowErrors(win({ pickup_end: "2026-11-25T10:00" }), NOW).pickup_end).toMatch(/7 jours/);
  });
  it("applique la règle DLC mais pas DDM", () => {
    const late = { expiry_at: "2026-11-10T14:00" };
    expect(windowErrors(win(late), NOW).expiry_at).toMatch(/DLC/);
    expect(windowErrors(win({ ...late, date_type: "ddm" }), NOW)).toEqual({});
  });
});

describe("listingSchema", () => {
  const base = {
    title: "Pains du soir",
    category: "boulangerie" as const,
    quantity: "5",
    unit: "kg" as const,
    date_type: "ddm" as const,
    storage_condition: "ambient" as const,
    allergens: [],
    pickup_start: "2099-01-01T10:00",
    pickup_end: "2099-01-01T12:00",
    expiry_at: "2099-01-02T12:00",
    location_text: "12 rue du Marché",
  };
  it("rejette une quantité nulle", () => {
    expect(listingSchema.safeParse({ ...base, quantity: "0" }).success).toBe(false);
  });
  it("rejette un titre trop court", () => {
    expect(listingSchema.safeParse({ ...base, title: "ab" }).success).toBe(false);
  });
});

import { phoneField } from "./schemas";

describe("phoneField", () => {
  it.each(["06 12 34 56 78", "+221 77 123 45 67", "(06) 12-34-56-78"])("accepte %s", (v) => {
    expect(phoneField.safeParse(v).success).toBe(true);
  });
  it.each(["0612", "abcdefghij", "+33 1 2", "0612345678901234567"])("refuse %s", (v) => {
    expect(phoneField.safeParse(v).success).toBe(false);
  });
});
