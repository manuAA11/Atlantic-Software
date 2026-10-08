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
COLORS = {'background': '#0B1220', 'surface': '#172235', 'surface_alt': '#111B2E', 'surface_hover': '#21304A', 'input': '#0F192A', 'sidebar': '#182438', 'sidebar_hover': '#22324D', 'sidebar_active': '#213D79', 'topbar': '#172235', 'primary': '#16C784', 'primary_dark': '#0EAD70', 'accent': '#3B82F6', 'accent_hover': '#2563EB', 'text': '#F8FAFC', 'muted': '#94A3B8', 'line': '#2A3953', 'success': '#34D399', 'success_bg': '#10352E', 'danger': '#FB7185', 'danger_bg': '#3B1D29', 'warning': '#FBBF24', 'warning_bg': '#3A2E16', 'blue': '#60A5FA', 'blue_bg': '#172F59', 'purple': '#A78BFA', 'purple_bg': '#2B214B'}

# Existing components retain their palettes, spacing, sizing and focus behavior.
COMPONENT_MODULES = ("desktop_ui", "responsive_ui", "ui_visuals", "date_input", "money_input")
