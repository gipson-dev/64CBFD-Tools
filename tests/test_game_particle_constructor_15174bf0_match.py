"""Recovered source, packet ABI, native32 and both full-owner padders."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_particle_constructor_15174bf0_match as source
class ParticleConstructor15174BF0MatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/1B0740.s','conker/asm/data/24BC30.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_particle_constructor_15174bf0_match','tools.tests.game_particle_constructor_15174bf0_padder','tools.tests.game_particle_constructor_15174bf0_oracle','tools.tests.game_particle_constructor_15174bf0_native'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'semantic-report.json').read_text())
        self.assertEqual((report['semantic_cases'],report['candidate_words'],report['caller_cases']),(1152,237,72))
if __name__=='__main__':unittest.main()
