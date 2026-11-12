import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ListingCard } from "../components/ListingCard";
import { Button, Field, Select, Textarea } from "../components/ui";
import type { Listing } from "../lib/api";
import { ALLERGEN_LABEL, CATEGORY_LABEL, localToIso, presetWindow } from "../lib/format";
import { post, useAction } from "../lib/queries";
import { listingSchema, type ListingValues } from "../lib/schemas";

const UNITS = [["kg", "kilogrammes"], ["pieces", "pièces"], ["portions", "portions"], ["barquettes", "barquettes"], ["litres", "litres"]] as const;

export default function CreateListing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const initial = presetWindow("evening");
  const {
    register, handleSubmit, watch, setValue, formState: { errors },
  } = useForm<ListingValues>({
    resolver: zodResolver(listingSchema),
    mode: "onChange",
    defaultValues: {
      category: "boulangerie", unit: "kg", date_type: "ddm", storage_condition: "ambient", allergens: [],
      pickup_start: initial.start, pickup_end: initial.end, expiry_at: initial.expiry, quantity: "", title: "", location_text: "",
    },
  });

  const create = useAction(
    (v: ListingValues) =>
      post<Listing>("/listings", {
        ...v,
        description: v.description || null,
        pickup_start: localToIso(v.pickup_start),
        pickup_end: localToIso(v.pickup_end),
        expiry_at: localToIso(v.expiry_at),
      }),
    { success: "Annonce publiée", onSuccess: (l) => navigate(`/app/listings/${l.id}`) },
  );

  const v = watch();
  const allergens = v.allergens ?? [];
  const applyPreset = (kind: "soon" | "evening") => {
    const p = presetWindow(kind);
    setValue("pickup_start", p.start, { shouldValidate: true });
    setValue("pickup_end", p.end, { shouldValidate: true });
    setValue("expiry_at", p.expiry, { shouldValidate: true });
  };

  const iso = (s: string) => (Number.isNaN(Date.parse(s)) ? "" : new Date(s).toISOString());
  const preview: Listing = {
    id: "preview", provider_id: user?.id ?? "", title: v.title ?? "", description: v.description ?? null,
    category: v.category, quantity: v.quantity || "0", quantity_claimed: "0", quantity_remaining: v.quantity || "0",
    unit: v.unit, date_type: v.date_type, storage_condition: v.storage_condition, allergens,
    pickup_start: iso(v.pickup_start), pickup_end: iso(v.pickup_end) || new Date(Date.now() + 3600_000).toISOString(),
    expiry_at: iso(v.expiry_at), status: "available", location_text: v.location_text ?? "", image_url: null,
    provider_name: user?.organization_name ?? user?.full_name ?? "", provider_verified: !!user?.is_verified, created_at: "",
  };

  return (
    <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr]">
      <form onSubmit={handleSubmit((vals) => create.mutate(vals))} className="space-y-7" noValidate>
        <div>
          <h1 className="text-3xl font-bold">Publier un surplus</h1>
          <p className="mt-1 text-oat-700">Quatre rubriques, deux minutes. L'aperçu se met à jour pendant que tu écris.</p>
        </div>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold">Le produit</h2>
          <Field label="Titre" placeholder="Pains et viennoiseries du soir" error={errors.title?.message} {...register("title")} />
          <div className="grid gap-4 sm:grid-cols-3">
            <Select label="Catégorie" {...register("category")}>
              {Object.entries(CATEGORY_LABEL).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </Select>
            <Field label="Quantité" type="number" inputMode="decimal" step="0.01" min="0" error={errors.quantity?.message} {...register("quantity")} />
            <Select label="Unité" {...register("unit")}>
              {UNITS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </Select>
          </div>
          <Textarea label="Description (facultatif)" error={errors.description?.message} {...register("description")} />
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold">Sécurité alimentaire</h2>
          <fieldset>
            <legend className="mb-1.5 text-sm font-semibold text-leaf-800">Type de date</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              {([["dlc", "DLC", "À consommer avant : ne jamais dépasser. Le retrait doit finir avant."], ["ddm", "DDM", "À consommer de préférence avant : la qualité, pas la sécurité."]] as const).map(([val, title, text]) => (
                <label key={val} className="cursor-pointer">
                  <input type="radio" value={val} className="peer sr-only" {...register("date_type")} />
                  <span className="block rounded-xl border border-oat-300 p-3.5 peer-checked:border-leaf-700 peer-checked:bg-leaf-50 peer-focus-visible:ring-2 peer-focus-visible:ring-leaf-500">
                    <span className="block font-semibold">{title}</span>
                    <span className="block text-sm text-oat-700">{text}</span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>
          <Select label="Conservation" {...register("storage_condition")}>
            <option value="ambient">Température ambiante</option>
            <option value="chilled">Réfrigéré</option>
            <option value="frozen">Surgelé</option>
          </Select>
          <fieldset>
            <legend className="mb-1.5 text-sm font-semibold text-leaf-800">Allergènes présents</legend>
            <div className="flex flex-wrap gap-2">
              {Object.entries(ALLERGEN_LABEL).map(([k, label]) => {
                const on = allergens.includes(k);
                return (
                  <button
                    type="button" key={k} aria-pressed={on}
                    onClick={() => setValue("allergens", on ? allergens.filter((a) => a !== k) : [...allergens, k], { shouldValidate: true })}
                    className={`rounded-full px-3 py-1.5 text-sm font-semibold transition-colors ${on ? "bg-honey-100 text-honey-700 ring-1 ring-honey-500" : "bg-oat-100 text-oat-700 hover:bg-oat-200"}`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold">Retrait</h2>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" className="!py-2" onClick={() => applyPreset("soon")}>Dans 30 min, sur 2 h</Button>
            <Button type="button" variant="secondary" className="!py-2" onClick={() => applyPreset("evening")}>Ce soir, 18 h à 19 h 30</Button>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Début du retrait" type="datetime-local" error={errors.pickup_start?.message} {...register("pickup_start")} />
            <Field label="Fin du retrait" type="datetime-local" error={errors.pickup_end?.message} {...register("pickup_end")} />
          </div>
          <Field
            label={v.date_type === "dlc" ? "Date limite de consommation" : "Date de durabilité minimale"}
            type="datetime-local" error={errors.expiry_at?.message} {...register("expiry_at")}
          />
          <Field label="Lieu de retrait" placeholder="12 rue du Marché, entrée côté livraison" error={errors.location_text?.message} {...register("location_text")} />
        </section>

        <Button type="submit" className="w-full sm:w-auto" loading={create.isPending}>Publier l'annonce</Button>
      </form>

      <aside className="lg:sticky lg:top-24 lg:h-fit">
        <p className="mb-3 text-sm font-semibold text-oat-700">Aperçu tel que les associations le verront</p>
        <ul><ListingCard listing={preview} preview /></ul>
      </aside>
    </div>
  );
}
