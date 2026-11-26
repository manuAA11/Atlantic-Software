# Public Supabase production CA bundle

supabase-prod-ca.crt contains the public production CA certificates (2021 and 2025) distributed by Supabase CLI v3.4.0, under its MIT license:

- https://github.com/supabase/cli/blob/v3.4.0/apps/cli/src/command-internal/supabase-ca-templates/prod-ca-2021.ts
- https://github.com/supabase/cli/blob/v3.4.0/apps/cli/src/command-internal/supabase-ca-templates/prod-ca-2025.ts

No private key or project credentials are included. Backup connections retain sslmode=verify-full with host verification. Staging CAs and arbitrary peer certificates are excluded.
