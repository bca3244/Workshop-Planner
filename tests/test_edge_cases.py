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
def ok(n,c,x=''): res.append(c); print('PASS' if c else 'FAIL',n,x)
async def main():
  async with async_playwright() as p:
    b=await launch(p)
    ctx=await b.new_context(viewport={'width':1280,'height':800}); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
    await pg.goto(URL); await pg.wait_for_timeout(400)
    U=lambda l: pg.evaluate(f"()=>Object.keys(items).find(u=>items[u].label==={json.dumps(l)})")
    # 1 constructor
    evil={'items':[{'label':'X','cat':'constructor','w':50,'h':50,'x':100,'y':100},{'label':'Y','cat':'__proto__','w':50,'h':50,'x':200,'y':200}]}
    await pg.set_input_files('#jsonImport',files=[{'name':'e.json','mimeType':'application/json','buffer':json.dumps(evil).encode()}])
    await pg.wait_for_timeout(200); await pg.reload(); await pg.wait_for_timeout(300)
    ok('prototype-name category safe', await pg.evaluate("()=>Object.values(items).every(i=>i.cat==='Custom')&&document.querySelectorAll('.item').length===2"))
    await pg.evaluate("()=>{localStorage.clear()}"); await pg.reload(); await pg.wait_for_timeout(300)
    saw=await U('Table Saw')
    # 2 undo with select focused
    await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);rotateSel(1)}}")
    await pg.select_option('#snapSelect','5'); await pg.focus('#snapSelect'); await pg.keyboard.press('Control+z')
    ok('Ctrl+Z works with snap select focused', await pg.evaluate(f"()=>items['{saw}'].rot")==0)
    await pg.select_option('#snapSelect','10')
    # 3 z of new items after reorder
    await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);reorder(true);addPreset(PRESETS[0].items[0],{{x:150,y:100}})}}")
    z=await pg.evaluate("()=>{const n=items[[...sel][0]];return [n.z,Math.max(...Object.values(items).filter(o=>o.z!=null&&o!==n).map(o=>o.z))]}")
    ok('new item above reordered items', z[0]>z[1], str(z))
    await pg.keyboard.press('Control+z'); await pg.keyboard.press('Control+z')
    # 4 nudge after undo recorded
    await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);afterSelChange()}}"); await pg.mouse.click(5,400)
    await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);afterSelChange()}}")
    await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('Control+z'); await pg.keyboard.press('ArrowDown')
    ok('nudge right after undo is undoable', await pg.evaluate("()=>hist.length")>=1)
    await pg.keyboard.press('Control+z')
    # 5 oversize item doesn't freeze group
    await pg.evaluate("()=>{items.big=cleanItem({label:'BIG',cat:'Structure',w:500,h:20,x:0,y:300});render()}")
    r=await pg.evaluate(f"()=>{{sel=new Set(['{saw}','big']);const x=items['{saw}'].x;nudge(10,0);return [x,items['{saw}'].x]}}")
    ok('oversize item does not freeze group', r[1]==r[0]+10, str(r))
    # custom too big rejected
    await pg.evaluate("()=>{delete items.big;render()}")
    await pg.evaluate("()=>{cName.value='HUGE';cW.value='50';cH.value='4';addCustom()}")
    ok('custom too big rejected', 'Too big' in await pg.evaluate("()=>cErr.textContent"))
    # 6 column on saw flagged
    n=await pg.evaluate(f"()=>{{const s=items['{saw}'];items.col=cleanItem({{label:'COL',cat:'Structure',w:10,h:10,x:s.x+5,y:s.y+5}});render();return issues.pairs.length}}")
    ok('Structure column overlapping saw flagged', n>=2, str(n))
    ok('paint booth still not flagged', await pg.evaluate("()=>!issues.body.has(Object.keys(items).find(u=>items[u].label==='PAINT BOOTH'))"))
    await pg.evaluate("()=>{delete items.col;render()}")
    # 7 delete wall blocked, locked confirm
    nw=await U('NORTH WALL')
    await pg.evaluate(f"()=>{{sel=new Set(['{nw}']);deleteSel()}}")
    ok('wall not deleted', await pg.evaluate(f"()=>!!items['{nw}']"))
    # 9 drag back to start no history
    await pg.evaluate("()=>{settings.snap=0}"); x0=await pg.evaluate(f"()=>items['{saw}'].x")
    h0=await pg.evaluate("()=>hist.length")
    c=await pg.evaluate(f"()=>{{const r=document.getElementById('i_{saw}').getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}}")
    await pg.mouse.move(*c); await pg.mouse.down(); await pg.mouse.move(c[0]+60,c[1],steps=4); await pg.mouse.move(c[0],c[1],steps=4); await pg.mouse.up()
    ok('drag back to start adds no history', await pg.evaluate("()=>hist.length")==h0)
    # Esc cancels drag
    await pg.mouse.move(*c); await pg.mouse.down(); await pg.mouse.move(c[0]+80,c[1]+30,steps=4); await pg.keyboard.press('Escape'); await pg.mouse.up()
    ok('Esc cancels drag', await pg.evaluate(f"()=>items['{saw}'].x")==x0)
    await pg.evaluate("()=>{settings.snap=10}")
    # 10 Enter on button
    await pg.evaluate(f"()=>{{sel=new Set(['{saw}']);afterSelChange()}}"); await pg.focus('#btnMeasure'); await pg.keyboard.press('Enter')
    ok('Enter on button does not open edit', not await pg.is_visible('#dlgOv'))
    await pg.evaluate("()=>setMode('select')")
    # 12 png width
    await pg.fill('#shedW','20'); await pg.keyboard.press('Enter')
    ok('Enter applies shed size + png min width', await pg.evaluate("()=>[shedW,renderCanvas('dark',1).width]")==[20,440])
    await pg.keyboard.press('Control+z')
    # layout header height
    for vw in (1280,1024):
      await pg.set_viewport_size({'width':vw,'height':800}); await pg.wait_for_timeout(100)
      h=await pg.evaluate("()=>document.querySelector('header').offsetHeight")
      ok(f'header single row at {vw}', h<70, str(h))
    await pg.set_viewport_size({'width':1280,'height':800}); await pg.wait_for_timeout(100)
    ok('no errors', not errs, str(errs))
    await b.close()
  print(sum(res),'/',len(res))
  sys.exit(0 if all(res) else 1)
asyncio.run(main())
