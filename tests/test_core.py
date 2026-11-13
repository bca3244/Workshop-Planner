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
def ok(name,cond,extra=''):
    res.append((name,bool(cond))); print(('PASS' if cond else 'FAIL'),name,extra)
async def center(pg,uid):
    return await pg.evaluate(f"""()=>{{const r=document.getElementById('i_{uid}').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}}""")
async def uid_by(pg,label):
    return await pg.evaluate(f"""()=>Object.keys(items).find(u=>items[u].label==={json.dumps(label)})""")
async def main():
    async with async_playwright() as p:
        b=await launch(p)
        ctx=await b.new_context(viewport={'width':1500,'height':950})
        # --- legacy migration: old-format (v13) save captured from the previous app version
        await ctx.add_init_script("if(!sessionStorage.seeded){localStorage.setItem('ws_planner_v13',"+json.dumps(LEGACY)+");sessionStorage.seeded=1}")
        legacy=LEGACY
        pg=await ctx.new_page(); errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        m=await pg.evaluate("()=>{const s=Object.values(items).find(i=>i.label==='MY SAW');return s&&{x:s.x,n:Object.keys(items).length,walls:Object.values(items).filter(i=>i.wall).length,doors:Object.values(items).filter(i=>i.door).map(d=>[d.w,d.h,d.door.type])}}")
        ok('legacy v13 state migrated', m and m['x']==200 and m['n']==30 and m['walls']==4, str(m))
        await pg.evaluate("()=>{localStorage.clear()}"); await pg.reload(); await pg.wait_for_timeout(500)
        # 2: rotate + undo
        saw=await uid_by(pg,'Table Saw')
        await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);rotateSel(1)}}")
        r1=await pg.evaluate(f"()=>items['{saw}'].rot"); await pg.keyboard.press('Control+z')
        r2=await pg.evaluate(f"()=>items['{saw}'].rot")
        ok('rotate then undo restores', r1==90 and r2==0, f'{r1}->{r2}')
        # 3: click without move adds no history
        h0=await pg.evaluate("()=>hist.length"); x,y=await center(pg,saw)
        await pg.mouse.click(x,y); await pg.wait_for_timeout(600); h1=await pg.evaluate("()=>hist.length")
        ok('click-select adds no undo entry', h0==h1)
        # drag
        await pg.mouse.move(x,y); await pg.mouse.down(); await pg.mouse.move(x+60,y+40,steps=5); await pg.mouse.up()
        moved=await pg.evaluate(f"()=>[items['{saw}'].x,items['{saw}'].y]")
        await pg.keyboard.press('Control+z'); back=await pg.evaluate(f"()=>[items['{saw}'].x,items['{saw}'].y]")
        ok('drag moves, undo returns', moved!=[100,295] and back==[100,295], f'{moved} {back}')
        # 4: snap off survives undo
        await pg.select_option('#snapSelect','0')
        await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);rotateSel(1)}}"); await pg.keyboard.press('Control+z')
        ok('snap OFF survives undo', await pg.evaluate("()=>settings.snap")==0)
        await pg.select_option('#snapSelect','10')
        # 5: delete pinned → no orphan chip
        sh=await uid_by(pg,'SHELVES')
        n0=await pg.evaluate("()=>document.querySelectorAll('#pinLayer .chip').length")
        await pg.evaluate(f"()=>{{sel=new Set(['{sh}']);afterSelChange()}}"); await pg.keyboard.press('Delete')
        n1=await pg.evaluate("()=>document.querySelectorAll('#pinLayer .chip').length")
        ok('delete pinned leaves no chip', n1==n0-1, f'{n0}->{n1}')
        await pg.keyboard.press('Control+z')
        # 6: POS correct when zoomed
        await pg.evaluate("()=>setZoom(2.5)")
        pt=await pg.evaluate("()=>{wrap.scrollLeft=0;wrap.scrollTop=0;const r=floor.getBoundingClientRect(),i=inner();return [r.left+(i.l+50)*zoom,r.top+(i.t+30)*zoom]}")
        await pg.mouse.move(pt[0],pt[1]); pos=await pg.inner_text('#iPos')
        ok('POS correct at 250% zoom', pos.startswith('5.0, 3.0'), pos)
        await pg.evaluate("()=>zoomFit()")
        # 7/8: shed resize moves east-wall items, PNG matches size
        eg=await uid_by(pg,'East Garage Door'); ch=await uid_by(pg,'CRAFTSMAN')
        before=await pg.evaluate(f"()=>[items['{eg}'].x,items['{ch}'].x]")
        await pg.fill('#shedW','50'); await pg.fill('#shedH','70'); await pg.click('text=Apply')
        after=await pg.evaluate(f"()=>[items['{eg}'].x,items['{ch}'].x,shedW]")
        ok('shed resize: east door + chest follow wall', after[0]==before[0]+100 and after[1]==before[1]+100, f'{before}->{after}')
        cv=await pg.evaluate("()=>{const c=renderCanvas('dark',1);return [c.width,c.height]}")
        ok('PNG canvas matches shed size', cv==[580,780+56], str(cv))
        await pg.keyboard.press('Control+z')
        ok('undo shed resize', await pg.evaluate("()=>[shedW,shedH]")==[40,60])
        # 9: XSS via import
        evil={'version':3,'shedW':40,'shedH':60,'items':[{'label':'<img src=x onerror="window.pwned=1">','cat':'Custom','w':50,'h':50,'x':100,'y':100}]}
        await pg.set_input_files('#jsonImport',files=[{'name':'e.json','mimeType':'application/json','buffer':json.dumps(evil).encode()}])
        await pg.wait_for_timeout(300)
        ok('import with HTML label does not execute', await pg.evaluate("()=>window.pwned===undefined && Object.keys(items).length===1"))
        await pg.keyboard.press('Control+z')
        ok('undo import', await pg.evaluate("()=>Object.keys(items).length")==30)
        # versions: save, change, load (incl legacy-format version)
        await pg.evaluate("()=>{document.getElementById('verName').value='A';saveVersion()}")
        await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);deleteSel()}}")
        await pg.evaluate("()=>loadVersion(0)")
        ok('version load works', await pg.evaluate("()=>Object.keys(items).length")==30)
        await pg.evaluate("(st)=>{const v=loadVersions();v.push({name:'old',date:'x',itemCount:30,state:st});saveVersions(v);loadVersion(1)}", legacy)
        ok('legacy version loads', await pg.evaluate("()=>!!Object.values(items).find(i=>i.label==='MY SAW')"))
        await pg.evaluate("()=>{resetLayout();localStorage.removeItem(VSK)}")
        # marquee + nudge merge
        await pg.evaluate("()=>zoomFit()")
        a=await pg.evaluate("()=>{const r=floor.getBoundingClientRect(),z=zoom;return [r.left+95*z,r.top+240*z,r.left+205*z,r.top+330*z]}")
        await pg.mouse.move(a[0],a[1]); await pg.mouse.down(); await pg.mouse.move(a[2],a[3],steps=6); await pg.mouse.up()
        nsel=await pg.evaluate("()=>[...sel].map(u=>items[u].label)")
        ok('marquee selects several', len(nsel)>=3, str(nsel))
        h0=await pg.evaluate("()=>hist.length")
        for _ in range(3): await pg.keyboard.press('ArrowRight')
        h1=await pg.evaluate("()=>hist.length"); xs=await pg.evaluate(f"()=>items['{saw}'].x")
        ok('arrow nudge x3 = one undo step', h1==h0+1 and xs==130, f'{h0}->{h1} x={xs}')
        await pg.keyboard.press('Control+z'); ok('nudge undo', await pg.evaluate(f"()=>items['{saw}'].x")==100)
        # share roundtrip
        code=await pg.evaluate("async()=>await encodeShare()")
        rt=await pg.evaluate("async(c)=>{const L=parseLayout(await decodeShare(c));return [L.items.length,L.shedW]}",code)
        ok('share link roundtrip', rt==[30,40], f'len={len(code)} {rt}')
        pg2=await ctx.new_page(); pg2.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg2.goto(URL+'#l='+code); await pg2.wait_for_timeout(700)
        ok('share link loads on open', await pg2.evaluate("()=>Object.keys(items).length==30 && location.hash===''")); await pg2.close()
        # measure
        await pg.keyboard.press('Escape'); await pg.keyboard.press('m')
        await pg.mouse.move(a[0],a[1]); await pg.mouse.down(); await pg.mouse.move(a[0]+200,a[1],steps=4); await pg.mouse.up()
        mt=await pg.evaluate("()=>[...document.querySelectorAll('#overlay text')].map(t=>t.textContent)")
        ok('measure shows distance', any('ft' in t for t in mt), str(mt))
        await pg.keyboard.press('Escape')
        # context menu + library + edit dialog
        x,y=await center(pg,saw); await pg.mouse.click(x,y,button='right')
        ok('context menu opens', await pg.is_visible('#ctx'))
        await pg.keyboard.press('Escape'); await pg.mouse.click(5,300)
        n=await pg.evaluate("()=>Object.keys(items).length")
        await pg.click('summary:has-text("Utilities")'); await pg.click('.lib-item:has-text("240V Drop")')
        ok('library click adds item', await pg.evaluate("()=>Object.keys(items).length")==n+1)
        x,y=await center(pg,saw); await pg.mouse.dblclick(x,y); await pg.wait_for_timeout(100)
        ok('dbl-click opens edit', await pg.is_visible('#dlgOv'))
        await pg.fill('#dW','6'); await pg.fill('#cB','5'); await pg.keyboard.press('Enter')
        w=await pg.evaluate(f"()=>[items['{saw}'].w,items['{saw}'].clr]")
        ok('edit applies size + clearance', w[0]==60 and w[1].get('b')==5, str(w))
        cl=await pg.evaluate("()=>issues.clrCount")
        ok('clearance conflict detected (saw outfeed vs wood table)', cl>=1, str(cl))
        # door swing collision
        d=await pg.evaluate("()=>{const it=cleanItem({label:'BOX',cat:'Custom',w:20,h:20,x:80,y:605});items[newId()]=it;render();return issues.swingHits}")
        ok('item in door swing flagged', d>=1)
        # print canvas light
        ok('print canvas renders', await pg.evaluate("()=>renderCanvas('light',1).width")==480)
        ok('no page errors', not errs, str(errs))
        await b.close()
    passed=sum(r for _,r in res); print(passed,'/',len(res))
    sys.exit(0 if passed==len(res) else 1)
asyncio.run(main())
