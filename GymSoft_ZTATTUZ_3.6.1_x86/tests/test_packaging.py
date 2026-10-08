import ast
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from product_config import VERSION


class PackageTest(unittest.TestCase):
    def test_existing_installations_are_updated_in_place(self):
        for name,uid in [('admin','E89DF404-FD78-4A97-89E8-9BA23D3B0B19'),('recepcion','8F529E62-5D29-49E0-99AA-28255D920ECE')]:
            source=(ROOT/f'instalador_{name}.iss').read_text(encoding='utf-8-sig')
            self.assertIn(uid,source)
            self.assertIn('UsePreviousAppDir=yes',source)
            self.assertIn('MinVersion=10.0',source)
            self.assertIn('ArchitecturesAllowed=x86os',source)
            self.assertIn(f'#define AppVersion "{VERSION}"',source)
            self.assertEqual(source.count('IconFilename:'),3)
            self.assertIn('SHChangeNotify($08000000, 0, 0, 0)',source)
        bundle=(ROOT/'instalador_completo.iss').read_text()
        self.assertIn('ZTATTUZ_Admin_{#AppVersion}.exe',bundle)
        self.assertIn('ZTATTUZ_Recepcion_{#AppVersion}.exe',bundle)
        self.assertIn('RaiseException',bundle)

    def test_icon_has_windows_sizes(self):
        data=(ROOT/'icono.ico').read_bytes()
        reserved,kind,count=struct.unpack_from('<HHH',data)
        self.assertEqual((reserved,kind),(0,1))
        sizes=set()
        for i in range(count):
            w,h,_,_,_,_,size,offset=struct.unpack_from('<BBBBHHII',data,6+i*16)
            sizes.add(w or 256);self.assertLessEqual(offset+size,len(data))
        self.assertTrue({16,32,48,256}.issubset(sizes))

    def test_build_includes_runtime_diagnostic_and_keeps_existing_data(self):
        source=(ROOT/'build_windows.py').read_text()
        self.assertIn('--onedir',source)
        self.assertIn('--diagnostico',source)
        self.assertNotIn('owner_panel.py',source)
        self.assertFalse((ROOT/'licensing.py').exists())

    def test_all_app_dialogs_use_dark_module(self):
        for path in ROOT.glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if isinstance(node,ast.ImportFrom) and node.module=='tkinter':
                    self.assertFalse({'messagebox','simpledialog','filedialog'} & {x.name for x in node.names},path.name)

    def test_parity_entry_points_visible(self):
        admin=(ROOT/'app.py').read_text(encoding='utf-8')
        reception=(ROOT/'reception_app.py').read_text(encoding='utf-8')
        self.assertIn('Consultar y editar pagos',admin)
        self.assertIn('Corregir el pago seleccionado',admin)
        self.assertIn('open_payment_manager(',admin)
        self.assertIn('Crear gasto',reception)
        self.assertIn('open_reception_expense_manager(',reception)
        for feature in ['MarketingPage','ShopPage','RoutinesPage','ClassesPage','CheckinPage']:
            self.assertTrue('class '+feature in admin,feature)


if __name__=='__main__':unittest.main()
