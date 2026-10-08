"""Apply shared edits once; original files remain in git for review."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
for edition in ROOT.glob('GymSoft_*'):
 (edition/'gym_time.py').write_text((ROOT/'common/gym_time.py').read_text())
 for name in ('cloud_database.py','reception_database.py'):
  p=edition/name;s=p.read_text()
  s=s.replace('from __future__ import annotations','from __future__ import annotations\nfrom gym_time import display_timestamp, local_datetime, timezone_for')
  s=s.replace('    @staticmethod\n    def _timestamp(value: Any) -> str:\n        if not value:\n            return ""\n        return str(value).replace("T", " ")',
   '    def _timestamp(self, value: Any) -> str:\n        return display_timestamp(value, timezone_for(self))')
  if name=='cloud_database.py':
   start=s.index('    def membership_snapshot(');end=s.index('    def register_checkin(',start)
   s=s[:start]+'''    def membership_snapshot(self, client_id: int) -> dict[str, Any]:
        value = self._execute(self.client.rpc("reception_membership_snapshot", {
            "p_gym_id": self.gym_id, "p_client_id": client_id})).data
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise ValueError("No se pudo consultar el estado de la membresía.")
        return value

'''+s[end:]
   # Both technical and Excel backups use this method. Preserve ledger even if a check-in was deleted.
   start=s.index('    def _cloud_table_rows(');body=s.index('\n',s.index(') ->',start))+1
   s=s[:body]+'''            if table == "memberships":
                value = self._execute(self.client.rpc("ticket_backup_memberships", {"p_gym_id": self.gym_id})).data
                return json.loads(value) if isinstance(value, str) else list(value or [])
'''+s[body:]
   s=s.replace('datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)',
    'local_datetime(text, timezone_for(self)).replace(tzinfo=None)')
  p.write_text(s)
 for name in ('app.py','reception_app.py','fingerprint_ui.py'):
  p=edition/name;s=p.read_text()
  insertion='from gym_time import display_timestamp, timezone_for, ticket_access_note, checkin_label\n'
  if 'from __future__ import annotations' in s:
   s=s.replace('from __future__ import annotations','from __future__ import annotations\n'+insertion)
  else:s=insertion+s
  if name=='app.py':
   s=s.replace('self.result_details.configure(text=details)','self.result_details.configure(text=details + ("\\n" + ticket_access_note(result) if ticket_access_note(result) else ""))')
  if name=='reception_app.py':
   s=s.replace('        if allowed and show_confirmation:', '        self.status_detail.set(ticket_access_note(result) or str(result.get("status", "")))\n\n        if allowed and show_confirmation:')
  if name=='fingerprint_ui.py':
   s=s.replace("page.status_detail.set(str(result.get('status','')))","page.status_detail.set(ticket_access_note(result) or str(result.get('status','')))")
  # Existing code sliced raw ISO strings; convert before presentation, leaving dates untouched.
  s=re.sub(r'str\((\w+\.get\([\"\'](?:checkin_at|created_at|paid_at|updated_at|sold_at|sent_at|started_at|ended_at)[\"\'][^\n]*?\))\)\.replace\([\"\']T[\"\'], [\"\'] [\"\']\)\[:(?:16|19)\]',
   r'display_timestamp(\1, timezone_for(self.db))',s)
  p.write_text(s)
 p=edition/'payment_revision.py';s=p.read_text();s=s.replace('from __future__ import annotations','from __future__ import annotations\nfrom gym_time import local_datetime, timezone_for')
 start=s.index('def _when(');end=s.index('\n\ndef open_payment_manager',start)
 s=s[:start]+'''def _when(value: Any, zone: str = 'America/Bogota') -> str:
    if not value: return '—'
    try: return local_datetime(value, zone).strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError): return str(value)
'''+s[end:]
 s=re.sub(r'_when\((row\.get\([^\n]*?\))\)',r'_when(\1, timezone_for(db))',s)
 p.write_text(s)
print('Shared database/UI helpers updated in all editions.')
