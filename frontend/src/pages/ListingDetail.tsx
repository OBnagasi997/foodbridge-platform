import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ConfirmButton } from "../components/ConfirmButton";
import { ContactActions } from "../components/ContactActions";
import { PickupCode } from "../components/PickupCode";
import { ListingStatusBadge } from "../components/StatusBadge";
import { Badge, Button, ButtonLink, EmptyState, Textarea } from "../components/ui";
import { ApiError, type Claim } from "../lib/api";
import {
  ALLERGEN_LABEL, CATEGORY_LABEL, STORAGE_LABEL, UNIT_LABEL, dayLabel, formatQuantity, hm, timeLeft,
} from "../lib/format";
import { del, post, useAction, useListing } from "../lib/queries";

function ReservePanel({ listingId, remaining, unit }: { listingId: string; remaining: number; unit: string }) {
  const step = unit === "kg" || unit === "litres" ? 0.5 : 1;
  const [qty, setQty] = useState(Math.min(step, remaining));
  const [notes, setNotes] = useState("");
  const [claim, setClaim] = useState<Claim | null>(null);
  const reserve = useAction(
    () => post<Claim>(`/listings/${listingId}/claim`, { quantity: qty.toFixed(2), notes: notes.trim() || undefined }),
    { success: "Réservation confirmée", onSuccess: setClaim },
  );

  if (claim?.pickup_code) {
    return (
      <div className="space-y-4">
        <PickupCode code={claim.pickup_code} />
        {claim.contact_phone && <ContactActions phone={claim.contact_phone} who={claim.provider_name} />}
        <p className="text-sm text-oat-700">
          Tu retrouves ce code à tout moment dans{" "}
          <Link to="/app/claims" className="font-semibold text-leaf-700 underline">Mes réservations</Link>.
          Ne le communique qu'au commerçant, sur place.
        </p>
      </div>
    );
  }
  const clamp = (n: number) => Math.max(step, Math.min(remaining, Math.round(n * 100) / 100));
  return (
    <div className="space-y-4">
      <div>
        <p className="mb-1.5 text-sm font-semibold text-leaf-800">Quantité à réserver</p>
        <div className="flex items-center gap-3">
          <Button variant="secondary" className="!px-4" aria-label="Diminuer" onClick={() => setQty(clamp(qty - step))} disabled={qty <= step}>−</Button>
          <span className="min-w-24 text-center font-display text-2xl font-bold tabular-nums">
            {formatQuantity(qty)} {UNIT_LABEL[unit]}
          </span>
          <Button variant="secondary" className="!px-4" aria-label="Augmenter" onClick={() => setQty(clamp(qty + step))} disabled={qty >= remaining}>+</Button>
          <Button variant="ghost" className="!px-3 !py-2 text-sm" onClick={() => setQty(remaining)}>Tout prendre</Button>
        </div>
      </div>
      <Textarea label="Message pour le commerçant (facultatif)" value={notes} maxLength={500} onChange={(e) => setNotes(e.target.value)} placeholder="Ex. : je passe avec un camion frigorifique" />
      <Button className="w-full" loading={reserve.isPending} onClick={() => reserve.mutate(undefined)}>
        Réserver {formatQuantity(qty)} {UNIT_LABEL[unit]}
      </Button>
      {reserve.error instanceof ApiError && reserve.error.status === 409 && (
        <p className="text-sm text-oat-700">Quelqu'un vient peut-être de réserver : la quantité disponible s'est mise à jour.</p>
      )}
    </div>
  );
}

export default function ListingDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { data: l, isPending, isError } = useListing(id);
  const cancel = useAction(() => del(`/listings/${id}`), {
    success: "Annonce retirée",
    onSuccess: () => navigate("/app/mine"),
  });

  if (isPending) return <div className="skeleton h-96" aria-busy="true" aria-label="Chargement" />;
  if (isError || !l)
    return (
      <EmptyState title="Annonce introuvable" action={<ButtonLink to="/app">Voir les surplus</ButtonLink>}>
        Elle a peut-être été retirée par le commerçant.
      </EmptyState>
    );

  const left = timeLeft(l.pickup_end);
  const remaining = Number(l.quantity_remaining);
  const open = (l.status === "available" || l.status === "partially_claimed") && left.label !== "Créneau terminé";
  const isOwner = user?.id === l.provider_id;

  return (
    <div className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
      <article>
        <Link to="/app" className="text-sm font-semibold text-leaf-700 underline">Retour aux surplus</Link>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge>{CATEGORY_LABEL[l.category]}</Badge>
          <Badge tone={left.urgent ? "honey" : "oat"}>{left.label}</Badge>
          {isOwner && <ListingStatusBadge status={l.status} />}
        </div>
        <h1 className="mt-3 text-3xl font-bold">{l.title}</h1>
        <p className="mt-1 text-oat-700">
          {l.provider_name}
          {l.provider_verified && <span className="ml-1.5 font-semibold text-leaf-700">· Organisation vérifiée</span>}
        </p>
        {l.description && <p className="mt-5 max-w-prose text-lg">{l.description}</p>}

        <dl className="mt-6 grid max-w-xl grid-cols-[auto_1fr] gap-x-8 gap-y-3 rounded-2xl bg-white p-6 shadow-card">
          <dt className="text-oat-500">Quantité</dt>
          <dd className="font-semibold">{formatQuantity(l.quantity_remaining)} disponibles sur {formatQuantity(l.quantity)} {UNIT_LABEL[l.unit]}</dd>
          <dt className="text-oat-500">Retrait</dt>
          <dd className="font-semibold">{dayLabel(l.pickup_start)}, de {hm(l.pickup_start)} à {hm(l.pickup_end)}</dd>
          <dt className="text-oat-500">Lieu</dt>
          <dd className="font-semibold">{l.location_text}</dd>
          <dt className="text-oat-500">Conservation</dt>
          <dd className="font-semibold">{STORAGE_LABEL[l.storage_condition]}</dd>
          <dt className="text-oat-500">{l.date_type === "dlc" ? "À consommer avant (DLC)" : "À consommer de préférence avant (DDM)"}</dt>
          <dd className="font-semibold">{dayLabel(l.expiry_at)} à {hm(l.expiry_at)}</dd>
          <dt className="text-oat-500">Allergènes</dt>
          <dd className="font-semibold">{l.allergens.length ? l.allergens.map((a) => ALLERGEN_LABEL[a] ?? a).join(", ") : "Aucun déclaré"}</dd>
        </dl>
        {l.date_type === "dlc" && (
          <p className="mt-4 max-w-xl text-sm text-oat-700">
            Cette denrée a une date limite de consommation : elle ne doit jamais être consommée après cette date.
          </p>
        )}
      </article>

      <aside className="h-fit rounded-3xl bg-white p-6 shadow-card lg:sticky lg:top-24">
        {isOwner ? (
          <div className="space-y-4">
            <h2 className="text-lg font-bold">Ton annonce</h2>
            <ButtonLink to="/app/pickups" variant="secondary" className="w-full">Voir les réservations</ButtonLink>
            {open && (
              <ConfirmButton confirmLabel="Oui, retirer l'annonce" loading={cancel.isPending} onConfirm={() => cancel.mutate(undefined)}>
                Retirer l'annonce
              </ConfirmButton>
            )}
          </div>
        ) : user?.role === "beneficiary" && open ? (
          <>
            <h2 className="mb-4 text-lg font-bold">Réserver</h2>
            <ReservePanel key={l.quantity_remaining} listingId={l.id} remaining={remaining} unit={l.unit} />
          </>
        ) : (
          <p className="text-oat-700">
            {open ? "Seuls les comptes bénéficiaires peuvent réserver." : "Cette annonce n'est plus disponible à la réservation."}
          </p>
        )}
      </aside>
    </div>
  );
}
