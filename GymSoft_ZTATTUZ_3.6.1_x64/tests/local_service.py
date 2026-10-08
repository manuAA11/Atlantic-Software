"""Transporte local para ejecutar las clases de datos reales contra PGlite.

Adapta el subconjunto de consultas usado por Gym soft. No es una instancia
de Supabase/PostgREST: sus servicios de Auth, HTTP y Realtime se prueban aparte.
"""
import json
from pathlib import Path
import queue
import shutil
import subprocess
import threading
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]


class LocalDatabaseError(Exception):
    def __init__(self, data):
        self.code=data.get('code','')
        self.message=data['message']
        self.details=data.get('detail','')
        super().__init__(self.message)


class Engine:
    def __init__(self):
        node=shutil.which('node')
        if not node:
            raise RuntimeError('La simulación de PostgreSQL requiere Node.js en el equipo de compilación.')
        self.process=subprocess.Popen([node,str(ROOT/'tests/pg_bridge.mjs')],cwd=ROOT,
                                      stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      text=True,encoding='utf-8',bufsize=1)
        self.lock=threading.Lock()
        self.responses=queue.Queue()
        self.calls=[]
        def read():
            for line in self.process.stdout:
                try:self.responses.put(json.loads(line))
                except ValueError:self.responses.put({'error':{'message':'Respuesta local inválida: '+line}})
            self.responses.put({'error':{'message':'La base local se cerró antes de terminar la prueba.'}})
        threading.Thread(target=read,daemon=True).start()
        if not self.responses.get(timeout=60).get('ready'):
            raise RuntimeError('No se pudo iniciar la base local de prueba.')

    def request(self, message):
        with self.lock:
            self.calls.append(message)
            self.process.stdin.write(json.dumps(message,ensure_ascii=False,default=str)+'\n')
            self.process.stdin.flush()
            value=self.responses.get(timeout=30)
        if 'error' in value:raise LocalDatabaseError(value['error'])
        return value

    def sql(self, sql, params=(), user=None):
        return self.request(dict(op='sql',sql=sql,params=list(params),user=user))['data']

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write('{"op":"close"}\n');self.process.stdin.flush()
            try:self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.process.stdin.close();self.process.stdout.close()


class Client:
    def __init__(self, engine, user):self.engine,self.user=engine,user
    def rpc(self, name, params=None):return Query(self,dict(op='rpc',name=name,params=params or {}))
    def table(self, name):return Query(self,dict(op='table',table=name,steps=[]))


class Query:
    def __init__(self, client, message):self.client,self.message=client,message
    def __getattr__(self, name):
        if name not in {'select','insert','update','upsert','delete','eq','neq','gt','gte','lt','lte','is_',
                        'like','ilike','in_','order','limit','range','single','maybe_single'}:
            raise AttributeError('Consulta sin adaptar para la simulación: '+name)
        def step(*args,**kwargs):
            self.message['steps'].append(dict(method=name,args=args,kwargs=kwargs))
            return self
        return step
    def execute(self):
        return SimpleNamespace(**self.client.engine.request(dict(self.message,user=self.client.user)))
