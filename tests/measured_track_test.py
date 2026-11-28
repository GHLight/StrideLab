"""Independent tests for native device-track FIT/TCX serialization.
Only fixed ocean coordinates are used as test inputs. No app location bridge is mocked.
"""
import datetime as dt
import io
import math
from pathlib import Path
import subprocess
import tempfile
import fitdecode
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
HARNESS=r"""
package lab.stridelab;
import java.nio.file.Files;
import java.nio.file.Paths;
public class MeasuredTrackHarness {
 public static void main(String[] args) throws Exception {
  MeasuredTrack m=new MeasuredTrack();
  long t=1893456000L;
  if(m.add(t,0,-140))throw new AssertionError("not recording");
  m.start();
  if(!m.add(t,0,-140)||!m.add(t+10,0,-139.9999)||!m.add(t+20,.0001,-139.9999)||!m.add(t+30,.0001,-140))throw new AssertionError("valid fixes");
  if(m.add(t+29,0,-140)||m.add(t+40,91,-140)||m.add(t+40,0,Double.NaN))throw new AssertionError("invalid fixes");
  try{m.fit();throw new AssertionError("recording export");}catch(IllegalStateException expected){}
  m.stop();
  if(m.size()!=4||m.duration()!=30||Math.abs(m.distance()-33.3585)>.01)throw new AssertionError("track summary");
  Files.write(Paths.get(args[0],"fixture.fit"),m.fit());
  Files.write(Paths.get(args[0],"fixture.tcx"),m.tcx());
  m.start();m.stop();
  try{m.tcx();throw new AssertionError("empty export");}catch(IllegalStateException expected){}
 }
}
"""
with tempfile.TemporaryDirectory() as temp:
    d=Path(temp)
    java=d/'MeasuredTrackHarness.java'
    java.write_text(HARNESS)
    subprocess.check_call(['javac','-d',temp,str(ROOT/'app/src/main/java/lab/stridelab/MeasuredTrack.java'),str(java)])
    subprocess.check_call(['java','-cp',temp,'lab.stridelab.MeasuredTrackHarness',temp])
    with fitdecode.FitReader(io.BytesIO((d/'fixture.fit').read_bytes()),check_crc=fitdecode.CrcCheck.RAISE) as reader:
        msgs=[m for m in reader if isinstance(m,fitdecode.FitDataMessage)]
    records=[m for m in msgs if m.name=='record']
    pos=[(0,-140),(0,-139.9999),(.0001,-139.9999),(.0001,-140)]
    ns={'t':'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}
    xml=etree.parse(str(d/'fixture.tcx'))
    tracks=xml.findall('.//t:Trackpoint',ns)
    assert len(records)==len(tracks)==len(pos)
    for i,(m,node,(lat,lon)) in enumerate(zip(records,tracks,pos)):
        assert abs(m.get_value('position_lat')*180/2**31-lat)<1e-7
        assert abs(m.get_value('position_long')*180/2**31-lon)<1e-7
        expected=dt.datetime.fromtimestamp(1893456000+10*i,dt.timezone.utc)
        assert m.get_value('timestamp')==expected
        assert dt.datetime.fromisoformat(node.findtext('t:Time',namespaces=ns).replace('Z','+00:00'))==expected
        assert abs(float(node.findtext('t:Position/t:LatitudeDegrees',namespaces=ns))-lat)<1e-7
        assert abs(float(node.findtext('t:Position/t:LongitudeDegrees',namespaces=ns))-lon)<1e-7
        assert abs(m.get_value('distance')-float(node.findtext('t:DistanceMeters',namespaces=ns)))<=.00501
        assert not any(f.name in ('heart_rate','cadence') for f in m.fields)
    assert not xml.findall('.//t:HeartRateBpm',ns) and not xml.findall('.//t:Cadence',ns)
    session=next(m for m in msgs if m.name=='session')
    assert session.get_value('total_timer_time')==30
    assert abs(session.get_value('total_distance')-33.3585)<.01
print('PASS: native Java track export; FIT CRC/coordinates/time/distance, TCX parity, invalid and empty track rejection')
