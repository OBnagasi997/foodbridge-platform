import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  api,
  ApiError,
  type Category,
  type Claim,
  type ImpactSummary,
  type Listing,
  type ListingPage,
} from "./api";

export const useImpact = (scope: "global" | "me" = "global") =>
  useQuery({
    queryKey: ["impact", scope],
    queryFn: () => api<ImpactSummary>(scope === "me" ? "/impact/me" : "/impact/summary"),
    staleTime: 30_000,
  });

export const useListings = (category: Category | undefined, q: string) =>
  useInfiniteQuery({
    queryKey: ["listings", "feed", category ?? "all", q],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ limit: "12" });
      if (category) params.set("category", category);
      if (q) params.set("q", q);
      if (pageParam) params.set("cursor", pageParam);
      return api<ListingPage>(`/listings?${params}`);
    },
    getNextPageParam: (last) => last.next_cursor,
    refetchInterval: 60_000,
  });

export const useListing = (id: string | undefined) =>
  useQuery({ queryKey: ["listings", "one", id], queryFn: () => api<Listing>(`/listings/${id}`), enabled: !!id });

export const useMyListings = () =>
  useQuery({ queryKey: ["listings", "mine"], queryFn: () => api<Listing[]>("/listings/mine") });

export const useMyClaims = () =>
  useQuery({ queryKey: ["claims", "mine"], queryFn: () => api<Claim[]>("/claims/me"), refetchInterval: 30_000 });

export const useReceivedClaims = () =>
  useQuery({
    queryKey: ["claims", "received"],
    queryFn: () => api<Claim[]>("/claims/received"),
    refetchInterval: 30_000,
  });

/** Mutation qui invalide les caches concernés et affiche une erreur lisible. */
export function useAction<TVars, TResult>(
  fn: (vars: TVars) => Promise<TResult>,
  options: { success?: string; onSuccess?: (r: TResult) => void } = {},
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: (result) => {
      void qc.invalidateQueries({ queryKey: ["listings"] });
      void qc.invalidateQueries({ queryKey: ["claims"] });
      void qc.invalidateQueries({ queryKey: ["impact"] });
      if (options.success) toast.success(options.success);
      options.onSuccess?.(result);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Une erreur est survenue"),
  });
}

export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const del = (path: string) => api<null>(path, { method: "DELETE" });
