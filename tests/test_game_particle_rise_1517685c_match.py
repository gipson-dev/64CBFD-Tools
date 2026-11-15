"""Rise callback qualification without changing production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_rise_1517685c_match as source

class ParticleRise1517685CMatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/22FF90.rodata.s','conker/include/functions.h','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in('tools.experiments.game_particle_rise_1517685c_match','tools.tests.game_particle_rise_1517685c_oracle','tools.tests.game_particle_rise_1517685c_native','tools.tests.game_particle_rise_1517685c_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in paths})
        out=root/source.BUILD;r=json.loads((out/'raw-report.json').read_text());self.assertEqual((r['raw_words'],r['words'],r['frame'],r['guards'],r['neighbors'],r['corruption_controls']),(202,202,32,123,8,217));self.assertEqual(r['registry_slots'],[0x8008b884]);self.assertEqual(r['direct_callers'],[])
        r=json.loads((out/'behavior.json').read_text());self.assertEqual((r['cases'],r['visited_words'],r['dispatcher_cases'],r['registry_slots'],r['full_state_prefixes'],len(r['emitted_controls'])),(1936,200,64,1,85,5));self.assertEqual(r['unvisited_offsets'],['0x14c','0x2d4']);self.assertTrue(r['bookkeeping_control_killed'])
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['effective_controls'],v['unsigned_modulo_control_killed'])for v in r],[(1378,5,True)]*3)
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,123))

if __name__=='__main__':unittest.main()
