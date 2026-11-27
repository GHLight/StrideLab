from playwright.sync_api import sync_playwright
from pathlib import Path
import zipfile, json,csv,io,tempfile
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1,accept_downloads=True,is_mobile=True,has_touch=True)
 errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 html=(ROOT/'StrideLab_v0.1.html').read_text();page.set_content(html.replace('<script>/* StrideLab', '<script>Object.defineProperty(window,"localStorage",{value:{getItem:k=>window._store?.[k]||null,setItem:(k,v)=>{(window._store??={})[k]=v}},configurable:true});</script><script>/* StrideLab',1));page.wait_for_selector('#routeSvg circle');assert page.locator('#npts').inner_text()=='26';assert abs(float(page.locator('#len').inner_text())-400)<1
 page.screenshot(path=str(ROOT/'route-test.png'),full_page=True)
 page.click('#clear');assert page.locator('#npts').inner_text()=='0';page.click('#undo');assert page.locator('#npts').inner_text()=='26';page.click('#redo');assert page.locator('#npts').inner_text()=='0';page.click('#preset')
 page.locator('[data-node="3"]').click();page.click('#insert');assert page.locator('#npts').inner_text()=='27';page.click('#delete');assert page.locator('#npts').inner_text()=='26'
 page.locator('nav [data-go="sim"]').click();page.fill('#count','3');page.uncheck('#randomStart');page.locator('#fixedStart').fill('30');page.locator('#noise').fill('0');page.screenshot(path=str(ROOT/'sim-test.png'),full_page=True)
 page.click('#generate');page.wait_for_selector('#results',state='visible');assert page.locator('#modelDist').inner_text()=='2.000';assert page.locator('#rms').inner_text()=='0.00';assert page.locator('#summaryBody tr').count()==3
 page.screenshot(path=str(ROOT/'analysis-test.png'),full_page=True)
 page.locator('nav [data-go="files"]').click()
 with page.expect_download() as d: page.click('#download')
 out=d.value.path()
 with zipfile.ZipFile(out) as z:
  assert z.testzip() is None;assert '用途声明.txt' in z.namelist();m=json.loads(z.read('manifest.json'));assert m['synthetic'] and len(m['summary'])==3;assert m['config']['fixedStart']==30
  for n in z.namelist():
   if n.startswith('samples/'):
    r=list(csv.DictReader(io.StringIO(z.read(n).decode())));assert len(r)==721 and all(x['synthetic']=='true' for x in r);assert 'lat' not in r[0]
 saved=page.evaluate('window._store');page=browser.new_page(viewport={'width':390,'height':844});page.on('pageerror',lambda e: errors.append(str(e)));page.set_content(html.replace('<script>/* StrideLab', '<script>window._store='+json.dumps(saved)+';Object.defineProperty(window,"localStorage",{value:{getItem:k=>window._store?.[k]||null,setItem:(k,v)=>{window._store[k]=v}},configurable:true});</script><script>/* StrideLab',1));page.locator('nav [data-go="sim"]').click();assert page.locator('#count').input_value()=='3';assert not page.locator('#randomStart').is_checked();assert page.locator('#fixedStart').input_value()=='30'
 assert not errors, errors
 print('PASS: mobile Chromium UI, route edit history, settings, simulation, ZIP contents, mocked draft persistence, no JS errors')
 browser.close()
