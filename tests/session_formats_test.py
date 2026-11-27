"""Independent FIT CRC/message decoding and TCX XML/schema validation."""
import io,json,subprocess,datetime,os
from pathlib import Path
import fitdecode
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
script=r'''
const C=require('./app/src/main/assets/core.js'),F=require('./app/src/main/assets/session-formats.js');
const cases=[];
for(const [index,zone,start,end] of [[0,'+08:00','2030-12-31T23:55:00+08:00','2031-01-01T00:07:00+08:00'],[1,'-05:30','2030-12-31T23:55:00-05:30','2031-01-01T00:07:00-05:30']]){
 const c={count:3,distance:2,pace:6,cv:5,noise:1.5,seed:9876,fixedStart:30,direction:'random',fatigue:'normal',accel:true,decel:true,randomStart:false};
 const s=C.simulate(c,C.standardTrack(),true,index),t={sample_id:s.id,synthetic:true,scenario_start:start,scenario_end:end};
 cases.push({session:s,timeline:t,fit:Buffer.from(F.fit(s,t)).toString('base64'),tcx:F.tcx(s,t)});
 for(const bad of [null,{...t,sample_id:'missing'},{...t,scenario_end:start}]){let rejected=false;try{F.fit(s,bad)}catch(e){rejected=true}if(!rejected)throw Error('invalid timeline accepted')}
 const bad=structuredClone(s);bad.rows[2].distance_m=-1;let rejected=false;try{F.fit(bad,t)}catch(e){rejected=true}if(!rejected)throw Error('invalid data accepted');
}
console.log(JSON.stringify(cases));
'''
cases=json.loads(subprocess.check_output(['node','-e',script],cwd=ROOT))
import base64
ns={'t':'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2','a':'http://www.garmin.com/xmlschemas/ActivityExtension/v2'}
schema_path=os.getenv('TCX_SCHEMA');schema=etree.XMLSchema(etree.parse(schema_path)) if schema_path else None
for c in cases:
    with fitdecode.FitReader(io.BytesIO(base64.b64decode(c['fit'])),check_crc=fitdecode.CrcCheck.RAISE) as reader:
        messages=[f for f in reader if isinstance(f,fitdecode.FitDataMessage)]
    records=[m for m in messages if m.name=='record'];sessions=[m for m in messages if m.name=='session']
    assert len(records)==len(c['session']['rows']) and len(sessions)==1
    start=datetime.datetime.fromisoformat(c['timeline']['scenario_start']).astimezone(datetime.timezone.utc)
    for m,r in zip(records,c['session']['rows']):
        assert m.get_value('timestamp')==start+datetime.timedelta(seconds=r['t'])
        assert abs(m.get_value('distance')-r['distance_m'])<=.00501
        assert abs(m.get_value('speed')-r['speed_mps'])<=.000501
        assert abs(m.get_value('cadence')*2-r['cadence_spm'])<=1.00001
        assert abs(m.get_value('heart_rate')-r['hr_bpm'])<=.50001
        assert not any(f.name in ('position_lat','position_long') for f in m.fields)
    ss=sessions[0];assert ss.get_value('total_timer_time')==720 and ss.get_value('total_distance')==2000
    assert ss.get_value('sport')=='running' and ss.get_value('sport_profile_name')=='SYNTHETIC_RESEARCH'
    xml=etree.fromstring(c['tcx'].encode());tracks=xml.findall('.//t:Trackpoint',ns)
    if schema:schema.assertValid(xml)
    assert len(tracks)==721 and not xml.findall('.//t:Position',ns)
    for t,r in zip(tracks,c['session']['rows']):
        assert abs(float(t.find('t:DistanceMeters',ns).text)-r['distance_m'])<.000001
        assert abs(float(t.find('t:Extensions/a:TPX/a:Speed',ns).text)-r['speed_mps'])<.000001
    assert 'SYNTHETIC_RESEARCH' in ''.join(xml.itertext())
# Separate fixed coordinate fixture. Do not conflate local sessions with GPS.
gps=json.loads(subprocess.check_output(['node','-e',"""const F=require('./app/src/main/assets/session-formats.js');console.log(JSON.stringify({fit:Buffer.from(F.gpsFixtureFit()).toString('base64'),tcx:F.gpsFixtureTcx()}));"""],cwd=ROOT))
with fitdecode.FitReader(io.BytesIO(base64.b64decode(gps['fit'])),check_crc=fitdecode.CrcCheck.RAISE) as reader:
    frames=[m for m in reader if isinstance(m,fitdecode.FitDataMessage)]
records=[m for m in frames if m.name=='record']
positions=[(0,-140),(0,-139.9999),(.0001,-139.9999),(.0001,-140)]
assert len(records)==len(positions)
for m,(lat,lon) in zip(records,positions):
    assert abs(m.get_value('position_lat')*180/2**31-lat)<1e-7
    assert abs(m.get_value('position_long')*180/2**31-lon)<1e-7
assert next(m for m in frames if m.name=='session').get_value('sport_profile_name')=='SYNTHETIC_RESEARCH'
xml=etree.fromstring(gps['tcx'].encode())
if schema:schema.assertValid(xml)
track=xml.findall('.//t:Trackpoint/t:Position',ns)
assert len(track)==4
for node,(lat,lon) in zip(track,positions):
    assert float(node.find('t:LatitudeDegrees',ns).text)==lat
    assert float(node.find('t:LongitudeDegrees',ns).text)==lon
assert 'fixed ocean coordinate parser fixture' in ''.join(xml.itertext())
print('PASS: fixed GPS fixture FIT coordinate decoding and matching TCX positions')
print('PASS: selected session FIT independent CRC/decode, UTC offsets, cadence units, row/summary consistency, invalid inputs, TCX XML'+(' and official XSD' if schema else '; XSD not requested'))
