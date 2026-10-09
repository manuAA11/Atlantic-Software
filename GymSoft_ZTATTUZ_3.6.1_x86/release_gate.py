"""Final installers require the user's local and external acceptance evidence."""
import ast
import hashlib
import json
from pathlib import Path

REQUIRED = ('whatsapp_pilot', 'wompi_sandbox', 'chatbot_pilot', 'automation_pilot',
    'timezone', 'audit_clock', 'freeze', 'freeze_checkin', 'ticket_daily',
    'relay_hardware', 'scheduler_gym_timezone', 'prior_regressions',
    'added_regressions', 'concurrent_two_sessions')


def _commercial_relay_not_applicable(root, version, item):
    """Only the Commercial product has no relay to accept; keep that evidence current."""
    if item.get('passed') is not False or item.get('state') != 'not_applicable':
        return False
    if not isinstance(item.get('reason'), str) or not item['reason'].strip():
        return False
    try:
        # Read product identity from this edition's code, without importing it or
        # trusting a product/applicability flag from the acceptance manifest.
        identity = {}
        for node in ast.parse((root/'product_config.py').read_text(encoding='utf-8')).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ('PRODUCT_NAME', 'VERSION'):
                        identity[target.id] = node.value.value
        if identity != {'PRODUCT_NAME': 'Atlantic Gym', 'VERSION': version}:
            return False
        evidence = item.get('evidence')
        if not isinstance(evidence, str) or not evidence:
            return False
        path = (root/evidence).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            return False
        proof = json.loads(path.read_text(encoding='utf-8'))
        if (proof.get('criterion') != 'relay_hardware'
                or proof.get('state') != 'not_applicable'
                or proof.get('product_name') != identity['PRODUCT_NAME']
                or proof.get('version') != version
                or proof.get('reason') != item['reason']):
            return False
        sources = proof.get('source_sha256', {})
        if (proof.get('source_hash_encoding') != 'UTF-8; line endings normalized to LF'
                or set(sources) != {'product_config.py', 'app.py', 'reception_app.py'}):
            return False
        # Git may check text out with CRLF in Windows; code must still match.
        if any(hashlib.sha256((root/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest() != digest
               for name, digest in sources.items()):
            return False
        return proof.get('absent_modules') == ['door_access.py'] and not (root/'door_access.py').exists()
    except (OSError, ValueError, TypeError, AttributeError, SyntaxError):
        return False


def require_release_ready(root, version):
    root=Path(root)
    manifest=root/'release_readiness.json'
    if not manifest.is_file():
        raise SystemExit('Entrega bloqueada: falta la evidencia de aceptación de la actualización.')
    try:
        data=json.loads(manifest.read_text(encoding='utf-8'))
        if data.get('version') != version:
            raise ValueError('La evidencia debe corresponder a la versión que se va a compilar.')
        checks=data.get('checks', {})
        missing=[]
        for name in REQUIRED:
            item=checks.get(name, {})
            if item.get('state') == 'not_applicable':
                if name != 'relay_hardware' or not _commercial_relay_not_applicable(root, version, item):
                    missing.append(name)
                continue
            evidence=item.get('evidence')
            if item.get('passed') is not True or not isinstance(evidence,str) or not evidence or not (root/evidence).is_file():
                missing.append(name)
        if missing:
            raise ValueError('Falta comprobar: '+', '.join(missing))
    except (ValueError, TypeError, AttributeError) as error:
        raise SystemExit('Entrega bloqueada. '+str(error)) from error

