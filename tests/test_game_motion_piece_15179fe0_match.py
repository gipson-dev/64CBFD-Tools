"""Direct C, caller ABI, native32, padders and immutable production state."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,unittest
from tools.experiments import game_motion_piece_15179fe0_match as source
class MotionPiece15179FE0MatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();paths=(source.SOURCE,'conker/asm/1A7260.s','conker/asm/1B0740.s','conker/build/conker.us.elf','conker/progress.csv','conker/retail_word_patches.us.csv')
        before={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths};env=dict(os.environ,CBFD_CONSUMER_ROOT=str(root))
        for module in ('tools.experiments.game_motion_piece_15179fe0_match','tools.tests.game_motion_piece_15179fe0_padder','tools.tests.game_motion_piece_15179fe0_oracle','tools.tests.game_motion_piece_15179fe0_native','tools.tests.game_motion_piece_15179fe0_lifecycle'):
            q=subprocess.run([sys.executable,'-m',module],cwd=root,env=env,capture_output=True,text=True);self.assertEqual(q.returncode,0,module+'\n'+q.stdout+'\n'+q.stderr);print(module+': '+q.stdout.strip(),flush=True)
        self.assertEqual(before,{p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths})
        report=json.loads((root/source.BUILD/'behavior.json').read_text());self.assertEqual((report['valid_cases'],report['predivision_zero_prefixes'],report['caller_cases']),(3654,38,96))
if __name__=='__main__':unittest.main()
