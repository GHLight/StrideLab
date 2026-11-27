"""Exercise the exact assets packaged into the Android APK, not the standalone prototype."""
import base64
import csv
import io
import json
import os
import threading
import zipfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "app/src/main/assets"
OUT = ROOT / "test-evidence"
OUT.mkdir(exist_ok=True)
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ASSETS)))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH") or None, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script("""window.__exports=[]; window.StrideAndroid={save:(name,mime,data)=>window.__exports.push({name,mime,data}),locate:()=>{}};""")
        page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        expect(page.locator("#npts")).to_have_text("26")
        page.screenshot(path=str(OUT/"route.png"), full_page=True)
        page.click("#clear")
        expect(page.locator("#npts")).to_have_text("0")
        page.click("#undo")
        expect(page.locator("#npts")).to_have_text("26")
        page.locator('nav [data-go="sim"]').click()
        page.fill("#count","3")
        page.uncheck("#randomStart")
        page.fill("#fixedStart","30")
        page.fill("#noise","0")
        page.screenshot(path=str(OUT/"simulation.png"), full_page=True)
        page.click("#generate")
        expect(page.locator("#results")).to_be_visible(timeout=30000)
        expect(page.locator("#summaryBody tr")).to_have_count(3)
        expect(page.locator("#rms")).to_have_text("0.00")
        page.screenshot(path=str(OUT/"analysis.png"), full_page=True)
        page.locator('nav [data-go="files"]').click()
        page.click("#download")
        exports = page.evaluate("window.__exports")
        assert len(exports) == 1 and exports[0]["mime"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(exports[0]["data"]))) as z:
            assert z.testzip() is None and "用途声明.txt" in z.namelist()
            manifest = json.loads(z.read("manifest.json"))
            assert manifest["synthetic"] is True and len(manifest["summary"]) == 3
            assert manifest["config"]["fixedStart"] == 30
            sample_names = [n for n in z.namelist() if n.startswith("samples/")]
            assert len(sample_names) == 3
            for n in sample_names:
                rows = list(csv.DictReader(io.StringIO(z.read(n).decode())))
                assert rows and all(r["synthetic"] == "true" for r in rows)
                assert "lat" not in rows[0] and "lon" not in rows[0]
        page.reload()
        page.locator('nav [data-go="sim"]').click()
        expect(page.locator("#count")).to_have_value("3")
        expect(page.locator("#fixedStart")).to_have_value("30")
        assert not page.locator("#randomStart").is_checked()
        page.locator('nav [data-go="analysis"]').click()
        expect(page.locator("#results")).to_be_visible()
        expect(page.locator("#summaryBody tr")).to_have_count(3)
        page.locator('nav [data-go="files"]').click()
        page.click("#download")
        restored = page.evaluate("window.__exports[0]")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(exports[0]["data"]))) as original_zip, zipfile.ZipFile(io.BytesIO(base64.b64decode(restored["data"]))) as restored_zip:
            assert sorted(original_zip.namelist()) == sorted(restored_zip.namelist())
            for name in original_zip.namelist():
                assert original_zip.read(name) == restored_zip.read(name), name
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print("PASS: packaged assets, mobile layout, route edit, synthetic ZIP bridge and real draft reload; native bridge mocked")
