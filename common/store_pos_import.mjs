import {fixture} from './membership_feature_fixture.mjs';
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

export async function testStorePosImport(){
 const f=await fixture(); const {db,gym,A,R,B,other,user,system,rpc,insert,clock}=f;
 let checks=0;const equal=(a,b,label)=>{assert.deepEqual(a,b,label);checks++;};
 async function deny(fn,pattern){await assert.rejects(fn,pattern);checks++;}
 try{
  // The standalone extension also remains idempotent on the combined migration.
  await system();
  const extension=fs.readFileSync(path.resolve(f.root,'../common/store_pos_import.sql'),'utf8');
  await db.exec(extension);await db.exec(extension);await user(A);
  const client=await insert('clients',{gym_id:gym,document:'RESTORE-1',first_name:'Cliente respaldo',active:true});
  const plan=await insert('plans',{gym_id:gym,name:'Plan respaldo',duration_days:30,price:70000});
  const product=await rpc('store_pos_save_product',{p_gym_id:gym,p_product_id:null,p_data:{name:'Coca-Cola respaldo',sku:'00034',barcode:'007701234567890',unit_cost:2000,sale_price:4000,stock_quantity:12,low_stock_threshold:5}});
  const received=await rpc('store_pos_inventory',{p_gym_id:gym,p_product_id:product.id,p_request_id:'77777777-7777-4777-8777-777777777771',p_mode:'RECEIVE',p_quantity:2,p_reason:'Compra',p_unit_cost:2100,p_expected_stock:12});
  const sale=await rpc('store_pos_checkout',{p_gym_id:gym,p_request_id:'77777777-7777-4777-8777-777777777772',p_items:[{product_id:product.id,quantity:2,expected_price:4000}],p_payment:{method:'EFECTIVO',received:10000},p_client_id:client,p_customer_name:'Cliente respaldo'});
  const second=await rpc('store_pos_checkout',{p_gym_id:gym,p_request_id:'77777777-7777-4777-8777-777777777773',p_items:[{product_id:product.id,quantity:1,expected_price:4000}],p_payment:{method:'TRANSFERENCIA'}});
  await rpc('store_pos_void',{p_gym_id:gym,p_order_id:second.order_id,p_reason:'Prueba devolución'});
  async function backup(){
   const tables={};
   for(const table of ['clients','plans','memberships','checkins','store_products','store_sales','accounting_expenses','trainers','staff_shifts','routines','exercises','classes','reservations','marketing_messages']){
    tables[table]=(await db.query(`select * from public.${table} where gym_id=$1`,[gym])).rows;
   }
   for(const table of ['store_orders','store_payments','store_inventory_movements','gym_store_settings'])tables[table]=await rpc('store_pos_backup_table',{p_gym_id:gym,p_table:table});
   return {format:f.commercial?'GymSoft-EXCEL-REPLACE-2':'ZTATTUZ-EXCEL-REPLACE-2',tables};
  }
  const archive=await backup();
  equal(archive.tables.store_orders.length,2,'both order statuses are backed up');
  equal(archive.tables.gym_store_settings[0].inventory_request_archive.length,1,'inventory idempotency archive');
  async function counts(){return {orders:(await rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'store_orders'})).length,movements:(await rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'store_inventory_movements'})).length};}
  const beforeCounts=await counts();
  const oldFile=structuredClone(archive);for(const t of ['store_orders','store_payments','store_inventory_movements','gym_store_settings'])delete oldFile.tables[t];
  await deny(()=>rpc('admin_replace_gym_from_excel',{p_data:oldFile}),/archivo antiguo/);
  equal(await counts(),beforeCounts,'old file refusal changes no history');
  const corrupt=structuredClone(archive);corrupt.tables.store_payments[0].amount++;corrupt.tables.store_payments[0].received++;
  await deny(()=>rpc('admin_replace_gym_from_excel',{p_data:corrupt}),/inconsistentes/);
  equal(await counts(),beforeCounts,'late restore failure rolls back complete replacement');
  await clock('2026-10-23T14:00:00Z');
  await rpc('admin_replace_gym_from_excel',{p_data:archive});
  const restored=await backup();
  equal(restored.tables.store_orders.map(o=>[o.sale_number,o.status,o.sold_at]),archive.tables.store_orders.map(o=>[o.sale_number,o.status,o.sold_at]),'order history retains actual instants');
  equal(restored.tables.store_sales.map(o=>[o.quantity,o.total_amount,o.unit_cost,o.status]),archive.tables.store_sales.map(o=>[o.quantity,o.total_amount,o.unit_cost,o.status]),'sale lines and nullable snapshots');
  equal(restored.tables.store_inventory_movements.map(m=>[m.quantity,m.stock_before,m.stock_after,m.movement_type,m.created_at]),archive.tables.store_inventory_movements.map(m=>[m.quantity,m.stock_before,m.stock_after,m.movement_type,m.created_at]),'movement balances and actual instants');
  const restoredProduct=restored.tables.store_products.find(p=>p.sku==='00034');
  equal(restoredProduct.barcode,'007701234567890','barcode keeps leading zeroes');
  equal(restoredProduct.stock_quantity,12,'void restored stock');
  const restoredOrder=restored.tables.store_orders.find(o=>o.request_id==='77777777-7777-4777-8777-777777777772');
  equal(restoredOrder.request_payload.items[0].product_id,restoredProduct.id,'idempotency payload product remapped');
  const retry=await rpc('store_pos_checkout',{p_gym_id:gym,p_request_id:restoredOrder.request_id,p_items:restoredOrder.request_payload.items,p_payment:restoredOrder.request_payload.payment,p_client_id:restoredOrder.client_id,p_customer_name:'Cliente respaldo'});
  equal(retry.duplicate,true,'checkout retry returns same restored order');
  const inventoryRetry=await rpc('store_pos_inventory',{p_gym_id:gym,p_product_id:restoredProduct.id,p_request_id:'77777777-7777-4777-8777-777777777771',p_mode:'RECEIVE',p_quantity:2,p_reason:'Compra',p_unit_cost:2100,p_expected_stock:12});
  equal(inventoryRetry.duplicate,true,'inventory retry remains idempotent after remap');
  equal(inventoryRetry.product_id,restoredProduct.id,'inventory result maps product');
  const maxNumber=restored.tables.gym_store_settings[0].last_sale_number;
  const third=await rpc('store_pos_checkout',{p_gym_id:gym,p_request_id:'77777777-7777-4777-8777-777777777774',p_items:[{product_id:restoredProduct.id,quantity:1,expected_price:4000}],p_payment:{method:'TARJETA'}});
  await rpc('admin_replace_gym_from_excel',{p_data:archive});
  const settings=await rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'gym_store_settings'});
  equal(Number(settings[0].last_sale_number),Number(maxNumber)+1,'restoring an older backup does not reuse a sale number');
  await user(B);
  await rpc('admin_replace_gym_from_excel',{p_data:archive});
  const otherOrders=await rpc('store_pos_backup_table',{p_gym_id:other,p_table:'store_orders'});
  equal(otherOrders.length,2,'independent gym can restore complete archive');
  equal(otherOrders.every(o=>!archive.tables.store_orders.some(old=>old.id===o.id)),true,'cross-gym order UUID collisions remap safely');
  const otherMovements=await rpc('store_pos_backup_table',{p_gym_id:other,p_table:'store_inventory_movements'});
  equal(otherMovements.every(m=>m.gym_id===other),true,'cross-gym inventory stays in target gym');
  await user(A);equal((await rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'store_orders'})).length,2,'source history survives cross-gym restoration');
  await user(R);await deny(()=>rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'store_orders'}),/permiso/);
  await user(B);await deny(()=>rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'store_orders'}),/permiso/);
  await user(A);await deny(()=>rpc('store_pos_backup_table',{p_gym_id:gym,p_table:'clients'}),/no permitida/);
  await system();equal((await db.query('select count(*) n from private.store_pos_context')).rows[0].n,0,'restore capability removed');
  console.log('STORE POS IMPORT SQL: '+checks+' checks PASS');
 }finally{await db.close();}
}

if(process.argv[1]?.endsWith('store_pos_import.mjs'))await testStorePosImport();
