const CACHE_NAME = "psx-shell-v2";
const SHELL_URLS = ["/", "/screener", "/watchlist"];

function shouldBypassCache(url) {
  return (
    url.pathname.startsWith("/_next/") ||
    url.pathname.startsWith("/api/") ||
    url.pathname.endsWith(".hot-update.json") ||
    url.pathname.endsWith(".hot-update.js")
  );
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_URLS).catch(() => undefined))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) return;

  // Never cache Next.js build assets — stale chunks break webpack module loading.
  if (shouldBypassCache(url)) return;

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.match(event.request).then((cached) => cached ?? caches.match("/"))
      )
    );
    return;
  }

  // Network-first for other same-origin assets (icons, manifest, etc.).
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "PSX Intelligence", body: "You have a new notification." };
  try {
    if (event.data) payload = event.data.json();
  } catch {
    /* use default payload */
  }

  event.waitUntil(
    self.registration.showNotification(payload.title ?? "PSX Intelligence", {
      body: payload.body ?? "",
      icon: "/globe.svg",
      badge: "/globe.svg",
      data: payload.data ?? {},
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url ?? "/";
  event.waitUntil(clients.openWindow(url));
});
