"""Customer warnings remain concise; diagnostic codes stay out of the dialog."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'GymSoft_ZTATTUZ_3.6.1_x86'))
from ui_performance import AsyncPageMixin,ReadFailure,classify_read_failure

class InterfaceTexts(unittest.TestCase):
    def test_future_token_has_safe_server_guidance(self):
        from common.session_manager import SessionClockError
        result=classify_read_failure(SessionClockError('synthetic'))
        self.assertEqual(result.category,'server_clock')
        self.assertIn('servidor',result.message)
        self.assertNotIn('contraseña',result.message)

    def test_same_cause_is_not_repeated_for_two_sections(self):
        text='Inicia sesión de nuevo para continuar.'
        page=NS(_view_error_details={
            'one':ReadFailure('session','PGRST303','GS-LECTURA-111111111111',text),
            'two':ReadFailure('session','PGRST303','GS-LECTURA-222222222222',text)},refresh=Mock())
        with patch('desktop_ui.messagebox.askretrycancel',return_value=False) as dialog:
            AsyncPageMixin.show_read_error(page)
        shown=dialog.call_args.args[1]
        self.assertEqual(shown.count(text),1)
        self.assertIn('GS-LECTURA-111111111111',shown)
        self.assertNotIn('PGRST303',shown)
        page.refresh.assert_not_called()
        self.assertEqual(len(page._view_error_details),2)

    def test_missing_server_feature_has_natural_safe_guidance(self):
        class Error(Exception):code='PGRST202'
        result=classify_read_failure(Error('Could not find the function public.membership_population(p_gym_id)'))
        self.assertEqual(result.category,'membership_update')
        self.assertIn('soporte de Atlantic Gym',result.message)
        for technical in ('.sql','p_gym_id','caché','PGRST202'):
            self.assertNotIn(technical,result.message)

if __name__=='__main__':unittest.main()
