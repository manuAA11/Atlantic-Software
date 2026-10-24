import {test} from 'node:test';
import assert from 'node:assert/strict';
import {canBookEvent,gymEventTime} from '../mobile/src/lib/gymSchedule.ts';

test('class times use the gym zone, including a different calendar day',()=>{
 const event={starts_at:'2030-02-10T02:30:00Z',timezone:'America/Bogota'};
 const bogota=gymEventTime(event),tokyo=gymEventTime({...event,timezone:'Asia/Tokyo'});
 assert.equal(bogota.time,'21:30');assert.match(bogota.date,/9/);assert.equal(bogota.zone,'Hora del gimnasio');
 assert.equal(tokyo.time,'11:30');assert.match(tokyo.date,/10/);
 assert.equal(gymEventTime({...event,timezone:'Invalid/Zone'}).zone,'Hora de tu dispositivo');
 assert.equal(gymEventTime({...event,timezone:null}).zone,'Hora de tu dispositivo');
 assert.deepEqual(gymEventTime({...event,starts_at:'invalid'}),{date:'Fecha por confirmar',time:'',zone:''});
});

test('only explicitly open classes bypass membership, and never capacity',()=>{
 const event={capacity:2,reserved:1};
 for(const condition of [undefined,null,true]){
  assert.equal(canBookEvent({...event,requires_membership:condition},null),false);
  assert.equal(canBookEvent({...event,requires_membership:condition},{active:false}),false);
  assert.equal(canBookEvent({...event,requires_membership:condition},{active:true}),true);
 }
 assert.equal(canBookEvent({...event,requires_membership:false},{active:false}),true);
 assert.equal(canBookEvent({...event,reserved:2,requires_membership:false},{active:true}),false);
});
