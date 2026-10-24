import unittest
from types import SimpleNamespace
from unittest.mock import patch
from common.training_models import ExerciseSelection, matches
from common.training_service import PendingWrites

class SelectionTests(unittest.TestCase):
    def test_filter_preserves_selection_and_supports_accents(self):
        selection=ExerciseSelection();row={'id':'one','name':'Extensión de cuádriceps','muscle':'Piernas','equipment':'Máquina'}
        selection.toggle(row)
        self.assertTrue(matches(row,'extension','Piernas y glúteos','Máquina'))
        self.assertFalse(matches(row,'bíceps'))
        self.assertEqual(selection.catalog_ids,{'one'})
        selection.items['one']['sets']='4'
        other=dict(row,id='two',name='Remo');selection.toggle(other);selection.move('two',-1)
        self.assertEqual([r['catalog_id'] for r in selection.payload()],['two','one'])
        self.assertEqual(selection.payload()[1]['sets'],4)
        selection.duplicate('one');self.assertEqual(len(selection.payload()),3)
        selection.toggle(row);self.assertEqual(selection.catalog_ids,{'two'})

    def test_repeated_exercises_survive_loading_and_are_distinct_days(self):
        selection=ExerciseSelection();selection.load([dict(catalog_id='one',name='Press',day='Lunes',sets=3,reps=10,weight_kg=0,rest_seconds=90),dict(catalog_id='one',name='Press',day='Jueves',sets=4,reps=8,weight_kg=0,rest_seconds=60)])
        self.assertEqual([r['day'] for r in selection.payload()],['Lunes','Jueves'])
        self.assertEqual(selection.catalog_ids,{'one'})
        selection.items[next(iter(selection.items))]['weight_kg']='NaN'
        with self.assertRaises(ValueError):selection.payload()
        with self.assertRaises(ValueError):selection.load([{'name':'Manual'}])

    def test_legacy_plan_can_be_linked_without_retyping_or_losing_parameters(self):
        selection=ExerciseSelection();selection.load([dict(name='Nombre antiguo',day='Martes',sets=4,reps=8,weight_kg=25,rest_seconds=60)],allow_legacy=True)
        with self.assertRaisesRegex(ValueError,'Vincula'):selection.payload()
        selection.resolve(next(iter(selection.items)),{'id':'global-one','name':'Nombre del catálogo'})
        self.assertEqual(selection.payload()[0]['weight_kg'],25)
        self.assertEqual(selection.payload()[0]['catalog_id'],'global-one')

    def test_failed_write_retry_keeps_request_identity(self):
        pending=PendingWrites();a=pending.payload('routine.assign',{'name':'A'})
        self.assertEqual(a,pending.payload('routine.assign',{'name':'A'}))
        self.assertNotEqual(a['request_id'],pending.payload('routine.assign',{'name':'B'})['request_id'])
        pending.complete();self.assertNotEqual(a['request_id'],pending.payload('routine.assign',{'name':'A'})['request_id'])

if __name__=='__main__':unittest.main()
