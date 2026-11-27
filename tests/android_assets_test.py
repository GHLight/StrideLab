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
        page.add_init_script("""window.__exports=[]; window.StrideAndroid={save:(name,mime,data)=>window.__exports.push({name,mime,data}),locate:()=>setTimeout(()=>window.StrideMapLocation(30,120,12),0)};""")
        page.route("https://tile.openstreetmap.org/**", lambda route: route.fulfill(status=200, content_type="image/png", body=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=")))
        page.route("https://server.arcgisonline.com/**", lambda route: route.fulfill(status=200, content_type="image/png", body=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=")))
        page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        expect(page.locator("#dismissGuide")).to_be_visible()
        page.click("#dismissGuide")
        expect(page.locator("#dismissGuide")).to_be_hidden()
        expect(page.locator("#currentLocationMarker")).to_have_count(1)
        expect(page.locator("#mapAdd")).to_be_enabled()
        page.click("#mapAdd")
        expect(page.locator("#mapCount")).to_have_text("1")
        page.click("#mapUndo")
        expect(page.locator("#mapCount")).to_have_text("0")
        page.click("#mapRedo")
        expect(page.locator("#mapCount")).to_have_text("1")
        page.reload()
        expect(page.locator("#mapCount")).to_have_text("1")
        page.locator(".coordinate-details summary").click()
        page.fill("#mapLat","30.0002")
        page.fill("#mapLon","120")
        page.click("#mapCenter")
        expect(page.locator("#mapAdd")).to_be_enabled()
        page.click("#mapAdd")
        page.fill("#mapLat","30.0002")
        page.fill("#mapLon","120.0002")
        page.click("#mapCenter")
        expect(page.locator("#mapAdd")).to_be_enabled()
        page.click("#mapAdd")
        expect(page.locator("#mapCount")).to_have_text("3")
        page.select_option("#mapProvider","satellite")
        expect(page.locator("#mapAdd")).to_be_enabled()
        expect(page.locator("#mapCount")).to_have_text("3")
        assert "World_Imagery" in page.locator("#tiles img").first.get_attribute("src")
        page.select_option("#mapProvider","street")
        expect(page.locator("#mapAdd")).to_be_enabled()

        page.locator(".reference-library summary").click()
        page.fill("#referenceName","参考测试场地")
        page.click("#referenceFavorite")
        expect(page.locator("#referenceSaved option")).to_have_count(2)
        page.click("#mapClear")
        expect(page.locator("#mapCount")).to_have_text("0")
        page.click("#referenceOpen")
        expect(page.locator("#mapCount")).to_have_text("3")
        page.click("#mapUndo")
        expect(page.locator("#mapCount")).to_have_text("0")
        page.click("#mapRedo")
        expect(page.locator("#mapCount")).to_have_text("3")
        page.locator('nav [data-go="sim"]').click()
        assert page.evaluate("window.StrideHandleBack()") is True
        expect(page.locator("#route")).to_be_visible()
        assert not page.locator("#manualRouteFold").evaluate("(el)=>el.open")
        expect(page.locator("#mapShapePreview")).to_be_visible()
        page.screenshot(path=str(OUT/"route.png"), full_page=True)
        page.locator("#manualRouteFold > summary").click()
        expect(page.locator("#npts")).to_have_text("26")
        page.click("#clear")
        expect(page.locator("#npts")).to_have_text("0")
        page.click("#undo")
        expect(page.locator("#npts")).to_have_text("26")
        page.locator('nav [data-go="sim"]').click()
        page.select_option("#durationMode","duration")
        page.fill("#durationMinutes","14")
        page.fill("#durationSeconds","30")
        assert abs(float(page.locator("#pace").input_value())-7.25)<0.00001
        page.fill("#durationMinutes","12")
        page.fill("#durationSeconds","0")
        expect(page.locator("#pace")).to_have_value("6")
        page.select_option("#durationMode","pace")
        page.fill("#count","31")
        expect(page.locator("#preflightError")).to_contain_text("count")
        page.fill("#count","3")
        expect(page.locator("#preflightError")).to_have_text("")
        page.fill("#scenarioDate","2030-12-31")
        page.fill("#scenarioTime","23:55")
        page.select_option("#scenarioZone","+08:00")
        page.fill("#scenarioDayGap","2")
        page.uncheck("#randomStart")
        page.fill("#fixedStart","30")
        page.fill("#noise","0")
        page.screenshot(path=str(OUT/"simulation.png"), full_page=True)
        assert page.evaluate("""() => {const c={...config(),scenarioGapMode:"range",scenarioGapMin:1,scenarioGapMax:3,count:10};const a=scenarioTimeline(c);return JSON.stringify(a)===JSON.stringify(scenarioTimeline(c))&&a.slice(1).every(r=>r.interval_days>=1&&r.interval_days<=3);}""")
        page.click("#generate")
        expect(page.locator("#results")).to_be_visible(timeout=30000)
        expect(page.locator("#summaryBody tr")).to_have_count(3)
        expect(page.locator("#rms")).to_have_text("0.00")
        expect(page.locator("#qualitySummary")).to_have_text("基础一致性检查通过")
        expect(page.locator("#qualityIntegral")).to_have_text("0.0000%")
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
        page.select_option("#fileSampleSelect","1")
        page.click("#downloadCsvOne")
        csv_export = page.evaluate("window.__exports.at(-1)")
        assert csv_export["name"] == "SIM-2_SYNTHETIC.csv"
        assert all(r["synthetic"] == "true" for r in csv.DictReader(io.StringIO(base64.b64decode(csv_export["data"]).decode())))
        # Selected-session export must follow the archived snapshot, not unsaved form edits.
        page.locator('nav [data-go="sim"]').click()
        page.fill("#distance","4")
        page.fill("#scenarioTime","10:00")
        page.locator('nav [data-go="files"]').click()
        page.click("#downloadFitOne")
        page.click("#downloadTcxOne")
        selected_exports = page.evaluate("window.__exports.slice(-2)")
        assert selected_exports[0]["name"] == "SIM-2_SYNTHETIC.fit"
        import fitdecode
        import xml.etree.ElementTree as ET
        with fitdecode.FitReader(io.BytesIO(base64.b64decode(selected_exports[0]["data"])), check_crc=fitdecode.CrcCheck.RAISE) as reader:
            decoded=[f for f in reader if isinstance(f,fitdecode.FitDataMessage)]
        fitted=[f for f in decoded if f.name=='session'][0]
        assert fitted.get_value('total_distance') == 2000
        assert fitted.get_value('start_time').isoformat() == '2031-01-02T15:55:00+00:00'
        selected_xml=ET.fromstring(base64.b64decode(selected_exports[1]["data"]))
        ns={"t":"http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"}
        assert selected_xml.find('.//t:TotalTimeSeconds',ns).text == '720'
        expect(page.locator("#downloadFitBatch")).to_have_text("导出 3 个 FIT · ZIP")
        assert not page.locator("#fileTestFold").evaluate("(el)=>el.open")
        assert not page.locator("#fileHistoryFold").evaluate("(el)=>el.open")
        page.screenshot(path=str(OUT / "files-selected-exports.png"), full_page=True)
        page.click("#downloadFitBatch")
        batch = page.evaluate("window.__exports.at(-1)")
        assert batch["name"] == "StrideLab_SYNTHETIC_FIT.zip" and batch["mime"] == "application/zip"
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(batch["data"]))) as z:
            assert z.testzip() is None
            manifest = json.loads(z.read("manifest.json"))
            assert manifest["synthetic"] is True and manifest["contains_gps"] is False and manifest["count"] == 3
            assert set(z.namelist()) == {"SIM-1_SYNTHETIC.fit","SIM-2_SYNTHETIC.fit","SIM-3_SYNTHETIC.fit","manifest.json","用途声明.txt"}
            for entry in manifest["files"]:
                data=z.read(entry["name"])
                assert len(data)==entry["size_bytes"]
                assert entry["synthetic"] is True and entry["position_source"]=="none"
                with fitdecode.FitReader(io.BytesIO(data),check_crc=fitdecode.CrcCheck.RAISE) as reader:
                    ms=[f for f in reader if isinstance(f,fitdecode.FitDataMessage)]
                session=next(m for m in ms if m.name=="session")
                assert session.get_value("total_distance")==2000
                assert session.get_value("sport_profile_name")=="SYNTHETIC_RESEARCH"
                assert not any(f.name in ("position_lat","position_long") for m in ms if m.name=="record" for f in m.fields)
            assert z.read("SIM-2_SYNTHETIC.fit")==base64.b64decode(selected_exports[0]["data"])
        page.locator("#fileTestFold > summary").click()
        # Fixed compatibility fixtures remain separate from current-session exports.
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
        # Verify a second experiment cannot replace the first archive.
        page.locator('#fileHistoryFold > summary').click()
        expect(page.locator("#projectHistory option")).to_have_count(1)
        expect(page.locator("#storageInfo")).to_contain_text("1/50")
        page.click("#projectBackup")
        backup = json.loads(base64.b64decode(page.evaluate("window.__exports.at(-1).data")))
        assert backup["synthetic"] is True and len(backup["projects"]) == 1
        page.locator('nav [data-go="sim"]').click()
        page.fill("#count","1")
        page.click("#generate")
        expect(page.locator("#summaryBody tr")).to_have_count(1)
        page.locator('nav [data-go="files"]').click()
        expect(page.locator("#projectHistory option")).to_have_count(2)
        page.select_option("#projectHistory",backup["projects"][0]["id"])
        page.click("#projectOpen")
        expect(page.locator("#summaryBody tr")).to_have_count(3)
        page.locator('nav [data-go="files"]').click()
        page.locator("#projectImportText").locator("xpath=..").locator("summary").click()
        page.fill("#projectImportText",json.dumps(backup))
        page.click("#projectImport")
        expect(page.locator("#projectMessage")).to_contain_text("导入 0 个")
        expect(page.locator("#projectHistory option")).to_have_count(2)
        page.click("#exportLocalPreview")
        local=page.evaluate("window.__exports.at(-1)")
        assert local["name"].endswith("_SYNTHETIC_LOCAL_TRACE.svg")
        svg=ET.fromstring(base64.b64decode(local["data"]))
        assert "NO GPS" in "".join(svg.itertext())
        assert len(svg.findall("{http://www.w3.org/2000/svg}path"))==2
        page.locator("#fileAboutFold > summary").click()
        page.click("#downloadDeclaration")
        notice=page.evaluate("window.__exports.at(-1)")
        assert notice["name"]=="StrideLab_SYNTHETIC_DATA_NOTICE.txt"
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(batch["data"]))) as z:
            assert base64.b64decode(notice["data"])==z.read("用途声明.txt")
        # The saved reference draft produces an adjustable interpolated local route.
        page.locator('nav [data-go="route"]').click()
        expect(page.locator("#mapCount")).to_have_text("3")
        expect(page.locator("#mapShapePreview")).to_be_visible()
        expect(page.locator("#mapShapeStatus")).to_contain_text("3 个标点")
        page.fill("#mapInterpolationCount","80")
        page.select_option("#mapInterpolation","smooth")
        expect(page.locator("#mapShapeStatus")).to_contain_text("80 个插值节点")
        page.select_option("#mapInterpolation","linear")
        expect(page.locator("#mapShapeStatus")).to_contain_text("80 个插值节点")
        preview=page.locator("#mapShapePreview path").get_attribute("d")
        page.click("#mapUseShape")
        expect(page.locator("#sim")).to_be_visible()
        expect(page.locator("#activeRouteInfo")).to_contain_text("80 个节点")
        assert page.locator("#activeRoutePreview path").get_attribute("d")==preview
        page.click("#changeActiveRoute")
        if not page.locator("#manualRouteFold").evaluate("(el)=>el.open"):
            page.locator("#manualRouteFold > summary").click()
        expect(page.locator("#npts")).to_have_text("80")
        assert 65 < float(page.locator("#len").inner_text()) < 90
        page.click("#undo")
        expect(page.locator("#npts")).to_have_text("26")
        page.click("#redo")
        expect(page.locator("#npts")).to_have_text("80")
        assert not errors, errors
        # First install without permission: keep a visible map panel and recover via search.
        denied = browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        denied.on("pageerror",lambda e: errors.append(str(e)))
        denied.add_init_script("""window.StrideAndroid={locate:()=>setTimeout(()=>window.StrideMapLocationError(),0),searchPlace:(q,id)=>setTimeout(()=>window.StrideMapSearchResults(id,[{label:'测试学校校园',lat:30.25,lon:120.15}]),0)};""")
        denied.route("https://tile.openstreetmap.org/**",lambda route:route.fulfill(status=200,content_type="image/png",body=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII=")))
        denied.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        expect(denied.locator("#referenceMap")).to_be_visible()
        expect(denied.locator("#mapMsg")).to_contain_text("尚未确定地图位置")
        expect(denied.locator("#mapLat")).to_have_value("")
        expect(denied.locator("#mapAdd")).to_be_disabled()
        denied.select_option("#mapProvider","satellite")
        expect(denied.locator("#referenceMap")).to_be_visible()
        denied.select_option("#mapProvider","street")
        denied.locator("#referenceMap").scroll_into_view_if_needed()
        denied.screenshot(path=str(OUT/"map-location-denied.png"))
        denied.fill("#mapSearch","测试学校")
        denied.click("#mapSearchGo")
        denied.get_by_role("button",name="前往此位置：测试学校校园").click()
        expect(denied.locator("#mapLat")).to_have_value("30.2500000")
        expect(denied.locator("#mapLon")).to_have_value("120.1500000")
        expect(denied.locator("#mapAdd")).to_be_enabled()
        denied.click("#mapAdd")
        expect(denied.locator("#mapCount")).to_have_text("1")
        denied.evaluate("window.StrideMapLocationError()")
        expect(denied.locator("#referenceMap")).to_be_visible()
        expect(denied.locator("#mapLat")).to_have_value("30.2500000")
        denied.reload()
        expect(denied.locator("#referenceMap")).to_be_visible()
        expect(denied.locator("#mapLat")).to_have_value("30.2500000")
        expect(denied.locator("#mapCount")).to_have_text("1")
        assert not errors,errors
        denied.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print("PASS: packaged assets, mobile layout, route edit, synthetic ZIP bridge and real draft reload; native bridge mocked")
