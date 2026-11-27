#!/usr/bin/env python3
"""Fixed, explicitly synthetic format fixture; independent of research routes and dates."""
import argparse, datetime as dt, math, struct, zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from generate import require, LABEL, NOTICE, pack
EPOCH=dt.datetime(1989,12,31,tzinfo=dt.timezone.utc)
# FIT protocol primitives; no compressed headers or developer fields.
FMT={0:('B',1),1:('b',1),2:('B',1),0x84:('H',2),0x85:('i',4),0x86:('I',4),0x8c:('I',4)}
def crc(data):
    x=0
    for b in data:
        x^=b
        for _ in range(8): x=(x>>1)^0xa001 if x&1 else x>>1
    return x

def timestamp(s): return round((dt.datetime.fromisoformat(s.replace('Z','+00:00'))-EPOCH).total_seconds())
def sc(x): return round(x*2**31/180)

class Fit:
    def __init__(self): self.data=bytearray(); self.defs={}
    def define(self,local,global_id,fields):
        self.defs[local]=fields; self.data.extend(struct.pack('<BBBHB',0x40|local,0,0,global_id,len(fields)))
        for num,typ,size in fields: self.data.extend(bytes((num,size,typ)))
    def msg(self,local,values):
        fields=self.defs[local]; require(len(values)==len(fields),'FIT field count')
        self.data.append(local)
        for (_,typ,size),v in zip(fields,values):
            if typ==7:
                b=str(v).encode('ascii')[:size-1]; self.data.extend(b+b'\0'*(size-len(b)))
            else: self.data.extend(struct.pack('<'+FMT[typ][0],v))
    def finish(self):
        h=struct.pack('<BBHI4s',14,0x20,2100,len(self.data),b'.FIT'); h+=struct.pack('<H',crc(h))
        b=h+self.data; return bytes(b)+struct.pack('<H',crc(b))

def f(num,typ): return (num,typ,FMT[typ][1])
def string(num,size=32): return (num,7,size)

def make_fit(rows,s,serial):
    t0=timestamp(rows[0]['timestamp_utc']); t1=timestamp(rows[-1]['timestamp_utc']); fit=Fit(); U=0x86; H=0x84; B=2; I=0x85; E=0
    fit.define(0,0,[f(0,E),f(1,H),f(2,H),f(3,0x8c),f(4,U),string(8)])
    fit.msg(0,[4,255,0,serial or 1,t0,LABEL])
    fit.define(1,21,[f(253,U),f(0,E),f(1,E)]); fit.msg(1,[t0,0,0])
    fit.define(2,20,[f(253,U),f(5,U),f(6,H),f(3,B),f(4,B),f(39,H),f(41,H),f(85,H)])
    for r in rows:
        fit.msg(2,[timestamp(r['timestamp_utc']),round(r['model_distance_m']*100),round(r['speed_m_s']*1000),r['heart_rate_bpm'],round(r['cadence_steps_min']/2),round(r['vertical_oscillation_mm']*10),round(r['ground_contact_ms']*10),round(r['step_length_m']*10000)])
    fit.msg(1,[t1,0,4]); dist=round(s['model_distance_m']*100); ms=s['duration_s']*1000; avg=round(s['model_distance_m']/s['duration_s']*1000); maxspeed=round(max(r['speed_m_s'] for r in rows)*1000); hr=round(s['avg_hr_bpm']); maxhr=max(r['heart_rate_bpm'] for r in rows); cad=round(s['avg_cadence_steps_min']/2); maxcad=round(max(r['cadence_steps_min'] for r in rows)/2); cycles=round(s['steps']/2)
    # One lap summary for the complete simulated session, not one message per track revolution.
    fit.define(3,19,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(7,U),f(8,U),f(9,U),f(10,U),f(13,H),f(14,H),f(15,B),f(16,B),f(17,B),f(18,B),f(25,E)])
    fit.msg(3,[0,t1,9,1,t0,ms,ms,dist,cycles,avg,maxspeed,hr,maxhr,cad,maxcad,1])
    fit.define(4,18,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(5,E),f(6,E),f(7,U),f(8,U),f(9,U),f(10,U),f(14,H),f(15,H),f(16,B),f(17,B),f(18,B),f(19,B),f(25,H),f(26,H),string(110)])
    fit.msg(4,[0,t1,8,1,t0,1,0,ms,ms,dist,cycles,avg,maxspeed,hr,maxhr,cad,maxcad,0,1,LABEL])
    fit.define(5,34,[f(253,U),f(0,U),f(1,H),f(2,E),f(3,E),f(4,E)])
    fit.msg(5,[t1,ms,1,0,26,1]); return fit.finish()

def validate_fit(b,n):
    require(len(b)>=16 and b[0]==14 and b[8:12]==b'.FIT','FIT header')
    size=struct.unpack_from('<I',b,4)[0]; end=14+size; require(end+2==len(b),'FIT length')
    require(crc(b[:12])==struct.unpack_from('<H',b,12)[0] and crc(b[:-2])==struct.unpack_from('<H',b,end)[0],'FIT CRC')
    defs={}; counts=Counter(); ts=[]; i=14
    while i<end:
        h=b[i]; i+=1; local=h&15; require(not h&0x80,'unexpected compressed header')
        if h&0x40:
            require(i+5<=end,'FIT truncated definition'); _,arch,g,nf=struct.unpack_from('<BBHB',b,i); i+=5
            require(arch==0 and i+3*nf<=end,'FIT definition')
            fs=[tuple(b[j:j+3]) for j in range(i,i+3*nf,3)]; i+=3*nf; defs[local]=(g,fs)
        else:
            require(local in defs,'FIT undefined message'); g,fs=defs[local]; counts[g]+=1
            for num,sz,typ in fs:
                require(i+sz<=end,'FIT truncated data')
                if g==20 and num==253: ts.append(struct.unpack_from('<I',b,i)[0])
                i+=sz
    require(i==end and all(counts[g]==1 for g in (0,18,19,34)) and counts[20]==n,'FIT required messages')
    require(all(x<y for x,y in zip(ts,ts[1:])) and LABEL.encode() in b,'FIT timestamp or synthetic label')

TCX='http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
ET.register_namespace('',TCX)
def tcx(rows,s):
    def add(p,n,v=None,**attrs):
        e=ET.SubElement(p,'{'+TCX+'}'+n,attrs)
        if v is not None: e.text=str(v)
        return e
    root=ET.Element('{'+TCX+'}TrainingCenterDatabase'); a=add(add(root,'Activities'),'Activity',Sport='Running'); add(a,'Id',s['start_utc']); lap=add(a,'Lap',StartTime=s['start_utc'])
    add(lap,'TotalTimeSeconds',s['duration_s']); add(lap,'DistanceMeters',round(s['model_distance_m'],3)); add(lap,'Calories',0); add(lap,'Intensity','Active'); add(lap,'TriggerMethod','Manual'); track=add(lap,'Track')
    for r in rows:
        p=add(track,'Trackpoint'); add(p,'Time',r['timestamp_utc']); add(p,'DistanceMeters',round(r['model_distance_m'],3)); add(add(p,'HeartRateBpm'),'Value',r['heart_rate_bpm']); add(p,'Cadence',round(r['cadence_steps_min']/2))
    add(lap,'Notes',LABEL+' - simulated data; calories not modeled'); add(a,'Notes',LABEL+' - not measured activity')
    b=ET.tostring(root,encoding='utf-8',xml_declaration=True); require(len(ET.fromstring(b).findall('.//{'+TCX+'}Trackpoint'))==len(rows),'TCX trackpoint count'); return b


def fixture(out):
    require(not out.exists() or (out.is_dir() and not any(out.iterdir())), 'output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    start=dt.datetime(2030,1,1,tzinfo=dt.timezone.utc)
    rows=[dict(timestamp_utc=(start+dt.timedelta(seconds=t)).isoformat(),model_distance_m=t*5/3,speed_m_s=5/3,heart_rate_bpm=100,cadence_steps_min=160,step_length_m=.625,ground_contact_ms=250,vertical_oscillation_mm=80) for t in range(31)]
    summary=dict(start_utc=start.isoformat(),duration_s=30,model_distance_m=50,avg_hr_bpm=100,avg_cadence_steps_min=160,steps=80)
    b=make_fit(rows,summary,1); validate_fit(b,len(rows)); (out/'SYNTHETIC_FORMAT_FIXTURE.fit').write_bytes(b)
    (out/'SYNTHETIC_FORMAT_FIXTURE.tcx').write_bytes(tcx(rows,summary))
    (out/'用途声明.txt').write_text(NOTICE,encoding='utf-8')
    (out/'README.txt').write_text('Fixed 50m / 30s non-geographic synthetic format fixture, not a research session. Internal binary/XML checks only. Not verified against an external client or official SDK.',encoding='utf-8')
    pack(out/'SYNTHETIC_FORMAT_FIXTURES.zip',sorted(out.iterdir()),out)
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); fixture(p.parse_args().output)
