/* StrideLab v0.0. Local-coordinate synthetic research only. */
(function(root){'use strict';
const VERSION='0.1.0', DECLARATION='本文件包为程序生成的合成研究数据，非实际运动或人体传感器实测记录。仅用于学习交流、教学演示、统计分析及授权测试，不可用于真实评测。模型未经人体或设备实测校准。地理坐标由地图参考位置和数学模型合成，非设备定位实测；局部坐标不等于经纬度。使用者对实际使用行为承担相应责任。';
function rng(seed){let a=seed>>>0;return ()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return ((t^t>>>14)>>>0)/4294967296;};}
function normal(r){return Math.sqrt(-2*Math.log(Math.max(r(),1e-12)))*Math.cos(2*Math.PI*r());}
function standardTrack(){let p=[],r=36.5,l=(400-2*Math.PI*r)/2;for(let i=0;i<=12;i++){let a=Math.PI+i*Math.PI/12;p.push([r*Math.cos(a),-l/2+r*Math.sin(a)]);}for(let i=0;i<=12;i++){let a=i*Math.PI/12;p.push([r*Math.cos(a),l/2+r*Math.sin(a)]);}return p;}
// Shape-only normalization. The local template retains no geographic anchor.
function referenceTrackShape(marks){
 if(!Array.isArray(marks)||marks.length<3||marks.length>120||!marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=85&&Math.abs(p[1])<=180))throw Error('请沿场地周边选择至少3个有效参考点，推荐4–8个');
 const lat=marks.reduce((a,p)=>a+p[0],0)/marks.length,lon=marks[0][1],rad=Math.PI/180,scale=6371008.8*rad;
 const xy=marks.map(p=>[(((p[1]-lon+540)%360)-180)*Math.cos(lat*rad)*scale,(p[0]-lat)*scale]);
 const mean=[xy.reduce((a,p)=>a+p[0],0)/xy.length,xy.reduce((a,p)=>a+p[1],0)/xy.length];
 let xx=0,yy=0,xycov=0;
 for(const p of xy){const x=p[0]-mean[0],y=p[1]-mean[1];xx+=x*x;yy+=y*y;xycov+=x*y;}
 const theta=.5*Math.atan2(2*xycov,xx-yy),cs=Math.cos(theta),sn=Math.sin(theta);
 const axes=xy.map(p=>[(p[0]-mean[0])*cs+(p[1]-mean[1])*sn,-(p[0]-mean[0])*sn+(p[1]-mean[1])*cs]);
 const span=i=>Math.max(...axes.map(p=>p[i]))-Math.min(...axes.map(p=>p[i]));
 const major=Math.max(span(0),span(1)),minor=Math.min(span(0),span(1));
 if(major<5||major>1000||minor<2||minor/major<.15)throw Error('参考点范围不足或过大，请在环形场地周边分散标点');
 const ratio=Math.max(.35,Math.min(.98,minor/major));
 const radius=100*ratio,halfStraight=100*(1-ratio),raw=[];
 for(let i=0;i<=24;i++){const a=Math.PI+i*Math.PI/24;raw.push([radius*Math.cos(a),-halfStraight+radius*Math.sin(a)]);}
 for(let i=0;i<=24;i++){const a=i*Math.PI/24;raw.push([radius*Math.cos(a),halfStraight+radius*Math.sin(a)]);}
 const factor=400/geometry(raw,true).len;
 const points=raw.map(p=>p.map(v=>v*factor));
 if(Math.max(...points.map(p=>Math.abs(p[1])))>100)for(const p of points){const x=p[0];p[0]=p[1];p[1]=-x;}
 return {points,closed:true,nominal_m:400,shape_ratio:ratio,source:'normalized_reference_shape'};
}
// Resample ordered LOCAL research geometry, preserving every original vertex.
function interpolateLocalRoute(marks,closed=true,count=100,mode='linear',smoothness=.5,referencePreview=false){
 if(!Array.isArray(marks)||marks.length>120||marks.length<(closed?3:2)||!marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)))throw Error('参考节点无效');
 const limit=referencePreview?1000:120;if(!Number.isInteger(count)||count<marks.length||count>limit)throw Error('节点总数须在原始点数与'+limit+'之间');
 if(!['linear','smooth'].includes(mode)||!Number.isFinite(smoothness)||smoothness<0||smoothness>1)throw Error('插值参数无效');
 const g=geometry(marks,closed),n=g.seg.length;
 const extra=count-marks.length,parts=g.seg.map(s=>1+Math.floor(extra*s.d/g.len));
 const fractions=g.seg.map((s,i)=>({i,rest:extra*s.d/g.len-Math.floor(extra*s.d/g.len)})).sort((a,b)=>b.rest-a.rest);
 let left=count-(closed?0:1)-parts.reduce((a,b)=>a+b,0);
 for(let i=0;i<left;i++)parts[fractions[i].i]++;
 const at=i=>marks[closed?(i+marks.length)%marks.length:Math.max(0,Math.min(marks.length-1,i))];
 const out=[];
 for(let i=0;i<n;i++){
   const a=at(i),b=at(i+1),prev=at(i-1),next=at(i+2);
   const d=g.seg[i].d;
   const tangent=(u,v)=>{const x=v[0]-u[0],y=v[1]-u[1],len=Math.hypot(x,y);return len?[x/len*d*smoothness,y/len*d*smoothness]:[0,0];};
   const m0=tangent(prev,b),m1=tangent(a,next);
   for(let j=0;j<parts[i];j++){
     const t=j/parts[i];
     out.push(a.map((v,k)=>{const linear=v+(b[k]-v)*t;if(mode==='linear'||!smoothness||j===0)return linear;
       const t2=t*t,t3=t2*t;
       return (2*t3-3*t2+1)*v+(t3-2*t2+t)*m0[k]+(-2*t3+3*t2)*b[k]+(t3-t2)*m1[k];}));
   }
 }
 if(!closed)out.push(marks.at(-1).slice());
 const result=geometry(out,closed);
 if(crossing(out,closed))throw Error('插值后路线自相交，请调整节点或使用直线模式');
 return {points:out,closed,length_m:result.len,mode,source:'local_research'};
}
function referenceLocalRoute(marks,closed,count,mode,smoothness,referencePreview=false){
 if(!Array.isArray(marks)||marks.length>120||marks.length<(closed?3:2)||!marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=85&&Math.abs(p[1])<=180))throw Error('请沿参考路线依次添加有效标点');
 const lat=marks.reduce((a,p)=>a+p[0],0)/marks.length,lon=marks[0][1],rad=Math.PI/180,scale=6371008.8*rad;
 const xy=marks.map(p=>[(((p[1]-lon+540)%360)-180)*Math.cos(lat*rad)*scale,-(p[0]-lat)*scale]);
 const mid=[0,1].map(i=>(Math.min(...xy.map(p=>p[i]))+Math.max(...xy.map(p=>p[i])))/2);
 const local=xy.map(p=>p.map((v,i)=>v-mid[i]));
 return {...interpolateLocalRoute(local,closed,count,mode,smoothness,referencePreview),georeference:{crs:'WGS84',origin_lat:lat-mid[1]/scale,origin_lon:wrapLongitude(lon+mid[0]/(scale*Math.cos(lat*rad))),scale_lat:lat,source:'synthetic_map_reference'}};
}
function previewReferenceRoute(marks,closed,count,mode,smoothness){return {...referenceLocalRoute(marks,closed,count,mode,smoothness,true),preview_only:true,purpose:'reference_geometry_only'};}
function wrapLongitude(lon){return ((lon+180)%360+360)%360-180;}
function validateReference(ref){
 if(!ref||ref.crs!=='WGS84'||ref.source!=='synthetic_map_reference'||!['origin_lat','origin_lon','scale_lat'].every(k=>Number.isFinite(ref[k]))||Math.abs(ref.origin_lat)>85.05113||Math.abs(ref.scale_lat)>85||ref.origin_lon< -180||ref.origin_lon>=180)throw Error('请先在地图中选择并应用有效参考路线');
 return {crs:'WGS84',origin_lat:ref.origin_lat,origin_lon:ref.origin_lon,scale_lat:ref.scale_lat,source:'synthetic_map_reference'};
}
function toGeographic(p,ref){
 const r=validateReference(ref),scale=6371008.8*Math.PI/180;
 if(!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))throw Error('局部位置无效');
 const lat=r.origin_lat-p[1]/scale,lon=wrapLongitude(r.origin_lon+p[0]/(scale*Math.cos(r.scale_lat*Math.PI/180)));
 if(Math.abs(lat)>85.05113||!Number.isFinite(lon))throw Error('超出地理研究模型范围');
 return [lat,lon];
}
function simulateResearch(c,points,closed,index,reference=null){
 const mode=c.positionMode??'none';
 if(!['none','geo'].includes(mode))throw Error('研究位置模式无效');
 const ref=mode==='geo'?validateReference(reference):null;
 validate(c);const resolved=sampleConfig(c,index),s=simulate(resolved,points,closed,index);
 if(c.distanceSpreadM)s.summary.target_distance_m=resolved.distance*1000;
 if(c.paceSpreadSec)s.summary.target_pace_sec_km=resolved.pace*60;
 if(ref){
  s.position_source='synthetic_map_reference';s.summary.position_source=s.position_source;
  for(const row of s.rows){const ideal=toGeographic([row.ideal_x_m,row.ideal_y_m],ref),observed=toGeographic([row.observed_x_m,row.observed_y_m],ref);
   row.ideal_lat_deg=ideal[0];row.ideal_lon_deg=ideal[1];row.latitude_deg=observed[0];row.longitude_deg=observed[1];row.position_source=s.position_source;}
 }
 return s;
}
function geometry(points,closed){if(!Array.isArray(points)||points.length<(closed?3:2))throw Error('参考点数量不足');let seg=[],len=0;for(let i=0;i<points.length-(closed?0:1);i++){let a=points[i],b=points[(i+1)%points.length],d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!Number.isFinite(d)||d<.05)throw Error('节点重合或非法');seg.push({a,b,d,start:len});len+=d;}if(len<5)throw Error('路线过短');return {seg,len,closed};}
function crossing(points,closed){let n=points.length-(closed?0:1),out=0;const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);for(let i=0;i<n;i++)for(let j=i+2;j<n;j++){if(closed&&i===0&&j===n-1)continue;let a=points[i],b=points[(i+1)%points.length],c=points[j],d=points[(j+1)%points.length];if(Math.max(a[0],b[0])<Math.min(c[0],d[0])||Math.max(c[0],d[0])<Math.min(a[0],b[0])||Math.max(a[1],b[1])<Math.min(c[1],d[1])||Math.max(c[1],d[1])<Math.min(a[1],b[1]))continue;if(cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0)out++;}return out;}
function pos(g,s){s=g.closed?((s%g.len)+g.len)%g.len:Math.max(0,Math.min(g.len,s));let v=g.seg.find(q=>s<=q.start+q.d)||g.seg.at(-1),f=(s-v.start)/v.d;return [v.a[0]+f*(v.b[0]-v.a[0]),v.a[1]+f*(v.b[1]-v.a[1])];}
function bounded(v,a,b){return Math.max(a,Math.min(b,v));}
// Local-only parameter sweep for statistical sensitivity experiments.
// Legacy configurations (zero/absent spread) retain their exact results.
function sampleConfig(c,index){
 const spread=c.distanceSpreadM??0,paceSpread=c.paceSpreadSec??0;
 distanceBounds(c);paceBounds(c);
 if(!spread&&!paceSpread)return c;
 if(!Number.isInteger(index)||index<0||index>=c.count)throw Error('样本索引无效');
 const r=rng((c.seed^0x44535452^Math.imul(index+1,0x9e3779b1))>>>0);
 const rp=rng((c.seed^0x50414345^Math.imul(index+1,0x9e3779b1))>>>0);
 const d=c.distance+(2*r()-1)*spread/1000;
 const pace=c.durationMode==='duration'?c.distance*c.pace/d:c.pace+(2*rp()-1)*paceSpread/60;
 return {...c,distance:d,pace,distanceSpreadM:0,paceSpreadSec:0};
}
function distanceBounds(c){
 const spread=c.distanceSpreadM??0;
 if(!Number.isFinite(spread)||spread<0||spread>5000)throw Error('距离浮动须为0–5000米');
 if(spread&&(c.positionMode??'none')!=='none')throw Error('距离区间实验仅用于无GPS局部研究');
 const lo=c.distance-spread/1000,hi=c.distance+spread/1000;
 if(lo<.1||hi>20)throw Error('距离浮动后须在0.1–20公里内');
 if(spread&&c.durationMode==='duration'&&(c.distance*c.pace/hi<3||c.distance*c.pace/lo>15))throw Error('固定时长下距离范围对应配速超限');
 return [lo,hi];
}
function paceBounds(c){
 const spread=c.paceSpreadSec??0;
 if(!Number.isFinite(spread)||spread<0||spread>300)throw Error('配速浮动须为0–300秒/公里');
 if(spread&&(c.positionMode??'none')!=='none')throw Error('配速区间实验仅用于无GPS局部研究');
 if(spread&&c.durationMode==='duration')throw Error('固定时长模式不能独立设置配速浮动');
 const lo=c.pace-spread/60,hi=c.pace+spread/60;
 if(lo<3||hi>15)throw Error('配速浮动后须在3–15分钟/公里内');
 return [lo,hi];
}
function maxSampleSeconds(c){
 const bounds=distanceBounds(c),pb=paceBounds(c);
 return Math.round(c.durationMode==='duration'?c.distance*c.pace*60:bounds[1]*pb[1]*60);
}
function validate(c){for(const [k,min,max] of [['count',1,30],['distance',.1,20],['pace',3,15],['cv',0,20],['noise',0,30],['seed',0,4294967295],['fixedStart',0,100]])if(!Number.isFinite(c[k])||c[k]<min||c[k]>max)throw Error('参数超出范围：'+k);if(c.count*(maxSampleSeconds(c)+1)>60000)throw Error('V0.1 单批最多60000个采样点，请减少样本数或时长');if(!Number.isInteger(c.count)||!Number.isInteger(c.seed))throw Error('次数和种子必须是整数');if(!['forward','reverse','random'].includes(c.direction)||!['none','normal','high'].includes(c.fatigue))throw Error('运动模式无效');}
function simulate(c,points,closed,index){validate(c);let seed=(c.seed+Math.imul(index+1,2654435761))>>>0,r=rng(seed),g=geometry(points,closed),distance=c.distance*1000;if(!closed&&distance>g.len+.01)throw Error('开放路线的目标距离不能超过路线长度');let seconds=Math.max(1,Math.round(c.distance*c.pace*60));if(seconds>18000)throw Error('单次样本时间过长');let v=[],state=0;for(let t=0;t<seconds;t++){let f=t/Math.max(1,seconds-1),fat=c.fatigue==='high'?.16:c.fatigue==='normal'?.07:0;state=.94*state+Math.sqrt(1-.94*.94)*normal(r);let ramp=(c.accel?Math.min(1,(t+1)/10):1)*(c.decel?Math.min(1,(seconds-t)/12):1);v.push(Math.max(.05,(1-fat*f+c.cv/100*bounded(state,-2.5,2.5))*ramp));}let scale=distance/v.reduce((a,b)=>a+b,0),dir=c.direction==='random'?(r()<.5?-1:1):c.direction==='reverse'?-1:1,start=closed?(c.randomStart?r()*g.len:c.fixedStart/100*g.len):(dir===1?0:g.len),s=0,hr=85,steps=0,obsDist=0,prev=null,rows=[],errSq=0;for(let t=0;t<=seconds;t++){let speed=t===0?0:v[t-1]*scale;if(t)s+=speed;let p=pos(g,start+dir*s); // Independent controlled observation perturbation for local-coordinate research.
let e=c.noise===0?[0,0]:[normal(r)*c.noise/Math.SQRT2,normal(r)*c.noise/Math.SQRT2],o=[p[0]+e[0],p[1]+e[1]];errSq+=e[0]**2+e[1]**2;if(prev)obsDist+=Math.hypot(o[0]-prev[0],o[1]-prev[1]);prev=o;let cadence=speed>0?bounded(125+14*speed,110,200):0,step=cadence?speed*60/cadence:0;if(t){steps+=cadence/60;hr+=(bounded(80+26*speed,80,185)-hr)*.035;}rows.push({t,ideal_x_m:p[0],ideal_y_m:p[1],observed_x_m:o[0],observed_y_m:o[1],speed_mps:speed,distance_m:s,hr_bpm:hr,cadence_spm:cadence,step_length_m:step,ground_contact_ms:speed>0?bounded(330-23*speed,150,350):null,vertical_oscillation_mm:speed>0?bounded(58+7*speed,45,110):null,synthetic:true});}return {id:`SIM-${index+1}`,seed,rows,summary:{id:`SIM-${index+1}`,synthetic:true,seed,seconds,model_distance_m:s,observed_distance_m:obsDist,pace_sec_km:seconds/(s/1000),steps:Math.round(steps),mean_hr:rows.reduce((a,b)=>a+b.hr_bpm,0)/rows.length,rms_error_m:Math.sqrt(errSq/rows.length),start_m:start,direction:dir,route_length_m:g.len}};}
// Derived research statistics are independent of the generation engine.
function describe(values){
 const v=values.filter(x=>typeof x==='number'&&Number.isFinite(x));
 if(!v.length)return {n:0,mean:null,sd:null,min:null,max:null,p50:null,p95:null};
 const n=v.length,mean=v.reduce((a,x)=>a+x,0)/n,sd=Math.sqrt(v.reduce((a,x)=>a+(x-mean)**2,0)/n),sorted=v.slice().sort((a,b)=>a-b);
 const quantile=p=>{const q=(n-1)*p,i=Math.floor(q);return sorted[i]+(sorted[Math.min(n-1,i+1)]-sorted[i])*(q-i);};
 return {n,mean,sd,min:sorted[0],max:sorted[n-1],p50:quantile(.5),p95:quantile(.95)};
}
function sampleStatistics(session){
 if(!session||!Array.isArray(session.rows)||!session.rows.length)throw Error('样本为空');
 const rows=session.rows,duration=rows.at(-1).t,active=rows.filter(r=>r.t>0),middle=active.filter(r=>r.t>=duration*.2&&r.t<=duration*.8);
 const speed=describe(middle.map(r=>r.speed_mps)),errors=rows.map(r=>Math.hypot(r.observed_x_m-r.ideal_x_m,r.observed_y_m-r.ideal_y_m));
 const result={synthetic:true,sample_id:session.id,steady_speed_cv_pct:speed.mean>0?100*speed.sd/speed.mean:null,step_length_m:describe(active.map(r=>r.step_length_m)),ground_contact_ms:describe(active.map(r=>r.ground_contact_ms)),vertical_oscillation_mm:describe(active.map(r=>r.vertical_oscillation_mm)),observation_error_m:describe(errors),heart_rate_bpm:describe(active.map(r=>r.hr_bpm)),cadence_spm:describe(active.map(r=>r.cadence_spm))};
 return result;
}
// Research integrity helpers; no modification of the generated observations.
function sha256(data){
 const bytes=typeof data==='string'?new TextEncoder().encode(data):data;
 if(!(bytes instanceof Uint8Array))throw Error('校验对象必须是文本或字节数组');
 const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 const H=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
 const padded=new Uint8Array(Math.ceil((bytes.length+9)/64)*64);padded.set(bytes);padded[bytes.length]=128;
 const view=new DataView(padded.buffer),bits=bytes.length*8;view.setUint32(padded.length-8,Math.floor(bits/4294967296));view.setUint32(padded.length-4,bits>>>0);
 const W=new Uint32Array(64),rot=(v,n)=>(v>>>n)|(v<<(32-n));
 for(let off=0;off<padded.length;off+=64){
  for(let i=0;i<16;i++)W[i]=view.getUint32(off+4*i);
  for(let i=16;i<64;i++){const a=W[i-15],b=W[i-2];W[i]=(W[i-16]+(rot(a,7)^rot(a,18)^(a>>>3))+W[i-7]+(rot(b,17)^rot(b,19)^(b>>>10)))>>>0;}
  let [a,b,c,d,e,f,g,h]=H;
  for(let i=0;i<64;i++){const t1=(h+(rot(e,6)^rot(e,11)^rot(e,25))+((e&f)^(~e&g))+K[i]+W[i])>>>0,t2=((rot(a,2)^rot(a,13)^rot(a,22))+((a&b)^(a&c)^(b&c)))>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
  const state=[a,b,c,d,e,f,g,h];for(let i=0;i<8;i++)H[i]=(H[i]+state[i])>>>0;
 }
 return Array.from(H,n=>n.toString(16).padStart(8,'0')).join('');
}
function researchArchive(files,metadata){
 const out={...files},hashes={};
 for(const name of Object.keys(out).sort()){if(name==='manifest.json'||name==='checksums.sha256')throw Error('保留文件名');hashes[name]=sha256(out[name]);}
 out['manifest.json']=JSON.stringify({...metadata,synthetic:true,integrity_algorithm:'SHA-256',file_hashes:hashes},null,2);
 out['checksums.sha256']=Object.keys(out).sort().map(name=>sha256(out[name])+'  '+name).join('\n')+'\n';
 return zip(out);
}
function validateResearchRows(s){
 if(!s||!Array.isArray(s.rows)||s.rows.length<2||s.rows[0].t!==0)throw Error('样本时间轴不完整');
 const rows=s.rows,issues=[],add=x=>{if(!issues.includes(x))issues.push(x);};
 let integrated=0,maxStepResidual=0;
 for(let i=0;i<rows.length;i++){
  const r=rows[i];if(r.synthetic!==true)add('来源标记缺失');
  if(!['t','distance_m','speed_mps','hr_bpm','cadence_spm','step_length_m'].every(k=>Number.isFinite(r[k])))add('非有限数值');
  if(r.speed_mps<0||r.cadence_spm<0||r.step_length_m<0)add('负运动量');
  if(i){const dt=r.t-rows[i-1].t;if(!(dt>0)||r.distance_m<rows[i-1].distance_m)add('时间或距离不单调');integrated+=r.speed_mps*dt;}
  maxStepResidual=Math.max(maxStepResidual,Math.abs(r.speed_mps-r.cadence_spm*r.step_length_m/60));
 }
 const total=rows.at(-1).distance_m,residual=Math.abs(integrated-total);
 if(!Number.isFinite(residual)||residual>Math.max(.01,total*.005))add('距离积分不一致');
 if(!Number.isFinite(maxStepResidual)||maxStepResidual>1e-6)add('步幅关系不一致');
 if(!Number.isFinite(s.summary?.model_distance_m)||Math.abs(total-s.summary.model_distance_m)>.01||s.summary.seconds!==rows.at(-1).t)add('摘要与逐点数据不一致');
 return {synthetic:true,passed:issues.length===0,issues,row_count:rows.length,integrated_distance_m:integrated,distance_residual_m:residual,max_step_relation_residual_mps:maxStepResidual};
}
function analysisRows(session,interval=1){
 if(![1,2,5,10,15,30].includes(interval))throw Error('分析采样间隔无效');
 if(!session||session.position_source||!session.rows?.length||session.rows.some(r=>'latitude_deg' in r||'longitude_deg' in r))throw Error('仅限无GPS局部研究分析');
 return session.rows.filter((r,i)=>i===0||i===session.rows.length-1||r.t%interval===0).map(r=>({...r,analysis_view:true}));
}
function compareResearchGroups(groups){
 if(!Array.isArray(groups)||groups.length<2||groups.length>5)throw Error('请选择2–5个独立实验组');
 return groups.map(g=>{
  if(!g||!Array.isArray(g.sessions)||!g.sessions.length||g.sessions.some(s=>s.position_source||s.rows.some(r=>'latitude_deg' in r)))throw Error('仅支持无GPS局部实验组');
  const stats=g.sessions.map(sampleStatistics);
  return {id:String(g.id),label:String(g.label),synthetic:true,n:g.sessions.length,distance_m:describe(g.sessions.map(s=>s.summary.model_distance_m)),pace_sec_km:describe(g.sessions.map(s=>s.summary.pace_sec_km)),mean_hr_bpm:describe(g.sessions.map(s=>s.summary.mean_hr)),steady_speed_cv_pct:describe(stats.map(x=>x.steady_speed_cv_pct)),rms_error_m:describe(g.sessions.map(s=>s.summary.rms_error_m)),valid_count:g.sessions.filter(s=>validateResearchRows(s).passed).length};
 });
}
// Independent local research groups. No geographic reference or absolute activity time.
const STUDY_PROFILES=Object.freeze({baseline:{label:'基准模型',hrOffset:0,cadenceOffset:0},lower:{label:'低响应敏感性',hrOffset:-8,cadenceOffset:-6},higher:{label:'高响应敏感性',hrOffset:8,cadenceOffset:6}});
function prepareLocalStudy(plan){
 if(!plan||!Number.isInteger(plan.seed)||plan.seed<0||plan.seed>4294967295||!Array.isArray(plan.groups)||plan.groups.length<1||plan.groups.length>5||![1,2,5,10,15,30].includes(plan.interval))throw Error('局部实验计划参数无效');
 let total=0;
 const groups=plan.groups.map((g,i)=>{
  if(!g||!Object.hasOwn(STUDY_PROFILES,g.profile))throw Error('实验组模型档案无效');
  const cfg={count:g.count,distance:g.distance,pace:g.pace,cv:g.cv,noise:g.noise,seed:(plan.seed+Math.imul(i,0x9e3779b1))>>>0,fixedStart:0,randomStart:false,direction:'forward',fatigue:'normal',accel:true,decel:true,positionMode:'none'};
  validate(cfg);total+=cfg.count*(maxSampleSeconds(cfg)+1);
  return {id:'GROUP-'+(i+1),profile:g.profile,config:cfg};
 });
 if(total>60000)throw Error('多组合计最多60000个原始采样点');
 return {synthetic:true,research_only:true,seed:plan.seed,interval:plan.interval,total_points_upper_bound:total,groups};
}
function localStudySample(group,index){
 if(!group||group.config?.positionMode!=='none'||!Object.hasOwn(STUDY_PROFILES,group.profile)||!Number.isInteger(index)||index<0||index>=group.config.count)throw Error('无效的局部实验任务');
 const s=simulateResearch(group.config,standardTrack(),true,index),p=STUDY_PROFILES[group.profile];
 if(group.profile!=='baseline'){
  let steps=0;
  for(const [i,r] of s.rows.entries()){
   r.hr_bpm=bounded(r.hr_bpm+p.hrOffset,0,220);
   if(i&&r.speed_mps>0){r.cadence_spm=bounded(r.cadence_spm+p.cadenceOffset,1,220);r.step_length_m=r.speed_mps*60/r.cadence_spm;steps+=r.cadence_spm*(r.t-s.rows[i-1].t)/60;}
  }
  s.summary.steps=Math.round(steps);s.summary.mean_hr=s.rows.reduce((sum,r)=>sum+r.hr_bpm,0)/s.rows.length;
 }
 s.study_group=group.id;s.profile=group.profile;s.research_only=true;
 return s;
}
function csv(rows){if(!rows.length)return '';let keys=Object.keys(rows[0]);return keys.join(',')+'\n'+rows.map(r=>keys.map(k=>typeof r[k]==='number'?String(Math.round(r[k]*1e6)/1e6):r[k]??'').join(',')).join('\n')+'\n';}
const table=Array.from({length:256},(_,i)=>{for(let j=0;j<8;j++)i=(i&1)?0xedb88320^(i>>>1):i>>>1;return i>>>0;});function crc32(bytes){let c=0xffffffff;for(let b of bytes)c=table[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function zip(files){let enc=new TextEncoder(),chunks=[],central=[],offset=0,clen=0;const make=n=>new Uint8Array(n),w=(a,p,n,v)=>{let d=new DataView(a.buffer);n===2?d.setUint16(p,v,true):d.setUint32(p,v,true);};for(let [name,value] of Object.entries(files)){let n=enc.encode(name),b=typeof value==='string'?enc.encode(value):value,crc=crc32(b),h=make(30+n.length);w(h,0,4,0x04034b50);w(h,4,2,20);w(h,6,2,2048);w(h,12,2,33);w(h,14,4,crc);w(h,18,4,b.length);w(h,22,4,b.length);w(h,26,2,n.length);h.set(n,30);chunks.push(h,b);let ch=make(46+n.length);w(ch,0,4,0x02014b50);w(ch,4,2,20);w(ch,6,2,20);w(ch,8,2,2048);w(ch,14,2,33);w(ch,16,4,crc);w(ch,20,4,b.length);w(ch,24,4,b.length);w(ch,28,2,n.length);w(ch,42,4,offset);ch.set(n,46);central.push(ch);clen+=ch.length;offset+=h.length+b.length;}let end=make(22);w(end,0,4,0x06054b50);w(end,8,2,central.length);w(end,10,2,central.length);w(end,12,4,clen);w(end,16,4,offset);let out=make(offset+clen+22),p=0;for(let b of [...chunks,...central,end]){out.set(b,p);p+=b.length;}return out;}
const api={VERSION,DECLARATION,standardTrack,referenceTrackShape,interpolateLocalRoute,referenceLocalRoute,previewReferenceRoute,validateReference,toGeographic,simulateResearch,sampleConfig,distanceBounds,paceBounds,maxSampleSeconds,geometry,crossing,simulate,validate,describe,sampleStatistics,sha256,researchArchive,validateResearchRows,analysisRows,compareResearchGroups,STUDY_PROFILES,prepareLocalStudy,localStudySample,csv,zip};if(typeof module!=='undefined')module.exports=api;else root.StrideCore=api;
})(globalThis);
