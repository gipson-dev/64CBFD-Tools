"""Projection submission: guarded exact C, opaque providers and complete image."""
import unittest
from tools.experiments import game_projection_submit_15035808_recovery as s
from tools.experiments import game_projection_submit_15035808_match as match
from tools.tests import game_projection_submit_15035808_normal_form as normal
from tools.tests import game_projection_submit_15035808_links as links
from tools.tests import game_projection_submit_15035808_validate as validate
from tools.tests import game_projection_submit_15035808_proof as proof
from tools.tests import game_projection_submit_15035808_controls as controls
from tools.tests import game_projection_submit_15035808_guest as guest
from tools.tests import game_projection_submit_15035808_native as native
from tools.tests import game_projection_submit_15035808_caller as caller
from tools.tests import game_projection_submit_15035808_abi as abi

class ProjectionSubmitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=s.screen()
        normal.run(source=s.WHERE/'candidate.o',label='matrix-normal-form')
    def test_01_source_owner_frame_pool_and_typed_caller(self):
        self.assertEqual((self.source['words'],self.source['frame'],self.source['neighbors'],self.source['caller_functions']),(345,216,9,28))
        self.assertTrue(self.source['pools_unchanged'])
        self.assertTrue(self.source['caller_padded_assembly_unchanged'])
    def test_02_original_assembly_relocations_and_closed_derivation(self):
        r=links.run();self.assertTrue(r['original_GNU_body_matches_retail_345_words'])
        r=validate.run();self.assertEqual((r['byte_exact_words'],r['relocation_sites']),(345,32))
        self.assertEqual(r['effective_input_controls'],['payload','binding','plan']);self.assertEqual(r['output_words_stored_in_plan'],0)
    def test_03_inductive_prefix_and_both_descriptor_lifetimes(self):
        r=proof.run(label='packaged-transfer-proof');self.assertTrue(r['equivalent'])
        self.assertEqual([r[p]['joint_paths']for p in('prefix','first-loop','retained-loop')],[78,31,31])
        self.assertTrue(r['ordered_FP_and_FCSR']);self.assertTrue(r['all_256_private_incoming_bytes'])
        self.assertEqual([v['unvisited_offsets']for v in r['coverage'].values()],[[],[]])
    def test_04_effective_instruction_defects_and_positive_color(self):
        r=controls.run();self.assertEqual((r['negative_controls'],r['positive_controls']),(6,1))
        self.assertTrue(r['controls']['positive-f6-to-f14']['passed'])
    def test_05_guest_packets_all_private_bytes_and_public_memory(self):
        r=guest.run(normalized=True,label='packaged-guest')
        self.assertEqual((r['cases'],r['calls'],r['allocations']),(1084,6908,877))
        self.assertEqual((r['equal_call_frames'],r['equal_final_frames']),(6908,1084))
        self.assertEqual(r['private_call_offsets'],{});self.assertEqual(r['private_return_offsets'],{})
    def test_06_native_defined_SDK_objects_and_source_controls(self):
        r=native.run(label='packaged-native');self.assertEqual([v['cases']for v in r['valid']],[1084]*3)
        self.assertEqual(len(r['rejected']),6)
    def test_07_actual_three_caller_windows_and_delay_controls(self):
        r=caller.run();self.assertEqual(r['cases'],822);self.assertTrue(r['all_three_actual_call_sites'])
        self.assertEqual([v['actual_window_words']for v in r['callers']],[10,21,11])
        self.assertTrue(all(v['effective_missing_delay_control']and not v['full_caller_claim']for v in r['callers']))
    def test_08_original_unused_result_ABI_and_negative_controls(self):
        r=abi.run();self.assertEqual(len(r['effective_result_read_controls']),3)
        self.assertEqual(r['unchanged_caller_functions'],28)
    def test_09_both_padders_actual_Make_and_strict_entire_image(self):
        r=match.qualify();self.assertEqual((r['guard_rows'],r['insertions'],r['omissions']),(316,0,0))
        self.assertEqual((r['changed_bytes'],r['exclusions'],r['function_slots']),(1050,0,6051))
        self.assertTrue(r['strict_predicted_ELF_equal']);self.assertTrue(r['protected_data_audit']['exact'])
        self.assertEqual(r['actual_Make']['commands'],3)
        self.assertEqual(r['caller_actual_Make']['commands'],5);self.assertTrue(r['caller_actual_Make']['mixed_GLOBAL_ASM_recipe'])
        self.assertTrue(r['complete_padded_caller_object_unchanged'])
