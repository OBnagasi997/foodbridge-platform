import { useImpact } from "../lib/queries";
import { CountUp } from "./CountUp";
import { EmptyState } from "./ui";

export function ImpactStats({ scope = "global" }: { scope?: "global" | "me" }) {
  const { data, isPending, isError, refetch } = useImpact(scope);

  if (isPending) {
    return (
      <div className="grid gap-4 sm:grid-cols-3" aria-busy="true" aria-label="Chargement des chiffres d'impact">
        {[0, 1, 2].map((i) => (
          <div key={i} className="skeleton h-28" />
        ))}
      </div>
    );
  }
  if (isError) {
    return (
      <p className="text-oat-700">
        Les chiffres d'impact sont momentanément indisponibles.{" "}
        <button className="font-semibold text-leaf-700 underline" onClick={() => refetch()}>
          Réessayer
        </button>
      </p>
    );
  }
  if (data.pickups_completed === 0) {
    return (
      <EmptyState title={scope === "me" ? "Ton compteur démarre à zéro" : "Le compteur démarre à zéro"}>
        Chaque retrait confirmé avec son code est compté ici, et rien d'autre.
        {scope === "me" ? " Ton premier don apparaîtra dès son retrait." : " Les premiers repas sauvés apparaîtront dès le premier don."}
      </EmptyState>
    );
  }
  const stats = [
    { value: data.kg_rescued, unit: "kg sauvés", note: "retraits confirmés uniquement" },
    { value: data.meals_estimated, unit: "repas estimés", note: "selon 0,4 kg par repas" },
    { value: data.co2e_avoided_kg, unit: "kg de CO₂e évités", note: "ordre de grandeur, voir hypothèses" },
  ];
  return (
    <dl className="grid gap-4 sm:grid-cols-3">
      {stats.map((s) => (
        <div key={s.unit} className="rounded-2xl bg-white p-6 shadow-card">
          <dt className="text-sm font-semibold text-oat-700">{s.unit}</dt>
          <dd className="mt-1 font-display text-4xl font-bold text-leaf-800">
            <CountUp value={s.value} />
          </dd>
          <p className="mt-1 text-sm text-oat-500">{s.note}</p>
        </div>
      ))}
    </dl>
  );
}
