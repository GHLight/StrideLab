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
function interpolateLocalRoute(marks,closed=true,count=100,mode='linear',smoothness=.5){
 if(!Array.isArray(marks)||marks.length>120||marks.length<(closed?3:2)||!marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)))throw Error('参考节点无效');
 if(!Number.isInteger(count)||count<marks.length||count>120)throw Error('节点总数须在原始点数与120之间');
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
function referenceLocalRoute(marks,closed,count,mode,smoothness){
 if(!Array.isArray(marks)||marks.length>120||marks.length<(closed?3:2)||!marks.every(p=>Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=85&&Math.abs(p[1])<=180))throw Error('请沿参考路线依次添加有效标点');
 const lat=marks.reduce((a,p)=>a+p[0],0)/marks.length,lon=marks[0][1],rad=Math.PI/180,scale=6371008.8*rad;
 const xy=marks.map(p=>[(((p[1]-lon+540)%360)-180)*Math.cos(lat*rad)*scale,-(p[0]-lat)*scale]);
 const mid=[0,1].map(i=>(Math.min(...xy.map(p=>p[i]))+Math.max(...xy.map(p=>p[i])))/2);
 const local=xy.map(p=>p.map((v,i)=>v-mid[i]));
 return {...interpolateLocalRoute(local,closed,count,mode,smoothness),georeference:{crs:'WGS84',origin_lat:lat-mid[1]/scale,origin_lon:wrapLongitude(lon+mid[0]/(scale*Math.cos(lat*rad))),scale_lat:lat,source:'synthetic_map_reference'}};
}
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
 if(ref){
  s.position_source='synthetic_map_reference';s.summary.position_source=s.position_source;
  for(const row of s.rows){const ideal=toGeographic([row.ideal_x_m,row.ideal_y_m],ref),observed=toGeographic([row.observed_x_m,row.observed_y_m],ref);
   row.ideal_lat_deg=ideal[0];row.ideal_lon_deg=ideal[1];row.latitude_deg=observed[0];row.longitude_deg=observed[1];row.position_source=s.position_source;}
 }
 return s;
}
function geometry(points,closed){if(!Array.isArray(points)||points.length<(closed?3:2))throw Error('参考点数量不足');let seg=[],len=0;for(let i=0;i<points.length-(closed?0:1);i++){let a=points[i],b=points[(i+1)%points.length],d=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!Number.isFinite(d)||d<.05)throw Error('节点重合或非法');seg.push({a,b,d,start:len});len+=d;}if(len<5)throw Error('路线过短');return {seg,len,closed};}
function crossing(points,closed){let n=points.length-(closed?0:1),out=0;const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);for(let i=0;i<n;i++)for(let j=i+2;j<n;j++){if(closed&&i===0&&j===n-1)continue;let a=points[i],b=points[(i+1)%points.length],c=points[j],d=points[(j+1)%points.length];if(cross(a,b,c)*cross(a,b,d)<0&&cross(c,d,a)*cross(c,d,b)<0)out++;}return out;}
function pos(g,s){s=g.closed?((s%g.len)+g.len)%g.len:Math.max(0,Math.min(g.len,s));let v=g.seg.find(q=>s<=q.start+q.d)||g.seg.at(-1),f=(s-v.start)/v.d;return [v.a[0]+f*(v.b[0]-v.a[0]),v.a[1]+f*(v.b[1]-v.a[1])];}
function bounded(v,a,b){return Math.max(a,Math.min(b,v));}
// Local-only parameter sweep for statistical sensitivity experiments.
// Legacy configurations (zero/absent spread) retain their exact results.
function sampleConfig(c,index){
 const spread=c.distanceSpreadM??0;
 if(!Number.isFinite(spread)||spread<0||spread>5000)throw Error('距离浮动须为0–5000米');
 if(!spread)return c;
 if((c.positionMode??'none')!=='none')throw Error('距离区间实验仅用于无GPS局部研究');
 if(!Number.isInteger(index)||index<0||index>=c.count)throw Error('样本索引无效');
 const r=rng((c.seed^0x44535452^Math.imul(index+1,0x9e3779b1))>>>0);
 const d=c.distance+(2*r()-1)*spread/1000;
 return {...c,distance:d,distanceSpreadM:0};
}
function distanceBounds(c){
 const spread=c.distanceSpreadM??0;
 if(!Number.isFinite(spread)||spread<0||spread>5000)throw Error('距离浮动须为0–5000米');
 if(spread&&(c.positionMode??'none')!=='none')throw Error('距离区间实验仅用于无GPS局部研究');
 const lo=c.distance-spread/1000,hi=c.distance+spread/1000;
 if(lo<.1||hi>20)throw Error('距离浮动后须在0.1–20公里内');
 return [lo,hi];
}
function validate(c){for(const [k,min,max] of [['count',1,30],['distance',.1,20],['pace',3,15],['cv',0,20],['noise',0,30],['seed',0,4294967295],['fixedStart',0,100]])if(!Number.isFinite(c[k])||c[k]<min||c[k]>max)throw Error('参数超出范围：'+k);if(c.count*(Math.round(distanceBounds(c)[1]*c.pace*60)+1)>60000)throw Error('V0.1 单批最多60000个采样点，请减少样本数或时长');if(!Number.isInteger(c.count)||!Number.isInteger(c.seed))throw Error('次数和种子必须是整数');if(!['forward','reverse','random'].includes(c.direction)||!['none','normal','high'].includes(c.fatigue))throw Error('运动模式无效');}
function simulate(c,points,closed,index){validate(c);let seed=(c.seed+Math.imul(index+1,2654435761))>>>0,r=rng(seed),g=geometry(points,closed),distance=c.distance*1000;if(!closed&&distance>g.len+.01)throw Error('开放路线的目标距离不能超过路线长度');let seconds=Math.max(1,Math.round(c.distance*c.pace*60));if(seconds>18000)throw Error('单次样本时间过长');let v=[],state=0;for(let t=0;t<seconds;t++){let f=t/Math.max(1,seconds-1),fat=c.fatigue==='high'?.16:c.fatigue==='normal'?.07:0;state=.94*state+Math.sqrt(1-.94*.94)*normal(r);let ramp=(c.accel?Math.min(1,(t+1)/10):1)*(c.decel?Math.min(1,(seconds-t)/12):1);v.push(Math.max(.05,(1-fat*f+c.cv/100*bounded(state,-2.5,2.5))*ramp));}let scale=distance/v.reduce((a,b)=>a+b,0),dir=c.direction==='random'?(r()<.5?-1:1):c.direction==='reverse'?-1:1,start=closed?(c.randomStart?r()*g.len:c.fixedStart/100*g.len):(dir===1?0:g.len),s=0,hr=85,steps=0,obsDist=0,prev=null,rows=[],errSq=0;for(let t=0;t<=seconds;t++){let speed=t===0?0:v[t-1]*scale;if(t)s+=speed;let p=pos(g,start+dir*s); // Independent controlled observation perturbation for local-coordinate research.
let e=c.noise===0?[0,0]:[normal(r)*c.noise/Math.SQRT2,normal(r)*c.noise/Math.SQRT2],o=[p[0]+e[0],p[1]+e[1]];errSq+=e[0]**2+e[1]**2;if(prev)obsDist+=Math.hypot(o[0]-prev[0],o[1]-prev[1]);prev=o;let cadence=speed>0?bounded(125+14*speed,110,200):0,step=cadence?speed*60/cadence:0;if(t){steps+=cadence/60;hr+=(bounded(80+26*speed,80,185)-hr)*.035;}rows.push({t,ideal_x_m:p[0],ideal_y_m:p[1],observed_x_m:o[0],observed_y_m:o[1],speed_mps:speed,distance_m:s,hr_bpm:hr,cadence_spm:cadence,step_length_m:step,ground_contact_ms:speed>0?bounded(330-23*speed,150,350):null,vertical_oscillation_mm:speed>0?bounded(58+7*speed,45,110):null,synthetic:true});}return {id:`SIM-${index+1}`,seed,rows,summary:{id:`SIM-${index+1}`,synthetic:true,seed,seconds,model_distance_m:s,observed_distance_m:obsDist,pace_sec_km:seconds/(s/1000),steps:Math.round(steps),mean_hr:rows.reduce((a,b)=>a+b.hr_bpm,0)/rows.length,rms_error_m:Math.sqrt(errSq/rows.length),start_m:start,direction:dir,route_length_m:g.len}};}
function csv(rows){if(!rows.length)return '';let keys=Object.keys(rows[0]);return keys.join(',')+'\n'+rows.map(r=>keys.map(k=>typeof r[k]==='number'?String(Math.round(r[k]*1e6)/1e6):r[k]??'').join(',')).join('\n')+'\n';}
const table=Array.from({length:256},(_,i)=>{for(let j=0;j<8;j++)i=(i&1)?0xedb88320^(i>>>1):i>>>1;return i>>>0;});function crc32(bytes){let c=0xffffffff;for(let b of bytes)c=table[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
function zip(files){let enc=new TextEncoder(),chunks=[],central=[],offset=0,clen=0;const make=n=>new Uint8Array(n),w=(a,p,n,v)=>{let d=new DataView(a.buffer);n===2?d.setUint16(p,v,true):d.setUint32(p,v,true);};for(let [name,value] of Object.entries(files)){let n=enc.encode(name),b=typeof value==='string'?enc.encode(value):value,crc=crc32(b),h=make(30+n.length);w(h,0,4,0x04034b50);w(h,4,2,20);w(h,6,2,2048);w(h,12,2,33);w(h,14,4,crc);w(h,18,4,b.length);w(h,22,4,b.length);w(h,26,2,n.length);h.set(n,30);chunks.push(h,b);let ch=make(46+n.length);w(ch,0,4,0x02014b50);w(ch,4,2,20);w(ch,6,2,20);w(ch,8,2,2048);w(ch,14,2,33);w(ch,16,4,crc);w(ch,20,4,b.length);w(ch,24,4,b.length);w(ch,28,2,n.length);w(ch,42,4,offset);ch.set(n,46);central.push(ch);clen+=ch.length;offset+=h.length+b.length;}let end=make(22);w(end,0,4,0x06054b50);w(end,8,2,central.length);w(end,10,2,central.length);w(end,12,4,clen);w(end,16,4,offset);let out=make(offset+clen+22),p=0;for(let b of [...chunks,...central,end]){out.set(b,p);p+=b.length;}return out;}
const api={VERSION,DECLARATION,standardTrack,referenceTrackShape,interpolateLocalRoute,referenceLocalRoute,validateReference,toGeographic,simulateResearch,sampleConfig,distanceBounds,geometry,crossing,simulate,validate,csv,zip};if(typeof module!=='undefined')module.exports=api;else root.StrideCore=api;
})(globalThis);
