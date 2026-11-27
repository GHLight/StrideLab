/* Synthetic research export. Geographic rows require explicit WGS84 synthetic provenance. */
(function(root){'use strict';
const LABEL='SYNTHETIC_RESEARCH',EPOCH=Date.UTC(1989,11,31)/1000;
function checked(session,timeline){
 if(!session||!session.summary||session.summary.synthetic!==true||!Number.isFinite(session.summary.model_distance_m)||!Number.isFinite(session.summary.seconds)||!Array.isArray(session.rows)||session.rows.length<2)throw Error('没有可导出的样本');
 if(!timeline||timeline.synthetic!==true||timeline.sample_id!==session.id)throw Error('此历史样本未设置时间轴，请重新生成后导出');
 const start=Date.parse(timeline.scenario_start)/1000,rows=session.rows;
 if(!Number.isInteger(start)||start<EPOCH||start+rows.at(-1).t-EPOCH>=0xffffffff)throw Error('日期超出 FIT 可表示范围（1989-12-31 至 2126 年）');
 for(let i=0;i<rows.length;i++){
  const r=rows[i];if(r.synthetic!==true||!['t','distance_m','speed_mps','hr_bpm','cadence_spm'].every(k=>Number.isFinite(r[k])&&r[k]>=0)||!Number.isInteger(r.t)||r.hr_bpm>254||r.cadence_spm>508||r.speed_mps>=65.535||r.distance_m>=42949672.95||i===0&&(r.t!==0||r.distance_m!==0)||i>0&&(r.t<=rows[i-1].t||r.distance_m<rows[i-1].distance_m))throw Error('样本数据未通过导出一致性检查');
 }
 if(Math.abs(rows.at(-1).distance_m-session.summary.model_distance_m)>1e-6||rows.at(-1).t!==session.summary.seconds||Date.parse(timeline.scenario_end)/1000!==start+rows.at(-1).t)throw Error('时间轴、汇总和逐点记录不一致');
 return {start,rows,end:start+rows.at(-1).t,seconds:rows.at(-1).t,distance:rows.at(-1).distance_m};
}
function crc(bytes){let c=0;for(let b of bytes){c^=b;for(let i=0;i<8;i++)c=(c&1)?(c>>>1)^0xa001:c>>>1;}return c;}
function encodeFit(session,timeline,positions=null){
 const s=checked(session,timeline),data=[],defs=new Map(),sizes={0:1,2:1,132:2,133:4,134:4,140:4},U=134,H=132,B=2,E=0;
 const f=(n,t,size=sizes[t])=>[n,t,size],put=(a,v,n)=>{for(let i=0;i<n;i++)a.push((v>>>(8*i))&255);};
 function define(l,g,fs){defs.set(l,fs);data.push(64|l,0,0);put(data,g,2);data.push(fs.length);for(const[n,t,size]of fs)data.push(n,size,t);}
 function msg(l,vs){data.push(l);defs.get(l).forEach(([n,t,size],i)=>{const v=vs[i];if(t===7){for(let j=0;j<size;j++)data.push(j<Math.min(v.length,size-1)?v.charCodeAt(j):0);}else put(data,v,size);});}
 const t0=s.start-EPOCH,t1=s.end-EPOCH,elapsed=s.seconds*1000,dist=Math.round(s.distance*100),speed=Math.round(s.distance/s.seconds*1000);
 const active=s.rows.slice(1),avg=k=>active.reduce((a,r)=>a+r[k],0)/active.length,max=k=>active.reduce((a,r)=>Math.max(a,r[k]),0),hr=Math.round(avg('hr_bpm')),cad=Math.round(avg('cadence_spm')/2),cycles=Math.round(active.reduce((a,r,i)=>a+r.cadence_spm*(r.t-s.rows[i].t)/120,0));
 define(0,0,[f(0,E),f(1,H),f(2,H),f(3,140),f(4,U),f(8,7,32)]);msg(0,[4,255,0,session.seed||1,t0,LABEL]);
 define(1,21,[f(253,U),f(0,E),f(1,E)]);msg(1,[t0,0,0]);
 const semicircle=n=>Math.max(-2147483648,Math.min(2147483646,Math.round(n*2147483648/180)));
 define(2,20,[f(253,U),f(5,U),f(6,H),f(3,B),f(4,B),...(positions?[f(0,133),f(1,133)]:[])]);
 for(const [i,r] of s.rows.entries())msg(2,[t0+r.t,Math.round(r.distance_m*100),Math.round(r.speed_mps*1000),Math.round(r.hr_bpm),Math.round(r.cadence_spm/2),...(positions?positions[i].map(semicircle):[])]);
 msg(1,[t1,0,4]);
 const common=[elapsed,elapsed,dist,cycles,speed,Math.round(max('speed_mps')*1000),hr,Math.round(max('hr_bpm')),cad,Math.round(max('cadence_spm')/2)];
 define(3,19,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(7,U),f(8,U),f(9,U),f(10,U),f(13,H),f(14,H),f(15,B),f(16,B),f(17,B),f(18,B),f(25,E)]);msg(3,[0,t1,9,1,t0,...common,1]);
 define(4,18,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(5,E),f(6,E),f(7,U),f(8,U),f(9,U),f(10,U),f(14,H),f(15,H),f(16,B),f(17,B),f(18,B),f(19,B),f(25,H),f(26,H),f(110,7,32)]);msg(4,[0,t1,8,1,t0,1,0,...common,0,1,LABEL]);
 define(5,34,[f(253,U),f(0,U),f(1,H),f(2,E),f(3,E),f(4,E)]);msg(5,[t1,elapsed,1,0,26,1]);
 // All definitions in this encoder use FIT 1.x base fields; no developer fields.
 const head=[14,16];put(head,2100,2);put(head,data.length,4);head.push(46,70,73,84);put(head,crc(head),2);
 const out=new Uint8Array(head.length+data.length+2);out.set(head);out.set(data,head.length);new DataView(out.buffer).setUint16(out.length-2,crc(out.subarray(0,-2)),true);return out;
}
function encodeTcx(session,timeline,positions=null){
 const s=checked(session,timeline),stamp=t=>new Date((s.start+t)*1000).toISOString(),num=n=>String(Math.round(n*1e6)/1e6);
 const track=s.rows.map((r,i)=>'<Trackpoint><Time>'+stamp(r.t)+'</Time>'+(positions?'<Position><LatitudeDegrees>'+num(positions[i][0])+'</LatitudeDegrees><LongitudeDegrees>'+num(positions[i][1])+'</LongitudeDegrees></Position>':'')+'<DistanceMeters>'+num(r.distance_m)+'</DistanceMeters><HeartRateBpm><Value>'+Math.round(r.hr_bpm)+'</Value></HeartRateBpm><Cadence>'+Math.round(r.cadence_spm/2)+'</Cadence><Extensions><ns3:TPX><ns3:Speed>'+num(r.speed_mps)+'</ns3:Speed><ns3:RunCadence>'+Math.round(r.cadence_spm/2)+'</ns3:RunCadence></ns3:TPX></Extensions></Trackpoint>').join('');
 return '<?xml version="1.0" encoding="UTF-8"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2"><Activities><Activity Sport="Running"><Id>'+stamp(0)+'</Id><Lap StartTime="'+stamp(0)+'"><TotalTimeSeconds>'+s.seconds+'</TotalTimeSeconds><DistanceMeters>'+num(s.distance)+'</DistanceMeters><Calories>0</Calories><Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod><Track>'+track+'</Track><Notes>'+LABEL+' - simulated, not measured; cadence is cycles/minute; calories unavailable</Notes></Lap><Notes>'+LABEL+(positions?(session.position_source==='synthetic_map_reference'?' - synthetic geographic research, map-derived coordinates, not measured activity':' - fixed ocean coordinate parser fixture, not measured activity'):' - model distance, no GPS position; not measured activity')+'</Notes></Activity></Activities></TrainingCenterDatabase>';
}
// This fixed, non-user-configurable coordinate fixture is separate from all
// sessions and reference maps. The points lie in the open Pacific.
function gpsFixture(){
 const positions=[[0,-140],[0,-139.9999],[0.0001,-139.9999],[0.0001,-140]];
 const step=6371008.8*Math.PI/180*.0001;
 const rows=positions.map((p,i)=>({t:i*10,distance_m:i*step,speed_mps:i?step/10:0,hr_bpm:0,cadence_spm:0,synthetic:true}));
 const session={id:'FIXTURE',seed:1,rows,summary:{synthetic:true,model_distance_m:rows.at(-1).distance_m,seconds:30}};
 const timeline={sample_id:'FIXTURE',synthetic:true,scenario_start:'2030-01-01T00:00:00Z',scenario_end:'2030-01-01T00:00:30Z'};
 return {session,timeline,positions};
}
function researchPositions(session){
 if(!session||!Array.isArray(session.rows))throw Error('没有可导出的样本');
 if(session.position_source===undefined||session.position_source==='none'){
   if(session.rows.some(r=>r.latitude_deg!==undefined||r.longitude_deg!==undefined))throw Error('缺少合成地理来源标识');
   return null;
 }
 if(session.position_source!=='synthetic_map_reference'||session.summary?.position_source!==session.position_source)throw Error('地理研究来源标识不一致');
 return session.rows.map(r=>{if(r.position_source!==session.position_source||!Number.isFinite(r.latitude_deg)||!Number.isFinite(r.longitude_deg)||Math.abs(r.latitude_deg)>90||r.longitude_deg< -180||r.longitude_deg>=180)throw Error('合成经纬度无效');return [r.latitude_deg,r.longitude_deg];});
}
function fit(session,timeline){return encodeFit(session,timeline,researchPositions(session));}
function tcx(session,timeline){return encodeTcx(session,timeline,researchPositions(session));}
function gpsFixtureFit(){const g=gpsFixture();return encodeFit(g.session,g.timeline,g.positions);}
function gpsFixtureTcx(){const g=gpsFixture();return encodeTcx(g.session,g.timeline,g.positions);}
const api={fit,tcx,checked,gpsFixtureFit,gpsFixtureTcx};if(typeof module!=='undefined')module.exports=api;else root.StrideFormats=api;
})(globalThis);
