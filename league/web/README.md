# Atlantic League: member PWA

Standalone React / TypeScript / Vite application. No Expo or React Native dependency.
Published at **https://atlantic-league.atlanticsoftware11.workers.dev/** for the existing owner pilot.
The hosting link is public; the existing server-side pilot allowlist remains in force.
See the current deployment evidence below; physical device and real-member acceptance are pending.

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

The member broker, schema and member services are deployed for the existing pilot. New registrations become eligible automatically
only in gyms enabled by the existing League settings. The current pilot allowlist remains
effective; this increment does not enable every existing client in production.

## Services and source contracts

| Feature | Implementation | Remaining dependency |
| --- | --- | --- |
| Existing-member access | `../backend/member-access.mjs`, dedicated Auth identity, durable attempt limit, automatic link | Deployed; real-member HTTP login acceptance pending |
| Membership | Existing gateway fallback; new sanitized server projection for plan/start/end/status/days | Deployed; owner source snapshot verified without modifying the source data |
| Renewals | Persisted requests, cancellation, history, active-period uniqueness, retry handling | Schema/function deployed; administrative review integration and real-member acceptance pending |
| Classes | Existing authorized calendar/reserve/cancel endpoints | Real account and concurrent PostgreSQL/Safari acceptance |
| Events and history | Search/date filtering of existing upcoming calendar | Backend does not currently expose independent events or past reservations |
| Routines | Original source files and routine contracts unchanged; integrated read-only member view | Current routine/source data preserved; physical mobile acceptance remains |
| Notifications | Persisted renewal notices and read state | Reconciliation and jobs deployed; real-device acceptance remains |
| Push | Opt-in subscription registration/removal, generic private lock-screen content | Dispatcher, VAPID bootstrap, invalid-subscription cleanup and private cron implemented; device acceptance remains |
| Install/offline/update | Manifest, original icons, static-only cache, explicit update activation | Physical iPhone/Android installation and reopen acceptance |

No payment gateway, XP, ranking, feed or competition was added.

## QA backend setup

Review the source SQL in `../member/sql/schema.sql`, followed by `../member/sql/access.sql`.
The existing pilot schema has already been applied; do not reapply SQL merely to publish the PWA.
For other environments, generate and review migrations using the installed Supabase CLI after
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


## Installation-first mobile entry

See [INSTALLATION_QA.md](INSTALLATION_QA.md) for the new mobile welcome screen, standalone
boundary, browser-specific guidance, essential-auth exemptions and verification matrix.
The latest suite has 28 passing groups; the physical mobile acceptance column remains pending.
The installation entry is published on Cloudflare. Desktop web access stays available.

## Hosted service evidence — 2026-11-19

The member schema and isolated access/member/job functions were deployed for the existing
ZTATTUZ owner pilot. Core directory authorization returned enabled for the current provider.
The owner source check ran in a rolled-back transaction: the real account has no assigned plan
and two routines; the calendar is empty. Empty membership dates are normalized to null by the
League projection. No plan, payment or membership was created to fill that empty state.
The job schedule is active every five minutes. No additional mobile identities were activated.
Anonymous member access was rejected with 401 and a foreign origin with 403; all new tables
have RLS enabled and no privileged member RPC is executable by anon. RLS-without-policy
linter notices on the service-only tables are intentional: ordinary roles have no grants.
Physical login/installation, hosted valid-user HTTP acceptance, and push delivery remain
unverified. The email-length correction was deployed in access-function v2. The Cloudflare origin was
subsequently added in access-function v3 and member-function v2; existing origins and pilot
authorization were preserved.


## Cloudflare publication evidence — 2026-11-21

- Public URL: https://atlantic-league.atlanticsoftware11.workers.dev/
- Published source: `470d98c3a9a14ef424d8a8b17df559d105ea96c7` on `pruebas`.
- Cloudflare Worker version: `ec0802ca-9ffc-477d-8c65-879b06fcd393`.
- GitHub Actions: https://github.com/manuAA11/Atlantic-Software/actions/runs/44954143063 — successful validation, deployment, public checks and session logout.
- All 28 Node test groups, TypeScript/Vite build, Wrangler package validation and encrypted authorization handoff self-test passed.
- Live verification passed: League HTML/assets, standalone manifest, service-worker headers, SPA routes, auth/recovery/invitation route reachability, exact-origin CORS, foreign-origin rejection and anonymous member-request rejection.
- An independent HTTPS request confirmed the root serves Atlantic League HTML rather than the previous placeholder. Both member services returned 204 with the exact Cloudflare origin on preflight.
- Desktop visual review found the Cédula/Contraseña form and the instruction to enter the document in both fields; no registration or email-verification step was shown. That browser tool did not support mobile emulation.

Publishing used official Wrangler device authorization for this session. Device verification
links were encrypted for the deployment operator; OAuth credentials stayed on the ephemeral
runner and Wrangler logout completed after publication. No API token was placed in this
repository. A future device-authorized release needs a newly generated operator recipient
public key; the previous one-session recipient private key must not be committed or reused.

This publication does not establish physical iPhone/Android installation, real-member login,
installed-session persistence, push delivery or provider recovery acceptance. Those checks
remain pending as shown in [INSTALLATION_QA.md](INSTALLATION_QA.md). No additional clients,
plans, memberships or routines were activated or changed by this hosting release.
