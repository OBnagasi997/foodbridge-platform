import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Badge, Button, ButtonLink } from "../components/ui";
import { ImpactStats } from "../components/ImpactStats";
import { PickupCode } from "../components/PickupCode";

/** Aperçu interactif : montre le geste de réservation et le code de retrait. Données fictives. */
function ReserveDemo() {
  const [state, setState] = useState<"idle" | "loading" | "done">("idle");

  const reserve = () => {
    setState("loading");
    window.setTimeout(() => setState("done"), 800);
  };

  return (
    <div className="rounded-3xl bg-white p-5 shadow-card sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-oat-700">Boulangerie Les Trois Épis</p>
          <h2 className="mt-0.5 text-xl font-bold">Pains et viennoiseries du soir</h2>
        </div>
        <Badge tone="honey">Plus que 42 min</Badge>
      </div>
      <p className="mt-3 text-sm text-oat-700">6 kg disponibles · À retirer entre 18 h 30 et 19 h · Ambiant · Contient du gluten</p>

      <div className="mt-5 min-h-[92px]">
        <AnimatePresence mode="wait" initial={false}>
          {state !== "done" ? (
            <motion.div key="action" exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.15 }}>
              <Button className="w-full" onClick={reserve} loading={state === "loading"}>
                {state === "loading" ? "Réservation en cours" : "Réserver 2 kg"}
              </Button>
              <p className="mt-2 text-center text-xs text-oat-500">Aperçu : exemple fictif</p>
            </motion.div>
          ) : (
            <motion.div key="done" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <PickupCode code="482913" label="Réservé. Présente ce code au retrait" />
              <button className="mt-3 block w-full text-center text-xs font-semibold text-leaf-700 underline" onClick={() => setState("idle")}>
                Rejouer l'aperçu
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

const steps = [
  { title: "Le commerçant publie", text: "Quantité, créneau de retrait, date limite (DLC ou DDM), conservation et allergènes. Deux minutes suffisent." },
  { title: "Une association réserve", text: "Les organisations vérifiées par un administrateur sont signalées par un badge. Plusieurs associations peuvent se partager un même lot." },
  { title: "Le retrait se valide par un code", text: "Le commerçant saisit le code à 6 chiffres remis au retrait. C'est ce geste qui fait compter le don." },
];


const audiences = [
  {
    title: "Pour les commerçants",
    lead: "Donner plutôt que jeter, sans paperasse.",
    points: [
      "Une annonce en deux minutes, avec des créneaux prêts à l'emploi",
      "Vous choisissez qui récupère, et quand",
      "Un retrait validé par code : une trace fiable de chaque don",
      "Vos chiffres d'impact personnels, retrait après retrait",
    ],
    cta: { to: "/register?role=provider", label: "Publier un surplus" },
  },
  {
    title: "Pour les associations",
    lead: "Des denrées de qualité, au bon moment.",
    points: [
      "Les surplus du quartier, triés par urgence",
      "Réservation partielle : prenez ce dont vous avez besoin, les autres se partagent le reste",
      "Allergènes, conservation et dates affichés avant de réserver",
      "Un code unique par réservation, rien à imprimer",
    ],
    cta: { to: "/register?role=beneficiary", label: "Voir les surplus" },
  },
];

const safety = [
  { title: "DLC et DDM distinguées", text: "Une date limite de consommation interdit tout retrait après son échéance. Une date de durabilité minimale reste informative." },
  { title: "14 allergènes déclarés", text: "La liste réglementaire européenne, visible avant chaque réservation." },
  { title: "Chaîne du froid indiquée", text: "Ambiant, réfrigéré ou surgelé : l'association sait ce qu'elle doit prévoir." },
];

const faq = [
  { q: "Combien ça coûte ?", a: "FoodBridge est un projet d'apprentissage : il n'y a ni abonnement ni commission." },
  { q: "Que devient une annonce que personne ne réserve ?", a: "Elle expire automatiquement à la fin du créneau de retrait et disparaît de la liste." },
  { q: "Comment est calculé l'impact ?", a: "Uniquement à partir des retraits confirmés par code. Les équivalences en repas et en CO₂e reposent sur des facteurs modifiables et documentés, ce sont des ordres de grandeur." },
  { q: "Et si quelqu'un ne se présente pas ?", a: "Le commerçant le signale une fois le créneau terminé. Après plusieurs absences, les réservations d'un compte sont suspendues." },
];

export default function Landing() {
  return (
    <>
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:pt-20">
        <div>
          <h1 className="text-4xl font-extrabold leading-[1.05] sm:text-6xl">
            Ce qui reste ce soir peut nourrir quelqu'un demain.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-oat-700">
            FoodBridge relie les commerçants aux associations vérifiées de leur quartier. Un surplus encore bon est
            publié, réservé et retiré avec un code, en quelques minutes.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/register?role=provider">Je donne mes surplus</ButtonLink>
            <ButtonLink to="/register?role=beneficiary" variant="secondary">
              Je cherche des denrées
            </ButtonLink>
          </div>
        </div>
        <ReserveDemo />
      </section>

      <section className="bg-oat-100 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-3xl font-bold">Comment ça marche</h2>
          <ol className="mt-8 grid gap-5 md:grid-cols-3">
            {steps.map((s, i) => (
              <li key={s.title} className="rounded-2xl bg-white p-6 shadow-card">
                <span className="grid h-9 w-9 place-items-center rounded-full bg-leaf-700 font-display font-bold text-oat-50" aria-hidden>
                  {i + 1}
                </span>
                <h3 className="mt-4 text-lg font-bold">{s.title}</h3>
                <p className="mt-2 text-oat-700">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>


      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 md:grid-cols-2">
          {audiences.map((a) => (
            <div key={a.title} className="flex flex-col rounded-3xl bg-leaf-900 p-8 text-oat-50">
              <h2 className="text-2xl font-bold">{a.title}</h2>
              <p className="mt-1 text-leaf-200">{a.lead}</p>
              <ul className="mt-5 space-y-2.5">
                {a.points.map((pt) => (
                  <li key={pt} className="flex gap-3">
                    <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-leaf-300" />
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
              <ButtonLink to={a.cta.to} variant="secondary" className="mt-8 self-start">{a.cta.label}</ButtonLink>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-oat-100 py-16">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <h2 className="text-3xl font-bold">La sécurité alimentaire d'abord</h2>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {safety.map((x) => (
              <div key={x.title} className="rounded-2xl bg-white p-6 shadow-card">
                <h3 className="text-lg font-bold">{x.title}</h3>
                <p className="mt-2 text-oat-700">{x.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 className="text-3xl font-bold">L'impact, compté honnêtement</h2>
        <p className="mt-2 max-w-2xl text-oat-700">
          Un don n'entre dans ces chiffres qu'une fois le retrait confirmé. Pas de projection, pas d'annonce comptée
          deux fois.
        </p>
        <div className="mt-8">
          <ImpactStats />
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 pb-20 sm:px-6">
        <h2 className="text-3xl font-bold">Questions fréquentes</h2>
        <div className="mt-6 divide-y divide-oat-200 rounded-2xl bg-white shadow-card">
          {faq.map((f) => (
            <details key={f.q} className="group px-6 py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                {f.q}
                <span aria-hidden className="text-xl text-leaf-700 transition-transform duration-200 group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-oat-700">{f.a}</p>
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
