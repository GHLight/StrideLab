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
        expect(page.locator("#mapUseShape")).to_be_visible()
        expect(page.locator("#mapUseShape")).to_be_enabled()
        expect(page.locator("#mapEditFold")).not_to_have_attribute("open","")
        page.locator("#mapEditFold > summary").click()
        page.select_option("#mapNode","1")
        page.click("#mapNodeEarlier")
        expect(page.locator("#mapNode")).to_have_value("0")
        page.click("#mapUndo")
        expect(page.locator("#mapCount")).to_have_text("3")
        page.locator('#mapProvider-segments button[data-choice="satellite"]').click()
        expect(page.locator("#mapAdd")).to_be_enabled()
        expect(page.locator("#mapCount")).to_have_text("3")
        assert "World_Imagery" in page.locator("#tiles img").first.get_attribute("src")
        page.locator('#mapProvider-segments button[data-choice="street"]').click()
        expect(page.locator("#mapAdd")).to_be_enabled()

        page.locator("#mapStorageFold > summary").click()
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
        page.locator('#durationMode-segments button[data-choice="duration"]').click()
        page.fill("#durationMinutes","14")
        page.fill("#durationSeconds","30")
        assert abs(float(page.locator("#pace").input_value())-7.25)<0.00001
        page.fill("#durationMinutes","12")
        page.fill("#durationSeconds","0")
        expect(page.locator("#pace")).to_have_value("6")
        page.locator('#durationMode-segments button[data-choice="pace"]').click()
        page.fill("#count","31")
        expect(page.locator("#preflightError")).to_contain_text("count")
        page.fill("#count","3")
        expect(page.locator("#preflightError")).to_have_text("")
        page.fill("#scenarioDate","2030-12-31")
        page.fill("#scenarioTime","23:55")
        page.select_option("#scenarioZone","+08:00")
        page.get_by_role("button",name="随机区间",exact=True).click()
        expect(page.locator("#scenarioGapMin")).to_be_visible()
        expect(page.get_by_role("button",name="随机区间",exact=True)).to_have_attribute("aria-pressed","true")
        page.get_by_role("button",name="固定间隔",exact=True).click()
        expect(page.locator("#scenarioGapMin")).to_be_hidden()
        page.fill("#scenarioDayGap","2")
        page.uncheck("#randomStart")
        page.fill("#fixedStart","30")
        if not page.locator("#motionAdvancedFold").evaluate("(el)=>el.open"):
            page.locator("#motionAdvancedFold > summary").click()
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
        page.select_option("#fileSampleSelect","1")
        page.click("#exportLocalPreview")
        local=page.evaluate("window.__exports.at(-1)")
        assert local["name"]=="SIM-2_SYNTHETIC_LOCAL_TRACE.svg"
        assert page.locator("#sampleSelect").input_value()=="1"
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
        # A number field must permit an empty or temporarily too-small value
        # while the user is replacing the digits, without deleting map marks.
        count_field=page.locator("#mapInterpolationCount")
        count_field.fill("11")
        expect(count_field).to_have_value("11")
        count_field.fill("")
        expect(count_field).to_have_value("")
        expect(page.locator("#mapUseShape")).to_be_disabled()
        count_field.press_sequentially("17")
        expect(count_field).to_have_value("17")
        expect(page.locator("#mapShapeStatus")).to_contain_text("17 个插值节点")
        expect(page.locator("#mapCount")).to_have_text("3")
        expect(page.locator("#mapUseShape")).to_be_enabled()
        count_field.fill("1")
        expect(count_field).to_have_value("1")
        expect(page.locator("#mapUseShape")).to_be_disabled()
        count_field.fill("300")
        expect(page.locator("#mapShapeStatus")).to_contain_text("300 个插值节点")
        expect(page.locator("#mapUseShape")).to_be_disabled()
        expect(page.locator("#mapPreviewExport")).to_be_enabled()
        page.fill("#nominalRouteLength","80")
        expect(page.locator("#referenceGeometryMetrics")).to_contain_text("标称 80.0 m")
        page.click("#mapPreviewExport")
        preview_json=json.loads(base64.b64decode(page.evaluate("window.__exports.at(-1).data")))
        assert preview_json["properties"]["purpose"]=="reference_geometry_only"
        assert len(preview_json["geometry"]["coordinates"])==301
        assert "timestamp" not in preview_json["properties"]
        page.reload()
        expect(count_field).to_have_value("300")
        expect(page.locator("#nominalRouteLength")).to_have_value("80")
        count_field.fill("80")
        page.locator('#mapInterpolation-segments button[data-choice="smooth"]').click()
        expect(page.locator("#mapShapeStatus")).to_contain_text("80 个插值节点")
        page.locator('#mapInterpolation-segments button[data-choice="linear"]').click()
        expect(page.locator("#mapShapeStatus")).to_contain_text("80 个插值节点")
        page.reload()
        expect(page.locator("#mapInterpolationCount")).to_have_value("80")
        expect(page.locator("#mapInterpolation")).to_have_value("linear")
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
        expect(page.locator("#positionMode")).to_have_value("geo")
        # Map-derived route: the actual exported archive contains geographic FIT records
        # and retains the explicitly synthetic label. The mode can still be switched off.
        expect(page.locator("#mapFittedOverlay")).to_have_count(1)
        page.click("#mapUseShape")
        expect(page.locator("#positionMode")).to_have_value("geo")
        page.fill("#count","2")
        page.fill("#distance","2")
        page.fill("#scenarioDate","2030-01-01")
        page.fill("#scenarioTime","00:00")
        if not page.locator("#motionAdvancedFold").evaluate("(el)=>el.open"):
            page.locator("#motionAdvancedFold > summary").click()
        page.fill("#noise","0")
        page.click("#generate")
        expect(page.locator("#summaryBody tr")).to_have_count(2)
        page.locator('nav [data-go="files"]').click()
        page.click("#downloadFitBatch")
        geo_batch=page.evaluate("window.__exports.at(-1)")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(geo_batch["data"]))) as z:
            assert z.testzip() is None
            manifest=json.loads(z.read("manifest.json"))
            assert manifest["contains_gps"] is True and manifest["count"]==2 and manifest["synthetic"] is True
            for entry in manifest["files"]:
                assert entry["position_source"]=="synthetic_map_reference"
                with fitdecode.FitReader(io.BytesIO(z.read(entry["name"])),check_crc=fitdecode.CrcCheck.RAISE) as reader:
                    ms=[m for m in reader if isinstance(m,fitdecode.FitDataMessage)]
                assert next(m for m in ms if m.name=="session").get_value("sport_profile_name")=="SYNTHETIC_RESEARCH"
                records=[m for m in ms if m.name=="record"]
                assert len(records)==721
                for record in records:
                    assert 29.99999 <= record.get_value("position_lat")*180/2**31 <= 30.00021
                    assert 119.99999 <= record.get_value("position_long")*180/2**31 <= 120.00021
        page.reload()
        page.locator('nav [data-go="files"]').click()
        page.click("#downloadFitBatch")
        geo_restored=page.evaluate("window.__exports.at(-1)")
        assert geo_restored["data"]==geo_batch["data"]
        page.locator('nav [data-go="sim"]').click()
        page.locator('#positionMode-segments button[data-choice="none"]').click()
        page.click("#generate")
        expect(page.locator("#analysis")).to_be_visible(timeout=30000)
        expect(page.locator("#summaryBody tr")).to_have_count(2)
        page.locator('nav [data-go="files"]').click()
        page.click("#downloadFitBatch")
        local_batch=page.evaluate("window.__exports.at(-1)")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(local_batch["data"]))) as z:
            assert json.loads(z.read("manifest.json"))["contains_gps"] is False
            with fitdecode.FitReader(io.BytesIO(z.read("SIM-1_SYNTHETIC.fit")),check_crc=fitdecode.CrcCheck.RAISE) as reader:
                assert not any(f.name in ("position_lat","position_long") for m in reader if isinstance(m,fitdecode.FitDataMessage) and m.name=="record" for f in m.fields)

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
        denied.locator('#mapProvider-segments button[data-choice="satellite"]').click()
        expect(denied.locator("#referenceMap")).to_be_visible()
        denied.locator('#mapProvider-segments button[data-choice="street"]').click()
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
        # Independent local sensitivity study using actual app controls and export.
        local_page=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        local_page.on("pageerror",lambda e: errors.append(str(e)))
        local_page.add_init_script("""window.__exports=[]; window.StrideAndroid={save:(name,mime,data)=>window.__exports.push({name,mime,data}),locate:()=>setTimeout(()=>window.StrideMapLocationError(),0)};""")
        local_page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        local_page.locator('nav [data-go="sim"]').click()
        local_page.locator('#positionMode-segments button[data-choice="none"]').click()
        assert local_page.evaluate("""() => {const c=config(),d=openedAt,p=n=>String(n).padStart(2,"0");return c.scenarioDate===d.getFullYear()+"-"+p(d.getMonth()+1)+"-"+p(d.getDate())&&c.scenarioTime===p(d.getHours())+":"+p(d.getMinutes());}""")
        local_page.fill("#count","5")
        local_page.fill("#distance","2")
        local_page.fill("#distanceSpreadM","100")
        local_page.fill("#paceSpreadSec","20")
        # Open the advanced parameter section as a user would.
        seed_details=local_page.locator("#seed").locator("xpath=ancestor::details")
        if seed_details.count():
            for j in reversed(range(seed_details.count())):
                fold=seed_details.nth(j)
                if not fold.evaluate("(el)=>el.open"):
                    fold.locator("xpath=./summary").click()
        expect(local_page.locator("#seed")).to_be_visible()
        local_page.fill("#seed","17")
        expect(local_page.locator("#preflightError")).to_have_text("")
        local_page.click("#generate")
        expect(local_page.locator("#results")).to_be_visible(timeout=30000)
        expect(local_page.locator("#summaryBody tr")).to_have_count(5)
        expect(local_page.locator("#qualityIntegral")).to_have_text("0.0000%")
        expect(local_page.locator("#statSpeedCV")).to_contain_text("%")
        expect(local_page.locator("#statStepChart path")).not_to_have_count(0)
        local_page.click("#statDownload")
        report=json.loads(base64.b64decode(local_page.evaluate("window.__exports.at(-1).data")))
        assert report["synthetic"] is True and len(report["samples"])==5
        assert report["batch_distance_m"]["n"]==5 and report["batch_distance_m"]["sd"]>0
        local_page.locator('nav [data-go="files"]').click()
        local_page.click("#download")
        sweep_export=local_page.evaluate("window.__exports.at(-1)")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(sweep_export["data"]))) as z:
            import hashlib
            manifest=json.loads(z.read("manifest.json"))
            assert manifest["integrity_algorithm"]=="SHA-256"
            assert "README.txt" in z.namelist()
            assert all(hashlib.sha256(z.read(n)).hexdigest()==h for n,h in manifest["file_hashes"].items())
            for line in z.read("checksums.sha256").decode().splitlines():
                h,n=line.split("  ",1)
                assert hashlib.sha256(z.read(n)).hexdigest()==h
            assert all(x["passed"] for x in json.loads(z.read("quality.json")))
            targets=[s["target_distance_m"] for s in manifest["summary"]]
            assert len(set(targets))==5 and all(1900<=d<=2100 for d in targets)
            for i,s in enumerate(manifest["summary"]):
                assert abs(s["model_distance_m"]-targets[i])<1e-6
                assert 340 <= s["target_pace_sec_km"] <= 380
                assert abs(s["seconds"]-targets[i]*s["target_pace_sec_km"]/1000)<=0.500001
            assert len(set(s["target_pace_sec_km"] for s in manifest["summary"]))==5
        local_page.reload()
        local_page.locator('nav [data-go="sim"]').click()
        expect(local_page.locator("#distanceSpreadM")).to_have_value("100")
        expect(local_page.locator("#paceSpreadSec")).to_have_value("20")
        local_page.locator('nav [data-go="files"]').click()
        local_page.click("#download")
        assert local_page.evaluate("window.__exports.at(-1).data")==sweep_export["data"]
        local_page.locator('nav [data-go="analysis"]').click()
        local_page.locator("#localSampleTools > summary").click()
        local_page.click("#verifySampleReplay")
        expect(local_page.locator("#sampleReviewStatus")).to_contain_text("复现一致")
        local_page.click("#exportSampleJson")
        review=json.loads(base64.b64decode(local_page.evaluate("window.__exports.at(-1).data")))
        assert review["synthetic"] is True and review["quality"]["passed"]
        local_page.select_option("#analysisInterval","5")
        local_page.click("#exportAnalysisCsv")
        analysis_rows=list(csv.DictReader(io.StringIO(base64.b64decode(local_page.evaluate("window.__exports.at(-1).data")).decode())))
        assert len(analysis_rows)<len(review["sample"]["rows"])
        assert int(analysis_rows[-1]["t"])==review["sample"]["rows"][-1]["t"]
        assert all(r["analysis_view"]=="true" for r in analysis_rows)
        # A second saved local experiment enables a comparison without modifying either archive.
        local_page.locator('nav [data-go="sim"]').click()
        local_page.fill("#distance","2.05")
        local_page.click("#generate")
        expect(local_page.locator("#analysis")).to_be_visible(timeout=30000)
        local_page.locator("#groupCompareFold > summary").click()
        expect(local_page.locator("#compareGroups")).to_be_enabled()
        local_page.click("#compareGroups")
        expect(local_page.locator("#groupCompareBody tr")).to_have_count(2)
        local_page.click("#exportGroupComparison")
        comparison=json.loads(base64.b64decode(local_page.evaluate("window.__exports.at(-1).data")))
        assert comparison["synthetic"] is True and len(comparison["groups"])==2
        assert all(g["valid_count"]==g["n"] for g in comparison["groups"])
        # Independent local multi-group workspace: no FIT/TCX or geographic data.
        local_page.locator('nav [data-go="sim"]').click()
        local_page.locator("#localStudyFold > summary").click()
        local_page.fill("#study-0-count","1")
        local_page.fill("#study-1-count","1")
        local_page.fill("#study-0-distance","0.2")
        local_page.fill("#study-1-distance","0.2")
        local_page.select_option("#study-1-profile","higher")
        local_page.click("#studyRun")
        expect(local_page.locator("#studySummary tr")).to_have_count(2,timeout=30000)
        expect(local_page.locator("#studyExport")).to_be_enabled()
        local_page.click("#studyExport")
        study_export=local_page.evaluate("window.__exports.at(-1)")
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(study_export["data"]))) as z:
            manifest=json.loads(z.read("manifest.json"))
            assert manifest["research_only"] is True and manifest["synthetic"] is True
            assert len(manifest["summary"])==2 and all(g["valid"] for g in manifest["summary"])
            assert not any(n.endswith((".fit",".tcx")) for n in z.namelist())
            for name in (n for n in z.namelist() if n.endswith("_SYNTHETIC.csv")):
                rows=list(csv.DictReader(io.StringIO(z.read(name).decode())))
                assert rows and all(r["synthetic"]=="true" for r in rows)
                assert "latitude_deg" not in rows[0] and "longitude_deg" not in rows[0]
        local_page.reload()
        local_page.locator('nav [data-go="sim"]').click()
        local_page.locator("#localStudyFold > summary").click()
        expect(local_page.locator("#studySummary tr")).to_have_count(2)
        local_page.click("#studyExport")
        expect(local_page.locator("#studyStatus")).to_contain_text("已请求保存",timeout=30000)
        assert local_page.evaluate("window.__exports.at(-1).data")==study_export["data"]
        # Simulate an archive at capacity using configuration metadata only.
        # Generation must preserve an unarchived current run.
        local_page.evaluate("""() => {
            const key='stridelab.projects.v1', existing=JSON.parse(localStorage.getItem(key));
            const template=existing.at(-1); // retain the current archived experiment at capacity
            const entries=Array.from({length:50},(_,i)=> {
              const entry=structuredClone(template);
              entry.id='capacity-'+i;
              if(i) entry.snapshot.config.seed=10000+i;
              // Timelines are independent of seed in the fixed-gap case.
              return entry;
            });
            localStorage.setItem(key,JSON.stringify(entries));
        }""")
        local_page.locator('nav [data-go="sim"]').click()
        local_page.fill("#distance","2.1")
        local_page.click("#generate")
        expect(local_page.locator("#analysis")).to_be_visible()
        saved=local_page.evaluate("localStorage.getItem('stridelab.completed.v1')")
        assert json.loads(saved)["config"]["distance"]==2.1
        local_page.locator('nav [data-go="sim"]').click()
        local_page.fill("#distance","2.2")
        local_page.click("#generate")
        expect(local_page.locator("#status")).to_contain_text("当前结果尚未归档")
        assert local_page.evaluate("localStorage.getItem('stridelab.completed.v1')")==saved
        local_page.locator('nav [data-go="files"]').click()
        fold=local_page.locator("#fileHistoryFold")
        if not fold.evaluate("(el)=>el.open"):
            fold.locator("xpath=./summary").click()
        local_page.click("#projectBackup")
        capacity_backup=json.loads(base64.b64decode(local_page.evaluate("window.__exports.at(-1).data")))
        assert len(capacity_backup["projects"])==50
        assert capacity_backup["unarchived_current"]["snapshot"]==json.loads(saved)
        local_page.close()
        # A damaged draft must not be silently overwritten during startup.
        damaged=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,has_touch=True)
        damaged.on("pageerror",lambda e: errors.append(str(e)))
        damaged.add_init_script("""window.__exports=[];window.StrideAndroid={save:(name,mime,data)=>window.__exports.push({name,mime,data}),locate:()=>setTimeout(()=>window.StrideMapLocationError(),0)};if(!localStorage.getItem('injected_draft_test')){localStorage.setItem('stridelab.v0','{broken');localStorage.setItem('injected_draft_test','1');}""")
        damaged.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        expect(damaged.locator("#draftWarning")).to_be_visible()
        assert damaged.evaluate("localStorage.getItem('stridelab.v0')")=="{broken"
        damaged.click("#exportRawDraft")
        assert base64.b64decode(damaged.evaluate("window.__exports.at(-1).data")).decode()=="{broken"
        damaged.click("#resetCorruptDraft")
        assert damaged.evaluate("localStorage.getItem('stridelab.v0')")=="{broken"
        damaged.click("#resetCorruptDraft")
        expect(damaged.locator("#draftWarning")).to_be_hidden()
        assert json.loads(damaged.evaluate("localStorage.getItem('stridelab.v0')"))["points"]
        damaged.close()
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print("PASS: packaged assets, mobile layout, route edit, synthetic ZIP bridge and real draft reload; native bridge mocked")
