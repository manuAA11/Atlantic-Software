// One-session official Wrangler device authorization. Plaintext device codes and
// OAuth credentials never enter public logs, artifacts or repository files.
import { spawn } from 'node:child_process';
import nacl from './vendor/nacl-fast.cjs';
const CONTEXT = 'league/cloudflare-authorization';
const PRIVATE_ORIGIN = 'https://dash.cloudflare.com';
const PUBLIC_KEY = '12b6ee35245c723b4374b4c83a03baa3283a10730926c798636d494b3a73d05d';
const toHex = value => Buffer.from(value).toString('hex');
function seal(uri, publicKey) {
  const ephemeral = nacl.box.keyPair();
  const nonce = nacl.randomBytes(nacl.box.nonceLength);
  const box = nacl.box(Buffer.from(uri), nonce, publicKey, ephemeral.secretKey);
  return { nonce: toHex(nonce), publicKey: toHex(ephemeral.publicKey), box: toHex(box) };
}
function verificationUri(output) {
  if (!output.includes(PRIVATE_ORIGIN + '/oauth2/device')) return null;
  const code = output.match(/and enter the code:\s*([A-Z0-9-]{6,20})/i)?.[1];
  if (!code) return null;
  const url = new URL('/oauth2/device', PRIVATE_ORIGIN);
  url.searchParams.set('user_code', code);
  return url.href;
}
if (process.argv.includes('--self-test')) {
  const recipient = nacl.box.keyPair();
  const expected = PRIVATE_ORIGIN + '/oauth2/device?user_code=TEST-CODE';
  const envelope = seal(expected, recipient.publicKey);
  const bytes = nacl.box.open(
    Buffer.from(envelope.box, 'hex'), Buffer.from(envelope.nonce, 'hex'),
    Buffer.from(envelope.publicKey, 'hex'), recipient.secretKey);
  if (!bytes || Buffer.from(bytes).toString() !== expected) throw Error('Encrypted handoff self-test failed');
  if (verificationUri('https://example.com/oauth2/device and enter the code: TEST-CODE')) throw Error('Untrusted URI accepted');
  if (verificationUri(PRIVATE_ORIGIN + '/oauth2/device\nand enter the code:\n TEST-CODE') !== expected) throw Error('Device output parsing failed');
  console.log('Encrypted authorization handoff self-test passed.');
  process.exit(0);
}
const token = process.env.GITHUB_TOKEN;
const repository = process.env.GITHUB_REPOSITORY;
const sha = process.env.GITHUB_SHA;
if (!token || repository !== 'manuAA11/Atlantic-Software' || !sha) throw Error('Missing expected deployment context');
async function status(state, description, targetUrl) {
  const response = await fetch('https://api.github.com/repos/' + repository + '/statuses/' + sha, {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28' },
    body: JSON.stringify({ state, context: CONTEXT, description, ...(targetUrl ? {target_url: targetUrl} : {}) })
  });
  if (!response.ok) throw Error('Could not publish encrypted authorization status: HTTP ' + response.status);
}
const { GITHUB_TOKEN: omitted, ...childEnv } = process.env;
childEnv.WRANGLER_SEND_METRICS = 'false';
const child = spawn('npx', ['--yes', 'wrangler@4.136.3', 'login', '--device',
  '--browser=false', '--scopes', 'account:read', 'user:read', 'workers_scripts:write'],
  { env: childEnv, stdio: ['ignore', 'pipe', 'pipe'] });
let privateOutput = '';
let handoff = null;
let handoffError = null;
function observe(chunk) {
  privateOutput = (privateOutput + chunk.toString()).slice(-80000);
  if (handoff) return;
  const uri = verificationUri(privateOutput);
  if (!uri) return;
  const envelope = seal(uri, Buffer.from(PUBLIC_KEY, 'hex'));
  const target = 'https://github.com/' + repository + '?league_auth=' + encodeURIComponent(JSON.stringify(envelope));
  if (target.length > 2000) { handoffError = Error('Authorization envelope too large'); child.kill(); return; }
  handoff = status('pending', 'Encrypted device approval is ready for the authorized operator', target)
    .then(() => console.log('Private Cloudflare device approval is ready.'))
    .catch(error => { handoffError = error; child.kill(); });
}
child.stdout.on('data', observe);
child.stderr.on('data', observe);
const timer = setTimeout(() => child.kill('SIGTERM'), 7 * 60 * 1000);
try {
  const code = await new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('exit', resolve);
  });
  if (handoff) await handoff;
  if (handoffError) throw handoffError;
  if (code !== 0 || !privateOutput.includes('Successfully logged in.')) {
    let reason = 'Cloudflare device login was not completed';
    if (/unknown argument|unknown arguments/i.test(privateOutput)) reason = 'Wrangler rejected device login options';
    else if (/expired|timed out|timeout/i.test(privateOutput)) reason = 'Cloudflare device authorization expired';
    else if (/denied|access_denied/i.test(privateOutput)) reason = 'Cloudflare device approval was denied';
    else if (/invalid_scope/i.test(privateOutput)) reason = 'Cloudflare rejected the requested deployment scopes';
    await status('failure', reason);
    throw Error(reason + '; private authentication output withheld.');
  }
  await status('success', 'Cloudflare approved this one-session deployment; credentials stay on the runner');
  console.log('Cloudflare deployment authorization completed.');
} finally {
  clearTimeout(timer);
  privateOutput = '';
}
