import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: "prompt",
      manifest: {
        name: "AI-Based Symptom Checker",
        short_name: "Symptom Checker",
        description: "Informational symptom assessment, not a medical diagnosis.",
        theme_color: "#0f766e",
        background_color: "#ffffff",
        display: "standalone",
        start_url: "/",
        icons: [
          {
            src: "/icons/pwa-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "/icons/pwa-512.png",
            sizes: "512x512",
            type: "image/png",
          },
        ],
      },
workbox: {
  navigateFallback: null,
  globPatterns: ["**/*.{js,css,html,svg,png,ico,woff2}"],
  runtimeCaching: [
    {
      urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
      handler: "NetworkOnly",
    },
    {
      urlPattern: ({ request }) => request.mode === "navigate",
      handler: "NetworkFirst",
      options: {
        cacheName: "page-navigation",
        networkTimeoutSeconds: 3,
        expiration: {
          maxEntries: 10,
        },
        plugins: [
          {
            handlerDidError: async ({ request }) => {
  const cacheStorage = (
    globalThis as unknown as {
      caches: {
        match: (
          request: string,
          options?: { ignoreSearch?: boolean },
        ) => Promise<Response | undefined>;
      };
    }
  ).caches;

  const offlineUrl = new URL("/offline.html", request.url).href;

  return (
    (await cacheStorage.match(offlineUrl, {
      ignoreSearch: true,
    })) ?? Response.error()
  );
},
          },
        ],
      },
    },
  ],
},

    }),
  ],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
