import ast
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from product_config import VERSION


class PackageTest(unittest.TestCase):
    def test_versioned_icons_are_installed(self):
        for name,count in [('instalador_clientes.iss',4),('instalador_propietario.iss',2)]:
            source=(ROOT/name).read_text(encoding='utf-8')
            self.assertIn(f'#define AppVersion "{VERSION}"',source)
            self.assertIn('DestName: "GymSoft-{#AppVersion}.ico"',source)
            if name == 'instalador_clientes.iss':
                self.assertEqual(source.count('IconFilename: "{app}\\GymSoft-{#AppVersion}.ico"'), 2)
                self.assertEqual(source.count('IconFilename: "{app}\\GymSoft-Recepcion-{#AppVersion}.ico"'), 2)
                self.assertIn('Source: "icono_recepcion.ico"', source)
            else:
                self.assertEqual(source.count('IconFilename: "{app}\\GymSoft-{#AppVersion}.ico"'), count)
            icons=source.split('[Icons]',1)[1].split('\n[',1)[0]
            self.assertEqual(icons.count('WorkingDir:'),count)
            self.assertEqual(icons.count('AppUserModelID:'),count)
            self.assertIn('SHChangeNotify($08000000, 0, 0, 0)',source)

    def test_icon_has_windows_sizes(self):
        data=(ROOT/'icono.ico').read_bytes()
        reserved,kind,count=struct.unpack_from('<HHH',data)
        self.assertEqual((reserved,kind),(0,1))
        sizes=set()
        for i in range(count):
            w,h,_,_,_,_,size,offset=struct.unpack_from('<BBBBHHII',data,6+i*16)
            sizes.add(w or 256);self.assertLessEqual(offset+size,len(data))
        self.assertTrue({16,32,48,256}.issubset(sizes))

    def test_owner_not_in_client_installer(self):
        source=(ROOT/'instalador_clientes.iss').read_text(encoding='utf-8')
        self.assertNotIn('GymSoftControl',source)
        self.assertNotIn('owner_panel',source)

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
