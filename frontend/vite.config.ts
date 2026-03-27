import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
  },
  test: {
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
    },
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
  },
});
