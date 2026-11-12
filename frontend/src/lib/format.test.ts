import { describe, expect, it } from "vitest";
import { formatQuantity, timeLeft } from "./format";

const now = new Date("2026-11-10T18:00:00Z").getTime();

describe("timeLeft", () => {
  it("signale l'urgence sous une heure", () => {
    expect(timeLeft("2026-11-10T18:25:00Z", now)).toEqual({ label: "Plus que 25 min", urgent: true });
  });
  it("reste calme au-delà de 3 heures", () => {
    expect(timeLeft("2026-11-10T23:30:00Z", now)).toEqual({ label: "Encore 5 h", urgent: false });
  });
  it("indique un créneau terminé", () => {
    expect(timeLeft("2026-11-10T17:00:00Z", now).label).toBe("Créneau terminé");
  });
});

describe("formatQuantity", () => {
  it("retire les décimales inutiles", () => {
    expect(formatQuantity("10.00")).toBe("10");
    expect(formatQuantity("2.5")).toBe("2,5");
  });
});

import { localToIso, presetWindow, toLocalInput } from "./format";

describe("presetWindow", () => {
  it("'soon' commence dans 30 min et dure 2 h", () => {
    const now = new Date(2026, 10, 10, 12, 0);
    const p = presetWindow("soon", now);
    expect(p.start).toBe("2026-11-10T12:30");
    expect(p.end).toBe("2026-11-10T14:30");
  });
  it("'evening' vise 18h-19h30, et bascule à demain si c'est déjà passé", () => {
    expect(presetWindow("evening", new Date(2026, 10, 10, 9, 0)).start).toBe("2026-11-10T18:00");
    expect(presetWindow("evening", new Date(2026, 10, 10, 20, 0)).start).toBe("2026-11-11T18:00");
  });
  it("la date limite suit toujours la fin du retrait", () => {
    const p = presetWindow("evening", new Date(2026, 10, 10, 9, 0));
    expect(new Date(p.expiry).getTime()).toBeGreaterThan(new Date(p.end).getTime());
  });
});

describe("conversion datetime-local", () => {
  it("aller-retour sans perte", () => {
    const d = new Date(2026, 10, 10, 18, 5);
    expect(toLocalInput(d)).toBe("2026-11-10T18:05");
    expect(new Date(localToIso("2026-11-10T18:05")).getTime()).toBe(d.getTime());
  });
});

import { telUrl, whatsappUrl } from "./format";

describe("liens de contact", () => {
  it("construit un lien tel: propre", () => {
    expect(telUrl("+33 6 12 34 56 78")).toBe("tel:+33612345678");
  });
  it("construit un lien WhatsApp sans le +", () => {
    expect(whatsappUrl("+221771234567")).toBe("https://wa.me/221771234567");
  });
});
