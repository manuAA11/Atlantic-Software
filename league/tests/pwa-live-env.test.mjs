import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLivePwaConfig} from '../scripts/check-live-pwa-env.mjs';
test('live PWA requires the same modern public-key contract as the mobile client',()=>{
 const env={EXPO_PUBLIC_SUPABASE_URL:'https://abcdefghijklmnopqrst.supabase.co',EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY:'sb_publishable_synthetic_only',EXPO_PUBLIC_LEAGUE_ENDPOINT:'https://abcdefghijklmnopqrst.supabase.co/functions/v1/atlantic-league'};
 assert.equal(validateLivePwaConfig(env).ready,true);
 for(const bad of [{EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY:'eyJ_legacy_anon_synthetic'},{EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY:'sb_secret_never_public'},{EXPO_PUBLIC_LEAGUE_ENDPOINT:'https://differentprojectxxxx.supabase.co/functions/v1/atlantic-league'},{EXPO_PUBLIC_SUPABASE_URL:''}])assert.throws(()=>validateLivePwaConfig({...env,...bad}),/clave publicable moderna/);
});
