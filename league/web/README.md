# Atlantic League: member PWA

Standalone React / TypeScript / Vite application. No Expo or React Native dependency.
This is a tested development increment, not a completed or deployed MVP.

## Run locally

From `league/web`:

```sh
npm ci --workspaces=false
npm test
npm run build
npm run dev
```

Copy `.env.example` to `.env.local` and configure only public keys/URLs for an isolated QA project.
Built static files are in `dist/`; the service worker is generated after the Vite build.
Serve using HTTPS, with SPA fallback to `/index.html`, and do not cache `sw.js` permanently.
The existing approved Atlantic icon is reused at 192 and 512 pixels.

## Latest access decision

The login page has **Cédula** and **Contraseña**. The member enters the document in both fields.
There is no registration screen, email prompt, OTP, confirmation message or verification step.
The existing source profile provisioning prepares eligible registered clients. The access broker
automatically prepares/reuses a dedicated member Auth identity on first access, without a user
creation step. Passwords of shared Gym/Core staff identities are never reset to a document.
Internal Auth credentials use a private HMAC derivation; no raw document/password is stored
by the broker. Nevertheless, the requested public credential remains predictable: anyone
knowing the member's document can sign in. Rate limits do not remove that limitation.

The new broker and SQL are not deployed. New registrations become eligible automatically
only in gyms enabled by the existing League settings. The current pilot allowlist remains
effective; this increment does not enable every existing client in production.

## Services and source contracts

| Feature | Implementation | Remaining dependency |
| --- | --- | --- |
| Existing-member access | `../backend/member-access.mjs`, dedicated Auth identity, durable attempt limit, automatic link | Apply/review QA SQL and deploy access function; configure public access gym/URL |
| Membership | Existing gateway fallback; new sanitized server projection for plan/start/end/status/days | Deploy new member endpoint and validate source snapshot in QA |
| Renewals | Persisted requests, cancellation, history, active-period uniqueness, retry handling | QA schema/function activation; administrative review integration |
| Classes | Existing authorized calendar/reserve/cancel endpoints | Real account and concurrent PostgreSQL/Safari acceptance |
| Events and history | Search/date filtering of existing upcoming calendar | Backend does not currently expose independent events or past reservations |
| Routines | Original source files and routine contracts unchanged; integrated read-only member view | Current routine/source data preserved; physical mobile acceptance remains |
| Notifications | Persisted renewal notices and read state | Source reconciliation implemented; hosted acceptance remains |
| Push | Opt-in subscription registration/removal, generic private lock-screen content | Dispatcher, VAPID bootstrap, invalid-subscription cleanup and private cron implemented; device acceptance remains |
| Install/offline/update | Manifest, original icons, static-only cache, explicit update activation | Physical iPhone/Android installation and reopen acceptance |

No payment gateway, XP, ranking, feed or competition was added.

## QA backend setup

Review `../member/sql/schema.sql`, followed by `../member/sql/access.sql`. These are SQL drafts,
not applied migrations. Generate final migration files using the installed Supabase CLI after
local validation; hosted changes require authorization. The current member adapter requires
the shared Gym/League database; it does not assume remote providers share private tables.

New functions:

- `atlantic-league-members`: authenticated member requests; reuses legacy entitlement and link checks.
- `atlantic-league-member-access`: document/password broker; only dedicated member identities.

Server-only environment: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`,
`LEAGUE_MEMBER_ACCESS_PEPPER` (at least 32 random characters), `LEAGUE_WEB_ORIGINS`, and the
existing League/Core runtime settings (`LEAGUE_SHARED_PROJECT=true`). Never expose the pepper
or server key through Vite variables. Keep the pepper stable; rotate only with a reviewed identity
migration plan. Do not disable signup confirmation globally to enable this broker.

Eligible registered members receive dedicated member Auth identities internally, without
registration or verification screens. Legacy links are preserved. The service resolves the
new identity to the same canonical source profile; existing accounts and assigned routines
are not transferred or deleted. Private source queries revalidate Core entitlement.

SQL install order: `schema.sql`, `access.sql`, `content.sql`, `notifications.sql`,
`settings.sql`, `activity.sql`. They create League-owned tables/functions; no source
client, membership, payment or routine schema is changed. `settings.sql` generates private
server keys inside the database, so no administrative credential is bundled in the PWA.
Deploy member access, member API and member jobs functions after applying the reviewed SQL.
The jobs function initializes the VAPID key pair atomically and records its project URL.
`install-schedule.sql` then registers a five-minute cron job using the private stored key.

The initial rollout retains the existing source pilot allowlist. Existing/new clients
outside it are not enabled until the gym is explicitly opened for a wider pilot.

## Verification

2026-11-16: clean `npm ci --offline --ignore-scripts --workspaces=false` succeeded; TypeScript
and Vite build passed. Fourteen Node test groups cover the access broker, local PGlite SQL,
ownership/revocation, duplicate renewals, unchanged membership/payment fixture, CORS/auth
failures, push endpoint validation and private-request cache exclusions. Access SQL was exercised
in PGlite for automatic activation for new member identities, repeated activation, preservation of legacy links/source profile, rate limits
and identity mismatch rejection. These tests do not prove hosted Auth delivery or two-connection
PostgreSQL concurrency. Initial login rendering was inspected in desktop Safari; the final
document/password form still needs physical mobile acceptance. No production schema, hosted
function or published site was changed.
