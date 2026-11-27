"""Run regression tests with standard library: python scripts/test_skill.py."""
import datetime as dt, json, tempfile, unittest, zipfile
from pathlib import Path
from generate import configure, Route, simulate, generate
from format_fixture import fixture
class TestSkill(unittest.TestCase):
    def cfg(self,**kw): return configure(dict(seed=42,**kw))[0]
    def run_one(self,c,g=1,j=1): return simulate(c,Route(c),g,j,dt.datetime(2030,1,1,tzinfo=dt.timezone.utc))
    def test_default(self):
        c=self.cfg(); a,s=self.run_one(c); self.assertAlmostEqual(s['model_distance_m'],2000); self.assertAlmostEqual(Route(c).length,400,places=2); self.assertEqual(s['duration_s'],720)
    def test_zero_noise_and_seed(self):
        c=self.cfg(gps_noise_m=0); a,s=self.run_one(c); self.assertEqual((a,s),self.run_one(c)); self.assertEqual(s['realized_rms_m'],0); self.assertNotEqual(a,self.run_one(c,j=2)[0])
    def test_noise_independence(self):
        a,s=self.run_one(self.cfg(gps_noise_m=0)); b,t=self.run_one(self.cfg(gps_noise_m=6)); self.assertEqual([r['speed_m_s'] for r in a],[r['speed_m_s'] for r in b]); self.assertEqual([r['heart_rate_bpm'] for r in a],[r['heart_rate_bpm'] for r in b]); self.assertGreater(t['realized_rms_m'],0)
    def test_fixed_start_reverse(self):
        c=self.cfg(random_start=False,fixed_start_m=50,direction='reverse'); a,s=self.run_one(c); self.assertEqual(s['phase_m'],50); self.assertEqual(s['direction'],-1); self.assertEqual((a[0]['ideal_x_m'],a[0]['ideal_y_m']),Route(c).xy(50))
    def test_multinode(self):
        for n in [3,8,50]:
            import math
            p=[[50*math.cos(i*2*math.pi/n),50*math.sin(i*2*math.pi/n)] for i in range(n)]; c=self.cfg(route_nodes=p,coordinate_system='LOCAL_M'); route=Route(c); self.assertEqual(len(route.nodes),n); self.assertEqual(route.crossings,[])
    def test_open(self):
        c=self.cfg(closed=False,random_start=False,route_nodes=[[0,0],[100,0],[100,100]],coordinate_system='LOCAL_M',distance_m=200,direction='reverse'); a,s=self.run_one(c); self.assertAlmostEqual(a[-1]['ideal_x_m'],0); self.assertAlmostEqual(a[-1]['ideal_y_m'],0)
        with self.assertRaises(ValueError): Route(self.cfg(closed=False,random_start=False,route_nodes=[[0,0],[100,0]],coordinate_system='LOCAL_M',distance_m=200))
    def test_crossing_and_unknown_crs(self):
        p=[[0,0],[100,100],[0,100],[100,0]]; self.assertTrue(Route(self.cfg(route_nodes=p,coordinate_system='LOCAL_M')).crossings)
        with self.assertRaises(ValueError): Route(self.cfg(route_nodes=p,coordinate_system='GCJ02'))
    def test_reference_separated(self):
        c=self.cfg(route_nodes=[[35,100],[35.001,100],[35.001,100.001]],coordinate_system='WGS84'); a,s=self.run_one(c); self.assertIsNotNone(Route(c).reference); self.assertNotIn('latitude_deg',a[0]); self.assertNotIn('longitude_deg',a[0])
    def test_duration(self):
        c=self.cfg(duration_s=600); a,s=self.run_one(c); self.assertEqual(s['duration_s'],600); self.assertAlmostEqual(s['pace_min_km'],5)
    def test_optional_metrics(self):
        a,s=self.run_one(self.cfg(metrics=['steps'])); self.assertNotIn('heart_rate_bpm',a[0]); self.assertIn('steps_cumulative',a[0]); self.assertIsNone(s['avg_hr_bpm'])
    def test_batch_and_rerun(self):
        raw=dict(seed=42,groups=2,count_range=[2,3],distance_m=100,formats=['csv','json']);
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); s=generate(raw,p/'a'); a=generate(raw,p/'b','group_01_run_001'); b=generate(raw,p/'c','group_01_run_001',1); self.assertEqual(s[0],a[0]); self.assertNotEqual(a[0]['seed'],b[0]['seed']); self.assertGreaterEqual(len(s),4); self.assertLessEqual(len(s),6)
            for z in (p/'a').glob('*.zip'):
                with zipfile.ZipFile(z) as f: self.assertIsNone(f.testzip()); self.assertIn('用途声明.txt',f.namelist())
    def test_fixture(self):
        with tempfile.TemporaryDirectory() as d: fixture(Path(d)/'fixture'); self.assertTrue((Path(d)/'fixture'/'SYNTHETIC_FORMAT_FIXTURE.fit').is_file())
if __name__=='__main__': unittest.main(verbosity=2)
