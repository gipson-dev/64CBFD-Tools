import os,subprocess,sys,unittest
from tools.experiments import game_side_effect_update_1519f4f0_match as s

class SideEffectUpdateTests(unittest.TestCase):
    def test_complete_qualification(self):
        s.main();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT))
        for suffix in ('proof','oracle','callers','native'):
            subprocess.run([sys.executable,'-m','tools.tests.game_side_effect_update_1519f4f0_'+suffix],cwd=s.ROOT,env=env,check=True)
if __name__=='__main__':unittest.main()
