import asyncio, json, os, sys
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parent.parent
URL=(ROOT/'index.html').as_uri()
LEGACY=(ROOT/'tests'/'fixtures'/'legacy_v13.json').read_text()
CHROME=os.environ.get('CHROME')   # optional: path to a Chrome/Chromium binary
async def launch(p):
    kw={'args':['--no-sandbox']}
    if CHROME: kw['executable_path']=CHROME
    return await p.chromium.launch(**kw)
res=[]
def ok(n,c,x=''): res.append(bool(c)); print('PASS' if c else 'FAIL',n,x)
async def main():
  async with async_playwright() as p:
    b=await launch(p); pg=await (await b.new_context(viewport={'width':1400,'height':900})).new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
    await pg.goto(URL); await pg.evaluate("()=>localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(400)
    E=pg.evaluate
    U=lambda l: E(f"()=>Object.keys(items).find(u=>items[u].label==={json.dumps(l)})")
    ok('default layout: no overhead issues, 14 ft ceiling', await E("()=>[issues.over.length,ceilH]")==[0,14])
    sg=await U('South Garage Door')
    sp=await E(f"()=>garageSpec(items['{sg}'].door)")
    ok('standard 10 ft door: track 10, backroom 11.5, ceiling 11', abs(sp['backroom']-11.5)<1e-9 and sp['trackElev']==10 and abs(sp['needCeil']-11)<1e-9, str(sp))
    # ceiling too low
    await pg.fill('#shedC','9'); await pg.keyboard.press('Enter')
    ok('9 ft ceiling flags both garage doors', await E("()=>issues.over.filter(o=>/ceiling/.test(o.msg)).length")==2)
    await pg.keyboard.press('Control+z')
    ok('undo restores ceiling', await E("()=>ceilH")==14)
    # tall item under south track
    await E("()=>{items.t=cleanItem({label:'RACK',cat:'Storage',w:40,h:30,x:250,y:560,ht:11});render()}")
    ok('11 ft item under 10 ft track flagged', await E("()=>issues.over.some(o=>o.u==='t'&&/track/.test(o.msg))"))
    await E("()=>{items.t.ht=9;render()}")
    ok('9 ft item under track OK', not await E("()=>issues.over.some(o=>o.u==='t')"))
    await E("()=>{items.t.ht=11;render()}")
    await E(f"()=>{{Object.assign(items['{sg}'].door,{{lift:'high',hl:3}});render()}}")
    ok('high-lift +3 clears 11 ft item, fits 14 ft', await E("()=>issues.over.length")==0)
    await E(f"()=>{{Object.assign(items['{sg}'].door,{{lift:'vert',hl:0}});render()}}")
    v=await E(f"()=>[garageSpec(items['{sg}'].door),issues.over.map(o=>o.msg)]")
    ok('vertical lift: no track, needs 21 ft ceiling', v[0]['backroom']==0 and v[0]['trackElev'] is None and any('21.0' in m for m in v[1]), str(v[1]))
    await E(f"()=>{{Object.assign(items['{sg}'].door,{{lift:'std'}});delete items.t;render()}}")
    # stacked items
    await E("()=>{items.b=cleanItem({label:'BENCH',cat:'Wood',w:60,h:25,x:150,y:340});items.c=cleanItem({label:'UPPER',cat:'Storage',w:60,h:12,x:150,y:340,elev:5,ht:2.5});render()}")
    ok('bench with unknown height clashes with upper cabinet', await E("()=>issues.pairs.some(p=>p.includes('b')&&p.includes('c'))"))
    await E("()=>{items.b.ht=3;render()}")
    ok('3 ft bench under 5 ft cabinet: no clash', not await E("()=>issues.pairs.some(p=>p.includes('b')&&p.includes('c'))"))
    # high-mounted item doesn't block clearance
    saw=await U('Table Saw')
    await E(f"()=>{{const s=items['{saw}'];items.h=cleanItem({{label:'HEAD',cat:'HVAC',w:30,h:10,x:s.x,y:s.y+32,elev:8,ht:1}});items.k=cleanItem({{label:'BOX',cat:'Custom',w:20,h:10,x:s.x+10,y:s.y+32,elev:8,ht:1}});render()}}")
    ok('item mounted at 8 ft does not block clearance', await E("()=>issues.clrCount")==0)
    await E("()=>{items.k.elev=0;render()}")
    ok('same item on the floor does block it', await E("()=>issues.clrCount")>=1)
    await E("()=>{delete items.b;delete items.c;delete items.h;delete items.k;render()}")
    # too tall for ceiling
    await E("()=>{items.x=cleanItem({label:'TALL',cat:'Shop',w:20,h:20,x:300,y:500,ht:15});render()}")
    ok('15 ft item above 14 ft ceiling flagged', await E("()=>issues.over.some(o=>o.u==='x'&&/ceiling/.test(o.msg))"))
    await E("()=>{delete items.x;render()}")
    # edit dialog UI
    await E(f"()=>{{sel=new Set(['{sg}']);afterSelChange();openEdit('{sg}')}}")
    info=await pg.inner_text('#doorInfo')
    ok('door dialog shows computed clearances', 'Needs 11.0 ft ceiling' in info and '11.5 ft deep' in info, info)
    await pg.select_option('#dLift','high'); await pg.fill('#dHl','2'); await pg.click('#dlgOv .btn.pri')
    ok('edit applies high-lift', await E(f"()=>[items['{sg}'].door.lift,items['{sg}'].door.hl]")==['high',2])
    await E(f"()=>openEdit('{saw}')"); await pg.fill('#dHt','3'); await pg.fill('#dElev',''); await pg.click('#dlgOv .btn.pri')
    ok('edit sets item height', await E(f"()=>items['{saw}'].ht")==3)
    await E(f"()=>{{sel=new Set(['{saw}']);afterSelChange()}}")
    ok('elevation panel shows for selection', await pg.is_visible('#elevPanel') and 'TABLE SAW' in await E("()=>elevSvg.textContent"))
    ok('size readout includes height', '3 ft H' in await pg.inner_text('#iSize'))
    # persistence / share
    await pg.fill('#shedC','16'); await pg.keyboard.press('Enter')
    code=await E("async()=>await encodeShare()")
    ok('share link carries ceiling', await E("async(c)=>parseLayout(await decodeShare(c)).ceilH",code)==16)
    await pg.reload(); await pg.wait_for_timeout(300)
    ok('ceiling + heights persist after reload', await E(f"()=>[ceilH,items['{saw}'].ht,items['{sg}'].door.lift]")==[16,3,'high'])
    await pg.screenshot(path='/tmp/heights.png')
    ok('no page errors', not errs, str(errs))
    await b.close()
  print(sum(res),'/',len(res)); sys.exit(0 if all(res) else 1)
asyncio.run(main())
