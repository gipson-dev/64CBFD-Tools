"""Keep the refined particle normalization private while qualifying its derivation."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_configurable_particle_15175390_normalization as source

class ConfigurableParticle15175390NormalizationTests(unittest.TestCase):
    def test_private_normalization(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/1B0740.s','conker/include/functions.h','conker/asm/data/24BC30.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_configurable_particle_15175390_normalization','tools.tests.game_configurable_particle_15175390_normalization_oracle'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        out=root/source.BUILD
        report=json.loads((out/'normalization-report.json').read_text())
        self.assertEqual((report['words'],report['frame'],report['raw_differences'],report['normalized_differences'],report['neighbors'],report['named_bindings'],report['corruption_controls']),(370,184,219,0,8,27,397))
        self.assertEqual(report['proof']['query_branch_cases'],54)
        self.assertFalse(report['installed']);self.assertEqual(report['c_match_credit'],0)
        report=json.loads((out/'semantic-report.json').read_text())
        self.assertEqual((report['semantic_cases'],report['directed_source_cases'],report['source_streams'],report['retail_and_normalized_unwritten_cases']),(1152,63,3,24))
        self.assertEqual(len(report['source_guest_boundaries']),8)
        self.assertEqual(len(report['effective_source_controls']),3)
        self.assertEqual(report['normalized_differences'],0)
        self.assertFalse(report['installed']);self.assertEqual(report['c_match_credit'],0)

if __name__=='__main__':unittest.main()
