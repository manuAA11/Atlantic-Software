import assert from 'node:assert/strict';
import {fixture} from './membership_feature_fixture.mjs';

export async function testStorePosOwner(){
 const f=await fixture();const {db,gym,other,A,B,O,user,rpc,person,system}=f;let checks=0;
 const ok=(condition,label)=>{assert.ok(condition,label);checks++;};
 const backup=g=>rpc('owner_editor_backup',{p_gym_id:g});
 const suspend=g=>rpc('owner_set_status',{p_gym_id:g,p_status:'suspended',p_reason:'Restauración de prueba aislada'});
 try{
  await user(A);
  const product=await rpc('store_pos_save_product',{p_gym_id:gym,p_product_id:null,p_data:{name:'Producto propietario POS',sku:'OWN-001',barcode:'000123456789',sale_price:4000,unit_cost:2000,stock_quantity:10}});
  const client=await person();
  await rpc('store_pos_inventory',{p_gym_id:gym,p_request_id:'e1000000-0000-4000-8000-000000000001',p_product_id:product.id,p_mode:'RECEIVE',p_quantity:5,p_reason:'Recepción prueba',p_expected_stock:10});
  const order=await rpc('store_pos_checkout',{p_gym_id:gym,p_request_id:'e1000000-0000-4000-8000-000000000002',p_items:[{product_id:product.id,quantity:2,expected_price:4000}],p_payment:{method:'EFECTIVO',received:10000},p_client_id:client});
  await user(O);const source=await backup(gym);
  for(const table of ['store_orders','store_payments','store_inventory_movements','gym_store_settings'])ok(Array.isArray(source.tables[table]),'owner backup includes '+table);
  ok(source.tables.gym_store_settings[0].inventory_request_archive.length===1,'inventory retry archive included');
  ok((await backup(gym)).fingerprint===source.fingerprint,'read events do not alter POS snapshot fingerprint');
  const preview=await rpc('owner_editor_validate_import',{p_data:source});ok(preview.total>0,'UUID headers/payments accepted in complete backup');
  const sale=(await rpc('owner_editor_rows',{p_gym_id:gym,p_table:'store_sales'})).rows.find(row=>row.data.order_id===order.id);
  await assert.rejects(()=>rpc('owner_editor_record',{p_gym_id:gym,p_table:'store_sales',p_id:sale.data.id,p_expected:sale.version,p_patch:{quantity:1},p_reason:'Intento de corrección POS'}),/inmutable|procedimientos/i);checks++;
  ok((await backup(gym)).fingerprint===source.fingerprint,'rejected owner edit rolls back stock, sale and audit');
  await suspend(other);let target=await backup(other);
  await rpc('owner_editor_import',{p_gym_id:other,p_data:source,p_name:target.gym.name,p_expected:target.fingerprint,p_reason:'Restaurar copia POS completa verificada'});
  const restored=await backup(other);
  ok(restored.tables.store_orders.length===1,'full owner restore retains POS header');
  ok(restored.tables.store_payments[0].amount===8000,'restored payment matches header');
  ok(restored.tables.store_sales[0].order_id===restored.tables.store_orders[0].id,'line remapped to restored order');
  ok(restored.tables.store_orders[0].id!==order.id,'cross-gym UUID collision remapped');
  ok(restored.tables.store_products[0].stock_quantity===13,'stock preserved without double subtraction');
  ok(restored.tables.store_orders[0].client_id===restored.tables.clients[0].id,'optional buyer maps into destination');
  ok(restored.tables.store_orders[0].request_payload.items[0].product_id===restored.tables.store_products[0].id,'checkout idempotency payload remapped');
  ok(restored.tables.store_inventory_movements.length===3,'complete ledger retained');
  ok(restored.tables.store_inventory_movements.map(row=>row.created_at).join()===source.tables.store_inventory_movements.map(row=>row.created_at).join(),'actual movement instants preserved');
  const old=structuredClone(source);for(const table of ['store_orders','store_payments','store_inventory_movements','gym_store_settings'])delete old.tables[table];
  await assert.rejects(()=>rpc('owner_editor_import',{p_gym_id:other,p_data:old,p_name:restored.gym.name,p_expected:restored.fingerprint,p_reason:'Copia antigua incompleta de prueba'}),/archivo antiguo|historial POS/i);checks++;
  ok((await backup(other)).fingerprint===restored.fingerprint,'old-file rejection precedes destructive writes');
  // Confirmed owner deletion remains available with the full dependency graph.
  await rpc('owner_editor_delete_gym',{p_gym_id:other,p_name:restored.gym.name,p_expected:restored.fingerprint,p_reason:'Eliminar gimnasio de prueba aislado'});
  await system();
  for(const table of ['store_orders','store_sales','store_payments','store_inventory_movements','gym_store_settings'])ok((await db.query(`select count(*) n from public.${table} where gym_id=$1`,[other])).rows[0].n===0,'confirmed gym deletion clears '+table);
  await user(O);ok((await backup(gym)).fingerprint===source.fingerprint,'source gym unchanged by restore/delete');
  console.log(`STORE POS OWNER: ${checks} checks PASS (local PostgreSQL engine)`);
 }finally{await db.close();}
}
if(process.argv[1]?.endsWith('store_pos_owner.mjs'))await testStorePosOwner();
