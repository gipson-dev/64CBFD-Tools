import os,subprocess,sys,unittest
from tools.experiments import game_perpendicular_offset_1519ef90_match as s

class PerpendicularOffsetMatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        s.main();env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT))
        for module in ('game_perpendicular_offset_1519ef90_proof','game_perpendicular_offset_1519ef90_oracle',
                       'game_perpendicular_offset_1519ef90_callers','game_perpendicular_offset_1519ef90_boundaries',
                       'game_perpendicular_offset_1519ef90_native'):
            subprocess.run([sys.executable,'-m','tools.tests.'+module],cwd=s.ROOT,env=env,check=True)
if __name__=='__main__':unittest.main()
