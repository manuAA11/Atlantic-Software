"""Verify the published candidate with the production updater; never execute installers."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, tempfile
from urllib.parse import urlsplit, urljoin
import httpx
from common.updater import Updater, TRUSTED_ASSET_HOSTS

REPOSITORY = 'manuAA11/Atlantic-Software'

def text_asset(client, asset):
    url = asset['browser_download_url']
    for _ in range(6):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname not in TRUSTED_ASSET_HOSTS or parsed.username or parsed.password or parsed.port not in (None,443):
            raise ValueError('Unexpected asset redirect')
        with client.stream('GET', url, headers={'Accept-Encoding':'identity'}) as response:
            if response.status_code in (301,302,303,307,308):
                url = urljoin(url,response.headers.get('location',''))
                continue
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data)>1024*1024: raise ValueError('Oversized text asset')
            if len(data)!=asset['size'] or 'sha256:'+hashlib.sha256(data).hexdigest()!=asset['digest']:
                raise ValueError('Text asset digest mismatch')
            return json.loads(data)
    raise ValueError('Too many asset redirects')

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tag',required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--windows-run',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'atlantic-gym-[0-9]+[.][0-9]+[.][0-9]+-piloto',args.tag) or not re.fullmatch('[a-f0-9]{40}',args.commit) or not args.windows_run.isdigit():
        raise ValueError('Invalid candidate identity')
    expected_updater=subprocess.check_output(['git','show',args.commit+':common/updater.py'])
    if expected_updater!=Path('common/updater.py').read_bytes():
        raise ValueError('The verifier must use the exact validated updater')
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
    if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    with httpx.Client(timeout=30,follow_redirects=False) as client:
        response=client.get('https://api.github.com/repos/'+REPOSITORY+'/releases/tags/'+args.tag,headers=headers)
        response.raise_for_status();release=response.json()
        if release['draft'] or not release['prerelease'] or release['target_commitish']!=args.commit:
            raise ValueError('Release provenance mismatch')
        assets={a['name']:a for a in release['assets']}
        manifest=text_asset(client,assets['PILOT_UPDATE_MANIFEST.json'])
        if manifest['source_commit']!=args.commit or manifest['github_run_id']!=args.windows_run or manifest['final'] is not False:
            raise ValueError('Manifest provenance mismatch')
        expected={('ztattuz','windows-x86'),('ztattuz','windows-x64'),('commercial','windows-x64')}
        if len(manifest['releases'])!=3 or {(r['variant'],r['architecture']) for r in manifest['releases']}!=expected:
            raise ValueError('Incomplete installer profiles')
        results=[]
        with tempfile.TemporaryDirectory() as folder:
            for index,item in enumerate(manifest['releases']):
                asset=assets[item['file']]
                if item['version']!=manifest['version'] or item['installer_url']!=asset['browser_download_url'] or item['bytes']!=asset['size'] or 'sha256:'+item['sha256']!=asset['digest']:
                    raise ValueError('Published installer differs from build manifest')
                candidate=dict(item,channel='beta',policy='OPTIONAL')
                updater=Updater(Path(folder)/str(index),item['architecture'],'beta','0.0.0',schema_supported=lambda schema:schema=='core-1',http=client,variant=item['variant'])
                selected=updater.select([candidate])
                if selected is None or selected.version!=manifest['version']:
                    raise ValueError('Production updater did not select the candidate')
                path=updater.download(selected)
                updater.verify(selected,path)
                if updater.journal.value['state']!='UPDATE_VERIFIED':raise ValueError('Installer was not verified')
                results.append(dict(file=item['file'],variant=item['variant'],architecture=item['architecture'],bytes=path.stat().st_size,sha256=item['sha256'],status='PASS',installation=item.get('installation')))
        print(json.dumps(dict(status='PASS',version=manifest['version'],source_commit=args.commit,windows_run=args.windows_run,release_id=release['id'],manifest=manifest,downloads=results,installer_executed=False),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
