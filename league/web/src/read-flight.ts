// Share only concurrent, non-critical reads. No TTL or persistent response cache.
const shareable = new Set(['gym.routines', 'gym.templates', 'gym.catalog', 'push.config']);
export function createReadFlights() {
 const pending = new Map<string, Promise<unknown>>();
 return {
  clear() { pending.clear(); },
  run<T>(scope: string, action: string, data: Record<string, unknown>, load: () => Promise<T>): Promise<T> {
   if (!shareable.has(action)) {
    pending.clear();
    return Promise.resolve().then(load).finally(() => pending.clear());
   }
   const key = JSON.stringify([scope, action, data]);
   const existing = pending.get(key);
   if (existing) return existing as Promise<T>;
   const request = Promise.resolve().then(load).finally(() => {
    // A cleared, older request must never evict its replacement.
    if (pending.get(key) === request) pending.delete(key);
   });
   pending.set(key, request);
   return request;
  },
 };
}
