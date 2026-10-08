import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import queue
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from owner_panel import OwnerPanel, Form
from desktop_ui import friendly_error


def panel_stub():
    return NS(_closing=False,busy=True,queue=queue.Queue(),set_controls_enabled=Mock(),
              message=Mock(),cloud=NS(email='owner@example.test'),pending_detail=None,
              after=Mock(return_value='next'),poll=Mock(),load_detail=Mock())


class PanelResilienceTest(unittest.TestCase):
    def test_callback_error_does_not_stop_polling(self):
        panel=panel_stub();panel.queue.put((True,{},Mock(side_effect=ValueError('render failure'))))
        with patch('owner_panel.messagebox.showerror') as error:OwnerPanel.poll(panel)
        self.assertFalse(panel.busy);panel.after.assert_called_once();error.assert_called_once()

    def test_rpc_error_does_not_stop_polling(self):
        panel=panel_stub();panel.queue.put((False,ValueError('server failure'),Mock()))
        with patch('owner_panel.messagebox.showerror'):OwnerPanel.poll(panel)
        self.assertFalse(panel.busy);panel.set_controls_enabled.assert_called_with(True)
        panel.after.assert_called_once()

    def test_pending_new_selection_gets_loaded(self):
        panel=panel_stub();panel.pending_detail='new-gym'
        panel.queue.put((True,{},Mock()))
        OwnerPanel.poll(panel)
        panel.load_detail.assert_called_once();self.assertIsNone(panel.pending_detail)

    def test_busy_selection_discards_stale_detail(self):
        tree=Mock();tree.selection.return_value=('new-gym',)
        panel=NS(_populating=False,tree=tree,rows={'new-gym':{'id':'new-gym','name':'New','plan':'Standard'}},
                 detail={'users':['old-user']},detail_target='old-gym',detail_trees={},busy=True,
                 selection_label=Mock(),marketing_status=Mock())
        OwnerPanel.load_detail(panel)
        self.assertEqual(panel.detail,{});self.assertIsNone(panel.detail_target)
        self.assertEqual(panel.pending_detail,'new-gym')

    def test_cannot_toggle_stale_access(self):
        panel=NS(selected=lambda:{'id':'new-gym'},detail_target='old-gym',load_detail=Mock())
        with patch('owner_panel.messagebox.showinfo') as info:OwnerPanel.toggle(panel,'users',False)
        info.assert_called_once();panel.load_detail.assert_called_once()

    def test_invalid_form_stays_open(self):
        form=NS(vars={'reference':Mock(get=lambda:'')},feedback=Mock(),close=Mock(),
                validate=Mock(side_effect=ValueError('Falta referencia')))
        Form.accept(form)
        form.close.assert_not_called();form.feedback.set.assert_called_with('Falta referencia')

    def test_valid_form_returns_validated_payload(self):
        form=NS(vars={'reference':Mock(get=lambda:' Recibo-1 ')},feedback=Mock(),close=Mock(),
                validate=lambda x:{'p_reference':x['reference']})
        Form.accept(form)
        self.assertEqual(form.raw,{'reference':'Recibo-1'})
        form.close.assert_called_once_with({'p_reference':'Recibo-1'})

    def test_error_dictionary_is_not_shown_raw(self):
        self.assertEqual(friendly_error("{'message': 'Indica un motivo.', 'code': 'P0001', 'hint': None}"),'Indica un motivo.')


if __name__=='__main__':unittest.main()
