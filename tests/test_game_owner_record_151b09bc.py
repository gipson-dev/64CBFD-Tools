"""Complete owner record construction, real copy loop, padders and strict image."""
import json
import unittest
from tools.experiments import game_owner_record_151b09bc_match as source
from tools.tests import game_owner_record_151b09bc_derive as normalizer
from tools.tests import game_owner_record_151b09bc_proof as proof
from tools.tests import game_owner_record_151b09bc_oracle as guest
from tools.tests import game_owner_record_151b09bc_native as native
from tools.tests import game_owner_record_151b09bc_callers as caller

class OwnerRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.state=source.prepare()

    def record(self,name,report):(source.OUT/name).write_text(json.dumps(report,indent=2)+'\n')

    def test_01_owner_padders_and_guard_controls(self):
        self.assertEqual(source.guard_controls(),206)
        self.assertEqual(len(source.PIN['guard_rows']),33)

    def test_02_complete_paths_copy_and_return(self):
        report=proof.main(self.state['raw_words'],self.state['retail_words'])
        self.assertEqual(report['raw_relation']['paths'],38)
        self.assertEqual(report['raw_relation']['private_and_incoming_bytes'],244)
        self.assertEqual(len(report['effective_negatives']),9)

    def test_03_guest_payload_and_actual_memcpy(self):
        report=guest.main(self.state['retail_words'],self.state['raw_words'],normalizer.derive(self.state['raw_words']))
        self.assertEqual(report['cases_per_stream'],928)
        self.assertEqual(report['target_coverage'],[114,114,114])
        self.assertEqual(report['actual_memcpy_words'],[11,11,11])

    def test_04_fresh_native32_and_controls(self):
        report=native.main()
        self.assertEqual(report['cases'],928)
        self.assertEqual(len(report['runs']),12)
        self.assertTrue(report['passes'])
        self.record('native-report.json',report)

    def test_05_original_caller_connections(self):
        report=caller.run((self.state['retail_words'],self.state['raw_words'],normalizer.derive(self.state['raw_words'])))
        self.assertEqual(len(report['effective_argument_controls']),3)
        self.assertEqual([r['cases_per_stream']for r in report['callers']],[104,104,104])
        self.record('caller-report.json',report)

    def test_06_actual_Make_and_strict_image(self):
        report=source.qualify_image()
        self.assertEqual(report['image']['strict_exclusions'],0)
        self.assertEqual(report['neighbors_unchanged'],15)
        self.assertTrue(report['all_other_6050_bodies_and_all_addresses_unchanged'])

if __name__=='__main__':unittest.main()
