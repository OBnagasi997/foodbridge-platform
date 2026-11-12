import { useAuth } from "../auth/AuthContext";
import { ImpactStats } from "../components/ImpactStats";

export default function Impact() {
  const { user } = useAuth();
  return (
    <div className="space-y-12">
      <section>
        <h1 className="text-3xl font-bold">Ton impact</h1>
        <p className="mt-1 max-w-2xl text-oat-700">
          {user?.role === "provider" ? "Ce que tes dons ont permis de sauver, retrait après retrait." : "Ce que tu as récupéré grâce à la plateforme."}
        </p>
        <div className="mt-6"><ImpactStats scope="me" /></div>
      </section>
      <section>
        <h2 className="text-2xl font-bold">Toute la plateforme</h2>
        <p className="mt-1 max-w-2xl text-oat-700">
          Un don n'entre dans ces chiffres qu'une fois le retrait confirmé par son code. Les équivalences (repas, CO₂e)
          reposent sur des facteurs modifiables en base, documentés dans le dépôt.
        </p>
        <div className="mt-6"><ImpactStats /></div>
      </section>
    </div>
  );
}
