import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fixture} from './membership_feature_fixture.mjs';
const f=await fixture();const {db,root,gym,other,A,R,B,user,system,rpc,clock,person}=f;
let checks=0;
function ok(value,message){assert.ok(value,message);checks++;}
async function deny(fn,pattern){await assert.rejects(fn,pattern);checks++;}
async function business(fn,pattern){await assert.rejects(fn,e=>e.code==='GS001'&&pattern.test(e.message));checks++;}
const call=(name,params={})=>rpc(name,{p_gym_id:gym,...params});
let n=0;const request=()=>`f1000000-0000-4000-8000-${String(++n).padStart(12,'0')}`;
try{
 // Standalone execution also works before edition migration fixtures include POS.
 await system();await db.exec(fs.readFileSync(path.join(root,'..','common','store_pos.sql'),'utf8'));
 await user(A);
 const save=(data,id=null)=>call('store_pos_save_product',{p_product_id:id,p_data:data});
 const water=await save({name:'Agua POS',sku:'AGUA-POS',barcode:'7701234567890',description:'Botella',category:'Bebidas',sale_price:3000,unit_cost:1000,stock_quantity:10,low_stock_threshold:3});
 const cola=await save({name:'Cola POS',barcode:'7701234567891',category:'Bebidas',sale_price:4000,stock_quantity:6,low_stock_threshold:2});
 ok(water.barcode==='7701234567890'&&water.unit_cost===1000,'barcode and real cost persist');
 await deny(()=>save({name:'Invisible POS',barcode:'ABC\u200b123',sale_price:1}),/barras/i);
 await deny(()=>save({name:'Invisible espacio POS',barcode:'ABC\u00a0123',sale_price:1}),/barras/i);
 await deny(()=>save({name:'Duplicado POS',barcode:water.barcode,sale_price:1}),/barras|barcode|existe/i);
 const optional=await save({name:'Sin barcode POS',barcode:'',sale_price:10});ok(optional.barcode===null,'optional barcode normalized');
 ok((await call('store_pos_products',{p_search:water.barcode}))[0].id===water.id,'barcode search');
 ok((await call('store_pos_products',{p_search:'Bebidas'})).length===2,'category search');
 ok((await call('store_pos_products',{p_search:'AGUA-POS'}))[0].id===water.id,'manual SKU search');
 ok((await call('store_pos_products',{p_search:'Agua POS'}))[0].id===water.id,'manual name search');
 ok((await save({barcode:'7701234567899'},water.id)).barcode==='7701234567899','administrator edits barcode');
 await save({barcode:water.barcode},water.id);
 await user(B);ok((await call('store_pos_save_product',{p_gym_id:other,p_product_id:null,p_data:{name:'Otro gym POS',barcode:water.barcode,sale_price:1}})).barcode===water.barcode,'barcode uniqueness is scoped to gym');await user(A);

 await deny(()=>save({stock_quantity:11},water.id),/inventario|stock/i);
 await user(R);let products=await call('store_pos_products');ok(!('unit_cost' in products[0]),'reception never receives cost');
 await deny(()=>save({name:'No autorizado',sale_price:1}),/permiso/i);
 await deny(()=>call('store_pos_inventory',{p_request_id:request(),p_product_id:water.id,p_mode:'RECEIVE',p_quantity:2}),/permiso/i);
 const items=[{product_id:water.id,quantity:2,expected_price:3000},{product_id:cola.id,quantity:1,expected_price:4000}];
 const id=request();const payload={p_request_id:id,p_items:items,p_payment:{method:'EFECTIVO',received:20000},p_customer_name:'Venta rápida'};
 const sale=await call('store_pos_checkout',payload);
 ok(sale.total_amount===10000&&sale.payment.change_amount===10000,'cash total and change');
 ok(sale.items.length===2&&sale.number==='V-000001'&&/(?:Z|[+-]\d{2}:\d{2})$/.test(sale.sold_at)&&Date.parse(sale.sold_at)===Date.parse('2026-10-20T14:00:00Z'),'server order number and instant');
 ok(!('unit_cost' in sale.items[0]),'reception receipt hides costs');
 const retry=await call('store_pos_checkout',payload);ok(retry.id===sale.id&&retry.duplicate,'idempotent exact retry');
 await deny(()=>call('store_pos_checkout',{...payload,p_payment:{method:'EFECTIVO',received:15000}}),/otros datos|referencia/i);
 products=await call('store_pos_products');ok(products.find(p=>p.id===water.id).stock_quantity===8,'stock reduces once');
 await business(()=>call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:99,expected_price:3000}],p_payment:{method:'TARJETA'}}),/Stock|Existencias/i);
 await deny(()=>call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:null}],p_payment:{method:'TARJETA'}}),/precio|línea/i);
 await business(()=>call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:2999}],p_payment:{method:'TARJETA'}}),/precio/i);
 await business(()=>call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:3000}],p_payment:{method:'EFECTIVO',received:2999}}),/efectivo/i);
 ok((await call('store_pos_history')).length===1,'reception sees own sale');
 await user(A);ok((await call('store_pos_history')).length===1,'administrator sees reception sale');
 let stats=await call('store_pos_stats');ok(stats.store_income===10000&&stats.sale_count===1&&stats.units_sold===3,'separate store statistics count cart once');ok(stats.gross_profit===null&&stats.unknown_cost_units===1,'unknown cost produces no invented profit');
 const finance=await call('admin_store_finance',{p_date_from:'2026-10-01',p_date_to:'2026-10-31'});ok(finance.sale_count===1&&finance.store_income===10000,'legacy finance counts orders once');
 let moves=await call('store_pos_movements',{p_product_id:water.id});ok(moves[0].movement_type==='SALE'&&moves[0].quantity===-2&&moves[0].stock_before===10&&moves[0].stock_after===8,'signed movement with balances');
 await business(()=>call('store_pos_inventory',{p_request_id:request(),p_product_id:water.id,p_mode:null,p_quantity:1}),/inválido/i);
 const invID=request();let inventory={p_request_id:invID,p_product_id:water.id,p_mode:'RECEIVE',p_quantity:24,p_unit_cost:1200};
 let receive=await call('store_pos_inventory',inventory);ok(receive.stock_after===32,'receive stock');ok((await call('store_pos_inventory',inventory)).duplicate,'inventory idempotency');
 await deny(()=>call('store_pos_inventory',{...inventory,p_quantity:1}),/otros datos/i);
 await business(()=>call('store_pos_inventory',{p_request_id:request(),p_product_id:water.id,p_mode:'ADJUST',p_quantity:30,p_reason:'Dañados',p_expected_stock:8}),/cambió/i);
 const adjust=await call('store_pos_inventory',{p_request_id:request(),p_product_id:water.id,p_mode:'ADJUST',p_quantity:30,p_reason:'Dañados',p_expected_stock:32});ok(adjust.stock_after===30&&adjust.movement.quantity===-2,'motivated physical adjustment');
 await deny(()=>call('store_pos_inventory',{p_request_id:request(),p_product_id:water.id,p_mode:'ADJUST',p_quantity:29,p_expected_stock:30}),/motivo/i);
 await deny(()=>db.query('update public.store_products set stock_quantity=999 where id=$1',[water.id]),/inventario/i);
 await deny(()=>db.query('delete from public.store_sales where order_id=$1',[sale.id]),/inmutable/i);
 await deny(()=>db.query('insert into public.store_sales(gym_id,product_id,product_name,quantity,unit_price,total_amount) values($1,$2,$3,1,3000,3000)',[gym,water.id,water.name]),/inmutable/i);
 await deny(()=>db.query('update public.store_products set unit_cost=0 where id=$1',[water.id]),/procedimientos/i);

 await system();await deny(()=>db.query('delete from public.store_orders where id=$1',[sale.id]),/inmutable/i);await user(A);
 const voided=await call('store_pos_void',{p_order_id:sale.id,p_reason:'Error de cobro'});ok(voided.status==='VOID','void keeps original');
 ok((await call('store_pos_void',{p_order_id:sale.id,p_reason:'Reintento'})).duplicate,'void idempotent');
 products=await call('store_pos_products');ok(products.find(p=>p.id===water.id).stock_quantity===32,'void restores stock once');
 stats=await call('store_pos_stats');ok(stats.store_income===0&&stats.sale_count===0,'void excluded statistics');
 ok((await call('admin_store_finance',{p_date_from:'2026-10-01',p_date_to:'2026-10-31'})).store_income===0,'void excluded legacy finance');
 const client=await person();
 const staffPlan=await f.insert('plans',{gym_id:gym,name:'Equipo POS',plan_type:'INTERNAL',duration_days:null,duration_months:null,price:0,has_expiration:false,unlimited_access:true,include_in_financial_stats:false});
 await f.tableRpc('assign_internal_membership',{p_gym_id:gym,p_client_id:client,p_plan_id:staffPlan,p_request_id:request()});
 let card=await call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:3000}],p_payment:{method:'TARJETA',reference:'terminal-123'},p_client_id:client});ok(card.payment.method==='TARJETA'&&card.client_id===client,'card payment and optional client');
 let transfer=await call('store_pos_checkout',{p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:3000}],p_payment:{method:'TRANSFERENCIA',reference:'bank-123'}});ok(transfer.payment.reference==='bank-123','transfer persisted');
 stats=await call('store_pos_stats');ok(stats.store_income===6000&&stats.sale_count===2&&stats.gross_profit===3600,'STAFF buyer remains a real store sale and known costs yield reliable margin');
 await clock('2026-10-21T04:30:00Z');stats=await call('store_pos_stats');ok(stats.today===6000&&stats.today_count===2&&stats.timezone==='America/Bogota','server gym timezone classifies sales across UTC midnight');await clock('2026-10-20T14:00:00Z');

 await user(R);ok((await call('store_pos_history')).length===1,'reception cannot read administrator sales');
 await deny(()=>call('store_pos_void',{p_order_id:card.id,p_reason:'No'}),/permiso/i);
 await user(B);await deny(()=>call('store_pos_products'),/permiso/i);
 await user(A);await call('store_pos_configure',{p_enabled:false});ok(!(await call('store_pos_settings')).enabled,'store disabled configuration');
 await deny(()=>call('store_pos_products'),/deshabilitada/i);await deny(()=>call('register_store_sale',{p_product_id:water.id,p_quantity:1,p_payment_method:'EFECTIVO',p_payment_reference:'',p_customer_name:'',p_notes:''}),/deshabilitada/i);
 ok((await call('store_pos_history',{p_filters:{request_id:id}}))[0].id===sale.id,'disabled store still resolves exact committed request');
 ok((await call('store_pos_inventory',inventory)).duplicate,'disabled store permits exact inventory retry');
 await user(R);ok((await call('store_pos_checkout',payload)).duplicate,'disabled store permits exact confirmed retry');await user(A);
 await call('store_pos_configure',{p_enabled:true});
 await clock('2026-12-20T14:00:00Z');
 ok((await call('store_pos_history',{p_filters:{request_id:id}}))[0].id===sale.id,'request lookup survives more than thirty days');
 ok((await call('store_pos_history',{p_filters:{request_id:request()}})).length===0,'request lookup never substitutes another sale');
 await clock('2026-10-20T14:00:00Z');
 // A payment failure occurs after header, lines, stock and movements have been written.
 const latePayload={p_request_id:request(),p_items:[{product_id:water.id,quantity:1,expected_price:3000}],p_payment:{method:'TARJETA'}};
 await system();
 async function state(){return (await db.query(`select
 (select count(*) from public.store_orders where gym_id=$1) orders,
 (select count(*) from public.store_sales where gym_id=$1) lines,
 (select count(*) from public.store_payments where gym_id=$1) payments,
 (select count(*) from public.store_inventory_movements where gym_id=$1) movements,
 (select count(*) from public.audit_logs where gym_id=$1) audits,
 (select last_sale_number from public.gym_store_settings where gym_id=$1) counter,
 (select stock_quantity from public.store_products where id=$2) stock`,[gym,water.id])).rows[0];}
 const beforeFailure=await state();
 await db.exec(`create function private.pos_test_fail_payment() returns trigger language plpgsql as $$begin raise exception 'Injected late payment failure';end$$;
 create trigger zz_pos_test_fail_payment before insert on public.store_payments for each row execute function private.pos_test_fail_payment();`);
 await user(A);await deny(()=>call('store_pos_checkout',latePayload),/Injected late payment failure/);
 await system();assert.deepEqual(await state(),beforeFailure);checks++;
 await db.exec('drop trigger zz_pos_test_fail_payment on public.store_payments;drop function private.pos_test_fail_payment()');
 await user(A);ok((await call('store_pos_checkout',latePayload)).number==='V-000004','rolled-back request retries successfully without consuming sale number');
 // Missing dependencies reject before changing any POS data and roll back the upgrade.
 await system();await db.exec('alter table public.clients rename to pos_preflight_clients');
 await deny(()=>db.exec(fs.readFileSync(path.join(root,'..','common','store_pos.sql'),'utf8')),/requiere Tienda/);
 await db.exec('rollback');await db.exec('alter table public.pos_preflight_clients rename to clients');

 // Migration is safe to apply again with existing completed/void orders.
 await system();await db.exec(fs.readFileSync(path.join(root,'..','common','store_pos.sql'),'utf8'));await user(A);ok((await call('store_pos_history')).length===4,'reapply preserves order history');
 console.log(`STORE POS OK (${checks} checks; PGlite, no physical HID or multi-session PostgreSQL claim)`);
}finally{await db.close();}
