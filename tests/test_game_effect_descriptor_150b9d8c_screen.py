"""Keep the descriptor candidate private while its caller/alias gap is open."""
import json
import unittest

from tools.experiments import game_effect_descriptor_150b9d8c_screen as screen
from tools.tests import game_effect_descriptor_150b9d8c_connected as connected
from tools.tests import game_effect_descriptor_150b9d8c_oracle as guest


class EffectDescriptorScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.state=screen.prepare()

    def receipt(self,name,result):
        (screen.OUT/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')

    def test_candidate_and_independent_padders(self):
        self.assertEqual(screen.OUT.name,'game-effect-descriptor-150b9d8c-match')
        self.assertEqual(len(screen.MANIFEST['guard_rows']),4)
        self.assertEqual(screen.payload(self.state['retail']),screen.payload(self.state['generated']))
        self.assertEqual(screen.payload(self.state['retail']),screen.payload(self.state['generic']))

    def test_ordinary_cases_and_private_descriptor_bytes(self):self.receipt('ordinary',guest.ordinary(self.state))
    def test_stack_overlap_rejects_each_raw_candidate(self):self.receipt('aliases',guest.aliases(self.state))
    def test_original_rng_connection(self):self.receipt('rng',connected.actual_rng(self.state))
    def test_direct_caller_census(self):self.receipt('census',connected.caller_census())


if __name__=='__main__':unittest.main(verbosity=2)
