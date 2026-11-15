"""Screen the private update recovery without changing production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_common_15175958_candidates as source
class ParticleCommon15175958RecoveryTests(unittest.TestCase):
    def test_private_recovery(self):
        root=source.ROOT
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/24BC30.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths}
        for module in ('tools.experiments.game_particle_common_15175958_candidates','tools.tests.game_particle_common_15175958_oracle','tools.tests.game_particle_common_15175958_native','tools.tests.game_particle_common_15175958_callers'):
            q=subprocess.run([sys.executable,'-m',module],cwd=root,capture_output=True,text=True)
            self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths})
        a=json.loads((source.OUT/'screen.json').read_text());self.assertEqual((a['words'],a['retail_words'],a['frame'],a['retail_frame'],a['neighbors'],a['exact_credit']),(956,961,200,200,8,0))
        b=json.loads((source.OUT/'behavior-screen.json').read_text());self.assertEqual((b['cases'],b['retail_words_visited'],b['streams'],len(b['effective_controls']),b['exact_credit']),(1483,881,2,5,0))
        self.assertEqual(b['predivision_zero_prefixes'],24)
        n=json.loads((source.OUT/'native-common-report.json').read_text());self.assertEqual([(r['cases'],r['effective_controls'],r['sequencing_control_killed'])for r in n],[(1315,6,True)]*3)
        c=json.loads((source.OUT/'caller-report.json').read_text());self.assertEqual((c['direct_sites'],c['direct_cases'],c['registry_entries'],c['registry_cases'],c['streams']),(3,120,4,160,2));self.assertTrue(c['bookkeeping_control_killed'])
if __name__=='__main__':unittest.main()
