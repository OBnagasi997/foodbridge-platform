/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Même contrat qu'en production : le navigateur appelle /api, jamais l'URL du backend.
    proxy: { "/api": "http://localhost:8000" },
  },
  test: { environment: "node", include: ["src/**/*.test.ts"] },
});
