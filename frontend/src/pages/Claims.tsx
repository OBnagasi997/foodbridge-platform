import { useState } from "react";
import { Link } from "react-router-dom";
import { ConfirmButton } from "../components/ConfirmButton";
import { ContactActions } from "../components/ContactActions";
import { PickupCode } from "../components/PickupCode";
import { ClaimStatusBadge } from "../components/StatusBadge";
import { Badge, Button, ButtonLink, EmptyState } from "../components/ui";
import type { Claim } from "../lib/api";
import { UNIT_LABEL, dayLabel, formatQuantity, hm } from "../lib/format";
import { post, useAction, useMyClaims, useReceivedClaims } from "../lib/queries";

/** Côté bénéficiaire : mes réservations et leur code de retrait. */
export function MyClaims() {
  const { data, isPending, isError, refetch } = useMyClaims();
  const cancel = useAction((id: string) => post<Claim>(`/claims/${id}/cancel`), { success: "Réservation annulée" });

  return (
    <div>
      <h1 className="text-3xl font-bold">Mes réservations</h1>
      <p className="mt-1 text-oat-700">Présente le code au commerçant au moment du retrait.</p>
      <div className="mt-8 space-y-4" aria-live="polite">
        {isPending ? (
          [0, 1].map((i) => <div key={i} className="skeleton h-40" />)
        ) : isError ? (
          <EmptyState title="Impossible de charger tes réservations" action={<Button onClick={() => refetch()}>Réessayer</Button>}>Réessaie dans un instant.</EmptyState>
        ) : data.length === 0 ? (
          <EmptyState title="Aucune réservation pour l'instant" action={<ButtonLink to="/app">Voir les surplus</ButtonLink>}>
            Dès que tu réserves un surplus, son code de retrait apparaît ici.
          </EmptyState>
        ) : (
          data.map((c) => (
            <article key={c.id} className="rounded-2xl bg-white p-5 shadow-card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <Link to={`/app/listings/${c.listing_id}`} className="text-lg font-bold hover:underline">{c.listing_title}</Link>
                  <p className="text-sm text-oat-700">{c.provider_name} · {c.location_text}</p>
                  <p className="text-sm text-oat-700">
                    {formatQuantity(c.quantity_claimed)} {UNIT_LABEL[c.unit]} · {dayLabel(c.pickup_start)}, {hm(c.pickup_start)} à {hm(c.pickup_end)}
                  </p>
                </div>
                <ClaimStatusBadge status={c.status} />
              </div>
              {c.pickup_code && (
                <div className="mt-4">
                  <PickupCode code={c.pickup_code} />
                  {c.contact_phone && (
                    <div className="mt-3"><ContactActions phone={c.contact_phone} who={c.provider_name} /></div>
                  )}
                  <div className="mt-2 flex justify-end">
                    <ConfirmButton confirmLabel="Oui, annuler" loading={cancel.isPending} onConfirm={() => cancel.mutate(c.id)}>
                      Annuler la réservation
                    </ConfirmButton>
                  </div>
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </div>
  );
}

function PickupRow({ claim }: { claim: Claim }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const ended = new Date(claim.pickup_end).getTime() <= Date.now();
  const pickup = useAction(() => post<Claim>(`/claims/${claim.id}/pickup`, { code }), {
    success: "Retrait validé. Merci pour ce don",
  });
  const noShow = useAction(() => post<Claim>(`/claims/${claim.id}/no-show`), { success: "Marqué comme non présenté" });
  const cancel = useAction(() => post<Claim>(`/claims/${claim.id}/cancel`), { success: "Réservation annulée" });

  const submit = () => {
    if (!/^\d{6}$/.test(code)) return setError("Le code comporte 6 chiffres");
    setError(null);
    pickup.mutate(undefined, { onError: () => setError("Code incorrect. Demande-le à la personne présente.") });
  };

  return (
    <article className="rounded-2xl bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-lg font-bold">{claim.listing_title}</p>
          <p className="text-sm text-oat-700">
            {claim.beneficiary_name}
            {claim.beneficiary_verified && <span className="ml-1.5 font-semibold text-leaf-700">· Vérifié</span>} ·{" "}
            {formatQuantity(claim.quantity_claimed)} {UNIT_LABEL[claim.unit]}
          </p>
          <p className="text-sm text-oat-500">{dayLabel(claim.pickup_start)}, {hm(claim.pickup_start)} à {hm(claim.pickup_end)}</p>
          {claim.notes && <p className="mt-2 text-sm italic text-oat-700">« {claim.notes} »</p>}
        </div>
        <ClaimStatusBadge status={claim.status} />
      </div>

      {claim.status === "confirmed" && (
        <div className="mt-4 space-y-3 rounded-2xl bg-oat-100 p-4">
          {claim.contact_phone && <ContactActions phone={claim.contact_phone} who={claim.beneficiary_name} />}
          <label htmlFor={`code-${claim.id}`} className="block text-sm font-semibold text-leaf-800">
            Code remis par la personne qui retire
          </label>
          <div className="flex flex-wrap gap-2">
            <input
              id={`code-${claim.id}`} inputMode="numeric" autoComplete="off" maxLength={6} value={code} placeholder="000000"
              onChange={(e) => { setCode(e.target.value.replace(/\D/g, "")); setError(null); }}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              aria-invalid={error ? true : undefined}
              className="w-36 rounded-xl border border-oat-300 bg-white px-4 py-3 text-center font-display text-xl tracking-[0.3em] tabular-nums outline-none focus:border-leaf-600 focus:ring-2 focus:ring-leaf-500/40"
            />
            <Button onClick={submit} loading={pickup.isPending}>Valider le retrait</Button>
          </div>
          {error && <p role="alert" className="text-sm text-danger-700">{error}</p>}
          <div className="flex flex-wrap justify-end gap-1">
            {ended && (
              <ConfirmButton confirmLabel="Oui, non présenté" loading={noShow.isPending} onConfirm={() => noShow.mutate(undefined)}>
                Non présenté
              </ConfirmButton>
            )}
            <ConfirmButton confirmLabel="Oui, annuler" loading={cancel.isPending} onConfirm={() => cancel.mutate(undefined)}>
              Annuler
            </ConfirmButton>
          </div>
        </div>
      )}
    </article>
  );
}

/** Côté commerçant : valider les retraits avec le code. */
export function ProviderPickups() {
  const { data, isPending, isError, refetch } = useReceivedClaims();
  const [tab, setTab] = useState<"todo" | "history">("todo");
  const todo = data?.filter((c) => c.status === "confirmed") ?? [];
  const history = data?.filter((c) => c.status !== "confirmed") ?? [];
  const shown = tab === "todo" ? todo : history;

  return (
    <div>
      <h1 className="text-3xl font-bold">Retraits</h1>
      <p className="mt-1 text-oat-700">Saisis le code que la personne te présente : le don n'est compté qu'à cet instant.</p>
      <div className="mt-6 flex gap-2" role="tablist">
        {([["todo", `À retirer${data ? ` (${todo.length})` : ""}`], ["history", "Historique"]] as const).map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${tab === k ? "bg-leaf-700 text-oat-50" : "bg-white text-oat-700 shadow-card"}`}>
            {label}
          </button>
        ))}
        {data && todo.length > 0 && <Badge tone="honey">{todo.length} en attente</Badge>}
      </div>
      <div className="mt-6 space-y-4" aria-live="polite">
        {isPending ? (
          [0, 1].map((i) => <div key={i} className="skeleton h-36" />)
        ) : isError ? (
          <EmptyState title="Impossible de charger les retraits" action={<Button onClick={() => refetch()}>Réessayer</Button>}>Réessaie dans un instant.</EmptyState>
        ) : shown.length === 0 ? (
          <EmptyState title={tab === "todo" ? "Aucun retrait en attente" : "Pas encore d'historique"}>
            {tab === "todo" ? "Les réservations de tes annonces apparaîtront ici dès qu'une association réserve." : "Les retraits validés ou annulés s'afficheront ici."}
          </EmptyState>
        ) : (
          shown.map((c) => <PickupRow key={c.id} claim={c} />)
        )}
      </div>
    </div>
  );
}
