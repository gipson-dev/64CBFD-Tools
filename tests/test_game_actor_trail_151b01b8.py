"""Actor trail source, full-path relation, concrete execution and strict image."""
import json
import unittest
from tools.experiments import game_actor_trail_151b01b8_match as source
from tools.tests import game_actor_trail_151b01b8_derive as normalizer
from tools.tests import game_actor_trail_151b01b8_proof as proof
from tools.tests import game_actor_trail_151b01b8_oracle as guest
from tools.tests import game_actor_trail_151b01b8_native as native
from tools.tests import game_actor_trail_151b01b8_callers as caller

class ActorTrailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=source.prepare()

    def record(self,name,report):
        (source.OUT/name).write_text(json.dumps(report,indent=2)+'\n')

    def test_01_owner_padders_and_guard_controls(self):
        self.assertEqual(source.guard_controls(),312)
        self.assertEqual(len(source.PIN['guard_rows']),50)

    def test_02_complete_private_and_call_relation(self):
        report=proof.main(self.state['raw_words'],self.state['retail_words'])
        self.assertEqual(report['raw_relation']['paths'],16)
        self.assertEqual(report['raw_relation']['private_and_incoming_bytes'],176)
        self.assertEqual(len(report['effective_negatives']),7)

    def test_03_guest_wrap_and_retained_mutations(self):
        report=guest.main(self.state['retail_words'],self.state['raw_words'],normalizer.derive(self.state['raw_words']))
        self.assertEqual(report['cases_per_stream'],912)
        self.assertEqual(report['coverage'],[128,128,128])

    def test_04_fresh_native32_and_controls(self):
        report=native.main()
        self.assertEqual(report['cases'],912)
        self.assertEqual(len(report['runs']),11)
        self.assertTrue(report['passes'])
        self.record('native-report.json',report)

    def test_05_original_caller_prefix_and_wrappers(self):
        report=caller.run((self.state['retail_words'],self.state['raw_words'],normalizer.derive(self.state['raw_words'])))
        self.assertEqual(len(report['callers']),3)
        self.assertEqual(len(report['effective_argument_controls']),3)
        self.assertEqual([r['cases_per_stream'] for r in report['callers']],[112,112,112])
        self.record('caller-report.json',report)

    def test_06_actual_Make_and_strict_image(self):
        report=source.qualify_image()
        self.assertEqual(report['image']['strict_exclusions'],0)
        self.assertEqual(report['neighbors_unchanged'],15)
        self.assertTrue(report['all_other_6050_bodies_and_all_addresses_unchanged'])

if __name__=='__main__':unittest.main()
