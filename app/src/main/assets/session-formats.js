/* Synthetic session export. Local coordinates are never encoded as GPS. */
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
function fit(session,timeline){
 const s=checked(session,timeline),data=[],defs=new Map(),sizes={0:1,2:1,132:2,134:4,140:4},U=134,H=132,B=2,E=0;
 const f=(n,t,size=sizes[t])=>[n,t,size],put=(a,v,n)=>{for(let i=0;i<n;i++)a.push((v>>>(8*i))&255);};
 function define(l,g,fs){defs.set(l,fs);data.push(64|l,0,0);put(data,g,2);data.push(fs.length);for(const[n,t,size]of fs)data.push(n,size,t);}
 function msg(l,vs){data.push(l);defs.get(l).forEach(([n,t,size],i)=>{const v=vs[i];if(t===7){for(let j=0;j<size;j++)data.push(j<Math.min(v.length,size-1)?v.charCodeAt(j):0);}else put(data,v,size);});}
 const t0=s.start-EPOCH,t1=s.end-EPOCH,elapsed=s.seconds*1000,dist=Math.round(s.distance*100),speed=Math.round(s.distance/s.seconds*1000);
 const active=s.rows.slice(1),avg=k=>active.reduce((a,r)=>a+r[k],0)/active.length,max=k=>active.reduce((a,r)=>Math.max(a,r[k]),0),hr=Math.round(avg('hr_bpm')),cad=Math.round(avg('cadence_spm')/2),cycles=Math.round(active.reduce((a,r,i)=>a+r.cadence_spm*(r.t-s.rows[i].t)/120,0));
 define(0,0,[f(0,E),f(1,H),f(2,H),f(3,140),f(4,U),f(8,7,32)]);msg(0,[4,255,0,session.seed||1,t0,LABEL]);
 define(1,21,[f(253,U),f(0,E),f(1,E)]);msg(1,[t0,0,0]);
 define(2,20,[f(253,U),f(5,U),f(6,H),f(3,B),f(4,B)]);
 for(const r of s.rows)msg(2,[t0+r.t,Math.round(r.distance_m*100),Math.round(r.speed_mps*1000),Math.round(r.hr_bpm),Math.round(r.cadence_spm/2)]);
 msg(1,[t1,0,4]);
 const common=[elapsed,elapsed,dist,cycles,speed,Math.round(max('speed_mps')*1000),hr,Math.round(max('hr_bpm')),cad,Math.round(max('cadence_spm')/2)];
 define(3,19,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(7,U),f(8,U),f(9,U),f(10,U),f(13,H),f(14,H),f(15,B),f(16,B),f(17,B),f(18,B),f(25,E)]);msg(3,[0,t1,9,1,t0,...common,1]);
 define(4,18,[f(254,H),f(253,U),f(0,E),f(1,E),f(2,U),f(5,E),f(6,E),f(7,U),f(8,U),f(9,U),f(10,U),f(14,H),f(15,H),f(16,B),f(17,B),f(18,B),f(19,B),f(25,H),f(26,H),f(110,7,32)]);msg(4,[0,t1,8,1,t0,1,0,...common,0,1,LABEL]);
 define(5,34,[f(253,U),f(0,U),f(1,H),f(2,E),f(3,E),f(4,E)]);msg(5,[t1,elapsed,1,0,26,1]);
 const head=[14,32];put(head,2100,2);put(head,data.length,4);head.push(46,70,73,84);put(head,crc(head),2);
 const out=new Uint8Array(head.length+data.length+2);out.set(head);out.set(data,head.length);new DataView(out.buffer).setUint16(out.length-2,crc(out.subarray(0,-2)),true);return out;
}
function tcx(session,timeline){
 const s=checked(session,timeline),stamp=t=>new Date((s.start+t)*1000).toISOString(),num=n=>String(Math.round(n*1e6)/1e6);
 const track=s.rows.map(r=>'<Trackpoint><Time>'+stamp(r.t)+'</Time><DistanceMeters>'+num(r.distance_m)+'</DistanceMeters><HeartRateBpm><Value>'+Math.round(r.hr_bpm)+'</Value></HeartRateBpm><Cadence>'+Math.round(r.cadence_spm/2)+'</Cadence><Extensions><ns3:TPX><ns3:Speed>'+num(r.speed_mps)+'</ns3:Speed><ns3:RunCadence>'+Math.round(r.cadence_spm/2)+'</ns3:RunCadence></ns3:TPX></Extensions></Trackpoint>').join('');
 return '<?xml version="1.0" encoding="UTF-8"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2"><Activities><Activity Sport="Running"><Id>'+stamp(0)+'</Id><Lap StartTime="'+stamp(0)+'"><TotalTimeSeconds>'+s.seconds+'</TotalTimeSeconds><DistanceMeters>'+num(s.distance)+'</DistanceMeters><Calories>0</Calories><Intensity>Active</Intensity><TriggerMethod>Manual</TriggerMethod><Track>'+track+'</Track><Notes>'+LABEL+' - simulated, not measured; cadence is cycles/minute; calories unavailable</Notes></Lap><Notes>'+LABEL+' - model distance, no GPS position; not measured activity</Notes></Activity></Activities></TrainingCenterDatabase>';
}
const api={fit,tcx,checked};if(typeof module!=='undefined')module.exports=api;else root.StrideFormats=api;
})(globalThis);
