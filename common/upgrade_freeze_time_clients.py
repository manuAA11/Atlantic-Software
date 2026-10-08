from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
for product in ROOT.glob('GymSoft_*'):
    for name in ('server_date.py', 'gym_time.py', 'membership_freeze_ui.py'):
        shutil.copyfile(ROOT/'common'/name, product/name)
    for name in ('cloud_database.py', 'reception_database.py'):
        p = product/name
        s = p.read_text()
        s = s.replace('from gym_time import display_timestamp, local_datetime, timezone_for',
                      'from gym_time import display_timestamp, local_datetime, timezone_for, parse_instant')
        import re
        s = re.sub(r"return self\._server_date\.get\(lambda: self\._execute\(self\.client\.rpc\('(gymsoft|ztattuz)_today'\)\)\.data\)",
                   'return self._server_date.get(self._fetch_clock)', s)
        if 'def _fetch_clock' not in s:
            pos = s.index('    def invalidate_today_cache')
            s = s[:pos]+'''    def _fetch_clock(self):
        clock = self._execute(self.client.rpc('gym_local_clock', {'p_gym_id': self.gym_id})).data
        if not isinstance(clock, dict):
            raise ValueError('No se pudo consultar el reloj del gimnasio.')
        parse_instant(clock['now'])
        self.cloud.timezone = clock['timezone']
        return clock

'''+s[pos:]
        if name == 'cloud_database.py':
            s = s.replace('timezone_for, parse_instant', 'timezone_for, parse_instant, local_wall_instant')
            start = s.index('    def _now(self)')
            end = s.index('    def _timestamp', start)
            s = s[:start]+'''    def _now(self) -> datetime:
        clock = self._fetch_clock()
        return parse_instant(clock['now']).astimezone(ZoneInfo(clock['timezone']))

'''+s[end:]
            s = s.replace('datetime.now().astimezone().isoformat()', 'self._now().isoformat()')
            s = s.replace('datetime.now().astimezone().isoformat(timespec="seconds")', 'self._now().isoformat(timespec="seconds")')
            s = s.replace('datetime.now().astimezone().replace(', 'self._now().replace(')
            s = s.replace('if key == "ticket_consumption_archive":', 'if key in ("ticket_consumption_archive", "freeze_archive"):')
            s = s.replace('"starts_at": starts_at,', '"starts_at": local_wall_instant(starts_at, timezone_for(self)).isoformat(),')
            s = s.replace('return datetime.combine(value, time.min).isoformat()',
                          "raise ValueError('Una fecha sin hora no puede importarse como evento. Revisa el registro original.')")
            s = s.replace('return value.replace(microsecond=0).isoformat()',
                          "return parse_instant(value).isoformat() if key in datetime_fields else value.isoformat()")
            s = s.replace('return parsed.replace(microsecond=0).isoformat()',
                          "return parse_instant(parsed).isoformat()")
            # Use the already-authorized bulk snapshot RPC instead of inferring active/frozen from dates.
            start = s.index('    def list_clients(self, search: str = "")')
            end = s.index('    def get_client(self, client_id:', start)
            s = s[:start]+'''    def list_clients(self, search: str = "") -> list[dict[str, Any]]:
        rows = self._execute(self.client.rpc('reception_list_clients', {
            'p_gym_id': self.gym_id, 'p_search': search.strip()})).data or []
        result = []
        for row in rows:
            item = dict(row)
            item['active'] = int(bool(item.get('active', True)))
            item['birthdate'] = item.get('birthdate') or item.get('birth_date') or ''
            item['photo_path'] = item.get('photo_path') or ''
            item['membership_status'] = item.get('membership_status') or item.get('status', 'VENCIDO')
            result.append(item)
        return result

'''+s[end:]
        p.write_text(s)
    p = product/'payment_revision.py'
    s = p.read_text()
    s = s.replace('_when(row["paid_at"])', '_when(row["paid_at"], timezone_for(self.db))')
    s = s.replace("_when(entry.get('created_at'))", "_when(entry.get('created_at'), timezone_for(self.db))")
    if "'Membresía y congelación'" not in s:
        marker='        self._button(controls, "Actualizar", lambda: self.load(self.offset)).pack(side="right")'
        assert marker in s
        s = s.replace(marker, marker+'''\n        from membership_freeze_ui import open_freeze_manager
        self._button(controls, 'Membresía y congelación', lambda: open_freeze_manager(
            self.window, self.db, self.client_id, client_name, self.on_changed)).pack(side='right', padx=8)''')
    p.write_text(s)
    # Every access screen uses the same denied message; the server decision gates the relay.
    for name in ('app.py', 'reception_app.py'):
        p = product/name
        s = p.read_text()
        if name == 'app.py':
            s = s.replace('timezone_for, ticket_access_note, checkin_label',
                          'timezone_for, ticket_access_note, checkin_label, business_today')
            s = s.replace('or date.today().strftime("%d/%m/%Y")', 'or business_today(parent).strftime("%d/%m/%Y")')
            s = s.replace('value=date.today().strftime("%d/%m/%Y")', 'value=db._today().strftime("%d/%m/%Y")')
            s = s.replace('value=datetime.now().strftime("%Y-%m-%d 18:00")', 'value=db._today().strftime("%Y-%m-%d 18:00")')
            s = s.replace('month_prefix = datetime.now().strftime("%Y-%m")', 'month_prefix = self.db._today().strftime("%Y-%m")')
            s = s.replace('today = date.today()', 'raise ValueError("No se pudo consultar la fecha del gimnasio. Reintenta con conexión al servidor.")')
            s = s.replace('reservation["created_at"][:16]', 'display_timestamp(reservation["created_at"], timezone_for(self.db), seconds=False)')
        s = s.replace('f"Estado: {result[\'status\']}"', 'result.get("denial_message") or f"Estado: {result[\'status\']}"')
        s = s.replace("f\"Estado: {result.get('status', '')}\"", "result.get('denial_message') or f\"Estado: {result.get('status', '')}\"")
        # DATE is never turned into an invented midnight event.
        s = s.replace('row.get("created_at_local") or display_timestamp(', 'display_timestamp(') if False else s
        p.write_text(s)
print('Both roles now use the gym clock and the shared freeze controls')
