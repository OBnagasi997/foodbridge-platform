import type { ClaimStatus, ListingStatus } from "../lib/api";
import { CLAIM_STATUS_LABEL, LISTING_STATUS_LABEL } from "../lib/format";
import { Badge } from "./ui";

const tone = (s: string): "leaf" | "honey" | "oat" =>
  ["available", "partially_claimed", "confirmed", "picked_up"].includes(s)
    ? "leaf"
    : ["fully_claimed", "pending"].includes(s)
      ? "honey"
      : "oat";

export const ListingStatusBadge = ({ status }: { status: ListingStatus }) => (
  <Badge tone={tone(status)}>{LISTING_STATUS_LABEL[status]}</Badge>
);

export const ClaimStatusBadge = ({ status }: { status: ClaimStatus }) => (
  <Badge tone={tone(status)}>{CLAIM_STATUS_LABEL[status]}</Badge>
);
