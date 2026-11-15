"""Focused particle callback qualification with unchanged production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_display_151770c8_match as source

class ParticleDisplay151770C8MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/data/22FF90.rodata.s','conker/include/functions.h','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_particle_display_151770c8_match','tools.tests.game_particle_display_151770c8_oracle','tools.tests.game_particle_display_151770c8_native','tools.tests.game_particle_display_151770c8_padder'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        out=root/source.BUILD;r=json.loads((out/'raw-report.json').read_text())
        self.assertEqual((r['words'],r['frame'],r['guards'],r['neighbors'],r['corruption_controls']),(101,144,4,8,119));self.assertEqual(r['registry_slots'],[0x8008b88c])
        r=json.loads((out/'behavior.json').read_text());self.assertEqual((r['cases'],r['streams'],r['visited_words'],r['callback_cases'],r['full_state_prefixes']),(1219,3,100,80,122))
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['effective_controls']) for v in r],[(376,5)]*3)
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,4))

if __name__=='__main__':unittest.main()
