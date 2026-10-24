"""Training workspaces composed from the shared Atlantic desktop widgets.

All writes use the authenticated Gym RPC. Tk is touched only on the UI thread.
"""
import calendar
from datetime import date
from functools import wraps
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from common.training_models import ExerciseSelection, GROUPS, matches, folded
from common.training_service import PendingWrites
from common import atlantic_ui as kit
from gym_time import display_timestamp, local_datetime, local_wall_instant, timezone_for
from responsive_ui import ScrollArea, fit_window, AutoScrollbar
from ui_tasks import run_io
from ui_performance import AsyncPageMixin, background_reads
from desktop_ui import decorate_window, messagebox


def guarded(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as error:
            from desktop_ui import friendly_error
            messagebox.showerror('No se pudo completar la operación', friendly_error(error), parent=self)
    return call


def text_field(parent, label, variable, row, column=0, options=None):
    box=ttk.Frame(parent,style='Surface.TFrame');box.grid(row=row,column=column,sticky='ew',padx=5,pady=5)
    ttk.Label(box,text=label,style='Field.TLabel').pack(anchor='w',pady=(0,4))
    entry=(ttk.Combobox(box,textvariable=variable,values=options,state='readonly') if options is not None else ttk.Entry(box,textvariable=variable))
    entry.pack(fill='x');return entry


def table(parent, columns, height=10):
    host=ttk.Frame(parent,style='Surface.TFrame');host.pack(fill='both',expand=True)
    host.rowconfigure(0,weight=1);host.columnconfigure(0,weight=1)
    tree=ttk.Treeview(host,columns=[c[0] for c in columns],show='headings',height=height,selectmode='browse')
    for key,title,width in columns:
        tree.heading(key,text=title);tree.column(key,width=width,minwidth=55,stretch=True)
    scroll=AutoScrollbar(host,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set)
    horizontal=AutoScrollbar(host,orient='horizontal',command=tree.xview);tree.configure(xscrollcommand=horizontal.set)
    tree.grid(row=0,column=0,sticky='nsew');scroll.grid(row=0,column=1,sticky='ns');horizontal.grid(row=1,column=0,sticky='ew')
    return tree


def populate(tree, rows, values):
    """Stable keyed updates preserve focus, selection and scroll across refreshes."""
    keep={str(row['id']) for row in rows}
    for key in tree.get_children():
        if key not in keep:tree.delete(key)
    for index,row in enumerate(rows):
        key=str(row['id']);content=values(row)
        if tree.exists(key):
            if tuple(map(str,tree.item(key,'values'))) != tuple(map(str,content)):tree.item(key,values=content)
            tree.move(key,'',index)
        else:tree.insert('','end',iid=key,values=content)


class AsyncPanel(AsyncPageMixin,ttk.Frame):
    def __init__(self,parent,db):
        super().__init__(parent,style='Card.TFrame',padding=12)
        self.db=db;self._read_inside_modal=True;self.init_reads();self.writes=PendingWrites();self.jobs={}
        self.notice=ttk.Label(self,textvariable=self._view_status,style='CardMuted.TLabel',wraplength=850,cursor='hand2')
        self.notice.pack(anchor='w',fill='x',pady=(0,8));self.notice.bind('<Button-1>',lambda _:self.show_read_error())
        self.feedback=tk.StringVar();ttk.Label(self,textvariable=self.feedback,style='CardMuted.TLabel').pack(side='bottom',anchor='w',pady=4)
        self.bind('<Destroy>',self._cleanup,add='+')
        self.bind('<Map>',lambda event: self.later('mapped',lambda:background_reads(self._root()).show(self)) if event.widget is self else None,add='+')

    def _cleanup(self,event):
        if event.widget is self:
            for job in self.jobs.values():
                try:self.after_cancel(job)
                except tk.TclError:pass
            self.jobs.clear()
            background_reads(self._root())._destroyed(event)

    def later(self,key,fn):
        old=self.jobs.pop(key,None)
        if old:self.after_cancel(old)
        def run():
            self.jobs.pop(key,None)
            if self.winfo_exists():fn()
        self.jobs[key]=self.after(180,run)

    def load_view(self,key,load,render,parameters=()):
        background_reads(self._root()).submit(self,key,parameters,load,render)

    def write(self,action,data):
        payload=self.writes.payload(action,data)
        result=run_io(self,lambda:self.db.training(action,payload),'Guardando cambios')
        self.writes.complete();self.feedback.set('Cambios guardados.')
        return result


class Window(tk.Toplevel):
    def __init__(self,parent,title,width=980,height=740):
        super().__init__(parent);self.title('Atlantic Gym · '+title);decorate_window(self)
        self.transient(parent.winfo_toplevel());fit_window(self,width,height,parent=parent)
        self.result=None;self.db=parent.db;self.writes=PendingWrites()
        footer=ttk.Frame(self,padding=12);footer.pack(side='bottom',fill='x')
        self.footer=footer
        area=ScrollArea(self,padding=14,minimum_width=440);area.pack(fill='both',expand=True);self.body=area.body
        self.body.columnconfigure(0,weight=1)
        ttk.Button(footer,text='Cerrar',command=self.close).pack(side='right')
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.after_idle(self.grab_set)

    def close(self):
        if getattr(self._root(),'_foreground_io',False):
            self.bell();return
        self.destroy()

    def write(self,action,data):
        result=run_io(self,lambda:self.db.training(action,self.writes.payload(action,data)),'Guardando cambios')
        self.writes.complete();return result


class CheckList(ttk.Frame):
    """Checkbox images, keyboard support and selected IDs independent of filtering."""
    def __init__(self,parent,on_change,height=9):
        super().__init__(parent,style='Surface.TFrame');self.checked=set();self.on_change=on_change
        self.tree=table(self,[('name','Nombre',245),('detail','Detalle',170)],height)
        self.tree.configure(show='tree headings');self.tree.column('#0',width=36,minwidth=36,stretch=False)
        self.tree.heading('#0',text='✓');self.rows={};self.photos={}
        self.tree.bind('<ButtonRelease-1>',self.click);self.tree.bind('<space>',self.keyboard)
        self.bind('<<AtlanticAppearanceChanged>>',lambda _:self.render_icons(),add='+')
        self.theme_binding=self._root().bind('<<AtlanticAppearanceChanged>>',self._theme,add='+')
        self.bind('<Destroy>',self._destroy,add='+')

    def _theme(self,_):
        if self.winfo_exists():self.render_icons()

    def _destroy(self,event):
        if event.widget is self:
            self.photos.clear()
            if self.theme_binding:
                try:self._root().unbind('<<AtlanticAppearanceChanged>>',self.theme_binding)
                except tk.TclError:pass

    def icon(self,checked):
        key=(kit.THEME,checked)
        if key not in self.photos:
            image=Image.new('RGBA',(60,60));draw=ImageDraw.Draw(image)
            draw.rounded_rectangle((9,9,51,51),radius=9,fill=kit.COLORS['primary'] if checked else kit.COLORS['surface'],outline=kit.COLORS['primary'] if checked else kit.COLORS['muted'],width=3)
            if checked:draw.line([(18,30),(27,39),(43,22)],fill='white',width=5,joint='curve')
            self.photos[key]=ImageTk.PhotoImage(image.resize((20,20),Image.Resampling.LANCZOS),master=self)
        return self.photos[key]

    def render_icons(self):
        for key in self.tree.get_children():self.tree.item(key,image=self.icon(key in self.checked))

    def show(self,rows,detail=lambda r:r.get('equipment','')):
        self.rows={str(r['id']):r for r in rows}
        populate(self.tree,rows,lambda r:(r['name'],detail(r)));self.render_icons()

    def click(self,event):
        key=self.tree.identify_row(event.y)
        if key and self.tree.identify_column(event.x)=='#0':self.toggle(key)

    def keyboard(self,event):
        if self.tree.focus():self.toggle(self.tree.focus())
        return 'break'

    def toggle(self,key):
        if key in self.checked:self.checked.remove(key)
        else:self.checked.add(key)
        self.tree.item(key,image=self.icon(key in self.checked));self.on_change(key,self.rows[key])


class ClientPicker(AsyncPanel):
    def __init__(self,parent,db,changed=lambda:None):
        super().__init__(parent,db);self.query=tk.StringVar();self.unassigned=tk.BooleanVar();self.offset=0;self.changed=changed
        bar=ttk.Frame(self,style='Surface.TFrame');bar.pack(fill='x')
        ttk.Label(bar,text='Buscar cliente por nombre o documento').pack(anchor='w')
        ttk.Entry(bar,textvariable=self.query).pack(fill='x',pady=5)
        ttk.Checkbutton(bar,text='Sólo clientes sin rutina',variable=self.unassigned,command=self.search).pack(anchor='w')
        self.list=CheckList(self,lambda *_:self.selection_changed());self.list.pack(fill='both',expand=True,pady=8)
        self.summary=ttk.Label(self,text='0 clientes seleccionados');self.summary.pack(anchor='w')
        pager=ttk.Frame(self);pager.pack(fill='x')
        ttk.Button(pager,text='Anterior',command=lambda:self.page(-1)).pack(side='left')
        self.next_button=ttk.Button(pager,text='Siguiente',command=lambda:self.page(1));self.next_button.pack(side='left',padx=6)
        self.query.trace_add('write',lambda *_:self.later('clients',self.search));self.after_idle(self.refresh)

    def selection_changed(self):
        self.summary.configure(text=f'{len(self.list.checked)} clientes seleccionados');self.changed()

    def search(self):self.offset=0;self.refresh()
    def page(self,delta):self.offset=max(0,self.offset+delta*50);self.refresh()
    def refresh(self):
        query=dict(query=self.query.get().strip(),unassigned=self.unassigned.get(),offset=self.offset,limit=50)
        self.load_view('clients',lambda:self.db.training('clients',query),self.render,tuple(query.values()))
    def render(self,rows):
        self.list.show(rows,lambda r:(str(r.get('document',''))+' · ' if r.get('document') else '')+('Con rutina' if r['has_routine'] else 'Sin rutina'));self.next_button.configure(state='normal' if len(rows)==50 else 'disabled')
        self.selection_changed()
        if not rows:self._view_status.set('No hay clientes que coincidan con esta búsqueda.')


class RoutineEditor(Window):
    def __init__(self,parent,initial=None,edit=False,template_edit=False):
        selection=ExerciseSelection()
        if initial and initial.get('exercises'):selection.load(initial['exercises'],allow_legacy=True)
        # Load before creating a modal: failures leave no orphan form.
        loaded=run_io(parent,lambda:(parent.db.training('catalog'),parent.db.training('templates'),parent.db.training('trainers'),date.fromisoformat(parent.db.training('context')['today'])))
        super().__init__(parent,'Asignar rutina');self.initial=initial or {};self.edit=edit;self.template_edit=template_edit;self.selection=selection;self.loading_fields=False
        self.catalog,self.templates,self.trainers,today=loaded
        for value in self.selection.items.values():
            if not value.get('catalog_id'):
                exact=[r for r in self.catalog if folded(r['name'])==folded(value['name'])]
                if len(exact)==1:value['catalog_id']=str(exact[0]['id'])
        self.catalog_by_id={str(r['id']):r for r in self.catalog}
        self.name=tk.StringVar(value=self.initial.get('name','Plan de entrenamiento'));self.goal=tk.StringVar(value=self.initial.get('goal',''))
        self.notes=tk.StringVar(value=self.initial.get('notes',''));self.start=tk.StringVar(value=str(self.initial.get('start_date') or today))
        self.coaches={'Sin asignar':None,**{f"{t['name']} · {t['id']}":t['id'] for t in self.trainers}}
        self.trainer=tk.StringVar(value=next((k for k,v in self.coaches.items() if v==self.initial.get('trainer_id')),'Sin asignar'))
        tabs=ttk.Notebook(self.body);tabs.grid(row=0,column=0,sticky='nsew');self.tabs=tabs
        details=ttk.Frame(tabs,padding=12,style='Card.TFrame');details.columnconfigure((0,1),weight=1);tabs.add(details,text='Plan')
        self.template_choices={'Seleccionar plantilla':None,**{f"{t['name']} · {t['id'][:6]}":t for t in self.templates}}
        self.template=tk.StringVar(value='Seleccionar plantilla')
        text_field(details,'Plantilla de partida',self.template,0,options=list(self.template_choices))
        ttk.Button(details,text='Usar plantilla',command=self.use_template).grid(row=0,column=1,padx=8,sticky='ew')
        text_field(details,'Nombre de la rutina',self.name,1);text_field(details,'Entrenador',self.trainer,1,1,list(self.coaches))
        text_field(details,'Objetivo',self.goal,2);text_field(details,'Fecha de inicio (AAAA-MM-DD)',self.start,2,1)
        text_field(details,'Indicaciones generales',self.notes,3)
        ttk.Label(details,text='Las plantillas son ejemplos. Revisa ejercicios y parámetros antes de asignar.',style='CardMuted.TLabel',wraplength=650).grid(row=4,column=0,columnspan=2,sticky='w',pady=14)
        exercises=ttk.Frame(tabs,padding=10,style='Card.TFrame');exercises.columnconfigure((0,1),weight=1);tabs.add(exercises,text='Ejercicios')
        filters=ttk.Frame(exercises);filters.grid(row=0,column=0,columnspan=2,sticky='ew');filters.columnconfigure((0,1,2),weight=1)
        self.query=tk.StringVar();self.muscle=tk.StringVar(value='Todos');self.equipment=tk.StringVar(value='Todos')
        text_field(filters,'Buscar ejercicio',self.query,0);text_field(filters,'Grupo muscular',self.muscle,0,1,['Todos',*GROUPS]);text_field(filters,'Equipamiento',self.equipment,0,2,['Todos',*sorted({r.get('equipment','') for r in self.catalog})])
        self.picker=CheckList(exercises,self.toggle,height=8);self.picker.grid(row=1,column=0,sticky='nsew',padx=(0,8))
        chosen=ttk.Frame(exercises,style='Surface.TFrame');chosen.grid(row=1,column=1,sticky='nsew');self.chosen=table(chosen,[('name','Seleccionados',180),('day','Día',80)],height=7)
        self.chosen.bind('<<TreeviewSelect>>',lambda _:self.load_fields())
        row=ttk.Frame(chosen);row.pack(fill='x',pady=6)
        for label,fn in [('Subir',lambda:self.move(-1)),('Bajar',lambda:self.move(1)),('Quitar',self.remove),('Otro día',self.repeat_exercise),('Vincular',self.resolve_exercise)]:ttk.Button(row,text=label,command=fn).pack(side='left',padx=2)
        params=ttk.Frame(exercises,style='Surface.TFrame');params.grid(row=2,column=0,columnspan=2,sticky='ew');params.columnconfigure((0,1,2,3),weight=1)
        self.params={k:tk.StringVar() for k in ('day','sets','reps','weight_kg','rest_seconds','notes')}
        for i,(key,label) in enumerate([('day','Día o días'),('sets','Series'),('reps','Repeticiones'),('weight_kg','Peso sugerido (kg)'),('rest_seconds','Descanso (segundos)'),('notes','Indicaciones del ejercicio')]):
            text_field(params,label,self.params[key],i//4,i%4)
            self.params[key].trace_add('write',lambda *_,key=key:self.store_field(key))
        self.count=ttk.Label(exercises,text='0 ejercicios seleccionados',style='Field.TLabel');self.count.grid(row=3,column=0,columnspan=2,sticky='w',pady=8)
        self.clients=ClientPicker(tabs,self.db);tabs.add(self.clients,text='Clientes')
        if self.initial.get('clients'):
            self.clients.list.checked={str(i) for i in self.initial['clients']}
        if self.edit:
            self.clients.list.checked={str(self.initial['client_id'])}
            tabs.tab(self.clients,state='disabled')
        for variable in (self.query,self.muscle,self.equipment):variable.trace_add('write',lambda *_:self.later_filter())
        self.filter_job=None
        self.render_selection();self.filter_catalog()
        ttk.Button(self.footer,text='Asignar rutina' if not edit else 'Guardar cambios',style='Primary.TButton',command=self.save).pack(side='left',padx=5)
        ttk.Button(self.footer,text='Guardar plantilla',command=self.save_template).pack(side='left',padx=5)
        self.bind('<Destroy>',self.cleanup,add='+')

    def cleanup(self,event):
        if event.widget is self and self.filter_job:
            self.after_cancel(self.filter_job);self.filter_job=None

    def later_filter(self):
        if self.filter_job:self.after_cancel(self.filter_job)
        self.filter_job=self.after(120,self.filter_catalog)

    def filter_catalog(self):
        self.filter_job=None;self.picker.checked=self.selection.catalog_ids
        self.picker.show([r for r in self.catalog if matches(r,self.query.get(),'' if self.muscle.get()=='Todos' else self.muscle.get(),'' if self.equipment.get()=='Todos' else self.equipment.get())],lambda r:r.get('muscle','')+' · '+r.get('equipment',''))

    def toggle(self,key,row):self.selection.toggle(row);self.render_selection()
    def render_selection(self):
        populate(self.chosen,[dict(v,id=k) for k,v in self.selection.items.items()],lambda r:(r['name']+(' · Pendiente' if not r.get('catalog_id') else ''),r.get('day','')))
        self.count.configure(text=f'{len(self.selection.items)} ejercicios seleccionados')
        self.picker.checked=self.selection.catalog_ids;self.picker.render_icons()
        if not self.chosen.selection() and self.chosen.get_children():self.chosen.selection_set(self.chosen.get_children()[0])
    def load_fields(self):
        key=next(iter(self.chosen.selection()),None);item=self.selection.items.get(key)
        if item:
            self.loading_fields=True
            for k,v in self.params.items():v.set(item.get(k,''))
            self.loading_fields=False
    def store_field(self,key):
        selected=next(iter(self.chosen.selection()),None)
        if not self.loading_fields and selected in self.selection.items:
            self.selection.items[selected][key]=self.params[key].get()
            if key=='day':self.chosen.set(selected,'day',self.params[key].get())
    def move(self,delta):
        selected=next(iter(self.chosen.selection()),None)
        if selected:self.selection.move(selected,delta);self.render_selection()
    @guarded
    def resolve_exercise(self):
        selected=next(iter(self.chosen.selection()),None);catalog=next(iter(self.picker.tree.selection()),None)
        if selected is None or catalog is None:raise ValueError('Selecciona el ejercicio del plan a la derecha y su equivalente del catálogo a la izquierda. Después pulsa Vincular.')
        self.selection.resolve(selected,self.catalog_by_id[catalog]);self.render_selection()
    def repeat_exercise(self):
        selected=next(iter(self.chosen.selection()),None)
        if selected:self.selection.duplicate(selected);self.render_selection()
    def remove(self):
        selected=next(iter(self.chosen.selection()),None)
        if selected:self.selection.items.pop(selected,None);self.render_selection()
    @guarded
    def use_template(self):
        template=self.template_choices.get(self.template.get())
        if not template:return
        if self.selection.items and not messagebox.askyesno('Usar plantilla','¿Reemplazar los ejercicios seleccionados por esta plantilla?',parent=self):return
        self.selection.load([dict(e,name=self.catalog_by_id.get(str(e['catalog_id']),{}).get('name','Ejercicio no disponible')) for e in template['exercises']])
        self.name.set(template['name']);self.goal.set(template.get('goal',''));self.notes.set(template.get('notes',''));self.render_selection();self.filter_catalog()
        self.tabs.select(1)
    def payload(self):
        if not 2<=len(self.name.get().strip())<=120:raise ValueError('Escribe un nombre de 2 a 120 caracteres.')
        date.fromisoformat(self.start.get().strip())
        return dict(name=self.name.get().strip(),goal=self.goal.get().strip(),notes=self.notes.get().strip(),start_date=self.start.get().strip(),trainer_id=self.coaches.get(self.trainer.get()),exercises=self.selection.payload())
    @guarded
    def save(self):
        data=self.payload();clients=sorted(int(i) for i in self.clients.list.checked)
        if not clients or len(clients)>50:raise ValueError('Selecciona de 1 a 50 clientes en la pestaña Clientes.')
        data['clients']=clients
        if self.edit:data['previous_id']=self.initial['id']
        if not messagebox.askyesno('Asignar rutina',f"Se guardará el plan para {len(clients)} cliente(s). ¿Confirmas la asignación?",parent=self):return
        self.result=self.write('routine.assign',data);self.saved_action='routine.assign';self.destroy()
    @guarded
    def save_template(self):
        data=self.payload()
        if self.template_edit and self.initial.get('gym_id'):data['id']=self.initial['id']
        self.result=self.write('template.save',data);self.saved_action='template.save'
        messagebox.showinfo('Plantilla guardada','La plantilla ya está disponible para futuras asignaciones.',parent=self)
        self.destroy()


class ExerciseEditor(Window):
    def __init__(self,parent,initial=None):
        super().__init__(parent,'Ejercicio del gimnasio',640,650);self.initial=initial or {};self.fields={}
        self.body.columnconfigure((0,1),weight=1)
        for i,(key,label,default) in enumerate([('name','Nombre',''),('muscle','Grupo muscular','Pecho'),('equipment','Equipamiento','Sin equipamiento'),('instructions','Indicaciones',''),('image_url','Imagen (HTTPS, opcional)',''),('video_url','Video (HTTPS, opcional)',''),('sort_order','Orden en el catálogo',0)]):
            self.fields[key]=tk.StringVar(value=self.initial.get(key,default));text_field(self.body,label,self.fields[key],i,options=list(GROUPS) if key=='muscle' else None)
        self.active=tk.BooleanVar(value=self.initial.get('active',True));ttk.Checkbutton(self.body,text='Disponible para nuevas rutinas',variable=self.active).grid(row=8,column=0,sticky='w')
        ttk.Button(self.footer,text='Guardar ejercicio',style='Primary.TButton',command=self.save).pack(side='left')
    @guarded
    def save(self):
        data={k:v.get().strip() for k,v in self.fields.items()};data['active']=self.active.get();data['sort_order']=int(data['sort_order'])
        if self.initial.get('gym_id'):data['id']=self.initial['id']
        self.result=self.write('catalog.save',data);self.destroy()


class RoutinesWorkspace(AsyncPanel):
    def __init__(self,parent,db,autostart=True):
        super().__init__(parent,db);self.query=tk.StringVar();self.state=tk.StringVar(value='ACTIVA');self.offset=0;self.rows=[];self.catalog=[];self.templates=[]
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True);self.tabs=tabs
        plans=ttk.Frame(tabs,padding=8,style='Card.TFrame');tabs.add(plans,text='Asignaciones')
        tools=ttk.Frame(plans,style='Surface.TFrame');tools.pack(fill='x');tools.columnconfigure((0,1),weight=1)
        self.search_entry=text_field(tools,'Buscar rutina, cliente o entrenador',self.query,0)
        text_field(tools,'Estado',self.state,0,1,['ACTIVA','HISTORIAL','TODAS'])
        self.tree=table(plans,[('name','Rutina',210),('client','Cliente',200),('trainer','Entrenador',180),('count','Ejercicios',70),('start','Inicio',100),('state','Estado',90)],8)
        actions=ttk.Frame(plans);actions.pack(fill='x',pady=8,before=self.tree.master)
        for label,fn in [('Asignar rutina',self.assign),('Editar plan',self.edit),('Duplicar',self.duplicate),('Ver ejercicios',self.detail)]:ttk.Button(actions,text=label,command=fn,style='Primary.TButton' if label=='Asignar rutina' else 'TButton').pack(side='left',padx=3)
        self.pager=ttk.Label(plans);self.pager.pack(anchor='w')
        row=ttk.Frame(plans);row.pack(fill='x')
        ttk.Button(row,text='Anterior',command=lambda:self.page(-1)).pack(side='left');self.next_button=ttk.Button(row,text='Siguiente',command=lambda:self.page(1));self.next_button.pack(side='left',padx=5)
        catalog=ttk.Frame(tabs,padding=8,style='Card.TFrame');tabs.add(catalog,text='Ejercicios')
        self.catalog_query=tk.StringVar();self.catalog_group=tk.StringVar(value='Todos');self.catalog_equipment=tk.StringVar(value='Todos');self.include_inactive=tk.BooleanVar()
        filters=ttk.Frame(catalog);filters.pack(fill='x');filters.columnconfigure((0,1,2),weight=1)
        text_field(filters,'Buscar ejercicio',self.catalog_query,0);text_field(filters,'Grupo muscular',self.catalog_group,0,1,['Todos',*GROUPS])
        self.equipment_filter=text_field(filters,'Equipamiento',self.catalog_equipment,0,2,['Todos'])
        ttk.Checkbutton(catalog,text='Mostrar desactivados',variable=self.include_inactive,command=self.refresh_catalog).pack(anchor='w')
        self.catalog_tree=table(catalog,[('name','Ejercicio',260),('muscle','Grupo',150),('equipment','Equipamiento',160),('scope','Origen',100),('active','Estado',100)],8)
        actions=ttk.Frame(catalog);actions.pack(fill='x',pady=8,before=self.catalog_tree.master)
        ttk.Button(actions,text='Crear ejercicio',command=self.create_exercise).pack(side='left',padx=3)
        ttk.Button(actions,text='Editar o crear variante',command=self.edit_exercise).pack(side='left',padx=3)
        templates=ttk.Frame(tabs,padding=8,style='Card.TFrame');tabs.add(templates,text='Plantillas')
        self.template_tree=table(templates,[('name','Plantilla',260),('goal','Objetivo',280),('count','Ejercicios',90),('scope','Origen',100)],8)
        row=ttk.Frame(templates);row.pack(fill='x',pady=8)
        for label,fn in [('Usar plantilla',self.from_template),('Editar o duplicar',self.edit_template),('Crear plantilla',self.new_template)]:ttk.Button(row,text=label,command=fn).pack(side='left',padx=3)
        clients=ClientPicker(tabs,db);tabs.add(clients,text='Clientes sin rutina');clients.unassigned.set(True);self.unassigned=clients
        ttk.Button(clients,text='Asignar a los seleccionados',command=self.assign_unassigned,style='Primary.TButton').pack(anchor='w',pady=8)
        for v in (self.query,self.state):v.trace_add('write',lambda *_:self.later('routines',self.search))
        for v in (self.catalog_query,self.catalog_group,self.catalog_equipment):v.trace_add('write',lambda *_:self.later('catalog_filter',self.render_catalog))
        ttk.Button(self,text='Actualizar',command=self.refresh).pack(anchor='w',pady=8)
        if autostart:self.after_idle(self.refresh)
    def search(self):self.offset=0;self.refresh_plans()
    def page(self,delta):self.offset=max(0,self.offset+delta*50);self.refresh_plans()
    def refresh(self):self.refresh_plans();self.refresh_catalog();self.refresh_templates();self.unassigned.refresh()
    def refresh_plans(self):
        data=dict(query=self.query.get(),offset=self.offset,limit=50)
        if self.state.get()!='TODAS':data['status']='ACTIVA' if self.state.get()=='ACTIVA' else 'ARCHIVADA'
        self.load_view('routines',lambda:self.db.training('routines',data),self.render_plans,tuple(data.values()))
    def render_plans(self,rows):
        self.rows=rows;populate(self.tree,rows,lambda r:(r['name'],r['client_name'],r['trainer_name'],r['exercise_count'],r['start_date'],'Activa' if r['active'] else 'Archivada'))
        self.pager.configure(text=f'{len(rows)} asignaciones · Página {self.offset//50+1}' if rows else 'No hay asignaciones que coincidan con los filtros.')
        self.next_button.configure(state='normal' if len(rows)==50 else 'disabled')
    def refresh_catalog(self):
        flag=self.include_inactive.get();self.load_view('catalog',lambda:self.db.training('catalog',{'include_inactive':flag}),self.loaded_catalog,(flag,))
    def loaded_catalog(self,rows):
        self.catalog=rows;self.equipment_filter.configure(values=['Todos',*sorted({r.get('equipment','') for r in rows})]);self.render_catalog()
    def render_catalog(self):
        rows=[r for r in self.catalog if matches(r,self.catalog_query.get(),'' if self.catalog_group.get()=='Todos' else self.catalog_group.get(),'' if self.catalog_equipment.get()=='Todos' else self.catalog_equipment.get())]
        populate(self.catalog_tree,rows,lambda r:(r['name'],r['muscle'],r['equipment'],'Gimnasio' if r.get('gym_id') else 'Global','Activo' if r['active'] else 'Desactivado'))
    def refresh_templates(self):self.load_view('templates',lambda:self.db.training('templates'),self.render_templates)
    def render_templates(self,rows):
        self.templates=rows;populate(self.template_tree,rows,lambda r:(r['name'],r['goal'],len(r['exercises']),'Gimnasio' if r['gym_id'] else 'Ejemplo'))
    def selected(self,tree,rows):
        selected=next(iter(tree.selection()),None);row=next((r for r in rows if str(r['id'])==selected),None)
        if row is None:raise ValueError('Selecciona un registro de la lista.')
        return row
    def open_editor(self,initial=None,edit=False,template_edit=False):
        editor=RoutineEditor(self,initial,edit,template_edit);self.wait_window(editor)
        if editor.result:
            if editor.saved_action=='template.save':self.refresh_templates();self.feedback.set('Plantilla guardada.')
            else:self.refresh_plans();self.unassigned.refresh();self.feedback.set('Rutina guardada para los clientes seleccionados.')
    @guarded
    def assign_unassigned(self):
        if not self.unassigned.list.checked:raise ValueError('Selecciona al menos un cliente.')
        self.open_editor({'clients':list(self.unassigned.list.checked)})
    @guarded
    def assign(self):self.open_editor()
    @guarded
    def edit(self):
        row=self.selected(self.tree,self.rows)
        if not row['active']:raise ValueError('Duplica el plan archivado para volver a utilizarlo.')
        self.open_editor(self.db.training('routine.detail',{'id':row['id']}),True)
    @guarded
    def duplicate(self):
        row=self.selected(self.tree,self.rows);data=self.db.training('routine.detail',{'id':row['id']});data['name']='Copia de '+data['name'];self.open_editor(data)
    @guarded
    def detail(self):
        row=self.selected(self.tree,self.rows);data=self.db.training('routine.detail',{'id':row['id']})
        window=Window(self,'Ejercicios asignados',800,560)
        tree=table(window.body,[('day','Día',90),('name','Ejercicio',240),('sets','Series',60),('reps','Reps',60),('weight','Kg',60),('rest','Descanso',75)],10)
        populate(tree,data['exercises'],lambda e:(e['day_name'],e['name'],e['sets'],e['reps'],e['weight'],e.get('league_rest_seconds',90)))
    @guarded
    def create_exercise(self):
        editor=ExerciseEditor(self);self.wait_window(editor)
        if editor.result:self.refresh_catalog()
    @guarded
    def edit_exercise(self):
        editor=ExerciseEditor(self,self.selected(self.catalog_tree,self.catalog));self.wait_window(editor)
        if editor.result:self.refresh_catalog()
    def template_data(self):
        data=dict(self.selected(self.template_tree,self.templates));catalog={r['id']:r['name'] for r in self.catalog}
        data['exercises']=[dict(e,name=catalog.get(e['catalog_id'],'Ejercicio no disponible')) for e in data['exercises']];return data
    @guarded
    def from_template(self):self.open_editor(self.template_data())
    @guarded
    def edit_template(self):self.open_editor(self.template_data(),template_edit=True)
    @guarded
    def new_template(self):self.open_editor()


class ClassEditor(Window):
    def __init__(self,parent,initial=None):
        trainers,today=run_io(parent,lambda:(parent.db.training('trainers'),date.fromisoformat(parent.db.training('context')['today'])))
        super().__init__(parent,'Editar clase' if initial else 'Programar clase',760,700);self.initial=initial or {};self.fields={}
        self.coaches={'Sin asignar':None,**{f"{t['name']} · {t['id']}":t['id'] for t in trainers}}
        current=self.initial.get('starts_at')
        current=display_timestamp(current,timezone_for(self.db),seconds=False) if current else str(today)+' 18:00'
        defaults=[('name','Nombre de la clase','',None),('trainer','Entrenador','Sin asignar',list(self.coaches)),
            ('starts_at','Fecha y hora local (AAAA-MM-DD HH:MM)',current,None),('duration_minutes','Duración (minutos)',60,None),
            ('capacity','Cupos',15,None),('status','Estado','PROGRAMADA',['PROGRAMADA','CANCELADA','FINALIZADA']),
            ('notes','Descripción','',None),('conditions','Condiciones de inscripción','',None),('repeat_count','Cantidad de fechas (1–26)',1,None),('interval_weeks','Repetir cada cuántas semanas',1,None)]
        self.body.columnconfigure((0,1),weight=1)
        for i,(key,title,default,options) in enumerate(defaults):
            if key in ('repeat_count','interval_weeks') and initial:continue
            value=(self.initial.get(key) if self.initial.get(key) is not None else default) if key!='starts_at' else current
            if key=='trainer':value=next((k for k,v in self.coaches.items() if v==self.initial.get('trainer_id')),'Sin asignar')
            self.fields[key]=tk.StringVar(value=value);text_field(self.body,title,self.fields[key],i//2,i%2,options)
        self.membership=tk.BooleanVar(value=self.initial.get('requires_membership',True))
        ttk.Checkbutton(self.body,text='Requiere membresía vigente y habilitada para inscribirse',variable=self.membership).grid(row=6,column=0,columnspan=2,sticky='w',pady=10)
        ttk.Label(self.body,text='Las repeticiones se crean como fechas independientes. Puedes editar o cancelar cada una sin afectar las demás.',style='CardMuted.TLabel',wraplength=620).grid(row=7,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Button(self.footer,text='Guardar clase',style='Primary.TButton',command=self.save).pack(side='left')
    @guarded
    def save(self):
        data={k:v.get().strip() for k,v in self.fields.items()};data['trainer_id']=self.coaches.get(data.pop('trainer'))
        data['starts_at']=local_wall_instant(data['starts_at'],timezone_for(self.db)).isoformat()
        for key in ('duration_minutes','capacity','repeat_count','interval_weeks'):
            if key in data:data[key]=int(data[key])
        data['requires_membership']=self.membership.get()
        if self.initial:data.update(id=self.initial['id'],version=self.initial['version'])
        if data.get('status')=='CANCELADA' and not messagebox.askyesno('Cancelar clase','Se cancelarán también sus reservas pendientes. ¿Deseas continuar?',parent=self):return
        self.result=self.write('class.save',data);self.destroy()


class ReservationEditor(Window):
    def __init__(self,parent,gym_class):
        super().__init__(parent,'Reservar un cupo',720,650);self.gym_class=gym_class
        ttk.Label(self.body,text=gym_class['name'],style='Section.TLabel').pack(anchor='w')
        ttk.Label(self.body,text=f"{gym_class['reserved']} de {gym_class['capacity']} cupos ocupados · "+display_timestamp(gym_class['starts_at'],timezone_for(self.db),seconds=False)).pack(anchor='w',pady=8)
        self.picker=ClientPicker(self.body,self.db);self.picker.pack(fill='both',expand=True)
        ttk.Button(self.footer,text='Confirmar reserva',style='Primary.TButton',command=self.save).pack(side='left')
    @guarded
    def save(self):
        if len(self.picker.list.checked)!=1:raise ValueError('Selecciona un solo cliente para esta reserva.')
        self.result=self.write('reservation.reserve',dict(class_id=self.gym_class['id'],client_id=int(next(iter(self.picker.list.checked)))));self.destroy()


class ClassesWorkspace(AsyncPanel):
    def __init__(self,parent,db,autostart=True):
        super().__init__(parent,db);self.rows=[];self.reservation_rows=[];self.coaches={'Todos':None};self.offset=0;self.res_offset=0;self.selected_class=None
        self.query=tk.StringVar();self.trainer=tk.StringVar(value='Todos');self.state=tk.StringVar(value='TODAS');self.date_from=tk.StringVar();self.date_to=tk.StringVar()
        self.res_query=tk.StringVar();self.res_state=tk.StringVar(value='TODAS');self.res_from=tk.StringVar();self.res_to=tk.StringVar();self.only_selected=tk.BooleanVar(value=False)
        self.calendar_date=None;self.calendar_counts={}
        tabs=ttk.Notebook(self);tabs.pack(fill='both',expand=True);self.tabs=tabs
        classes=ttk.Frame(tabs,padding=8,style='Card.TFrame');tabs.add(classes,text='Clases')
        filters=ttk.Frame(classes);filters.pack(fill='x');filters.columnconfigure((0,1,2),weight=1)
        self.search_entry=text_field(filters,'Buscar clase',self.query,0);self.trainer_filter=text_field(filters,'Entrenador',self.trainer,0,1,['Todos']);text_field(filters,'Estado',self.state,0,2,['TODAS','PROGRAMADA','CANCELADA','FINALIZADA'])
        text_field(filters,'Desde (AAAA-MM-DD)',self.date_from,1);text_field(filters,'Hasta (AAAA-MM-DD)',self.date_to,1,1)
        ttk.Button(filters,text='Lista / Calendario',command=self.toggle_calendar).grid(row=1,column=2,sticky='ew',padx=5)
        self.calendar_frame=ttk.Frame(classes,style='Surface.TFrame');self.calendar_visible=False
        self.calendar_frame.columnconfigure(tuple(range(7)),weight=1,uniform='month')
        self.calendar_title=ttk.Label(self.calendar_frame,style='Section.TLabel');self.calendar_title.grid(row=0,column=1,columnspan=5)
        ttk.Button(self.calendar_frame,text='Anterior',style='Calendar.TButton',command=lambda:self.month(-1)).grid(row=0,column=0,sticky='ew')
        ttk.Button(self.calendar_frame,text='Siguiente',style='Calendar.TButton',command=lambda:self.month(1)).grid(row=0,column=6,sticky='ew')
        self.calendar_days=ttk.Frame(self.calendar_frame);self.calendar_days.grid(row=1,column=0,columnspan=7,sticky='ew')
        self.tree=table(classes,[('name','Clase',210),('date','Horario',155),('trainer','Entrenador',150),('slots','Ocupados / cupos',110),('free','Disponibles',85),('state','Estado',100)],7)
        self.tree.bind('<<TreeviewSelect>>',self.select_class);self.tree.bind('<Double-1>',lambda _:self.edit())
        actions=ttk.Frame(classes);actions.pack(fill='x',pady=8,before=self.tree.master)
        for label,fn in [('Programar clase',self.create),('Editar / reprogramar',self.edit),('Reservar cliente',self.reserve),('Ver participantes',self.participants)]:ttk.Button(actions,text=label,command=fn,style='Primary.TButton' if label=='Programar clase' else 'TButton').pack(side='left',padx=3)
        self.summary=ttk.Label(classes);self.summary.pack(anchor='w');row=ttk.Frame(classes);row.pack(fill='x')
        ttk.Button(row,text='Anterior',command=lambda:self.page(-1)).pack(side='left');self.next_button=ttk.Button(row,text='Siguiente',command=lambda:self.page(1));self.next_button.pack(side='left',padx=5)
        reservations=ttk.Frame(tabs,padding=8,style='Card.TFrame');tabs.add(reservations,text='Reservas y asistencia')
        filters=ttk.Frame(reservations);filters.pack(fill='x');filters.columnconfigure((0,1),weight=1)
        text_field(filters,'Buscar cliente, documento o clase',self.res_query,0);text_field(filters,'Estado',self.res_state,0,1,['TODAS','RESERVADA','CANCELADA','ASISTIO'])
        text_field(filters,'Desde (AAAA-MM-DD)',self.res_from,1);text_field(filters,'Hasta (AAAA-MM-DD)',self.res_to,1,1)
        ttk.Checkbutton(reservations,text='Sólo la clase seleccionada',variable=self.only_selected,command=self.res_search).pack(anchor='w',pady=5)
        self.participants_label=ttk.Label(reservations,text='Reservas de todas las clases',style='Section.TLabel');self.participants_label.pack(anchor='w',pady=5)
        self.reservations=table(reservations,[('client','Cliente',190),('document','Documento',110),('class','Clase',180),('date','Horario',145),('status','Estado',90)],8)
        row=ttk.Frame(reservations);row.pack(fill='x',pady=8,before=self.reservations.master)
        for label,fn in [('Registrar asistencia',self.attend),('Cancelar reserva',self.cancel),('Ver historial',self.history)]:ttk.Button(row,text=label,command=fn).pack(side='left',padx=3)
        self.res_summary=ttk.Label(reservations);self.res_summary.pack(anchor='w');row=ttk.Frame(reservations);row.pack(fill='x')
        ttk.Button(row,text='Anterior',command=lambda:self.res_page(-1)).pack(side='left');self.res_next=ttk.Button(row,text='Siguiente',command=lambda:self.res_page(1));self.res_next.pack(side='left',padx=5)
        for v in (self.query,self.trainer,self.state,self.date_from,self.date_to):v.trace_add('write',lambda *_:self.later('classes',self.search))
        for v in (self.res_query,self.res_state,self.res_from,self.res_to):v.trace_add('write',lambda *_:self.later('reservations',self.res_search))
        ttk.Button(self,text='Actualizar',command=self.refresh).pack(anchor='w',pady=8)
        if autostart:self.after_idle(self.refresh)
    def refresh(self):
        self.refresh_classes();self.refresh_reservations();self.load_view('trainers',lambda:self.db.training('trainers'),self.render_trainers)
    def render_trainers(self,rows):
        self.coaches={'Todos':None,**{f"{t['name']} · {t['id']}":t['id'] for t in rows}};self.trainer_filter.configure(values=list(self.coaches))
    def search(self):self.offset=0;self.refresh_classes()
    def page(self,delta):self.offset=max(0,self.offset+delta*50);self.refresh_classes()
    def dates(self,data,start,end):
        for key,variable in [('date_from',start),('date_to',end)]:
            if variable.get().strip():
                try:date.fromisoformat(variable.get().strip())
                except ValueError:self._view_status.set('Escribe las fechas con el formato AAAA-MM-DD.');return False
                data[key]=variable.get().strip()
        if data.get('date_from','')>data.get('date_to','9999-12-31'):
            self._view_status.set('La fecha inicial debe ser anterior a la final.');return False
        return True
    def refresh_classes(self):
        data=dict(query=self.query.get(),offset=self.offset,limit=50)
        if self.trainer.get()!='Todos':data['trainer_id']=self.coaches.get(self.trainer.get())
        if self.state.get()!='TODAS':data['status']=self.state.get()
        if not self.dates(data,self.date_from,self.date_to):return
        self.load_view('classes',lambda:self.db.training('classes',data),self.render_classes,tuple(data.values()))
    def render_classes(self,rows):
        self.rows=rows;populate(self.tree,rows,lambda r:(r['name'],display_timestamp(r['starts_at'],timezone_for(self.db),seconds=False),r['trainer_name'],f"{r['reserved']} / {r['capacity']}",max(0,r['capacity']-r['reserved']),r['status']))
        self.summary.configure(text=f'{len(rows)} clases · Página {self.offset//50+1}' if rows else 'No hay clases con estos filtros.');self.next_button.configure(state='normal' if len(rows)==50 else 'disabled')
        if self.calendar_visible:self.load_calendar()
        current=next((r for r in rows if self.selected_class and r['id']==self.selected_class['id']),None)
        self.selected_class=current
        if self.only_selected.get() and not current:self.refresh_reservations()
    def select_class(self,event=None):
        key=next(iter(self.tree.selection()),None);self.selected_class=next((r for r in self.rows if str(r['id'])==key),None)
        if self.only_selected.get():self.res_search()
    def require_class(self):
        if not self.selected_class:raise ValueError('Selecciona una clase de la lista.')
        return self.selected_class
    def res_search(self):self.res_offset=0;self.refresh_reservations()
    def res_page(self,delta):self.res_offset=max(0,self.res_offset+delta*50);self.refresh_reservations()
    def refresh_reservations(self):
        data=dict(query=self.res_query.get(),offset=self.res_offset,limit=50)
        if self.res_state.get()!='TODAS':data['status']=self.res_state.get()
        if not self.dates(data,self.res_from,self.res_to):return
        if self.only_selected.get():
            if not self.selected_class:
                self.load_view('reservations',lambda:[],self.render_reservations,(None,));self.participants_label.configure(text='Selecciona primero una clase.');return
            data['class_id']=self.selected_class['id']
        self.participants_label.configure(text=self.selected_class['name'] if self.only_selected.get() and self.selected_class else 'Reservas de todas las clases')
        self.load_view('reservations',lambda:self.db.training('reservations',data),self.render_reservations,tuple(data.values()))
    def render_reservations(self,rows):
        self.reservation_rows=rows;populate(self.reservations,rows,lambda r:(r['client_name'],r.get('document',''),r['class_name'],display_timestamp(r['starts_at'],timezone_for(self.db),seconds=False),r['status']))
        self.res_summary.configure(text=f'{len(rows)} reservas · Página {self.res_offset//50+1}' if rows else 'No hay reservas con estos filtros.');self.res_next.configure(state='normal' if len(rows)==50 else 'disabled')
    @guarded
    def create(self):
        editor=ClassEditor(self);self.wait_window(editor)
        if editor.result:self.refresh()
    @guarded
    def edit(self):
        editor=ClassEditor(self,self.require_class());self.wait_window(editor)
        if editor.result:self.refresh()
    @guarded
    def reserve(self):
        editor=ReservationEditor(self,self.require_class());self.wait_window(editor)
        if editor.result:self.refresh()
    @guarded
    def participants(self):
        self.require_class();self.only_selected.set(True);self.tabs.select(1);self.res_search()
    def reservation(self):
        key=next(iter(self.reservations.selection()),None);row=next((r for r in self.reservation_rows if str(r['id'])==key),None)
        if not row:raise ValueError('Selecciona una reserva de la lista.')
        return row
    @guarded
    def attend(self):
        row=self.reservation();self.write('reservation.attend',{'id':row['id']});self.refresh()
    @guarded
    def cancel(self):
        row=self.reservation()
        if messagebox.askyesno('Cancelar reserva','¿Cancelar la reserva de '+row['client_name']+'?',parent=self):self.write('reservation.cancel',{'id':row['id']});self.refresh()
    @guarded
    def history(self):
        row=self.reservation();rows=self.db.training('reservation.history',{'id':row['id']})
        window=Window(self,'Historial de reserva',760,520)
        tree=table(window.body,[('date','Fecha',180),('previous','Antes',120),('status','Después',120)],8)
        populate(tree,rows,lambda r:(display_timestamp(r['created_at'],timezone_for(self.db),seconds=False),r.get('previous_status') or 'Creada',r['status']))
        if not rows:ttk.Label(window.body,text='Esta reserva es anterior al registro de historial. No se reconstruyen cambios pasados.').pack(anchor='w',pady=12)
    @guarded
    def toggle_calendar(self):
        self.calendar_visible=not self.calendar_visible
        self.tree.configure(height=4 if self.calendar_visible else 7)
        if self.calendar_visible:
            if self.calendar_date is None:
                today=date.fromisoformat(self.db.training('context')['today']);self.calendar_date=date(today.year,today.month,1)
            self.calendar_frame.pack(fill='x',before=self.tree.master);self.month(0)
        else:self.calendar_frame.pack_forget()
    def month(self,delta):
        n=self.calendar_date.year*12+self.calendar_date.month-1+delta;self.calendar_date=date(n//12,n%12+1,1)
        first=self.calendar_date;last=date(first.year,first.month,calendar.monthrange(first.year,first.month)[1])
        self.date_from.set(first.isoformat());self.date_to.set(last.isoformat());self.load_calendar()
    def load_calendar(self):
        if not self.calendar_date:return
        first=self.calendar_date
        data={'date_from':first.isoformat(),'date_to':date(first.year,first.month,calendar.monthrange(first.year,first.month)[1]).isoformat(),'query':self.query.get()}
        if self.trainer.get()!='Todos':data['trainer_id']=self.coaches.get(self.trainer.get())
        if self.state.get()!='TODAS':data['status']=self.state.get()
        def render(rows):
            self.calendar_counts={date.fromisoformat(r['day']):r['classes'] for r in rows};self.refresh_calendar()
        self.load_view('calendar',lambda:self.db.training('class.calendar',data),render,tuple(data.values()))
    def refresh_calendar(self):
        if not self.calendar_date:return
        self.calendar_title.configure(text=f'{self.calendar_date.month:02d} / {self.calendar_date.year}')
        for child in self.calendar_days.winfo_children():child.destroy()
        counts=self.calendar_counts
        for i,title in enumerate(['Lun','Mar','Mié','Jue','Vie','Sáb','Dom']):
            self.calendar_days.columnconfigure(i,weight=1);ttk.Label(self.calendar_days,text=title,anchor='center').grid(row=0,column=i,sticky='ew')
        for week,days in enumerate(calendar.monthcalendar(self.calendar_date.year,self.calendar_date.month),1):
            for col,day in enumerate(days):
                if day:
                    value=date(self.calendar_date.year,self.calendar_date.month,day);number=counts.get(value,0)
                    ttk.Button(self.calendar_days,style='Calendar.TButton',text=f'{day}'+(f' · {number}' if number else ''),command=lambda v=value:self.day(v)).grid(row=week,column=col,sticky='ew',padx=2,pady=2)
        self.summary.configure(text=f'Calendario mensual · {sum(counts.values())} clases. Selecciona un día para consultar sus horarios.')
    def day(self,value):self.date_from.set(value.isoformat());self.date_to.set(value.isoformat())


class TrainingStaffEditor(Window):
    def __init__(self,parent):
        rows=run_io(parent,lambda:parent.db.training('staff'))
        super().__init__(parent,'Permisos de entrenamiento',760,570)
        ttk.Label(self.body,text='Autoriza cuentas del gimnasio para gestionar rutinas, ejercicios, clases y reservas. No otorga permisos administrativos.',style='CardMuted.TLabel',wraplength=650).pack(anchor='w',pady=10)
        self.rows=rows
        self.tree=table(self.body,[('name','Cuenta',300),('role','Rol actual',100),('coach','Entrenamiento',140)],10)
        populate(self.tree,self.rows,lambda r:(r['name'],r['role'],'Autorizado' if r['coach'] or r['role']=='admin' else 'Sin autorización'))
        ttk.Button(self.footer,text='Autorizar / retirar',command=self.change).pack(side='left')
    @guarded
    def change(self):
        selected=next(iter(self.tree.selection()),None);row=next((r for r in self.rows if str(r['id'])==selected),None)
        if not row:raise ValueError('Selecciona una cuenta.')
        if row['role']=='admin':raise ValueError('Los administradores ya tienen acceso a entrenamiento.')
        enabled=not row['coach']
        if not messagebox.askyesno('Permisos de entrenamiento',('¿Autorizar a ' if enabled else '¿Retirar la autorización a ')+row['name']+'?',parent=self):return
        self.write('coach.grant',dict(user_id=row['id'],enabled=enabled));row['coach']=enabled
        populate(self.tree,self.rows,lambda r:(r['name'],r['role'],'Autorizado' if r['coach'] or r['role']=='admin' else 'Sin autorización'))
