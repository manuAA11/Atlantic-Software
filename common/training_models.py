"""Pure selection/filter logic, independent from Tk and network operations."""
import unicodedata

GROUPS = ('Pecho', 'Espalda', 'Piernas y glúteos', 'Hombros', 'Bíceps', 'Tríceps', 'Abdomen y core', 'Cardio', 'Cuerpo completo')


def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFD', str(value or '').casefold()) if not unicodedata.combining(c))


def muscle_group(value):
    return {'piernas': 'Piernas y glúteos', 'cadena posterior': 'Cuerpo completo'}.get(folded(value), value)


def matches(row, query='', muscle='', equipment=''):
    return (not query or folded(query) in folded(' '.join(str(row.get(k, '')) for k in ('name', 'muscle', 'equipment')))) and (
        not muscle or muscle_group(row.get('muscle', '')) == muscle) and (not equipment or row.get('equipment') == equipment)


class ExerciseSelection:
    def __init__(self):
        self.items = {}  # insertion order is the saved exercise order

    def toggle(self, row):
        key = str(row['id'])
        existing=[k for k,v in self.items.items() if v['catalog_id']==key]
        if existing:
            for occurrence in existing:del self.items[occurrence]
        else:
            self.items[key] = dict(catalog_id=key, name=row['name'], day='Día 1', sets='3', reps='10', weight_kg='0', rest_seconds='90', notes='')

    def load(self, exercises, allow_legacy=False):
        keys = [str(e.get('catalog_id') or e.get('league_catalog_id') or '') for e in exercises]
        if not all(keys) and not allow_legacy:
            raise ValueError('El plan contiene ejercicios manuales sin referencia al catálogo. Selecciona sus equivalentes del catálogo antes de crear una nueva revisión.')
        self.items = {(key or 'legacy')+'@'+str(i): dict(e, catalog_id=key or None) for i,(key,e) in enumerate(zip(keys, exercises))}

    @property
    def catalog_ids(self):
        return {v['catalog_id'] for v in self.items.values() if v['catalog_id']}

    def resolve(self, key, row):
        if key in self.items:self.items[key].update(catalog_id=str(row['id']),name=row['name'])

    def duplicate(self, key):
        if key in self.items:
            value=dict(self.items[key]);index=1
            while key+'@copy'+str(index) in self.items:index+=1
            value['day']='Otro día'
            self.items[key+'@copy'+str(index)]=value

    def move(self, key, delta):
        rows = list(self.items.items());index = next((i for i, (k, _) in enumerate(rows) if k == key), -1)
        if index >= 0 and 0 <= index + delta < len(rows):
            rows[index], rows[index+delta] = rows[index+delta], rows[index]
            self.items = dict(rows)

    def payload(self):
        result = []
        for index, value in enumerate(self.items.values(), 1):
            if not value.get('catalog_id'):
                raise ValueError('Vincula '+str(value.get('name','el ejercicio'))+' a un ejercicio del catálogo antes de guardar.')
            try:
                item = dict(catalog_id=value['catalog_id'], day=str(value.get('day', '')).strip(),
                    sets=int(value['sets']), reps=int(value['reps']), weight_kg=float(str(value['weight_kg']).replace(',', '.')),
                    rest_seconds=int(value['rest_seconds']), notes=str(value.get('notes', '')).strip(), position=index)
                if not (1 <= item['sets'] <= 20 and 1 <= item['reps'] <= 100 and 0 <= item['weight_kg'] <= 1000 and
                        0 <= item['rest_seconds'] <= 600 and 1 <= len(item['day']) <= 80):
                    raise ValueError()
            except (ValueError, TypeError, KeyError):
                raise ValueError('Revisa los parámetros de ' + str(value.get('name', 'cada ejercicio')) + '.') from None
            result.append(item)
        if not result:
            raise ValueError('Selecciona al menos un ejercicio.')
        return result
