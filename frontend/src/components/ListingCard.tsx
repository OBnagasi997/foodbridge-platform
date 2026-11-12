import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import type { Listing } from "../lib/api";
import {
  ALLERGEN_LABEL,
  CATEGORY_LABEL,
  STORAGE_LABEL,
  UNIT_LABEL,
  formatQuantity,
  hm,
  timeLeft,
} from "../lib/format";
import { Badge } from "./ui";

export function ListingCard({
  listing,
  index = 0,
  preview = false,
}: {
  listing: Listing;
  index?: number;
  preview?: boolean;
}) {
  const left = timeLeft(listing.pickup_end);
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <Badge>{CATEGORY_LABEL[listing.category]}</Badge>
        <Badge tone={left.urgent ? "honey" : "oat"}>{left.label}</Badge>
      </div>
      <h3 className="mt-3 text-lg font-bold">{listing.title || "Titre de l'annonce"}</h3>
      <p className="mt-1 text-sm text-oat-700">
        {listing.provider_name}
        {listing.provider_verified && <span className="ml-1.5 font-semibold text-leaf-700">· Vérifié</span>}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm">
        <dt className="text-oat-500">Disponible</dt>
        <dd className="font-semibold">
          {formatQuantity(listing.quantity_remaining)} {UNIT_LABEL[listing.unit]}
        </dd>
        <dt className="text-oat-500">Retrait</dt>
        <dd className="font-semibold">
          {Number.isNaN(Date.parse(listing.pickup_start)) ? "À définir" : `${hm(listing.pickup_start)} à ${hm(listing.pickup_end)}`}
        </dd>
        <dt className="text-oat-500">Conservation</dt>
        <dd className="font-semibold">
          {STORAGE_LABEL[listing.storage_condition]} · {listing.date_type.toUpperCase()}
        </dd>
      </dl>
      {listing.allergens.length > 0 && (
        <p className="mt-3 text-sm text-oat-700">
          Allergènes : {listing.allergens.map((a) => ALLERGEN_LABEL[a] ?? a).join(", ")}
        </p>
      )}
      <p className="mt-auto pt-4 text-sm text-oat-500">{listing.location_text || "Lieu de retrait"}</p>
    </>
  );

  return (
    <motion.li
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index, 8) * 0.05, duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className="flex"
    >
      {preview ? (
        <div className="flex w-full flex-col rounded-2xl bg-white p-5 shadow-card">{body}</div>
      ) : (
        <Link
          to={`/app/listings/${listing.id}`}
          className="flex w-full flex-col rounded-2xl bg-white p-5 shadow-card transition-transform duration-200 hover:-translate-y-0.5"
        >
          {body}
        </Link>
      )}
    </motion.li>
  );
}
