import { defineConfig } from "vite";

export default defineConfig({
  base: process.env.GITHUB_ACTIONS === "true"
    ? "/speech-to-speech-translation-and-transcription/"
    : "/",
  preview: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
