"""Decrypt an Atlantic logical backup locally; never connects to production.

Dependency: cryptography==50.0.0. Keep the recovery key separate from archives.
Usage: python atlantic_restore_backup.py ARCHIVE KEY_FILE NEW_PRIVATE_DIRECTORY
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'ATLANTIC-BACKUP-v1\0'


def decrypt_backup(archive, key_file, destination):
    key=Path(key_file).read_bytes()
    if len(key)!=32:raise ValueError('Invalid recovery key length')
    data=Path(archive).read_bytes()
    if not data.startswith(MAGIC):raise ValueError('Unsupported archive format')
    nonce=data[len(MAGIC):len(MAGIC)+12]
    plain=AESGCM(key).decrypt(nonce,data[len(MAGIC)+12:],MAGIC)
    with zipfile.ZipFile(io.BytesIO(plain)) as z:
        if set(z.namelist())!={'database.dump','manifest.json'}:raise ValueError('Invalid backup contents')
        dump=z.read('database.dump');manifest=json.loads(z.read('manifest.json'))
    if hashlib.sha256(dump).hexdigest()!=manifest['dump_sha256']:raise ValueError('Backup hash mismatch')
    os.umask(0o077)
    target=Path(destination);target.mkdir(mode=0o700,parents=True,exist_ok=False)
    (target/'database.dump').write_bytes(dump)
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {'project':manifest['project'],'verified':True,'bytes':len(dump)}


if __name__=='__main__':
    try:
        if len(sys.argv)!=4:raise ValueError('Expected archive, key file and new output directory')
        print(json.dumps(decrypt_backup(*sys.argv[1:])))
    except Exception as error:
        print('Recovery stopped safely: '+type(error).__name__+'; original archive and key unchanged.',file=sys.stderr)
        sys.exit(1)
