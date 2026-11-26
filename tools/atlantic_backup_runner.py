"""One-session backup worker. No production writes; no plaintext data artifacts.

Only the public request key and authenticated ciphertext may enter GitHub.
Private session key, database passfiles and decrypted dumps stay runner-private.
Uses cryptography==50.0.0. Not part of the desktop application runtime.
"""
import base64
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import zipfile
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

REFS = ('bawrakwhzkxmhmgkczqu', 'srmquhwpawgipncmvfjf')
MAGIC = b'ATLANTIC-BACKUP-v1\0'
ROOT = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'atlantic-backup'
OUTPUT = ROOT / 'output'
IMAGE = 'public.ecr.aws/docker/library/postgres:17'
RESTORE_IMAGE = 'public.ecr.aws/supabase/postgres:17.12.0.002'
RECOVERY_KEY = None


def run(args, *, data=None, env=None, timeout=300):
    result = subprocess.run(args, input=data, capture_output=True, env=env, timeout=timeout)
    if result.returncode:
        if RECOVERY_KEY is not None:
            nonce = secrets.token_bytes(12)
            detail = json.dumps({'program':args[0], 'exit':result.returncode,
                                 'stderr':result.stderr.decode(errors='replace')}).encode()
            (OUTPUT/'diagnostics.atlbak').write_bytes(MAGIC+nonce+AESGCM(RECOVERY_KEY).encrypt(nonce,detail,MAGIC))
        # stderr may contain row contents or credentials. Never publish it.
        raise RuntimeError('Private subprocess failed (exit %s); sensitive output withheld' % result.returncode)
    return result.stdout


def request():
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, exist_ok=True)
    OUTPUT.mkdir(mode=0o700, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    (ROOT / 'session-private.pem').write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    value = {'run_id': os.environ['GITHUB_RUN_ID'], 'source_sha': os.environ['GITHUB_SHA'],
             'nonce': secrets.token_hex(32), 'projects': REFS,
             'public_key': key.public_key().public_bytes(
                 serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()}
    (ROOT / 'request.json').write_text(json.dumps(value))
    print('One-session public request ready. Private key excluded from artifacts.')


def receive():
    req = json.loads((ROOT / 'request.json').read_text())
    path = 'ops/backup-handoff-' + req['run_id'] + '.json'
    endpoint = 'repos/' + os.environ['GITHUB_REPOSITORY'] + '/contents/' + path + '?ref=optimization/supabase-20261126'
    deadline = time.monotonic() + 12 * 60
    while time.monotonic() < deadline:
        p = subprocess.run(['gh', 'api', endpoint], capture_output=True)
        if p.returncode == 0:
            response = json.loads(p.stdout)
            envelope = json.loads(base64.b64decode(response['content']))
            private = serialization.load_pem_private_key((ROOT / 'session-private.pem').read_bytes(), password=None)
            key = private.decrypt(base64.b64decode(envelope['key']), padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
            plain = AESGCM(key).decrypt(base64.b64decode(envelope['nonce']),
                                       base64.b64decode(envelope['payload']), req['nonce'].encode())
            payload = json.loads(plain)
            if payload['run_id'] != req['run_id'] or payload['nonce'] != req['nonce']:
                raise RuntimeError('Incorrect credential handoff identity')
            if set(payload['projects']) != set(REFS):
                raise RuntimeError('Unexpected project scope')
            return payload
        time.sleep(5)
    raise RuntimeError('Encrypted credential handoff timed out; no database accessed')


def env_and_mount(ref, config):
    host = config['host']
    if not host.endswith('.pooler.supabase.com') or config['port'] != 5432:
        raise RuntimeError('Unexpected database host')
    if not config['user'].endswith('.' + ref) or config['database'] != 'postgres':
        raise RuntimeError('Unexpected database identity')
    directory = ROOT / ref
    directory.mkdir(mode=0o700, exist_ok=True)
    esc = lambda v: str(v).replace('\\', '\\\\').replace(':', '\\:')
    passfile = directory / 'pgpass'
    passfile.write_text(':'.join(map(esc, [host,5432,'postgres',config['user'],config['password']])) + '\n')
    passfile.chmod(0o600)
    env = directory / 'connection.env'
    env.write_text('\n'.join(['PGHOST='+host,'PGPORT=5432','PGUSER='+config['user'],
        'PGDATABASE=postgres','PGPASSFILE=/run/pgpass','PGSSLMODE=verify-full',
        'PGSSLROOTCERT=/run/root-ca.pem','PGCONNECT_TIMEOUT=20',
        'PGOPTIONS=-c default_transaction_read_only=on -c lock_timeout=5000 -c statement_timeout=180000'])+'\n')
    return ['docker','run','--rm','--network','host','--env-file',str(env),
            '--mount','type=bind,src='+str(passfile)+',dst=/run/pgpass,readonly',
            '--mount','type=bind,src='+str(Path('tools/vendor/supabase-prod-ca.crt').resolve())+',dst=/run/root-ca.pem,readonly', IMAGE]


def archive(ref, config, encryption_key):
    prefix = env_and_mount(ref, config)
    role = 'supabase_read_only_user'
    private_stderr=(ROOT/ref/'keeper.stderr').open('wb')
    keeper = subprocess.Popen(prefix+['psql','-X','-qAt','-v','ON_ERROR_STOP=1'],
                              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=private_stderr)
    def query(sql):
        marker = '__ATLANTIC_END__'
        keeper.stdin.write((sql+"; SELECT '"+marker+"';\n").encode()); keeper.stdin.flush()
        lines=[]
        while True:
            line=keeper.stdout.readline()
            if not line: raise RuntimeError('Snapshot session failed; sensitive output withheld')
            if line.strip()==marker.encode(): return b''.join(lines).decode()
            lines.append(line)
    try:
        query('SET ROLE '+role+'; BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        snapshot=query('SELECT pg_export_snapshot()').strip()
        if not snapshot or len(snapshot)>100: raise RuntimeError('Invalid snapshot')
        names=query("SELECT format('%I.%I',n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND (n.nspname IN ('public','private','auth','storage') OR n.nspname LIKE 'league%') ORDER BY 1").splitlines()
        counts={}
        for table in names:
            counts[table]=int(query('SELECT count(*) FROM '+table).strip())
        source_acl=json.loads(query("SELECT coalesce(jsonb_agg(jsonb_build_object('schema',n.nspname,'name',c.relname,'rls',c.relrowsecurity,'owner',pg_get_userbyid(c.relowner),'acl',c.relacl)),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND (n.nspname IN ('public','private','auth','storage') OR n.nspname LIKE 'league%')"))
        dump=run(prefix+['pg_dump','--format=custom','--compress=6','--role='+role,'--snapshot='+snapshot,'--no-password'])
        meta={'project':ref,'snapshot':snapshot,'counts':counts,'table_security':source_acl,
              'dump_sha256':hashlib.sha256(dump).hexdigest(),'source_sha':os.environ['GITHUB_SHA'],
              'scope':'Complete pg_dump archive including custom schemas and extension configuration data; platform keys/configuration and Storage files require separate recovery prerequisites.'}
        package=io.BytesIO()
        with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('database.dump',dump);z.writestr('manifest.json',json.dumps(meta))
        nonce=secrets.token_bytes(12)
        encrypted=MAGIC+nonce+AESGCM(encryption_key).encrypt(nonce,package.getvalue(),MAGIC)
        target=OUTPUT/(ref+'.atlbak');target.write_bytes(encrypted)
        # Authenticate/decrypt the saved file before beginning the restore rehearsal.
        saved=target.read_bytes();decoded=AESGCM(encryption_key).decrypt(saved[len(MAGIC):len(MAGIC)+12],saved[len(MAGIC)+12:],MAGIC)
        with zipfile.ZipFile(io.BytesIO(decoded)) as z:
            recovered=z.read('database.dump')
        if hashlib.sha256(recovered).hexdigest()!=meta['dump_sha256']:raise RuntimeError('Backup integrity mismatch')
        return ref,recovered,meta,hashlib.sha256(encrypted).hexdigest()
    finally:
        if keeper.poll() is None:
            try:keeper.stdin.write(b'ROLLBACK;\n\\q\n');keeper.stdin.flush();keeper.wait(timeout=10)
            except (BrokenPipeError,subprocess.TimeoutExpired):keeper.kill()
        private_stderr.close()


def rehearse(ref, dump, meta):
    name='atlantic-restore-'+ref
    password=secrets.token_hex(32)
    run(['docker','run','-d','--name',name,'--network','none','--env','POSTGRES_PASSWORD='+password,
         '--env','POSTGRES_USER=supabase_admin','--env','POSTGRES_DB=postgres',RESTORE_IMAGE,
         'postgres','-c','cron.launch_active_jobs=off','-c','pg_net.worker_enabled=false'])
    try:
        admin=None
        for _ in range(60):
            for user in ['supabase_admin','postgres']:
                p=subprocess.run(['docker','exec',name,'psql','-X','-qAt','-U',user,'-d','postgres','-c',
                                  'SELECT rolsuper FROM pg_roles WHERE rolname=current_user'],capture_output=True)
                if p.returncode==0 and p.stdout.strip()==b't':admin=user;break
            if admin:break
            time.sleep(2)
        if not admin:raise RuntimeError('Isolated restore database unavailable')
        # Restore to isolated infrastructure. Original ownership/ACL stay in the archive.
        # Suppressing them only in rehearsal permits matching different local reserved-role bootstrap.
        run(['docker','exec','-i',name,'pg_restore','-U',admin,'-d','postgres','--clean','--if-exists',
             '--no-owner','--no-privileges','--exit-on-error'],data=dump,timeout=360)
        for table,expected in meta['counts'].items():
            restored=int(run(['docker','exec',name,'psql','-X','-qAt','-U',admin,'-d','postgres','-c',
                              'SELECT count(*) FROM '+table]).strip())
            if restored!=expected:raise RuntimeError('Restored row count mismatch (table details withheld)')
        return {'restored_tables_checked':len(meta['counts']),'row_counts_match':True,
                'restore_scope':'All archived tables restored; source ACL/owner preserved in archive but not replayed in this isolated rehearsal. Vault depends on original project keys; no platform service authentication/hardware acceptance claimed.'}
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True)


def backup():
    global RECOVERY_KEY
    os.umask(0o077)
    payload=receive()
    key=base64.b64decode(payload['encryption_key'])
    RECOVERY_KEY=key
    print('Encrypted handoff accepted; preparing PostgreSQL client.',flush=True)
    run(['docker','pull',IMAGE],timeout=240)
    reports=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(archive,ref,payload['projects'][ref],key) for ref in REFS]
        backups=[task.result() for task in tasks]
    print('Both encrypted exports completed; preparing isolated restore.',flush=True)
    # Credentials are no longer used; only authenticated ciphertext goes to artifacts.
    payload=None
    for path in ROOT.glob('*/pgpass'):path.unlink(missing_ok=True)
    run(['docker','pull',RESTORE_IMAGE],timeout=360)
    for ref,dump,meta,encrypted_sha in backups:
        check=rehearse(ref,dump,meta)
        reports.append({'project':ref,'ciphertext_sha256':encrypted_sha,'dump_bytes':len(dump),**check})
    (OUTPUT/'verification.json').write_text(json.dumps({'success':True,'projects':reports},indent=2))
    print('Encrypted exports and isolated restore rehearsals completed. No production writes performed.')


if __name__=='__main__':
    try:
        if sys.argv[1]=='request':request()
        elif sys.argv[1]=='backup':backup()
        else:raise RuntimeError('Unknown command')
    except Exception as error:
        if RECOVERY_KEY is not None:
            nonce=secrets.token_bytes(12)
            details={'exception':type(error).__name__,'message':str(error),
                     'private_diagnostics':{p.parent.name:p.read_text(errors='replace') for p in ROOT.glob('*/keeper.stderr')}}
            (OUTPUT/'entrypoint-diagnostics.atlbak').write_bytes(MAGIC+nonce+AESGCM(RECOVERY_KEY).encrypt(nonce,json.dumps(details).encode(),MAGIC))
        # Do not leak dumps, passwords, SQL values or raw database exception messages.
        print('Backup operation stopped safely: '+type(error).__name__,file=sys.stderr)
        sys.exit(1)
