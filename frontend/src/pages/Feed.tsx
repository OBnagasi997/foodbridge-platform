import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { ListingCard } from "../components/ListingCard";
import { Button, ButtonLink, EmptyState } from "../components/ui";
import type { Category } from "../lib/api";
import { CATEGORY_LABEL } from "../lib/format";
import { useListings } from "../lib/queries";

function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

export default function Feed() {
  const { user } = useAuth();
  const [category, setCategory] = useState<Category | undefined>();
  const [query, setQuery] = useState("");
  const q = useDebounced(query.trim());
  const { data, isPending, isError, refetch, isFetching, hasNextPage, fetchNextPage, isFetchingNextPage } =
    useListings(category, q);
  const items = data?.pages.flatMap((p) => p.items) ?? [];

  const chip = (active: boolean) =>
    `rounded-full px-3.5 py-1.5 text-sm font-semibold transition-colors ${
      active ? "bg-leaf-700 text-oat-50" : "bg-white text-oat-700 shadow-card hover:bg-leaf-50"
    }`;

  return (
    <div>
      <h1 className="text-3xl font-bold">Surplus disponibles</h1>
      <p className="mt-1 text-oat-700">
        {user?.role === "provider" ? "Voici ce qui est publié autour de toi." : "Réserve avant la fin du créneau de retrait."}
      </p>

      <div className="mt-6 flex flex-col gap-4">
        <label className="sr-only" htmlFor="search">Rechercher une annonce</label>
        <input
          id="search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher un produit"
          className="w-full max-w-md rounded-xl border border-oat-300 bg-white px-4 py-3 outline-none placeholder:text-oat-500 focus:border-leaf-600 focus:ring-2 focus:ring-leaf-500/40"
        />
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrer par catégorie">
          <button className={chip(!category)} aria-pressed={!category} onClick={() => setCategory(undefined)}>Tout</button>
          {(Object.keys(CATEGORY_LABEL) as Category[]).map((c) => (
            <button key={c} className={chip(category === c)} aria-pressed={category === c} onClick={() => setCategory(c)}>
              {CATEGORY_LABEL[c]}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8" aria-live="polite">
        {isPending ? (
          <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Chargement des annonces">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <li key={i} className="rounded-2xl bg-white p-5 shadow-card">
                <div className="skeleton h-6 w-1/2" />
                <div className="skeleton mt-4 h-6 w-3/4" />
                <div className="skeleton mt-3 h-4 w-1/3" />
                <div className="skeleton mt-6 h-20 w-full" />
              </li>
            ))}
          </ul>
        ) : isError ? (
          <EmptyState title="Impossible de charger les annonces" action={<Button onClick={() => refetch()} loading={isFetching}>Réessayer</Button>}>
            Le serveur ne répond pas pour le moment. Tes données ne sont pas perdues.
          </EmptyState>
        ) : items.length === 0 ? (
          q || category ? (
            <EmptyState
              title="Aucun résultat"
              action={<Button variant="secondary" onClick={() => { setQuery(""); setCategory(undefined); }}>Effacer les filtres</Button>}
            >
              Aucune annonce ne correspond à ta recherche.
            </EmptyState>
          ) : user?.role === "provider" ? (
            <EmptyState title="Aucune annonce publiée pour l'instant" action={<ButtonLink to="/app/new">Publier un surplus</ButtonLink>}>
              Publie ton premier surplus en deux minutes : les associations du quartier le verront immédiatement.
            </EmptyState>
          ) : (
            <EmptyState title="Rien à récupérer pour l'instant">
              Les commerçants publient surtout en fin de journée. Repasse en fin d'après-midi : la liste se met à jour toute seule.
            </EmptyState>
          )
        ) : (
          <>
            <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((l, i) => (
                <ListingCard key={l.id} listing={l} index={i} />
              ))}
            </ul>
            {hasNextPage && (
              <div className="mt-8 text-center">
                <Button variant="secondary" onClick={() => fetchNextPage()} loading={isFetchingNextPage}>
                  Voir plus d'annonces
                </Button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
