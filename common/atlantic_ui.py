"""Atlantic UI Kit: tokens extracted from the approved Gym Soft desktop design.

Widget behavior remains in desktop_ui/responsive_ui/ui_visuals. No fonts are bundled.
"""
import sys

PUBLISHER = "Atlantic Tech Software"
COPYRIGHT = "© Atlantic Tech Software — All rights reserved. By Manuel Cuellar"

def system_font(platform=None):
    platform = sys.platform if platform is None else platform
    return ".AppleSystemUIFont" if platform == "darwin" else "Segoe UI" if platform == "win32" else "Arial"

UI_FONT = system_font()
DARK_COLORS = {'background': '#0B1220', 'surface': '#172235', 'surface_alt': '#111B2E', 'surface_hover': '#21304A', 'input': '#0F192A', 'sidebar': '#182438', 'sidebar_hover': '#22324D', 'sidebar_active': '#213D79', 'topbar': '#172235', 'primary': '#16C784', 'primary_dark': '#0EAD70', 'accent': '#3B82F6', 'accent_hover': '#2563EB', 'text': '#F8FAFC', 'muted': '#94A3B8', 'line': '#2A3953', 'success': '#34D399', 'success_bg': '#10352E', 'danger': '#FB7185', 'danger_bg': '#3B1D29', 'warning': '#FBBF24', 'warning_bg': '#3A2E16', 'blue': '#60A5FA', 'blue_bg': '#172F59', 'purple': '#A78BFA', 'purple_bg': '#2B214B'}

# Existing components retain their palettes, spacing, sizing and focus behavior.
COMPONENT_MODULES = ("desktop_ui", "responsive_ui", "ui_visuals", "date_input", "money_input")

# Mutate one shared dictionary so all existing components see the same palette.
from common.theme_settings import load_theme, THEMES
MINIMAL_COLORS = dict(DARK_COLORS, background='#152338', surface='#1B2C43',
    surface_alt='#1B2C43', surface_hover='#263E5B', input='#1B2C43',
    sidebar='#152338', sidebar_hover='#203650', sidebar_active='#234666',
    topbar='#152338', primary='#22D3E8', primary_dark='#06B6CC',
    text='#F3F7FD', muted='#AAC3DF', line='#304964', blue='#58BCFF',
    success_bg='#16483F', warning_bg='#4B3D25', danger_bg='#4B293C')
# League web palette, mapped onto the existing desktop component tokens.
LEAGUE_LIGHT_COLORS = dict(DARK_COLORS,
    background='#F6F8FA', surface='#FFFFFF', surface_alt='#EDF2F8',
    surface_hover='#E9F0FF', input='#FFFFFF', sidebar='#FFFFFF',
    sidebar_hover='#EDF2F8', sidebar_active='#E9F0FF', topbar='#F6F8FA',
    primary='#2766DE', primary_dark='#2057BE', accent='#E9F0FF', accent_hover='#DCE7FF',
    text='#192435', muted='#606F82', line='#E5EAF0', blue='#2766DE', blue_bg='#E9F0FF',
    success='#16835E', success_bg='#E6F4ED', danger='#B73A4A', danger_bg='#FAEAED',
    warning='#946200', warning_bg='#FFF3D6', purple='#7446B5', purple_bg='#F1EBFA')
LEAGUE_DARK_COLORS = dict(DARK_COLORS,
    background='#0B1423', surface='#13253B', surface_alt='#1A304A',
    surface_hover='#1A3455', input='#13253B', sidebar='#0B1423',
    sidebar_hover='#1A304A', sidebar_active='#1A3455', topbar='#0B1423',
    primary='#2766DE', primary_dark='#2057BE', accent='#1A3455', accent_hover='#263B53',
    text='#EDF3FA', muted='#A4B3C5', line='#263B53', blue='#82B4FF', blue_bg='#1A3455',
    success='#6CD6AD', success_bg='#10352E', danger='#FF9AAA', danger_bg='#3A2335')
PALETTES = {'dark': DARK_COLORS, 'minimal': MINIMAL_COLORS,
            'league_light': LEAGUE_LIGHT_COLORS, 'league_dark': LEAGUE_DARK_COLORS}
THEME = load_theme()
COLORS = dict(PALETTES[THEME])

def select_theme(name):
    global THEME
    if name not in THEMES:
        raise ValueError('Selecciona un tema disponible.')
    THEME = name
    COLORS.clear()
    COLORS.update(PALETTES[name])
