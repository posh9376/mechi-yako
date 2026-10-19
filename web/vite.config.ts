import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Fixture mode imports ../data/*.json directly, so the dev server must read the repo root.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    fs: { allow: [".."] },
  },
});
