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
        page.fill("#scenarioDate","2030-12-31")
        page.fill("#scenarioTime","23:55")
        page.select_option("#scenarioZone","+08:00")
        page.fill("#scenarioDayGap","2")
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
            timeline = manifest["scenario_timeline"]
            assert timeline[0]["scenario_start"] == "2030-12-31T23:55:00+08:00"
            assert timeline[0]["scenario_end"] == "2031-01-01T00:07:00+08:00"
            assert timeline[2]["scenario_start"] == "2031-01-04T23:55:00+08:00"
            assert all(r["synthetic"] is True for r in timeline)
            assert "scenario_timeline.csv" in z.namelist()
            sample_names = [n for n in z.namelist() if n.startswith("samples/")]
            assert len(sample_names) == 3
            for n in sample_names:
                rows = list(csv.DictReader(io.StringIO(z.read(n).decode())))
                assert rows and all(r["synthetic"] == "true" for r in rows)
                assert "lat" not in rows[0] and "lon" not in rows[0]
        page.reload()
        page.locator('nav [data-go="sim"]').click()
        expect(page.locator("#count")).to_have_value("3")
        expect(page.locator("#scenarioDate")).to_have_value("2030-12-31")
        expect(page.locator("#scenarioTime")).to_have_value("23:55")
        expect(page.locator("#scenarioZone")).to_have_value("+08:00")
        expect(page.locator("#scenarioDayGap")).to_have_value("2")
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
        # FIT and TCX are standalone fixed synthetic fixtures, not exports of the current experiment.
        page.click("#exportFitFixture")
        page.click("#exportTcxFixture")
        fixtures = page.evaluate("window.__exports.slice(-2)")
        assert fixtures[0]["name"] == "SYNTHETIC_FORMAT_FIXTURE.fit"
        assert fixtures[1]["name"] == "SYNTHETIC_FORMAT_FIXTURE.tcx"
        import sys
        import xml.etree.ElementTree as ET
        sys.path.insert(0, str(ROOT / "skills/synthetic-running-data/scripts"))
        from format_fixture import validate_fit
        validate_fit(base64.b64decode(fixtures[0]["data"]), 31)
        xml = ET.fromstring(base64.b64decode(fixtures[1]["data"]))
        ns = {"t": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
        assert len(xml.findall(".//t:Trackpoint", ns)) == 31
        assert xml.find(".//t:TotalTimeSeconds", ns).text == "30"
        assert xml.find(".//t:DistanceMeters", ns).text == "50"
        assert not xml.findall(".//t:Position", ns)
        assert "SYNTHETIC_RESEARCH" in "".join(xml.itertext())
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print("PASS: packaged assets, mobile layout, route edit, synthetic ZIP bridge and real draft reload; native bridge mocked")
