import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    // dev only: forward API calls to the running compose stack
    proxy: { "/api": "http://127.0.0.1:8080" },
  },
  build: {
    rollupOptions: {
      output: {
        // vendor chunks change rarely and stay cached between deploys
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom", "@tanstack/react-query"],
          charts: ["recharts"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
