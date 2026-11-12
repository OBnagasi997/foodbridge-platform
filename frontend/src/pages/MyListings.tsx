import { Link } from "react-router-dom";
import { ConfirmButton } from "../components/ConfirmButton";
import { ListingStatusBadge } from "../components/StatusBadge";
import { Button, ButtonLink, EmptyState } from "../components/ui";
import { UNIT_LABEL, dayLabel, formatQuantity, hm } from "../lib/format";
import { del, useAction, useMyListings } from "../lib/queries";

export default function MyListings() {
  const { data, isPending, isError, refetch } = useMyListings();
  const cancel = useAction((id: string) => del(`/listings/${id}`), { success: "Annonce retirée" });

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Mes annonces</h1>
          <p className="mt-1 text-oat-700">Suis ce qui est réservé et retire ce qui n'est plus disponible.</p>
        </div>
        <ButtonLink to="/app/new">Publier un surplus</ButtonLink>
      </div>
      <div className="mt-8 space-y-4" aria-live="polite">
        {isPending ? (
          [0, 1, 2].map((i) => <div key={i} className="skeleton h-28" />)
        ) : isError ? (
          <EmptyState title="Impossible de charger tes annonces" action={<Button onClick={() => refetch()}>Réessayer</Button>}>Réessaie dans un instant.</EmptyState>
        ) : data.length === 0 ? (
          <EmptyState title="Tu n'as encore rien publié" action={<ButtonLink to="/app/new">Publier mon premier surplus</ButtonLink>}>
            Une annonce prend deux minutes. Elle est visible immédiatement par les associations.
          </EmptyState>
        ) : (
          data.map((l) => {
            const pct = Math.min(100, (Number(l.quantity_claimed) / Number(l.quantity)) * 100);
            const open = l.status === "available" || l.status === "partially_claimed";
            return (
              <article key={l.id} className="rounded-2xl bg-white p-5 shadow-card">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <Link to={`/app/listings/${l.id}`} className="text-lg font-bold hover:underline">{l.title}</Link>
                    <p className="text-sm text-oat-700">{dayLabel(l.pickup_start)}, {hm(l.pickup_start)} à {hm(l.pickup_end)} · {l.location_text}</p>
                  </div>
                  <ListingStatusBadge status={l.status} />
                </div>
                <div className="mt-4">
                  <div className="h-2 overflow-hidden rounded-full bg-oat-200" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Quantité réservée">
                    <div className="h-full rounded-full bg-leaf-500 transition-all duration-500" style={{ width: `${pct}%` }} />
                  </div>
                  <p className="mt-1.5 text-sm text-oat-700">
                    {formatQuantity(l.quantity_claimed)} réservés sur {formatQuantity(l.quantity)} {UNIT_LABEL[l.unit]}
                  </p>
                </div>
                {open && (
                  <div className="mt-3 flex justify-end">
                    <ConfirmButton confirmLabel="Oui, retirer" loading={cancel.isPending} onConfirm={() => cancel.mutate(l.id)}>Retirer</ConfirmButton>
                  </div>
                )}
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}
