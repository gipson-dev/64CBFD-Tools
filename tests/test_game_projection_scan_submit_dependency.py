"""Keep the qualified projection caller input coupled to its complete snapshot."""
import copy,unittest
from tools.experiments import game_actor_projection_scan_15036148_recovery as source

class ProjectionScanSubmitDependencyTests(unittest.TestCase):
    def test_original_inputs_remain_valid(self):
        for name,digest in source.SPEC['inputs'].items():
            self.assertTrue(source.input_matches({},name,digest))

    def test_exact_qualified_caller_snapshot_is_accepted(self):
        entry=source.SPEC['compatible_input_snapshots'][-1]
        self.assertIn(entry['snapshot'],source.SPEC['compatible_installed_snapshots'])
        self.assertEqual(set(entry['inputs']),{'conker/src/game/generated_CDE80.c'})
        for name,digest in entry['inputs'].items():
            self.assertNotEqual(digest,source.SPEC['inputs'][name])
            self.assertTrue(source.input_matches(entry['snapshot'],name,digest))

    def test_other_snapshots_or_caller_changes_are_rejected(self):
        entry=source.SPEC['compatible_input_snapshots'][-1]
        name,digest=next(iter(entry['inputs'].items()))
        self.assertFalse(source.input_matches({},name,digest))
        self.assertFalse(source.input_matches(entry['snapshot'],name,'0'*64))
        for field in entry['snapshot']:
            with self.subTest(field=field):
                changed=copy.deepcopy(entry['snapshot']);changed[field]='0'*64
                self.assertFalse(source.input_matches(changed,name,digest))
