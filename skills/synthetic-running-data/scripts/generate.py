#!/usr/bin/env python3
"""StrideLab synthetic research generator, local metric coordinates, Python 3.10+."""
import argparse, bisect, csv, datetime as dt, hashlib, json, math, random, secrets, statistics, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='2.0.0'; LABEL='SYNTHETIC_RESEARCH'; EARTH=6371008.8
NOTICE=(ROOT/'用途声明.txt').read_text(encoding='utf-8')
DEFAULTS=dict(groups=1,runs_per_group=5,count_range=None,distance_m=2000,pace_min_km=6.0,duration_s=None,start_date='2030-01-01',day_gap=[1,3],time_window=['08:00','18:00'],utc_offset_hours=8,sample_seconds=1,track_length_m=400,route_nodes=None,boundary_points=None,coordinate_system=None,closed=True,random_start=True,fixed_start_m=0,direction='forward',speed_cv_pct=5,gps_noise_m=1.5,noise_correlation_s=6,fatigue='normal',start_acceleration=True,end_deceleration=True,scenario='steady',profile_mode='shared',resting_hr_bpm=65,max_hr_bpm=190,cadence_spm=165,profiles=None,metrics=['heart_rate','steps','cadence','step_length','ground_contact','vertical_oscillation'],seed=None,formats=['csv','json'])
def require(ok,msg):
    if not ok: raise ValueError(msg)
def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def bound(v,name,lo,hi,integer=False):
    a,b=(v,v) if finite(v) else v
    require(finite(a) and finite(b) and lo<=a<=b<=hi,f'{name}: invalid range')
    if integer: require(type(a)==type(b)==int,f'{name}: integers required')
    return [a,b]
def clamp(x,a,b): return max(a,min(b,x))
def minute(s):
    x=dt.time.fromisoformat(s); require(x.second==x.microsecond==0 and x.tzinfo is None,'time HH:MM only'); return x.hour*60+x.minute
def seed_for(seed,*parts): return int.from_bytes(hashlib.sha256(json.dumps([seed,*parts]).encode()).digest()[:8],'big')
def configure(raw):
    require(not(set(raw)-set(DEFAULTS)),f'unknown keys: {set(raw)-set(DEFAULTS)}')
    c={**DEFAULTS,**{k:v for k,v in raw.items() if v is not None}}; auto=[k for k in DEFAULTS if raw.get(k) is None]
    if c['seed'] is None: c['seed']=secrets.randbits(63)
    require(type(c['seed'])==int,'seed integer')
    require(type(c['groups'])==int and 1<=c['groups']<=30,'groups 1..30')
    if c['count_range'] is not None:
        require('runs_per_group' not in raw or raw['runs_per_group'] is None,'choose count_range OR runs_per_group')
        c['count_range']=bound(c['count_range'],'count_range',1,200,True)
        counts=[random.Random(seed_for(c['seed'],'count',i)).randint(*c['count_range']) for i in range(c['groups'])]
    else: counts=[c['runs_per_group']]*c['groups'] if type(c['runs_per_group'])==int else c['runs_per_group']
    require(len(counts)==c['groups'] and all(type(n)==int and 1<=n<=200 for n in counts) and sum(counts)<=500,'invalid counts; total cap 500')
    c['runs_per_group']=counts
    for k,lo,hi in [('distance_m',50,50000),('pace_min_km',2,30),('day_gap',1,365)]: c[k]=bound(c[k],k,lo,hi,k=='day_gap')
    if c['duration_s'] is not None:
        require('pace_min_km' not in raw or raw['pace_min_km'] is None,'set distance + duration OR distance + pace')
        c['duration_s']=bound(c['duration_s'],'duration_s',10,72000,True)
        require(2<=c['duration_s'][0]/c['distance_m'][1]*1000/60 and c['duration_s'][1]/c['distance_m'][0]*1000/60<=30,'duration implies unsupported pace')
    for k,lo,hi in [('track_length_m',100,2000),('speed_cv_pct',0,20),('gps_noise_m',0,30),('noise_correlation_s',.1,120),('utc_offset_hours',-12,14),('fixed_start_m',0,100000)]: require(finite(c[k]) and lo<=c[k]<=hi,f'{k}: range {lo}..{hi}')
    require(type(c['sample_seconds'])==int and 1<=c['sample_seconds']<=30,'sample_seconds 1..30')
    for k in ['closed','random_start','start_acceleration','end_deceleration']: require(type(c[k])==bool,k+' must be boolean')
    for k,opts in [('direction',['forward','reverse','random']),('fatigue',['none','normal','high']),('scenario',['steady','progressive_slowdown','interval']),('profile_mode',['shared','per_group'])]: require(c[k] in opts,k+' invalid')
    require(len(c['time_window'])==2 and minute(c['time_window'][0])<=minute(c['time_window'][1]),'time_window must not cross midnight')
    dt.date.fromisoformat(c['start_date']); require(c['formats'] and set(c['formats'])<={'csv','json'},'research formats csv/json; separate fixture command for FIT/TCX')
    require(set(c['metrics'])<=set(DEFAULTS['metrics']),'unknown metric')
    require(not(c['route_nodes'] and c['boundary_points']),'choose ordered nodes OR four references')
    return c,auto

def dist(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def intersect(a,b,c,d):
    eps=1e-8
    def on(a,b,p): return abs(cross(a,b,p))<=eps and all(min(a[i],b[i])-eps<=p[i]<=max(a[i],b[i])+eps for i in (0,1))
    return (cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0) or any((on(a,b,c),on(a,b,d),on(c,d,a),on(c,d,b)))
class Route:
    def __init__(self,c):
        self.closed=c['closed']; self.warnings=[]; self.reference=None; self.nominal=c['track_length_m']; p=c['route_nodes']; b=c['boundary_points']; crs=str(c['coordinate_system']).upper().replace('-','').replace('_','')
        if b is not None:
            require(set(b)=={'north','south','west','east'},'four point input incomplete; use default or complete points')
            p=[b[k] for k in ['north','east','south','west']]; require(self.closed,'four points require closed route')
        if p is not None:
            require(crs in ['WGS84','LOCALM'],'coordinate_system must be WGS84 or LOCAL_M (no silent conversion)')
            require(isinstance(p,list) and (3 if self.closed else 2)<=len(p)<=1000,'node count 2/3..1000')
            require(all(len(q)==2 and all(finite(v) for v in q) for q in p),'invalid node')
            if crs=='WGS84':
                require(all(-85<=a<=85 and -180<=b<=180 for a,b in p),'coordinate out of range'); require(max(q[1] for q in p)-min(q[1] for q in p)<1 and max(q[0] for q in p)-min(q[0] for q in p)<1,'reference extent too large; antimeridian unsupported')
                a=sum(q[0] for q in p)/len(p); b0=sum(q[1] for q in p)/len(p); ky=EARTH*math.pi/180; kx=ky*math.cos(math.radians(a)); xy=[((q[1]-b0)*kx,(q[0]-a)*ky) for q in p]
                coords=[[q[1],q[0]] for q in p]; self.reference={'type':'Feature','properties':{'source':'USER_REFERENCE_NOT_ACTIVITY','crs':'WGS84','geometry_mode':'ordered_reference_nodes','nominal_length_m':self.nominal},'geometry':{'type':'LineString','coordinates':coords+([coords[0]] if self.closed and coords[-1]!=coords[0] else [])}}
                self.warnings.append('Geographic reference stored separately; simulation uses local metric geometry, not georeferenced activity.')
            else: xy=[tuple(q) for q in p]
            self.mode='ordered_polyline'
            if c['boundary_points'] is not None: self.warnings.append('Four-point reference is a coarse polyline, not a measured running lane; use more ordered nodes for curvature.')
        elif self.closed:
            r=self.nominal*36.5/400; straight=(self.nominal-2*math.pi*r)/2
            xy=[(r,-straight/2),(r,straight/2)]+[(r*math.cos(math.pi*i/360),straight/2+r*math.sin(math.pi*i/360)) for i in range(1,361)]+[(-r,-straight/2)]+[(r*math.cos(math.pi+math.pi*i/360),-straight/2+r*math.sin(math.pi+math.pi*i/360)) for i in range(1,360)]
            self.mode='virtual_stadium'
        else: xy=[(0,0),(c['distance_m'][1],0)]; self.mode='virtual_open'
        if self.closed and dist(xy[0],xy[-1])<1e-7: xy=xy[:-1]
        require(len(xy)>=(3 if self.closed else 2),'not enough nodes'); self.nodes=xy; self.path=xy+([xy[0]] if self.closed else [])
        self.cum=[0.]; self.crossings=[]
        for a,b in zip(self.path,self.path[1:]):
            d=dist(a,b); require(d>1e-6,'duplicate consecutive nodes'); self.cum.append(self.cum[-1]+d)
        self.length=self.cum[-1]; require(1<=self.length<=100000,'route length unsupported')
        if self.closed: require(abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(self.path,self.path[1:])))>1e-6 or any(abs(cross(xy[0],xy[1],q))>1e-6 for q in xy[2:]),'collinear loop')
        if self.mode=='ordered_polyline':
            for i in range(len(self.path)-1):
                for j in range(i+2,len(self.path)-1):
                    if self.closed and i==0 and j==len(self.path)-2: continue
                    if intersect(*self.path[i:i+2],*self.path[j:j+2]): self.crossings.append([i+1,j+1])
        if self.crossings: self.warnings.append('Reference segments intersect; inspect route before interpretation.')
        if self.closed and abs(self.length-self.nominal)>1: self.warnings.append('Nominal perimeter differs from geometry; no silent rescaling.')
        if not self.closed:
            require(c['distance_m'][1]<=self.length+1e-6,'open route too short for target distance')
            require(not c['random_start'] and c['fixed_start_m']==0,'open route requires fixed endpoint (random_start=false, fixed_start_m=0)')
        if self.closed and not c['random_start']: require(c['fixed_start_m']<self.length,'fixed start outside route')
    def xy(self,s):
        s=s%self.length if self.closed else clamp(s,0,self.length); i=min(len(self.cum)-2,bisect.bisect_right(self.cum,s)-1); f=(s-self.cum[i])/(self.cum[i+1]-self.cum[i]); a,b=self.path[i:i+2]; return tuple(a[k]+(b[k]-a[k])*f for k in (0,1))
    def info(self): return dict(mode=self.mode,closed=self.closed,nodes_local_m=self.nodes,reference_length_m=self.length,nominal_length_m=self.nominal,crossings=self.crossings,warnings=self.warnings)

def profile(c,g):
    default={k:c[k] for k in ['resting_hr_bpm','max_hr_bpm','cadence_spm']}; p=c['profiles']
    if p is not None:
        require(len(p)==(1 if c['profile_mode']=='shared' else c['groups']),'profile count mismatch'); custom=p[0 if c['profile_mode']=='shared' else g-1]; require(not(set(custom)-set(default)),'unknown profile field'); default.update(custom)
    elif c['profile_mode']=='per_group':
        rng=random.Random(seed_for(c['seed'],'profile',g)); default['resting_hr_bpm']+=rng.randint(-5,5); default['max_hr_bpm']+=rng.randint(-5,5); default['cadence_spm']+=rng.randint(-6,6)
    require(all(finite(v) for v in default.values()) and 30<=default['resting_hr_bpm']<default['max_hr_bpm']<=230 and 90<=default['cadence_spm']<=220,'invalid profile'); return default

def simulate(c,route,g,j,start,revision=0):
    sid=f'group_{g:02d}_run_{j:03d}'; seed=seed_for(c['seed'],'run',g,j,revision); r=random.Random(seed); sensor=random.Random(seed_for(seed,'sensor')); phys=random.Random(seed_for(seed,'physiology')); p=profile(c,g)
    target=r.uniform(*c['distance_m']); duration=round(r.uniform(*c['duration_s'])) if c['duration_s'] else round(target/1000*r.uniform(*c['pace_min_km'])*60); duration=max(duration,1)
    ts=list(range(0,duration,c['sample_seconds']))+[duration]; require(len(ts)<=80000,'too many samples per run')
    direction=r.choice([-1,1]) if c['direction']=='random' else (1 if c['direction']=='forward' else -1)
    phase=(r.uniform(0,route.length) if c['random_start'] else c['fixed_start_m']) if route.closed else (0 if direction==1 else route.length)
    # Continuous bounded low-frequency speed variation, normalized to target integral.
    mid=[(a+b)/2 for a,b in zip(ts,ts[1:])]; wave=[]; state=0
    for a,b in zip(ts,ts[1:]):
        alpha=math.exp(-(b-a)/18); state=alpha*state+r.gauss(0,math.sqrt(1-alpha*alpha)); wave.append(state)
    stable=[i for i,t in enumerate(mid) if 0.2*duration<=t<=0.8*duration] or list(range(len(mid)))
    vals=[wave[i] for i in stable]; avg=statistics.mean(vals); sd=statistics.pstdev(vals) or 1
    raw=[]; fatigue={'none':0,'normal':.05,'high':.12}[c['fatigue']]
    if c['scenario']=='progressive_slowdown': fatigue=max(fatigue,.15)
    rampin=min(20,duration*.15); rampout=min(15,duration*.15)
    for i,t in enumerate(mid):
        u=t/duration; x=1-fatigue*u+c['speed_cv_pct']/100*clamp((wave[i]-avg)/sd,-2.5,2.5)
        if c['scenario']=='interval': x+=.15*math.sin(2*math.pi*t/120)
        if c['start_acceleration']: x*=.45+.55*min(1,t/rampin)
        if c['end_deceleration']: x*=.45+.55*min(1,(duration-t)/rampout)
        raw.append(max(.15,x))
    # Bound acceleration changes in relative speed then normalize; report actual CV and acceleration.
    for i in range(1,len(raw)): raw[i]=clamp(raw[i],raw[i-1]-.12*(mid[i]-mid[i-1]),raw[i-1]+.12*(mid[i]-mid[i-1]))
    factor=target/sum(v*(b-a) for v,a,b in zip(raw,ts,ts[1:])); speeds=[raw[0]*factor]+[v*factor for v in raw]
    model=obs=steps=0.; ex=ey=0.; last=None; rows=[]; hr=p['resting_hr_bpm']+10; prev=0; base=target/duration
    for i,(t,v) in enumerate(zip(ts,speeds)):
        delta=t-prev; prev=t; model+=v*delta; x,y=route.xy(phase+direction*model)
        a=math.exp(-delta/c['noise_correlation_s']); noise=c['gps_noise_m']/math.sqrt(2)
        if i==0: ex,ey=sensor.gauss(0,noise),sensor.gauss(0,noise)
        else: ex=a*ex+sensor.gauss(0,noise*math.sqrt(1-a*a)); ey=a*ey+sensor.gauss(0,noise*math.sqrt(1-a*a))
        q=(x+ex,y+ey)
        if last is not None: obs+=dist(last,q)
        last=q; cad=clamp(p['cadence_spm']+14*(v-base)+phys.gauss(0,1.0),90,220); step=v*60/cad; steps+=cad*delta/60
        htarget=p['resting_hr_bpm']+(p['max_hr_bpm']-p['resting_hr_bpm'])*clamp(.32+.14*v,.25,.9)+4*t/duration; hr+=(htarget-hr)*(1-math.exp(-delta/42)); hv=round(clamp(hr+phys.gauss(0,.6),p['resting_hr_bpm'],p['max_hr_bpm']))
        row=dict(source=LABEL,run_id=sid,elapsed_s=t,scenario_time=(start+dt.timedelta(seconds=t)).isoformat(),ideal_x_m=x,ideal_y_m=y,observed_x_m=q[0],observed_y_m=q[1],model_distance_m=model,observed_distance_m=obs,speed_m_s=v)
        optional=dict(heart_rate= ('heart_rate_bpm',hv),steps=('steps_cumulative',steps),cadence=('cadence_steps_min',cad),step_length=('step_length_m',step),ground_contact=('ground_contact_ms',clamp(260-22*(v-base)+phys.gauss(0,3),150,360)),vertical_oscillation=('vertical_oscillation_mm',clamp(80+6*(v-base)+phys.gauss(0,2),40,140)))
        row.update(dict(optional[k] for k in c['metrics'])); rows.append(row)
    cv=statistics.pstdev([speeds[i+1] for i in stable])/statistics.mean([speeds[i+1] for i in stable])*100
    rms=math.sqrt(statistics.mean((r['ideal_x_m']-r['observed_x_m'])**2+(r['ideal_y_m']-r['observed_y_m'])**2 for r in rows)); acc=max((abs(b-a)/max(.001,t-s) for a,b,s,t in zip(speeds,speeds[1:],ts,ts[1:])),default=0)
    require(abs(model-target)<1e-6 and all(b>a for a,b in zip(ts,ts[1:])),'integration/timestamps')
    if {'cadence','step_length'}<=set(c['metrics']): require(all(abs(r['speed_m_s']-r['cadence_steps_min']*r['step_length_m']/60)<1e-9 for r in rows),'stride identity')
    warnings=[]
    if abs(obs-target)/target>.05: warnings.append('Observed distance differs from model by >5%; raw observation retained.')
    if abs(cv-c['speed_cv_pct'])>3: warnings.append('Realized stable-stage CV differs from target; trend, sampling and constraints affect CV.')
    if acc>1.0: warnings.append('Acceleration exceeds illustrative 1 m/s² warning threshold; model not physiologically calibrated.')
    s=dict(source=LABEL,run_id=sid,seed=seed,revision=revision,start_local=start.isoformat(),duration_s=duration,model_distance_m=target,observed_distance_m=obs,observed_error_pct=(obs/target-1)*100,pace_min_km=duration/60/(target/1000),route_length_m=route.length,phase_m=phase,direction=direction,points=len(rows),target_cv_pct=c['speed_cv_pct'],realized_cv_pct=cv,target_rms_m=c['gps_noise_m'],realized_rms_m=rms,max_sample_accel_m_s2=acc,steps=round(steps) if 'steps' in c['metrics'] else None,avg_hr_bpm=statistics.mean(r['heart_rate_bpm'] for r in rows) if 'heart_rate' in c['metrics'] else None,warnings='; '.join(warnings),profile=p)
    return rows,s

def write_json(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding='utf-8')
def write_csv(p,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def pack(p,files,base):
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f,f.relative_to(base))
    with zipfile.ZipFile(p) as z: require(z.testzip() is None and '用途声明.txt' in z.namelist(),'archive validation')
def hashes(paths,base): return {str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def preview(path,route,rows):
    # Actual local sample plot, independent of any basemap or third-party app.
    xy=[(r[k],r[l]) for r in rows for k,l in [('ideal_x_m','ideal_y_m'),('observed_x_m','observed_y_m')]]+route.nodes
    xmin=min(p[0] for p in xy); ymin=min(p[1] for p in xy); scale=min(500/max(1,max(p[0] for p in xy)-xmin),360/max(1,max(p[1] for p in xy)-ymin))
    def pts(a): return ' '.join(f'{35+(x-xmin)*scale:.2f},{405-(y-ymin)*scale:.2f}' for x,y in a)
    ref=pts(route.path); ideal=pts([(r['ideal_x_m'],r['ideal_y_m']) for r in rows]); obs=pts([(r['observed_x_m'],r['observed_y_m']) for r in rows]); vmax=max(r['speed_m_s'] for r in rows); tmax=rows[-1]['elapsed_s']; speed=' '.join(f'{590+370*r["elapsed_s"]/tmax:.2f},{405-345*r["speed_m_s"]/max(vmax,.1):.2f}' for r in rows)
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="460" viewBox="0 0 1000 460"><rect width="1000" height="460" fill="#f4f5f0"/><g font-family="sans-serif" fill="#31463b"><text x="20" y="25" font-size="17">SYNTHETIC RESEARCH · Local route / speed</text><text x="20" y="445" font-size="13">Gray: reference · Green: model · Orange: observation (meters)</text><text x="590" y="445" font-size="13">Speed (m/s) · time (s) · peak {vmax:.2f}</text></g><g fill="none" stroke-linejoin="round"><polyline points="{ref}" stroke="#aaa" stroke-width="2"/><polyline points="{ideal}" stroke="#547e64" stroke-width="2"/><polyline points="{obs}" stroke="#b47843" stroke-width="1.1" opacity=".65"/><path d="M590 45V405H960" stroke="#888"/><polyline points="{speed}" stroke="#547e64" stroke-width="2"/></g></svg>',encoding='utf-8')

def generate(raw,out,only=None,revision=0):
    c,auto=configure(raw); route=Route(c); require(not out.exists() or (out.is_dir() and not any(out.iterdir())),'output directory must be empty'); out.mkdir(parents=True,exist_ok=True)
    # Preflight resource ceiling based on worst-case sample count.
    maxdur=c['duration_s'][1] if c['duration_s'] else c['distance_m'][1]/1000*c['pace_min_km'][1]*60
    require((1 if only else sum(c['runs_per_group']))*(maxdur/c['sample_seconds']+2)<=2_000_000,'sample budget exceeded; split experiments or increase sample interval')
    if only: require(any(only==f'group_{g:02d}_run_{j:03d}' for g,n in enumerate(c['runs_per_group'],1) for j in range(1,n+1)),'unknown run ID')
    notice=out/'用途声明.txt'; notice.write_text(NOTICE,encoding='utf-8'); write_json(out/'input_config.json',raw); write_json(out/'replay_config.json',dict(raw,seed=c['seed'])); write_json(out/'route_geometry.json',dict(source=LABEL,**route.info()))
    if route.reference: write_json(out/'route_reference.geojson',route.reference)
    tz=dt.timezone(dt.timedelta(hours=c['utc_offset_hours'])); all_s=[]; archives=[]; seen=set(); day0=dt.date.fromisoformat(c['start_date'])
    for g,n in enumerate(c['runs_per_group'],1):
        group=f'group_{g:02d}'; group_s=[]; day=day0; folder=out/group
        schedule=random.Random(seed_for(c['seed'],'schedule',g));
        for j in range(1,n+1):
            if j>1: day+=dt.timedelta(days=schedule.randint(*c['day_gap']))
            m=schedule.randint(*map(minute,c['time_window'])); start=dt.datetime.combine(day,dt.time(m//60,m%60),tz); sid=f'{group}_run_{j:03d}'
            if only and only!=sid: continue
            folder.mkdir(exist_ok=True); rows,s=simulate(c,route,g,j,start,revision); signature=hashlib.sha256(json.dumps([(r['ideal_x_m'],r['ideal_y_m'],r['speed_m_s'],r['observed_x_m'],r['observed_y_m']) for r in rows]).encode()).hexdigest(); s['duplicate_series']=signature in seen; seen.add(signature)
            group_s.append(s); all_s.append(s); stem=folder/(LABEL+'_'+sid)
            if 'csv' in c['formats']: write_csv(stem.with_suffix('.csv'),rows)
            if 'json' in c['formats']: write_json(stem.with_suffix('.json'),dict(synthetic=True,engine_version=VERSION,summary=s,samples=rows))
            if len(group_s)==1: preview(folder/'preview.svg',route,rows)
        if not group_s: continue
        (folder/'用途声明.txt').write_text(NOTICE,encoding='utf-8'); write_csv(folder/'summary.csv',group_s); write_json(folder/'manifest.json',dict(synthetic=True,engine_version=VERSION,config=c,automatic_fields=auto,records=group_s,hashes=hashes(sorted(folder.iterdir()),folder))); z=out/(group+'.zip'); pack(z,sorted(folder.iterdir()),folder); archives.append(z)
    write_csv(out/'summary.csv',all_s); files=[p for p in out.iterdir() if p.is_file()]; manifest=out/'manifest.json'; write_json(manifest,dict(synthetic=True,engine_version=VERSION,config=c,automatic_fields=auto,records=len(all_s),geometry=route.info(),validation='Local model integral, timestamps, stride identity, duplicate series reported, ZIP CRC; no client import or physiological validation.',hashes=hashes(sorted(files),out)))
    pack(out/'SYNTHETIC_RESEARCH_all_groups.zip',[*files,manifest],out); return all_s
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--config',type=Path); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--only'); ap.add_argument('--revision',type=int,default=0); a=ap.parse_args(); require(a.revision>=0,'revision nonnegative'); require(a.revision==0 or a.only,'revision requires --only'); raw=json.loads(a.config.read_text(encoding='utf-8')) if a.config else {}; result=generate(raw,a.output,a.only,a.revision); print(f'{len(result)} synthetic research sessions: {a.output}')
