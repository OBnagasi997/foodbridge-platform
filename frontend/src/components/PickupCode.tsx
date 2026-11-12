import { motion } from "framer-motion";

/** Code de retrait à 6 chiffres, révélé chiffre par chiffre. */
export function PickupCode({ code, label = "Présente ce code au retrait" }: { code: string; label?: string }) {
  return (
    <div className="rounded-2xl bg-leaf-50 p-4 text-center" role="status">
      <p className="text-sm font-semibold text-leaf-800">{label}</p>
      <p
        className="mt-2 flex justify-center gap-1.5 font-display text-3xl font-bold tabular-nums text-leaf-800"
        aria-label={`Code ${code.split("").join(" ")}`}
      >
        {code.split("").map((d, i) => (
          <motion.span
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 + i * 0.06, type: "spring", stiffness: 380, damping: 22 }}
            className="grid h-11 w-9 place-items-center rounded-lg bg-white shadow-sm"
          >
            {d}
          </motion.span>
        ))}
      </p>
    </div>
  );
}
