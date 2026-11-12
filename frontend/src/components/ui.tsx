import { motion } from "framer-motion";
import { forwardRef, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";
import { Link, type LinkProps } from "react-router-dom";

const base =
  "inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-[15px] font-semibold " +
  "transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-60 select-none";

const variants = {
  primary: "bg-leaf-700 text-oat-50 hover:bg-leaf-800",
  secondary: "bg-leaf-100 text-leaf-800 hover:bg-leaf-200",
  ghost: "text-leaf-800 hover:bg-oat-200",
} as const;

type Variant = keyof typeof variants;

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`h-4 w-4 animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"> {
  variant?: Variant;
  loading?: boolean;
}

export function Button({ variant = "primary", loading, children, disabled, className = "", ...rest }: ButtonProps) {
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      transition={{ duration: 0.12 }}
      className={`${base} ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </motion.button>
  );
}

export function ButtonLink({ variant = "primary", className = "", ...rest }: LinkProps & { variant?: Variant }) {
  return <Link className={`${base} ${variants[variant]} ${className}`} {...rest} />;
}

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, hint, id, className = "", ...rest },
  ref,
) {
  const fieldId = id ?? rest.name ?? label;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-semibold text-leaf-800">
        {label}
      </label>
      <input
        ref={ref}
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={`w-full rounded-xl border bg-white px-4 py-3 text-[15px] outline-none transition-shadow placeholder:text-oat-500 focus:ring-2 focus:ring-leaf-500/40 ${
          error ? "border-danger-700" : "border-oat-300 focus:border-leaf-600"
        } ${className}`}
        {...rest}
      />
      {error ? (
        <p id={`${fieldId}-error`} role="alert" className="mt-1.5 text-sm text-danger-700">
          {error}
        </p>
      ) : hint ? (
        <p id={`${fieldId}-hint`} className="mt-1.5 text-sm text-oat-700">
          {hint}
        </p>
      ) : null}
    </div>
  );
});

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2.5 font-display text-xl font-bold tracking-tight ${className}`}>
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
        <rect width="32" height="32" rx="9" fill="#2f5d46" />
        <path d="M8 20c0-6 4-10 16-10 0 8-4 12-10 12-2 0-3-1-3-2z" fill="#d8e8c8" />
        <path d="M9 24c3-5 6-8 11-10" stroke="#2f5d46" strokeWidth="1.6" strokeLinecap="round" fill="none" />
      </svg>
      FoodBridge
    </span>
  );
}

export function Badge({ children, tone = "leaf" }: { children: ReactNode; tone?: "leaf" | "honey" | "oat" }) {
  const tones = {
    leaf: "bg-leaf-100 text-leaf-800",
    honey: "bg-honey-100 text-honey-700",
    oat: "bg-oat-100 text-oat-700",
  };
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}

export function EmptyState({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-16 text-center">
      <svg width="88" height="88" viewBox="0 0 88 88" fill="none" aria-hidden>
        <circle cx="44" cy="44" r="42" fill="#e1edd2" />
        <path d="M24 42h40l-4 20a4 4 0 0 1-4 3H32a4 4 0 0 1-4-3l-4-20z" fill="#fbf9f4" stroke="#2f5d46" strokeWidth="2.5" strokeLinejoin="round" />
        <path d="M32 42c0-9 5-15 12-15s12 6 12 15" stroke="#2f5d46" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M44 27c0-6 4-9 9-9-1 6-4 9-9 9z" fill="#5b8a4e" />
      </svg>
      <h2 className="mt-5 text-xl font-bold">{title}</h2>
      <p className="mt-2 text-oat-700">{children}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

const inputBase =
  "w-full rounded-xl border bg-white px-4 py-3 text-[15px] outline-none transition-shadow placeholder:text-oat-500 focus:ring-2 focus:ring-leaf-500/40";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, error, id, children, ...rest },
  ref,
) {
  const fieldId = id ?? rest.name ?? label;
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-semibold text-leaf-800">
        {label}
      </label>
      <select ref={ref} id={fieldId} className={`${inputBase} ${error ? "border-danger-700" : "border-oat-300"}`} {...rest}>
        {children}
      </select>
      {error && <p role="alert" className="mt-1.5 text-sm text-danger-700">{error}</p>}
    </div>
  );
});

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { label, error, id, ...rest },
  ref,
) {
  const fieldId = id ?? rest.name ?? label;
  return (
    <div>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-semibold text-leaf-800">
        {label}
      </label>
      <textarea ref={ref} id={fieldId} rows={3} className={`${inputBase} ${error ? "border-danger-700" : "border-oat-300"}`} {...rest} />
      {error && <p role="alert" className="mt-1.5 text-sm text-danger-700">{error}</p>}
    </div>
  );
});
