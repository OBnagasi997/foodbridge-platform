import { AnimatePresence, motion } from "framer-motion";
import { Suspense } from "react";
import { NavLink, Navigate, Outlet, useLocation, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { PhoneBanner } from "./PhoneBanner";
import { Button, ButtonLink, Logo } from "./ui";

export function PageTransition({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation();
  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      >
        <Suspense fallback={<div className="skeleton mx-auto mt-16 h-10 w-48" role="status" aria-label="Chargement" />}>
          {children}
        </Suspense>
      </motion.div>
    </AnimatePresence>
  );
}

export function PublicLayout() {
  const { user } = useAuth();
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b border-oat-200/80 bg-oat-50/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <Link to="/" aria-label="FoodBridge, accueil">
            <Logo />
          </Link>
          <nav className="flex items-center gap-1.5">
            {user ? (
              <ButtonLink to="/app" variant="secondary" className="!py-2">
                Ouvrir l'application
              </ButtonLink>
            ) : (
              <>
                <ButtonLink to="/login" variant="ghost" className="!py-2">
                  Se connecter
                </ButtonLink>
                <ButtonLink to="/register" className="!py-2">
                  Créer un compte
                </ButtonLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>
      <footer className="border-t border-oat-200 py-8 text-sm text-oat-700">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          FoodBridge · Projet d'apprentissage DevOps. Les chiffres d'impact reposent sur des hypothèses documentées.
        </div>
      </footer>
    </div>
  );
}

const tabsFor = (role: string) =>
  role === "provider"
    ? [
        { to: "/app", label: "Surplus", end: true },
        { to: "/app/new", label: "Publier", end: false },
        { to: "/app/mine", label: "Mes annonces", end: false },
        { to: "/app/pickups", label: "Retraits", end: false },
        { to: "/app/impact", label: "Impact", end: false },
      ]
    : role === "beneficiary"
      ? [
          { to: "/app", label: "Surplus", end: true },
          { to: "/app/claims", label: "Réservations", end: false },
          { to: "/app/impact", label: "Impact", end: false },
        ]
      : [
          { to: "/app", label: "Surplus", end: true },
          { to: "/app/impact", label: "Impact", end: false },
        ];

export function AppLayout() {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="grid min-h-dvh place-items-center" role="status" aria-label="Chargement">
        <div className="skeleton h-10 w-40" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  const tabs = tabsFor(user.role);
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-[15px] font-semibold transition-colors ${
      isActive ? "bg-leaf-100 text-leaf-800" : "text-oat-700 hover:bg-oat-200"
    }`;

  return (
    <div className="min-h-dvh pb-20 sm:pb-0">
      <header className="sticky top-0 z-30 border-b border-oat-200/80 bg-oat-50/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/app" aria-label="FoodBridge, surplus">
            <Logo />
          </Link>
          <nav className="hidden items-center gap-1 sm:flex" aria-label="Navigation principale">
            {tabs.map((t) => (
              <NavLink key={t.to} to={t.to} end={t.end} className={linkClass}>
                {t.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-oat-700 md:block">{user.organization_name ?? user.full_name}</span>
            <Button variant="ghost" className="!px-3 !py-2" onClick={logout}>
              Se déconnecter
            </Button>
          </div>
        </div>
      </header>
      <PhoneBanner />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>
      <nav
        className="fixed inset-x-0 bottom-0 z-30 flex border-t border-oat-200 bg-oat-50/95 backdrop-blur sm:hidden"
        aria-label="Navigation principale"
      >
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `flex-1 py-4 text-center text-xs font-semibold ${isActive ? "text-leaf-700" : "text-oat-500"}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
