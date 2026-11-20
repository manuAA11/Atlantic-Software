// Atlantic League public static hosting. Authentication remains in Supabase.
// Immutable reviewed release; no visitor cookies, query values or tokens go upstream.
const RELEASE = 'c34b75ee6f12ab65debeca82a915a24fc0695819';
const BASE = 'https://raw.githubusercontent.com/manuAA11/Atlantic-Software/' + RELEASE + '/league/deploy/cloudflare-assets/';
const FILES = {
  '/index.html': ['index.html', 'text/html; charset=utf-8', 'no-cache'],
  '/sw.js': ['sw.js', 'application/javascript; charset=utf-8', 'no-cache'],
  '/manifest.webmanifest': ['manifest.webmanifest', 'application/manifest+json; charset=utf-8', 'no-cache'],
  '/assets/index-CUFRTh-G.js': ['assets/index-CUFRTh-G.js', 'application/javascript; charset=utf-8', 'public, max-age=31536000, immutable'],
  '/assets/index-BeyvP6vF.css': ['assets/index-BeyvP6vF.css', 'text/css; charset=utf-8', 'public, max-age=31536000, immutable'],
  '/icons/icon-192.png': ['icons/icon-192.png', 'image/png', 'public, max-age=86400'],
  '/icons/icon-512.png': ['icons/icon-512.png', 'image/png', 'public, max-age=86400']
};
export default {
  async fetch(request) {
    if (!['GET', 'HEAD'].includes(request.method)) {
      return new Response('Metodo no permitido.', {status: 405, headers: {'Allow': 'GET, HEAD', 'Cache-Control': 'no-store'}});
    }
    const url = new URL(request.url);
    const navigation = (request.headers.get('Accept') || '').includes('text/html') || request.headers.get('Sec-Fetch-Mode') === 'navigate';
    const file = FILES[url.pathname === '/' ? '/index.html' : url.pathname] || (navigation ? FILES['/index.html'] : null);
    if (!file) return new Response('No encontrado.', {status: 404, headers: {'Cache-Control': 'no-store'}});
    try {
      const asset = await fetch(BASE + file[0], {cf: {cacheEverything: true, cacheTtlByStatus: {'200-299': 86400, '300-599': -1}}});
      if (asset.status !== 200) throw new Error('Static asset unavailable');
      const headers = {'Content-Type': file[1], 'Cache-Control': file[2], 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Vary': 'Accept'};
      if (file[0] === 'sw.js') headers['Service-Worker-Allowed'] = '/';
      return new Response(request.method === 'HEAD' ? null : asset.body, {status: 200, headers});
    } catch {
      return new Response('Atlantic League no esta disponible en este momento. Vuelve a intentarlo.', {status: 503, headers: {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store', 'Retry-After': '30'}});
    }
  }
};
