"""Particle state qualification preserves production inputs before adoption."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_state_15176b84_match as source

class ParticleState15176B84MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/22FF90.rodata.s','conker/include/functions.h','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in('tools.experiments.game_particle_state_15176b84_match','tools.tests.game_particle_state_15176b84_oracle','tools.tests.game_particle_state_15176b84_native','tools.tests.game_particle_state_15176b84_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths})
        out=root/source.BUILD;r=json.loads((out/'raw-report.json').read_text())
        self.assertEqual((r['raw_words'],r['words'],r['frame'],r['guards'],r['neighbors'],r['corruption_controls']),(155,155,32,32,8,179));self.assertEqual(len(r['registry_slots']),4);self.assertEqual(r['direct_callers'],[])
        r=json.loads((out/'behavior.json').read_text());self.assertEqual((r['cases'],r['predivision_zero_prefixes'],r['visited_words'],r['dispatcher_cases'],r['full_state_prefixes'],len(r['emitted_controls'])),(841,16,152,128,82,5));self.assertEqual(r['unvisited_offsets'],['0x5c','0x1b0','0x228'])
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['effective_controls'],v['implicit_cast_control_killed'])for v in r],[(597,5,True)]*3)
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,32))

if __name__=='__main__':unittest.main()
