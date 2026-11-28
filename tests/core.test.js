const assert=require('node:assert/strict'),C=require('../app/src/main/assets/core.js');const p=C.standardTrack(),c={count:5,distance:2,pace:6,cv:5,noise:1.5,seed:17,fixedStart:0,randomStart:true,direction:'forward',fatigue:'normal',accel:true,decel:true};let g=C.geometry(p,true);assert.ok(Math.abs(g.len-400)<1);assert.equal(C.crossing(p,true),0);let a=C.simulate(c,p,true,0);assert.ok(Math.abs(a.summary.model_distance_m-2000)<1e-6);assert.equal(a.rows.length,721);assert.equal(a.summary.seconds,720);assert.deepEqual(a,C.simulate(c,p,true,0));assert.notEqual(a.seed,C.simulate(c,p,true,1).seed);assert.notEqual(a.summary.start_m,C.simulate(c,p,true,1).summary.start_m);let z=C.simulate({...c,noise:0,randomStart:false},p,true,0);assert.equal(z.summary.start_m,0);assert.equal(z.summary.rms_error_m,0);assert.ok(z.rows.every(r=>r.ideal_x_m===r.observed_x_m&&r.ideal_y_m===r.observed_y_m));assert.ok(a.rows.every(r=>Math.abs(r.speed_mps-r.cadence_spm*r.step_length_m/60)<1e-10&&r.synthetic));assert.throws(()=>C.simulate(c,[[0,0],[100,0]],false,0));assert.ok(C.crossing([[0,0],[10,10],[0,10],[10,0]],true)>0);assert.throws(()=>C.validate({...c,count:31}));let open=C.simulate({...c,distance:.1,direction:'reverse',noise:0},[[0,0],[100,0]],false,0);assert.equal(open.rows[0].ideal_x_m,100);assert.ok(Math.abs(open.rows.at(-1).ideal_x_m)<1e-6);console.log('PASS: geometry, crossing, deterministic seed, variation, distance integral, zero noise, cadence consistency, open route, input validation');

const marks=[[0,0],[0,.001],[.0004,.001],[.0004,0]];
const shaped=C.referenceTrackShape(marks);
assert.equal(shaped.closed,true);
assert.equal(shaped.points.length,50);
assert.ok(Math.abs(C.geometry(shaped.points,true).len-400)<1e-8);
assert.equal(C.crossing(shaped.points,true),0);
assert.ok(shaped.points.every(p=>p.every(Number.isFinite)));
assert.ok(!('lat' in shaped)&&!('lon' in shaped));
assert.throws(()=>C.referenceTrackShape([[0,0],[0,.001]]));
assert.throws(()=>C.referenceTrackShape([[0,0],[0,.001],[0,.002]]));
const normalized=C.simulate({...c,noise:0},shaped.points,true,0);
assert.ok(Math.abs(normalized.summary.route_length_m-400)<1e-8);
assert.ok(Math.abs(normalized.summary.model_distance_m-2000)<1e-6);
console.log('PASS: reference-shape normalization, closed local stadium, invalid marks and local simulation integration');

const irregular=[[0,0],[80,0],[90,30],[30,50],[-10,25]];
for(const closed of [true,false])for(const mode of ['linear','smooth'])for(const count of [5,30,120]){
 const r=C.interpolateLocalRoute(irregular,closed,count,mode,.7);
 assert.equal(r.points.length,count);
 assert.equal(r.closed,closed);
 assert.ok(irregular.every(p=>r.points.some(q=>p[0]===q[0]&&p[1]===q[1])));
 assert.equal(C.crossing(r.points,closed),0);
 if(mode==='linear')assert.ok(Math.abs(r.length_m-C.geometry(irregular,closed).len)<1e-8);
}
assert.throws(()=>C.interpolateLocalRoute(irregular,true,4));
assert.throws(()=>C.interpolateLocalRoute(irregular,true,121));
assert.throws(()=>C.interpolateLocalRoute([[0,0],[0,0],[5,5]],true,30));
const ref=C.referenceLocalRoute(marks,true,60,'linear',0);
assert.equal(ref.points.length,60);
assert.ok(ref.length_m>310&&ref.length_m<312);
assert.ok(!('lat' in ref)&&!('lon' in ref));
const research=C.simulate({...c,noise:0},ref.points,true,0);
assert.ok(Math.abs(research.summary.route_length_m-ref.length_m)<1e-8);
assert.equal(research.rows.length,721);
console.log('PASS: ordered local interpolation, vertex preservation, adjustable point count, actual local scale and simulation integration');

const sweep={...c,positionMode:'none',distanceSpreadM:100};
const cases=Array.from({length:sweep.count},(_,i)=>C.simulateResearch(sweep,p,true,i));
assert.equal(new Set(cases.map(s=>s.summary.target_distance_m)).size,sweep.count);
for(const [i,s] of cases.entries()){
 assert.ok(s.summary.target_distance_m>=1900&&s.summary.target_distance_m<=2100);
 assert.ok(Math.abs(s.summary.model_distance_m-s.summary.target_distance_m)<1e-6);
 assert.equal(s.summary.seconds,Math.round(C.sampleConfig(sweep,i).distance*sweep.pace*60));
 assert.deepEqual(s,C.simulateResearch(sweep,p,true,i));
 assert.ok(s.rows.every(r=>!('latitude_deg' in r)&&!('longitude_deg' in r)));
}
assert.throws(()=>C.validate({...sweep,distanceSpreadM:2000}));
assert.throws(()=>C.validate({...sweep,positionMode:'geo'}));
assert.deepEqual(C.simulateResearch({...c,positionMode:'none',distanceSpreadM:0},p,true,0),C.simulate(c,p,true,0));
console.log('PASS: local distance sweeps, exact integration, no-GPS separation, reproducible targets and legacy behavior');

const stats=C.sampleStatistics(z);
assert.equal(stats.synthetic,true);
assert.equal(stats.observation_error_m.p95,0);
assert.ok(stats.steady_speed_cv_pct>=0);
assert.equal(stats.step_length_m.n,z.rows.length-1);
assert.ok(stats.ground_contact_ms.mean>=150&&stats.ground_contact_ms.mean<=350);
assert.equal(C.describe([1,2,3,null,NaN]).mean,2);
assert.ok(Math.abs(C.describe([1,2,3]).p95-2.9)<1e-9);
assert.equal(C.describe([]).mean,null);
console.log('PASS: research statistics, quantiles, missing observations and zero-noise error distribution');

for(let i=0;i<sweep.count;i++)assert.equal(C.simulateResearch({...sweep,durationMode:'duration'},p,true,i).summary.seconds,720);
assert.throws(()=>C.validate({...sweep,durationMode:'duration',distanceSpreadM:2000}));
assert.throws(()=>C.validate({...sweep,durationMode:'duration',pace:3}));
console.log('PASS: fixed-duration local experiments and pace bounds');

const both={...sweep,paceSpreadSec:20};
const small={...both,paceSpreadSec:10};
for(let i=0;i<both.count;i++){
 const q=C.sampleConfig(both,i),r=C.sampleConfig(small,i),s=C.simulateResearch(both,p,true,i);
 assert.ok(q.pace>=6-20/60&&q.pace<=6+20/60);
 assert.ok(Math.abs((q.pace-6)-2*(r.pace-6))<1e-12);
 assert.equal(q.distance,r.distance);
 assert.equal(s.summary.seconds,Math.round(q.distance*q.pace*60));
 assert.ok(Math.abs(s.summary.target_pace_sec_km-q.pace*60)<1e-9);
 assert.deepEqual(s,C.simulateResearch(both,p,true,i));
}
assert.throws(()=>C.validate({...both,positionMode:'geo'}));
assert.throws(()=>C.validate({...both,durationMode:'duration'}));
assert.throws(()=>C.validate({...both,pace:3}));
assert.equal(C.maxSampleSeconds(both),Math.round(2.1*(6+20/60)*60));
console.log('PASS: independent local parameter sweeps, amplitude scaling, time bounds and replay');

const hashVectors=[["","e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],["abc","ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"],["a".repeat(1000000),"cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0"]];
for(const [v,h] of hashVectors)assert.equal(C.sha256(v),h);
assert.equal(C.sha256("合成研究\n"),require('node:crypto').createHash('sha256').update("合成研究\n").digest('hex'));
const quality=C.validateResearchRows(a);
assert.equal(quality.passed,true);assert.equal(quality.row_count,721);assert.ok(quality.distance_residual_m<1e-8);
const bad=JSON.parse(JSON.stringify(a));bad.rows[5].step_length_m+=1;assert.equal(C.validateResearchRows(bad).passed,false);
const analysis=C.analysisRows(a,5);assert.equal(analysis.length,145);assert.equal(analysis.at(-1).t,a.rows.at(-1).t);assert.ok(analysis.every(r=>r.analysis_view&&r.synthetic));assert.ok(a.rows.every(r=>!('analysis_view' in r)));
assert.throws(()=>C.analysisRows({...a,position_source:'synthetic_map_reference'},5));
const comp=C.compareResearchGroups([{id:'a',label:'A',sessions:[a,z]},{id:'b',label:'B',sessions:[z]}]);assert.equal(comp[0].n,2);assert.equal(comp[0].valid_count,2);assert.equal(comp[1].rms_error_m.mean,0);assert.throws(()=>C.compareResearchGroups([]));
console.log('PASS: independent SHA256 vectors, row validation, immutable local analysis and archived-group comparison');

const previewMarks=[[0,0],[0,.001],[.001,.001],[.001,0]];
const basePreview=C.referenceLocalRoute(previewMarks,true,120,'linear',0);
for(const n of [300,500,1000]){
 const v=C.previewReferenceRoute(previewMarks,true,n,'linear',0);
 assert.equal(v.points.length,n);assert.equal(v.preview_only,true);assert.equal(v.purpose,'reference_geometry_only');
 assert.ok(Math.abs(v.length_m-basePreview.length_m)<1e-7);
}
assert.throws(()=>C.previewReferenceRoute(previewMarks,true,1001,'linear',0));
assert.throws(()=>C.referenceLocalRoute(previewMarks,true,121,'linear',0));
console.log('PASS: high-resolution reference geometry previews, unchanged experimental route capacity');

const studyGroup={count:2,distance:.2,pace:6,cv:5,noise:0,profile:'baseline'};
const study=C.prepareLocalStudy({seed:17,interval:5,groups:[studyGroup,{...studyGroup,profile:'higher'}]});
assert.equal(study.groups.length,2);
assert.equal(study.total_points_upper_bound,292);
assert.notEqual(study.groups[0].config.seed,study.groups[1].config.seed);
const studyA=C.localStudySample(study.groups[0],0),studyB=C.localStudySample({...study.groups[0],profile:'higher'},0);
assert.ok(studyA.research_only&&studyB.research_only);
assert.equal(C.validateResearchRows(studyA).passed,true);
assert.equal(C.validateResearchRows(studyB).passed,true);
assert.ok(studyB.summary.mean_hr>studyA.summary.mean_hr);
assert.ok(studyB.rows.every(r=>!('latitude_deg' in r)&&!('longitude_deg' in r)));
assert.deepEqual(studyA,C.localStudySample(study.groups[0],0));
assert.throws(()=>C.prepareLocalStudy({seed:17,interval:5,groups:Array.from({length:5},()=>({...studyGroup,count:30,distance:20,pace:15}))}));
assert.throws(()=>C.localStudySample({...study.groups[0],config:{...study.groups[0].config,positionMode:'geo'}},0));
console.log('PASS: independent local multi-group plans, sensitivity profiles, reproducible samples, bounds and geographic separation');
