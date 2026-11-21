"""Actor projection scan: source, ABI, schedule, native and entire-image gates."""
from copy import deepcopy
import json,struct,unittest
from unittest.mock import patch
from tools.experiments import game_actor_projection_scan_15036148_recovery as s
from tools.experiments import game_actor_projection_scan_15036148_match as match
from tools.tests import game_actor_projection_scan_15036148_oracle as guest
from tools.tests import game_actor_projection_scan_15036148_native as native
from tools.tests import game_actor_projection_scan_15036148_caller as caller
from tools.tests.game_actor_projection_scan_15036148_normalizer import derive,prove,independent_links
from tools import pad_c_object as pc,pad_generated_object as pg
class ActorProjectionScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen=s.screen();cls.blob,cls.refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION)
        cls.rom=(s.ROOT/'conker/conker.us.bin').read_bytes();cls.retail=struct.unpack_from('>112I',cls.rom,s.ROM)
    def test_01_complete_source_frame_owner_and_typed_interfaces(self):
        r=self.screen;self.assertEqual((r['words'],r['frame'],r['neighbors'],r['helper_words']),(112,152,8,7))
        self.assertTrue(r['helper_still_unrecovered']);self.assertEqual(r['caller_functions_unchanged'],16)
        self.assertEqual(r['unchanged_caller_Warning_712_count'],3);self.assertTrue(r['verified_pool'])
        words=struct.unpack('>112I',self.blob)
        self.assertEqual([words[i]&65535 for i in(35,36,37,71)],[142,144,146,146])
        for value,expected in((0x0D40D852,[0x46854]),(s.ENTRY,[]),(0x0D40D602,[0x63764,0xCE44C,0xCE480]),(0x15035808,[])):
            literal=struct.pack('>I',value);self.assertEqual([i for i in range(0,len(self.rom)-3,4)if self.rom[i:i+4]==literal],expected)
        self.assertEqual(struct.unpack_from('>2I',self.rom,0x637B8),(0,0))
    def test_02_original_assembly_and_independent_rebases(self):
        r=independent_links();self.assertEqual(r['retail_words'],112);self.assertEqual(len(r['independent_links']),2)
        self.assertTrue(r['HI16_LO16_carry']);self.assertEqual(s.bind(*derive(self.blob,self.refs)),self.retail)
        self.assertEqual(r['raw_binding_negative_controls'],['payload','binding'])
    def test_03_complete_packet_state_and_opaque_FCSR_relation(self):
        r=prove(self.blob,self.refs);self.assertEqual(r['changed_words'],6)
        self.assertTrue(r['all_other_instructions_and_branches_identical']);self.assertTrue(r['complete_block_state_equal'])
        c=r['symbolic_block_controls'];self.assertEqual(c['positive_schedules'],5040);self.assertEqual(len(c['effective_semantic_controls']),5)
        self.assertTrue(c['full_GPR_FPR_private_byte_state']);self.assertTrue(c['FCSR_opaque_unchanged'])
    def test_04_guest_mutations_signed_height_and_complete_memory(self):
        r=guest.run();self.assertEqual((r['cases'],r['calls']),(768,9952));self.assertEqual(r['visited_words'],[112,112])
        self.assertEqual(r['private_bytes'],168);self.assertEqual(r['private_call_boundaries_equal'],9952)
        self.assertEqual(r['complete_final_memory_equal_cases'],768);self.assertFalse(r['FCSR_emulation'])
    def test_05_defined_native_SDK32_and_effective_controls(self):
        r=native.run();self.assertEqual([v['cases']for v in r['valid']],[768]*3);self.assertEqual(len(r['rejected']),5)
        self.assertTrue(r['SDK32_offsets_checked']);self.assertEqual(r['complete_actor_objects'],26)
    def test_06_original_caller_continues_with_ignored_result(self):
        r=caller.run();self.assertEqual((r['cases'],r['logical_helper_calls'],r['actual_original_words']),(96,1244,4))
        self.assertTrue(r['following_original_call_executed']);self.assertTrue(r['complete_RAM_equal']);self.assertFalse(r['full_outer_caller_claim'])
    def test_07_both_padders_actual_Make_whole_image_and_guard_controls(self):
        r=match.qualify();self.assertEqual((r['guards'],r['changed_bytes'],r['exclusions']),(8,396,0))
        self.assertTrue(r['strict_predicted_ELF_equal']);self.assertTrue(r['caller_complete_padded_object_unchanged']);self.assertTrue(r['owner_Make_recipe_unchanged'])
        self.assertTrue(r['named_definitions_preserved']);self.assertEqual(r['metadata_permutation_bytes'],28)
        self.assertEqual([r['actual_Make'][n]['commands']for n in('target','caller')],[3,3])
        path=match.WHERE/'proposed-guards.csv';counts={}
        for label,module in(('layout',pc),('assembly',pg)):
            guards=module.load_word_patches(path,'generated_61D10');rows={k:v for k,v in guards.items()if k[0]==s.FUNCTION};self.assertEqual(len(rows),8)
            def reject(changed,phrase):
                with patch.object(module,'load_word_patches',return_value=changed):
                    with self.assertRaisesRegex(ValueError,phrase):
                        if label=='layout':module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=path)
                        else:module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=path)
            word_controls=binding_controls=0
            for key,row in rows.items():
                changed=deepcopy(guards);changed[key]['expected']^=1;reject(changed,'stale word patch');word_controls+=1
                if row['expected_relocations']:
                    changed=deepcopy(guards);changed[key]['expected_relocations']=[('R_MIPS_26',s.FUNCTION)];reject(changed,'stale relocations');binding_controls+=1
            counts[label]=dict(expected_words_rejected=word_controls,expected_bindings_rejected=binding_controls)
        (s.OUT/'guard-controls.json').write_text(json.dumps(counts,indent=2)+'\n')
if __name__=='__main__':unittest.main()
