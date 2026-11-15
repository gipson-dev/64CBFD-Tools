import os,subprocess,sys,unittest
from tools.experiments import game_selector_mask_1515942c_match as s

class SelectorMaskMatchTests(unittest.TestCase):
    def test_complete_qualification(self):
        s.main()
        env=dict(os.environ,CBFD_CONSUMER_ROOT=str(s.ROOT),SELECTOR_CANDIDATE=str(s.OUT/'qualified.o'),SELECTOR_EXPECTED_TRACE_DIFFS='0')
        for module in ('game_selector_mask_1515942c_proof','game_selector_mask_1515942c_match_guest',
                       'game_selector_mask_1515942c_connected','game_selector_mask_1515942c_caller',
                       'game_selector_mask_1515942c_controls','game_selector_mask_1515942c_stack_alias',
                       'game_selector_mask_1515942c_match_native'):
            subprocess.run([sys.executable,'-m','tools.tests.'+module],cwd=s.ROOT,env=env,check=True)
if __name__=='__main__':unittest.main()
