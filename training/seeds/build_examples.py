"""Generate reviewable SQL examples. Does not connect to any database."""
import json
from pathlib import Path
from uuid import UUID, uuid5
ROOT=Path(__file__).parent
namespace=UUID('a75a4a02-7fc7-4e32-88c4-31d8f5776bc6')
groups={
'Pecho': [('bench-press','Press de banca','Banco y barra'),('incline-press','Press inclinado','Banco y mancuernas'),('decline-press','Press declinado','Banco y barra'),('dumbbell-fly','Aperturas con mancuernas','Banco y mancuernas'),('cable-crossover','Crossover en polea','Polea'),('machine-chest-press','Press en máquina','Máquina de pecho'),('push-up','Flexiones','Sin equipamiento')],
'Espalda':[('lat-pulldown','Jalón al pecho','Polea alta'),('pull-up','Dominadas','Barra fija'),('barbell-row','Remo con barra','Barra'),('seated-row','Remo sentado','Polea baja'),('dumbbell-row','Remo con mancuerna','Mancuerna'),('cable-pullover','Pullover en polea','Polea')],
'Piernas y glúteos':[('barbell-squat','Sentadilla con barra','Barra'),('leg-press','Prensa de piernas','Prensa'),('leg-extension','Extensión de cuádriceps','Máquina de extensión'),('leg-curl','Curl femoral','Máquina de curl femoral'),('romanian-deadlift','Peso muerto rumano','Barra'),('hip-thrust','Hip thrust','Banco y barra'),('lunge','Zancadas','Mancuernas'),('calf-raise','Elevación de gemelos','Máquina de gemelos'),('bulgarian-squat','Sentadilla búlgara','Banco y mancuernas')],
'Hombros':[('military-press','Press militar','Barra'),('dumbbell-shoulder-press','Press de hombros con mancuernas','Mancuernas'),('lateral-raise','Elevaciones laterales','Mancuernas'),('front-raise','Elevaciones frontales','Mancuernas'),('reverse-fly','Pájaros','Mancuernas'),('face-pull','Face pulls','Polea')],
'Bíceps':[('dumbbell-curl','Curl de bíceps con mancuernas','Mancuernas'),('hammer-curl','Curl martillo','Mancuernas'),('preacher-curl','Curl predicador','Banco predicador')],
'Tríceps':[('triceps-extension','Extensiones de tríceps','Mancuerna'),('dip','Fondos','Barras paralelas'),('triceps-pushdown','Extensión de tríceps en polea','Polea')],
'Abdomen y core':[('plank','Plancha','Colchoneta'),('crunch','Crunch','Colchoneta'),('leg-raise','Elevación de piernas','Colchoneta'),('cable-crunch','Abdominales en polea','Polea')],
'Cardio':[('treadmill','Caminadora','Caminadora'),('stationary-bike','Bicicleta estática','Bicicleta'),('elliptical','Elíptica','Elíptica'),('rowing-machine','Remo ergómetro','Remo ergómetro')],
'Cuerpo completo':[('deadlift','Peso muerto','Barra'),('burpee','Burpees','Sin equipamiento')]
}
existing=['barbell-squat','bench-press','deadlift','dumbbell-row','push-up','lat-pulldown','leg-press','dumbbell-shoulder-press','dumbbell-curl','triceps-pushdown']
ids={key:str(UUID(f'10000000-0000-4000-8000-{n:012d}')) for n,key in enumerate(existing,1)}
instructions = {
    "incline-press": "Empuje en banco inclinado con mancuernas. Registra el peso de cada mancuerna.",
    "decline-press": "Empuje en banco declinado con barra. Registra el peso total de la barra y los discos.",
    "dumbbell-fly": "Aperturas en banco con mancuernas. Ajusta el recorrido con el entrenador y registra la carga por mano.",
    "cable-crossover": "Aproximación de brazos en poleas para trabajar el pecho. Anota la carga y la altura de las poleas.",
    "machine-chest-press": "Empuje en máquina de pecho. Ajusta el asiento y anota la carga indicada en la máquina.",
    "pull-up": "Tracción en barra fija. Indica en las notas si se utiliza asistencia o lastre.",
    "barbell-row": "Remo con barra para espalda. Registra la carga total y la variante de agarre acordada.",
    "seated-row": "Remo sentado en polea baja. Anota el accesorio utilizado y la carga de la máquina.",
    "cable-pullover": "Extensión de hombros en polea para espalda. Registra el accesorio y la carga utilizada.",
    "leg-extension": "Extensión de rodillas en máquina. Ajusta asiento y rodillo con el entrenador antes de comenzar.",
    "leg-curl": "Flexión de rodillas en máquina para femorales. Indica si la variante es sentada o acostada.",
    "romanian-deadlift": "Peso muerto rumano para la cadena posterior. Registra el peso total de la barra y los discos.",
    "hip-thrust": "Extensión de cadera con apoyo en banco. Indica si se realiza con barra o máquina y registra la carga.",
    "lunge": "Zancadas con mancuernas. Registra las repeticiones por pierna y la carga de cada mancuerna.",
    "calf-raise": "Elevación de talones para gemelos. Indica la máquina y la carga utilizadas.",
    "bulgarian-squat": "Sentadilla con apoyo posterior en banco. Registra las repeticiones por pierna y la carga por mano.",
    "military-press": "Empuje vertical con barra. Registra el peso total y la variante sentada o de pie.",
    "lateral-raise": "Elevaciones laterales para hombros. Registra el peso de cada mancuerna.",
    "front-raise": "Elevaciones frontales para hombros. Indica si se alternan los brazos y la carga utilizada.",
    "reverse-fly": "Aperturas inversas para la parte posterior del hombro. Registra la carga por mano.",
    "face-pull": "Tracción hacia el rostro con cuerda en polea. Ajusta la altura con el entrenador y registra la carga.",
    "hammer-curl": "Flexión de codo con agarre neutro. Registra el peso de cada mancuerna y las repeticiones por lado.",
    "preacher-curl": "Curl con apoyo en banco predicador. Indica el implemento y la carga total utilizados.",
    "triceps-extension": "Extensión de codo con mancuerna. Indica la variante y si la carga se sostiene con una o dos manos.",
    "dip": "Fondos en barras paralelas. Indica si se utiliza asistencia, peso corporal o lastre.",
    "plank": "Trabajo isométrico de core. Especifica en las indicaciones la duración de cada sostén.",
    "crunch": "Flexión de tronco en colchoneta. Registra las repeticiones y cualquier carga adicional.",
    "leg-raise": "Elevación de piernas para abdomen. Indica la variante y registra las repeticiones completadas.",
    "cable-crunch": "Flexión de tronco con polea. Registra la carga y las repeticiones realizadas.",
    "treadmill": "Trabajo cardiovascular en caminadora. Especifica tiempo, velocidad e inclinación en las indicaciones.",
    "stationary-bike": "Trabajo cardiovascular en bicicleta estática. Especifica tiempo y resistencia en las indicaciones.",
    "elliptical": "Trabajo cardiovascular en elíptica. Especifica tiempo y resistencia en las indicaciones.",
    "rowing-machine": "Trabajo cardiovascular en ergómetro de remo. Especifica tiempo o distancia en las indicaciones.",
    "burpee": "Movimiento de cuerpo completo. Adapta el salto, la variante y el ritmo con el entrenador."
}
entries=[]
for muscle,rows in groups.items():
 for key,name,equipment in rows:
  entries.append(dict(id=ids.setdefault(key,str(uuid5(namespace,key))),name=name,muscle=muscle,equipment=equipment,standard_key=key,instructions=instructions.get(key,'Registra las series, repeticiones y cargas realizadas según las indicaciones de tu entrenador.')))
plans={
'Push — pecho, hombros y tríceps':[['bench-press','incline-press','lateral-raise','triceps-pushdown']],
'Pull — espalda y bíceps':[['lat-pulldown','seated-row','dumbbell-row','dumbbell-curl']],
'Legs — piernas y glúteos':[['barbell-squat','leg-press','leg-curl','hip-thrust','calf-raise']],
'Full Body — cuerpo completo':[['barbell-squat','bench-press','lat-pulldown','dumbbell-shoulder-press','crunch']],
'Upper Body — tren superior':[['bench-press','seated-row','lateral-raise','dumbbell-curl','triceps-pushdown']],
'Lower Body — tren inferior':[['leg-press','romanian-deadlift','lunge','leg-curl','calf-raise']],
'Hipertrofia de 4 días':[['bench-press','seated-row','lateral-raise'],['barbell-squat','leg-curl','calf-raise'],['incline-press','lat-pulldown','dumbbell-curl','triceps-pushdown'],['leg-press','hip-thrust','leg-extension']],
'Rutina básica de principiantes':[['leg-press','machine-chest-press','seated-row','crunch']]
}
templates=[]
for n,(name,days) in enumerate(plans.items(),1):
 exercises=[dict(catalog_id=ids[key],day=f'Día {day}',sets=3,reps=10,weight_kg=0,rest_seconds=90,notes='Ajustar antes de asignar.',position=i+1) for day,keys in enumerate(days,1) for i,key in enumerate(keys)]
 templates.append(dict(id=str(uuid5(namespace,'template-'+str(n))),name=name,seed_key='atlantic-example-'+str(n),goal='Plantilla de ejemplo para revisar y adaptar con el entrenador.',notes='No es una prescripción personalizada. Peso pendiente de definir. En ejercicios por tiempo, adaptar las indicaciones y el registro.',exercises=exercises))
# SQL is explicit and operator-controlled. DO NOTHING preserves edits on repeat loads.
def quoted(value):return "'"+value.replace("'","''")+"'"
lines=['-- Optional initial examples. REVIEW then run only in approved environment.','begin;']
for entry in entries:
 keys=list(entry);lines.append('insert into public.league_exercise_catalog('+','.join(keys)+') values('+','.join(quoted(entry[k]) for k in keys)+') on conflict do nothing;')
for t in templates:
 keys=list(t);lines.append('insert into public.gym_routine_templates('+','.join(keys)+') values('+','.join(quoted(json.dumps(t[k],ensure_ascii=False))+'::jsonb' if k=='exercises' else quoted(t[k]) for k in keys)+') on conflict do nothing;')
lines.append('commit;')
(ROOT/'examples.sql').write_text('\n'.join(lines)+'\n')
(ROOT/'examples.json').write_text(json.dumps(dict(exercises=entries,templates=templates),ensure_ascii=False,indent=2)+'\n')
print(f'{len(entries)} exercises, {len(templates)} templates; no database access.')
