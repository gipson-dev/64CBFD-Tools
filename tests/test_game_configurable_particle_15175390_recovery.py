"""Private reconstruction milestone with unchanged production inputs and no matching credit."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_configurable_particle_15175390_recovery as source
class ConfigurableParticle15175390RecoveryTests(unittest.TestCase):
    def test_private_recovery(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/1B0740.s','conker/include/functions.h','conker/asm/data/24BC30.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_configurable_particle_15175390_recovery','tools.tests.game_configurable_particle_15175390_oracle','tools.tests.game_configurable_particle_15175390_controls'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True);self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'semantic-report.json').read_text());self.assertEqual((report['semantic_cases'],report['directed_source_cases'],report['word_differences'],report['c_match_credit']),(1152,63,201,0))
if __name__=='__main__':unittest.main()
