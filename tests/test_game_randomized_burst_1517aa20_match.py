"""Direct C, caller ABI, native32, padders and immutable production state."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_randomized_burst_1517aa20_match as source
class RandomizedBurst1517AA20MatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();paths=(source.SOURCE,'conker/asm/1A7260.s','conker/asm/1B0740.s','conker/build/conker.us.elf','conker/progress.csv','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_randomized_burst_1517aa20_match','tools.tests.game_randomized_burst_1517aa20_padder','tools.tests.game_randomized_burst_1517aa20_oracle','tools.tests.game_randomized_burst_1517aa20_native'):
            q=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True);self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'behavior.json').read_text());self.assertEqual((report['cases'],report['caller_cases']),(832,36))
if __name__=='__main__':unittest.main()
