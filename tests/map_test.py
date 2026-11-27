from pathlib import Path
from playwright.sync_api import sync_playwright
import base64, json
ROOT=Path(__file__).resolve().parents[1]
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/Qn8AAAAASUVORK5CYII=')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);page=b.new_page(viewport={'width':390,'height':844},accept_downloads=True)
 errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 page.route('https://tile.openstreetmap.org/**',lambda r:r.fulfill(status=200,content_type='image/png',body=PNG))
 h=(ROOT/'StrideLab_v0.1.html').read_text();page.set_content(h.replace('<script>/* StrideLab','<script>Object.defineProperty(window,"localStorage",{value:{getItem:k=>null,setItem:(k,v)=>{}},configurable:true});</script><script>/* StrideLab',1))
 page.click('#mapEnable');page.wait_for_selector('#referenceMap',state='visible')
 for lat,lon in [(35,120),(35.001,120),(35.001,120.001),(35,120.001)]:
  page.fill('#mapLat',str(lat));page.fill('#mapLon',str(lon));page.click('#mapCenter');page.click('#mapAdd')
 assert page.locator('#mapCount').inner_text()=='4';assert 390<float(page.locator('#mapLength').inner_text())<420
 page.select_option('#mapNode','2');page.click('#mapDelete');assert page.locator('#mapCount').inner_text()=='3'
 page.click('#mapReverse');page.click('#mapSave');assert '3 个' in page.locator('#geoInfo').inner_text();assert page.locator('#npts').inner_text()=='26'
 with page.expect_download() as d:page.click('#exportGeo')
 g=json.loads(d.value.path().read_text());assert g['properties']['purpose']=='reference_only';assert len(g['geometry']['coordinates'])==3
 page.click('#helpBtn');assert page.locator('#helpDialog').is_visible();page.click('#helpClose');assert not page.locator('#helpDialog').is_visible()
 assert not errors,errors
 print('PASS: map UI with mocked tiles; coordinate entry, multiple reference points, measurement, delete, reverse, save, GeoJSON, independent simulation geometry, help dialog')
 b.close()
