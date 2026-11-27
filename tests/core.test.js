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
