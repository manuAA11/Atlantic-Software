"""UI entry-point and role-boundary regression checks, independent of Tk display."""
import ast
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class AppearanceLocation(unittest.TestCase):
    def test_appearance_only_in_configuration_pages(self):
        occurrences=[]
        for filename in ('app.py','reception_app.py','platform_ui.py'):
            tree=ast.parse((ROOT/'common'/filename).read_text())
            for cls in (n for n in ast.walk(tree) if isinstance(n,ast.ClassDef)):
                for call in (n for n in ast.walk(cls) if isinstance(n,ast.Call)):
                    name=getattr(call.func,'id',None) or getattr(call.func,'attr',None)
                    if name in ('appearance_settings','open_appearance'):occurrences.append((filename,cls.name,name))
        self.assertCountEqual(occurrences,[('app.py','SettingsPage','appearance_settings'),('reception_app.py','ReceptionSettingsPage','appearance_settings')])

    def test_reception_settings_do_not_inherit_admin_configuration(self):
        tree=ast.parse((ROOT/'common/reception_app.py').read_text())
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ReceptionSettingsPage')
        self.assertEqual([getattr(b,'id','') for b in cls.bases],['BasePage'])
        texts=[n.value for n in ast.walk(cls) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        self.assertIn('Apariencia',texts)
        self.assertNotIn('Planes',texts)

if __name__=='__main__':unittest.main()
