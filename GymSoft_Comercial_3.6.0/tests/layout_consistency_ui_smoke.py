"""Mismas columnas en ventana mediana y grande; paneles sin huecos intermedios."""
from pathlib import Path
import os
import sys
from datetime import date, timedelta
from types import SimpleNamespace as NS
from unittest.mock import patch
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
import responsive_ui as layout
from responsive_ui_smoke import shell, pump, descendants
from layout_modes_ui_smoke import assert_layout_contracts
from ui_assertions import destroy_root, resize_test_window


def main():
    checks = 0
    errors = []
    for factor in (1, 1.2, 1.25):
        with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
            root = shell(admin.GymSoftApp, factor)
        root.report_callback_exception = lambda kind, error, tb: errors.append(str(error))
        try:
            for mode, size in [('normal', '1280x800'), ('maximized', '1560x900'), ('normal', '1280x800'), ('normal', '900x620')]:
                with patch.object(layout, 'window_profile', return_value=(mode, round(layout.scale(root), 3))):
                    resize_test_window(root, size)
                    layout.layout_modes(root).changed(NS(widget=root))
                    for key in ('dashboard', 'statistics'):
                        with patch.object(root.page_types[key], 'refresh', lambda *_: None): root.show_page(key)
                        page = root.pages[key];pump(root, .2)
                        root.content_area.canvas.yview_moveto(0)
                        root.content_area.canvas.xview_moveto(0)
                        if key == 'dashboard':
                            assert {int(card.grid_info()['row']) for card in page.expiration_cards.values()} == {0}
                            assert {int(card.grid_info()['column']) for card in page.expiration_cards.values()} == {0, 1, 2, 3}
                            actions = [w for w in descendants(page) if isinstance(w, admin.QuickActionButton)]
                            assert len(actions) == 4 and {int(w.grid_info()['row']) for w in actions} == {0}
                            assert {(int(v.master.grid_info()['row']), int(v.master.grid_info()['column'])) for v in page.ticket_dashboard.counts.values()} == {(r, c) for r in range(2) for c in range(3)}
                            assert {int(card.grid_info()['row']) for card in page.birthday_cards.values()} == {0}
                            if size != '900x620':
                                assert not root.content_area._bars[1], (f'Dashboard no cabe en ventana mediana: {factor}, solicitado={size}, '
                                    f'real={root.winfo_geometry()}, monitor={layout.work_area(root)}, '
                                    f'visor={root.content_area.canvas.winfo_width()}, mínimo={layout.minimum_layout_width(root.content_area.body)}')
                            checks += 6
                        else:
                            page._render_refresh({
                                'metrics': dict(today_entries=2, today_unique=2, week_entries=12, week_unique=8,
                                                month_entries=25, month_unique=16, period_entries=25, period_unique=16),
                                'daily_series': [dict(date=str(date(2026, 9, 1)+timedelta(days=i)), count=i % 4) for i in range(14)],
                                'plan_breakdown': [dict(type='Mensualidad', people=10, entries=18, percentage=72),
                                                   dict(type='Sesión', people=6, entries=7, percentage=28)]
                            }, 14)
                            pump(root, .15)
                            card = page.chart.master
                            group = card.master
                            insights = page.insight_labels['daily_average'].master.master
                            gap = insights.winfo_rooty() - (card.winfo_rooty()+card.winfo_height())
                            assert 0 <= gap <= 20, f'Hueco entre gráfico e indicadores: {gap}px, {size}, {factor}'
                            assert group.rowconfigure(0)['weight'] > 0
                            assert page.chart.winfo_height() >= card.winfo_height()-75*factor
                            assert len(page.plan_tree.get_children()) == 2
                            checks += 4
                        assert_layout_contracts(page)
                        assert not errors, errors
                        folder = os.environ.get('GYMSOFT_QA_IMAGES')
                        if folder and size in ('1280x800', '1560x900'):
                            from PIL import ImageGrab
                            target=Path(folder);target.mkdir(parents=True,exist_ok=True)
                            ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((root.winfo_rootx(),root.winfo_rooty(),
                                root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(
                                target/f'{key}_{mode}_{int(factor*100)}.png')
        finally:
            destroy_root(root)
    print(f'PASS: {checks} comprobaciones de columnas estables, paneles sin huecos y contenido poblado al 100/120/125 %.')


if __name__ == '__main__': main()
