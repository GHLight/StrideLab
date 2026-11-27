"""Interact with the installed APK through Android UIAutomator, including system Save."""
import re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
OUT=Path('test-evidence');OUT.mkdir(exist_ok=True)
def adb(*args):return subprocess.check_output(['adb',*args],text=True)
def tree():
    # Accessibility may not be ready immediately after a cold restart.
    # Remove the old dump so a transient failure cannot pass on stale UI.
    for attempt in range(10):
        adb('shell','rm','-f','/sdcard/stride-workflow.xml')
        try:
            adb('shell','uiautomator','dump','/sdcard/stride-workflow.xml')
            return ET.fromstring(adb('shell','cat','/sdcard/stride-workflow.xml'))
        except (subprocess.CalledProcessError,ET.ParseError):
            if attempt==9:raise
            time.sleep(1)

def center(n):
    v=list(map(int,re.findall(r'\d+',n.get('bounds',''))))
    if len(v)!=4 or v[2]<=v[0] or v[3]<=v[1]:return None
    return ((v[0]+v[2])//2,(v[1]+v[3])//2)
def click(label,scroll=False):
    for attempt in range(18 if scroll else 4):
        root=tree()
        for n in root.iter('node'):
            if n.get('text')==label or n.get('content-desc')==label:
                c=center(n)
                if c and n.get('enabled')=='true':
                    # WebView exposes some offscreen nodes with bounds below the fixed navigation.
                    if scroll and c[1]>540:continue
                    adb('shell','input','tap',str(c[0]),str(c[1]));time.sleep(.8);return
        if scroll:adb('shell','input','swipe','160','490','160','170','350')
        time.sleep(.5)
    raise AssertionError('Visible Android control missing: '+label)
def capture(name):
    (OUT/(name+'.png')).write_bytes(subprocess.check_output(['adb','exec-out','screencap','-p']))
    (OUT/(name+'.xml')).write_text(ET.tostring(tree(),encoding='unicode'))
def assert_analysis():
    root=tree();labels=[n.get('text','') for n in root.iter('node')]
    assert any('模型里程' in t or '理论距离' in t or '模型距离' in t for t in labels),labels
    assert not any('还没有模拟结果' in t for t in labels)
# Use a fixed viewport, so scrolling avoids the bottom navigation on all runner AVDs.
adb('shell','wm','size','320x640');adb('shell','wm','density','160');time.sleep(1)
# Reproduce the reported first-run location denial on the actual Android WebView.
# This is an isolated CI emulator; no user installation is cleared.
adb('shell','pm','clear','lab.stridelab')
for permission in ['android.permission.ACCESS_FINE_LOCATION','android.permission.ACCESS_COARSE_LOCATION']:
    adb('shell','pm','revoke','lab.stridelab',permission)
    adb('shell','pm','set-permission-flags','lab.stridelab',permission,'user-set','user-fixed')
adb('shell','am','force-stop','lab.stridelab');adb('shell','am','start','-W','-n','lab.stridelab/.MainActivity');time.sleep(2)
# The generic div's aria-label is not consistently exposed by Android WebView.
# Require the visible recovery text inside the map, after scrolling it into view.
visible_prompt=False
for attempt in range(12):
    root=tree()
    if any('尚未确定地图位置' in n.get('text','') and center(n) and 30<center(n)[1]<530 for n in root.iter('node')):
        visible_prompt=True
        break
    adb('shell','input','swipe','6','490','6','170','350')
    time.sleep(.5)
capture('android-map-location-denied')
assert visible_prompt,'Visible location recovery prompt missing from map region'
web=next(n for n in root.iter('node') if n.get('class')=='android.webkit.WebView')
assert int(re.findall(r'\d+',web.get('bounds'))[1])>=20,'WebView overlaps status bar'
capture('android-map-location-denied')
for permission in ['android.permission.ACCESS_COARSE_LOCATION','android.permission.ACCESS_FINE_LOCATION']:
    adb('shell','pm','clear-permission-flags','lab.stridelab',permission,'user-set','user-fixed')
    adb('shell','pm','grant','lab.stridelab',permission)
adb('shell','am','force-stop','lab.stridelab');adb('shell','am','start','-W','-n','lab.stridelab/.MainActivity');time.sleep(2)
click('模拟');click('生成研究样本',scroll=True);time.sleep(2)
click('分析');assert_analysis();capture('android-generated-analysis')
adb('shell','am','force-stop','lab.stridelab');adb('shell','am','start','-W','-n','lab.stridelab/.MainActivity');time.sleep(2)
click('分析');assert_analysis();capture('android-restored-analysis')
click('文件');click('导出所选 FIT',scroll=True);capture('android-fit-save-dialog')
root=tree();labels=[n.get('text','') for n in root.iter('node')]
assert any('SIM-1_SYNTHETIC' in t for t in labels),labels
saved=False
for n in root.iter('node'):
    if n.get('text','').upper()=='SAVE' or n.get('text')=='保存' or n.get('content-desc','').lower()=='save':
        c=center(n)
        if c and n.get('enabled')=='true':adb('shell','input','tap',str(c[0]),str(c[1]));saved=True;break
assert saved,'System save control not found'
time.sleep(2)
paths=adb('shell','find','/sdcard/Download','-name','SIM-1_SYNTHETIC.fit').strip().splitlines()
assert paths,'Saved FIT missing from Downloads'
adb('pull',paths[0],str(OUT/'android-selected.fit'))
b=(OUT/'android-selected.fit').read_bytes();assert b[8:12]==b'.FIT' and len(b)>1000
c=0
for v in b:
    c^=v
    for _ in range(8):c=(c>>1)^0xa001 if c&1 else c>>1
assert c==0,'Saved FIT CRC mismatch'
capture('android-export-complete')
print('PASS: installed APK generation, process restart result recovery, selected FIT Android system save and file CRC')
