import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// El proxy lleva /api → la API de FastAPI (make api, puerto 8000).
// Si el 8000 está ocupado: API_URL=http://localhost:8001 npm run dev
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { "/api": { target: env.API_URL || "http://localhost:8000", changeOrigin: true } },
    },
  };
});
