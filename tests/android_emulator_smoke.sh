#!/usr/bin/env bash
set -euo pipefail
apk="${1:?usage: android_emulator_smoke.sh APK}"
package=lab.stridelab
mkdir -p test-evidence
capture() {
  adb exec-out screencap -p > test-evidence/android-screen.png || true
  adb logcat -d -v threadtime > test-evidence/android-logcat.txt || true
}
trap capture EXIT
adb wait-for-device
adb shell input keyevent 82
adb logcat -c
adb install -r -g "$apk"
# Test location path without blocking on an interactive permission dialog.
adb emu geo fix 120 30 || true
adb shell am force-stop "$package"
adb shell am start -W -n "$package/.MainActivity" | tee test-evidence/launch.txt
grep -q 'Status: ok' test-evidence/launch.txt
ready=0
for attempt in $(seq 1 15); do
  rm -f test-evidence/android-ui.xml
  adb shell rm -f /sdcard/stridelab-ui.xml || true
  if adb shell pidof "$package" >/dev/null && adb shell uiautomator dump /sdcard/stridelab-ui.xml >> test-evidence/ui-dump-attempts.txt 2>&1 && adb pull /sdcard/stridelab-ui.xml test-evidence/android-ui.xml >> test-evidence/ui-dump-attempts.txt 2>&1; then
    if grep -q 'StrideLab' test-evidence/android-ui.xml && grep -Eq '场地编辑|路线|地图参考编辑' test-evidence/android-ui.xml; then
      ready=1
      break
    fi
  fi
  echo "UI not ready on attempt $attempt" | tee -a test-evidence/ui-dump-attempts.txt
  sleep 2
done
if [ "$ready" != 1 ]; then
  echo "Application UI did not become ready; see UI dump attempts and screenshot" >&2
  exit 1
fi
adb shell pidof "$package" >/dev/null
adb logcat -d -v threadtime > test-evidence/android-logcat.txt
if grep -q 'Process: lab.stridelab,' test-evidence/android-logcat.txt; then
  echo "Application crash reported in logcat" >&2
  exit 1
fi
python3 tests/android_workflow_test.py
echo "PASS: installed APK, launch, live process and visible route UI on emulator"
