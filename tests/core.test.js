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
