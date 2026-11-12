import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../auth/AuthContext";
import { Button, Field } from "../components/ui";
import { ApiError } from "../lib/api";
import { loginSchema, registerSchema, type LoginValues, type RegisterValues } from "../lib/schemas";

function Shell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <div className="mx-auto grid max-w-md px-4 py-12 sm:py-16">
      <h1 className="text-3xl font-bold">{title}</h1>
      <p className="mt-2 text-oat-700">{subtitle}</p>
      <div className="mt-8 rounded-3xl bg-white p-6 shadow-card sm:p-8">{children}</div>
    </div>
  );
}

export function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/app";
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema), mode: "onTouched" });

  if (user) return <Navigate to="/app" replace />;

  const onSubmit = handleSubmit(async (v) => {
    try {
      const me = await login(v.email, v.password);
      toast.success(`Bon retour, ${me.full_name.split(" ")[0]}`);
      navigate(from, { replace: true });
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Connexion impossible";
      setError("root", { message: msg });
    }
  });

  return (
    <Shell title="Se connecter" subtitle="Retrouve les surplus de ton quartier.">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <Field label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <Field
          label="Mot de passe"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register("password")}
        />
        {errors.root && (
          <p role="alert" className="rounded-xl bg-danger-100 px-4 py-3 text-sm text-danger-700">
            {errors.root.message}
          </p>
        )}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Se connecter
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-oat-700">
        Pas encore de compte ?{" "}
        <Link className="font-semibold text-leaf-700 underline" to="/register">
          Créer un compte
        </Link>
      </p>
    </Shell>
  );
}

const roleOptions = [
  { value: "provider", title: "Commerçant", text: "Je publie des surplus" },
  { value: "beneficiary", title: "Association ou particulier", text: "Je réserve des denrées" },
] as const;

export function Register() {
  const { user, register: signUp } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const initialRole = params.get("role") === "provider" ? "provider" : "beneficiary";

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    mode: "onChange",
    defaultValues: { role: initialRole },
  });
  const role = watch("role");

  if (user) return <Navigate to="/app" replace />;

  const onSubmit = handleSubmit(async (v) => {
    try {
      await signUp(v);
      toast.success("Compte créé. Bienvenue sur FoodBridge");
      navigate("/app", { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError("email", { message: "Un compte existe déjà avec cet email" });
      } else {
        setError("root", { message: e instanceof ApiError ? e.message : "Création impossible" });
      }
    }
  });

  return (
    <Shell title="Créer un compte" subtitle="Moins d'une minute, sans carte bancaire.">
      <form onSubmit={onSubmit} className="space-y-5" noValidate>
        <fieldset>
          <legend className="mb-1.5 text-sm font-semibold text-leaf-800">Tu es</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {roleOptions.map((o) => (
              <label key={o.value} className="cursor-pointer">
                <input type="radio" value={o.value} className="peer sr-only" {...register("role")} />
                <span className="block rounded-xl border border-oat-300 p-3.5 transition-colors peer-checked:border-leaf-700 peer-checked:bg-leaf-50 peer-focus-visible:ring-2 peer-focus-visible:ring-leaf-500">
                  <span className="block font-semibold">{o.title}</span>
                  <span className="block text-sm text-oat-700">{o.text}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <Field label="Nom complet" autoComplete="name" error={errors.full_name?.message} {...register("full_name")} />
        <AnimatePresence initial={false}>
          {role === "provider" && (
            <motion.div
              key="org"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="p-0.5">
                <Field
                  label="Nom du commerce"
                  autoComplete="organization"
                  error={errors.organization_name?.message}
                  {...register("organization_name")}
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <Field
          label="Téléphone"
          type="tel"
          autoComplete="tel"
          placeholder="06 12 34 56 78 ou +221 77 123 45 67"
          hint="Visible uniquement de l'autre partie d'une réservation en cours, jamais publiquement."
          error={errors.phone?.message}
          {...register("phone")}
        />
        <Field label="Email" type="email" autoComplete="email" error={errors.email?.message} {...register("email")} />
        <Field
          label="Mot de passe"
          type="password"
          autoComplete="new-password"
          hint="10 caractères minimum"
          error={errors.password?.message}
          {...register("password")}
        />
        {errors.root && (
          <p role="alert" className="rounded-xl bg-danger-100 px-4 py-3 text-sm text-danger-700">
            {errors.root.message}
          </p>
        )}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Créer mon compte
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-oat-700">
        Déjà inscrit ?{" "}
        <Link className="font-semibold text-leaf-700 underline" to="/login">
          Se connecter
        </Link>
      </p>
    </Shell>
  );
}
