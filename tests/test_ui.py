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
    b=await launch(p); ctx=await b.new_context(viewport={'width':1440,'height':900}); pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
    await pg.goto(URL); await pg.evaluate("()=>localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(400)
    E=pg.evaluate
    U=lambda l: E(f"()=>Object.keys(items).find(u=>items[u].label==={json.dumps(l)})")
    ok('default layout opens with no issues', await pg.inner_text('#issuesBadge')=='✓ No issues')
    ok('first-run hint shown', await pg.is_visible('#firstHint'))
    await pg.click('#firstHint .btn'); await pg.reload(); await pg.wait_for_timeout(300)
    ok('hint stays dismissed', not await pg.is_visible('#firstHint'))
    ok('nothing selected → shop panel', await pg.is_visible('#shedW') and await pg.is_visible('#issuesGrp'))
    saw=await U('Table Saw')
    await E("()=>{items.q=cleanItem({label:'BOX',cat:'Custom',w:30,h:20,x:105,y:322});render()}")
    ok('badge counts issues', '2 issues' in await pg.inner_text('#issuesBadge'), await pg.inner_text('#issuesBadge'))
    rows=await pg.locator('#issuesGrp .issue').count()
    ok('issues list has a row per problem', rows==2, str(rows))
    await pg.locator('#issuesGrp .issue').first.click()
    ok('clicking an issue selects the items', await E("()=>[...sel].sort().join()")==','.join(sorted([saw,'q'])))
    ok('overlap / clearance marks differ', await E(f"()=>document.getElementById('i_q').classList.contains('hit-overlap') && document.getElementById('i_{saw}').classList.contains('hit-overlap')"))
    await E("()=>{delete items.q;sel.clear();render()}")
    await E("()=>{items.t=cleanItem({label:'RACK',cat:'Storage',w:40,h:30,x:250,y:560,ht:11});render()}")
    ok('overhead item gets ↥ badge', await E("()=>!!document.querySelector('#i_t .obadge')"))
    await E("()=>{delete items.t;render()}")
    # live edit: one undo step per field
    await E(f"()=>{{sel=new Set(['{saw}']);afterSelChange()}}")
    h0=await E("()=>hist.length")
    await pg.fill('#pName','My Saw'); await pg.keyboard.press('Enter')
    await pg.fill('#pW','5'); await pg.keyboard.press('Enter')
    ok('inspector edits apply live', await E(f"()=>[items['{saw}'].label,items['{saw}'].w]")==['My Saw',50])
    ok('one undo step per field', await E("()=>hist.length")==h0+2)
    await pg.keyboard.press('Control+z')
    ok('undo reverts last field only', await E(f"()=>[items['{saw}'].label,items['{saw}'].w]")==['My Saw',40])
    await pg.keyboard.press('Control+z')
    await pg.fill('#pW','99'); await pg.keyboard.press('Enter')
    ok('too-big width rejected inline', await E(f"()=>items['{saw}'].w")==40 and await E("()=>pW.classList.contains('invalid')"))
    await pg.fill('#pX','10'); await pg.keyboard.press('Enter')
    ok('position field moves item', await E(f"()=>items['{saw}'].x")==await E("()=>inner().l+100"))
    await pg.keyboard.press('Control+z')
    await pg.click('#inspHead .actions .btn >> nth=0')
    ok('rotate button works', await E(f"()=>items['{saw}'].rot")==90)
    await pg.keyboard.press('Control+z')
    # multi-select align / distribute
    ids=await E("()=>Object.keys(items).filter(u=>/WOOD TABLE|My Saw/.test(items[u].label))")
    await E(f"(ids)=>{{sel=new Set(ids);afterSelChange()}}", ids)
    ok('multi panel shows count', 'items selected' in (await pg.inner_text('#inspHead')).lower())
    await pg.click('button[title="Align top edges"]')
    tops=await E("(ids)=>ids.map(u=>items[u].y)", ids)
    ok('align top', len(set(tops))==1, str(tops))
    await pg.keyboard.press('Control+z')
    await pg.click('button[title="Distribute horizontally"]')
    xs=await E("(ids)=>ids.map(u=>[items[u].x,dims(items[u]).w]).sort((a,b)=>a[0]-b[0])", ids)
    gaps=[round(xs[i+1][0]-xs[i][0]-xs[i][1],3) for i in range(len(xs)-1)]
    ok('distribute evens gaps', len(set(gaps))==1, str(gaps))
    await pg.keyboard.press('Control+z')
    # labels follow zoom
    cv=await U('CENTRAL VAC')
    await E("()=>zoomFit()"); await pg.wait_for_timeout(80)
    small=await E(f"()=>document.querySelector('#i_{cv} .ilabel').textContent")
    await E("()=>setZoom(3)"); await pg.wait_for_timeout(80)
    big=await E(f"()=>document.querySelector('#i_{cv} .ilabel').textContent")
    ok('small item gains a label when zoomed in', small=='' and 'VAC' in big, f'{small!r} -> {big!r}')
    fs=await E("()=>Math.max(...[...document.querySelectorAll('.ilabel')].filter(e=>e.textContent).map(e=>parseFloat(e.style.fontSize)*zoom))")
    ok('on-screen label size capped at 16px', fs<=16.01, str(fs))
    await E("()=>zoomFit()")
    # file menu
    await pg.click('#btnFile')
    ok('file menu opens', await pg.is_visible('#fileMenu'))
    await pg.click('[data-file=versions]')
    ok('file menu → versions dialog', await pg.is_visible('#verOv'))
    await pg.keyboard.press('Escape')
    # layers: empty hidden by default
    n1=await pg.locator('#layers .layer-row').count()
    await pg.click('#layers .linkish'); n2=await pg.locator('#layers .layer-row').count()
    ok('empty layers can be shown', n2>n1, f'{n1}->{n2}')
    # portrait bottom sheet
    pg2=await (await b.new_context(viewport={'width':820,'height':1180},has_touch=True)).new_page()
    await pg2.goto(URL); await pg2.wait_for_timeout(300)
    box=await pg2.evaluate("()=>{const r=inspector.getBoundingClientRect();return [r.top,r.width]}")
    ok('portrait: inspector is a bottom sheet', box[0]>500 and box[1]>800, str(box))
    ok('no page errors', not errs, str(errs))
    await b.close()
  print(sum(res),'/',len(res)); sys.exit(0 if all(res) else 1)
asyncio.run(main())
