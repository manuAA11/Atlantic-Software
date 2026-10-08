"""Final installers require the user's local and external acceptance evidence."""
import json
from pathlib import Path

REQUIRED = ('whatsapp_pilot', 'wompi_sandbox', 'chatbot_pilot', 'automation_pilot',
    'timezone', 'audit_clock', 'freeze', 'freeze_checkin', 'ticket_daily',
    'relay_hardware', 'scheduler_gym_timezone', 'prior_regressions',
    'added_regressions', 'concurrent_two_sessions')

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
            evidence=item.get('evidence')
            if item.get('passed') is not True or not isinstance(evidence,str) or not evidence or not (root/evidence).is_file():
                missing.append(name)
        if missing:
            raise ValueError('Falta comprobar: '+', '.join(missing))
    except (ValueError, TypeError, AttributeError) as error:
        raise SystemExit('Entrega bloqueada. '+str(error)) from error

