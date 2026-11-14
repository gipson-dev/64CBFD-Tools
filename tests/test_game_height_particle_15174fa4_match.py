"""Full source, guest/native, caller and owner qualification without production writes."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_height_particle_15174fa4_match as source
class HeightParticle15174FA4MatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/1B0740.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_height_particle_15174fa4_match','tools.tests.game_height_particle_15174fa4_padder','tools.tests.game_height_particle_15174fa4_oracle','tools.tests.game_height_particle_15174fa4_native'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'semantic-report.json').read_text());self.assertEqual((report['semantic_cases'],report['caller_cases'],report['zero_width_traps']),(1152,48,4))
if __name__=='__main__':unittest.main()
