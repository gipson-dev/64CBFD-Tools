"""Recovered source, packet ABI, native32 and both full-owner padders."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_effect_dispatch_15183290_match as source
class EffectDispatch15183290MatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
        paths=(source.SOURCE,'conker/asm/1B0740.s','conker/asm/CDE80.s','conker/asm/data/24BD90.rodata.s','conker/build/conker.us.elf','conker/progress.csv','conker/Makefile','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_effect_dispatch_15183290_match','tools.tests.game_effect_dispatch_15183290_padder','tools.tests.game_effect_dispatch_15183290_oracle','tools.tests.game_effect_dispatch_15183290_native'):
            p=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,module+'\n'+p.stdout+'\n'+p.stderr);print(module+': '+p.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'guest-report.json').read_text())
        self.assertEqual((report['guest_cases'],report['visited_words'],report['caller_cases']),(1216,392,72))
if __name__=='__main__':unittest.main()
