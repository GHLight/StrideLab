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

# Geographic research output: independent reader verifies synthetic provenance,
# timestamp, coordinates and physiological data from the same generated row.
geo_script=r'''
const C=require('./app/src/main/assets/core.js'),F=require('./app/src/main/assets/session-formats.js');
const marks=[[30,120],[30,120.001],[30.0005,120.001],[30.0005,120]];
const shape=C.referenceLocalRoute(marks,true,80,'smooth',.5);
const cfg={count:2,distance:2,pace:6,cv:5,noise:1.5,seed:17,fixedStart:0,randomStart:false,direction:'forward',fatigue:'normal',accel:true,decel:true,positionMode:'geo'};
const s=C.simulateResearch(cfg,shape.points,true,0,shape.georeference);
const t={sample_id:s.id,synthetic:true,scenario_start:'2030-01-01T00:00:00Z',scenario_end:'2030-01-01T00:12:00Z'};
let rejected=0;
for(const bad of [null, {...shape.georeference,source:'invalid'}])try{C.simulateResearch(cfg,shape.points,true,0,bad)}catch(e){rejected++}
if(rejected!==2)throw Error('invalid reference accepted');
const bad=structuredClone(s);bad.rows[0].latitude_deg=999;try{F.fit(bad,t);throw Error('accepted')}catch(e){if(e.message==='accepted')throw e}
const ordinary=C.simulateResearch({...cfg,positionMode:'none'},shape.points,true,0,shape.georeference);
console.log(JSON.stringify({session:s,timeline:t,fit:Buffer.from(F.fit(s,t)).toString('base64'),tcx:F.tcx(s,t),ordinary:Buffer.from(F.fit(ordinary,t)).toString('base64')}));
'''
g=json.loads(subprocess.check_output(['node','-e',geo_script],cwd=ROOT))
with fitdecode.FitReader(io.BytesIO(base64.b64decode(g['fit'])),check_crc=fitdecode.CrcCheck.RAISE) as reader:
    messages=[m for m in reader if isinstance(m,fitdecode.FitDataMessage)]
records=[m for m in messages if m.name=='record']
assert len(records)==721
assert next(m for m in messages if m.name=='session').get_value('sport_profile_name')=='SYNTHETIC_RESEARCH'
xml=etree.fromstring(g['tcx'].encode())
track=xml.findall('.//t:Trackpoint',ns)
assert len(track)==len(records)
assert 'synthetic geographic research' in ''.join(xml.itertext())
if schema:schema.assertValid(xml)
for m,r,x in zip(records,g['session']['rows'],track):
    assert r['position_source']=='synthetic_map_reference' and r['synthetic'] is True
    assert abs(m.get_value('position_lat')*180/2**31-r['latitude_deg'])<1e-7
    assert abs(m.get_value('position_long')*180/2**31-r['longitude_deg'])<1e-7
    assert abs(m.get_value('heart_rate')-r['hr_bpm'])<=.50001
    assert abs(m.get_value('cadence')*2-r['cadence_spm'])<=1.00001
    assert abs(m.get_value('distance')-r['distance_m'])<=.00501
    assert m.get_value('timestamp')==datetime.datetime(2030,1,1,tzinfo=datetime.timezone.utc)+datetime.timedelta(seconds=r['t'])
    assert abs(float(x.find('t:Position/t:LatitudeDegrees',ns).text)-r['latitude_deg'])<=.00000051
    assert abs(float(x.find('t:Position/t:LongitudeDegrees',ns).text)-r['longitude_deg'])<=.00000051
with fitdecode.FitReader(io.BytesIO(base64.b64decode(g['ordinary'])),check_crc=fitdecode.CrcCheck.RAISE) as reader:
    assert not any(f.name in ('position_lat','position_long') for m in reader if isinstance(m,fitdecode.FitDataMessage) and m.name=='record' for f in m.fields)
print('PASS: geographic synthetic research FIT/TCX coordinates, cadence, HR, time and no-GPS separation')

# All ordinary and geographic exports use the FIT 1.x header and standard
# field definitions. Independently check the header size and payload length.
for encoded in [*(c['fit'] for c in cases),g['fit'],g['ordinary'],gps['fit']]:
    raw=base64.b64decode(encoded)
    assert raw[0]==14 and raw[1]==0x10 and raw[8:12]==b'.FIT'
    assert int.from_bytes(raw[4:8],'little')==len(raw)-16
print('PASS: FIT 1.0 headers for selected, geographic and no-GPS exports')
