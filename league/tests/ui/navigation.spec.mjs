import {test,expect} from '@playwright/test';

for(const viewport of [{width:320,height:640},{width:390,height:844},{width:430,height:932}]){
 test(`SVG navigation stays usable without fonts at ${viewport.width} × ${viewport.height}`,async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route(/\.(?:ttf|otf|woff2?)(?:\?|$)/,route=>route.abort());
  await page.setViewportSize(viewport);await page.goto('/');
  if(await page.getByRole('button',{name:'Cerrar instrucciones de instalación'}).isVisible())await page.getByRole('button',{name:'Cerrar instrucciones de instalación'}).click();
  await page.getByRole('button',{name:'Explorar demostración'}).click();
  await expect(page.getByRole('heading',{name:'Hola, Deportista'})).toBeVisible();
  for(const tab of ['Inicio','League','Agenda','Rutinas','Perfil']){
   const target=page.getByRole('tab',{name:tab,exact:true});await expect(target).toBeVisible();
   const rect=await target.boundingBox();expect(rect.width).toBeGreaterThanOrEqual(44);expect(rect.height).toBeGreaterThanOrEqual(44);expect(rect.y+rect.height).toBeLessThanOrEqual(viewport.height);
  }
  await page.getByRole('tab',{name:'Rutinas',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Mis rutinas'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Entrenamiento libre',exact:true}).locator('svg[data-league-icon="barbell-outline"]')).toBeVisible();
  await page.getByLabel('Buscar ejercicio',{exact:true}).fill('prensa');
  await expect(page.getByRole('button',{name:'Ver Prensa de piernas',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(await page.evaluate(()=>/[\uE000-\uF8FF]/.test(document.body.textContent||''))).toBe(false);
  await page.setViewportSize({width:viewport.width,height:460});
  const bar=await page.getByRole('tablist').boundingBox();expect(bar.y+bar.height).toBeLessThanOrEqual(460);
  await page.getByLabel('Buscar ejercicio',{exact:true}).fill('');
  await page.getByRole('button',{name:'Empezar rutina',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Cada serie cuenta'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Registrar este ejercicio'}).first()).toBeVisible();
  expect(errors).toEqual([]);
 });
}

test('dark mode covers the app and survives reopening',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await page.getByRole('button',{name:'Explorar demostración'}).click();
 await page.getByRole('button',{name:'Abrir mi perfil'}).click();
 await expect(page.getByRole('heading',{name:'Mi perfil'})).toBeVisible();
 await page.getByRole('switch',{name:'Modo oscuro',exact:true}).check();
 await expect(page.locator('html')).toHaveAttribute('data-league-theme','dark');
 for(const name of ['Inicio','League','Agenda','Rutinas','Perfil']){await page.getByRole('tab',{name,exact:true}).click();expect(await page.evaluate(()=>document.documentElement.dataset.leagueTheme)).toBe('dark');}
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-league-theme','dark');
 await page.getByRole('button',{name:'Explorar demostración'}).click();
 await page.getByRole('button',{name:'Abrir mi perfil'}).click();
 await expect(page.getByRole('switch',{name:'Modo oscuro',exact:true})).toBeChecked();
 await page.getByRole('switch',{name:'Modo oscuro',exact:true}).uncheck();
 await expect(page.locator('html')).toHaveAttribute('data-league-theme','light');
});
