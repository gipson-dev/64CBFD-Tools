"""Complete focused qualification without mutating the consumer's production inputs."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_configurable_particle_15175390_match as source

class ConfigurableParticle15175390MatchTests(unittest.TestCase):
    def test_match(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1A20A0.s','conker/asm/1B0740.s','conker/include/functions.h','conker/asm/data/24BC30.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        modules=('tools.experiments.game_configurable_particle_15175390_match','tools.tests.game_configurable_particle_15175390_match_oracle','tools.tests.game_configurable_particle_15175390_native','tools.tests.game_configurable_particle_15175390_callers','tools.tests.game_configurable_particle_15175390_padder')
        for module in modules:
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr)
            print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        out=root/source.BUILD
        r=json.loads((out/'raw-report.json').read_text());self.assertEqual((r['words'],r['frame'],r['guards'],r['neighbors'],r['corruption_controls']),(370,184,219,8,397))
        r=json.loads((out/'semantic-report.json').read_text());self.assertEqual((r['semantic_cases'],r['directed_source_cases'],r['source_streams'],r['retail_and_normalized_unwritten_cases'],r['normalized_differences']),(1152,63,3,24,0));self.assertEqual(len(r['source_guest_boundaries']),8);self.assertEqual(len(r['effective_source_controls']),3)
        r=json.loads((out/'native-report.json').read_text());self.assertEqual([(v['cases'],v['record_bytes_compared']) for v in r[:3]],[(639,992)]*3);self.assertEqual(r[-1]['effective_semantic_controls'],3)
        r=json.loads((out/'caller-report.json').read_text());self.assertEqual((r['caller_cases'],len(r['sites']),r['memory_prefixes'],r['connected_ground_failure_cases'],r['ground_failure_words']),(720,5,363,48,19))
        r=json.loads((out/'padder-report.json').read_text());self.assertEqual((r['padders'],r['layouts'],r['gnu_links'],r['owner_functions'],r['guards']),(2,4,12,9,219))

if __name__=='__main__':unittest.main()
