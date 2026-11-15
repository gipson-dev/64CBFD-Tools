"""Material renderer qualification without changing production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_material_15176df0_match as source

class ParticleMaterial15176DF0MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/22FF90.rodata.s','conker/include/functions.h','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_particle_material_15176df0_match','tools.tests.game_particle_material_15176df0_oracle','tools.tests.game_particle_material_15176df0_native','tools.tests.game_particle_material_15176df0_callers','tools.tests.game_particle_material_15176df0_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        out=root/source.BUILD;r=json.loads((out/'raw-report.json').read_text())
        self.assertEqual((r['raw_words'],r['words'],r['frame'],r['guards'],r['inserted_copy'],r['neighbors'],r['corruption_controls']),(181,182,216,75,1,8,202))
        self.assertEqual(len(r['registry_slots']),8);self.assertEqual(r['direct_callers'],[0x1a46e8])
        r=json.loads((out/'behavior.json').read_text());self.assertEqual((r['cases'],r['streams'],r['private_color_cases'],r['full_state_prefixes'],r['visited_words']),(1024,3,24,229,181))
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['effective_controls']) for v in r],[(704,5)]*3)
        r=json.loads((out/'caller-report.json').read_text());self.assertEqual((r['registry_cases'],r['connected_parent_cases'],r['actual_parent_words'],len(r['emitted_controls'])),(192,96,101,3))
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,75))

if __name__=='__main__':unittest.main()
