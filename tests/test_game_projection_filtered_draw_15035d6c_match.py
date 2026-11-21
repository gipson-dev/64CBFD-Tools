"""Filtered projection drawing: semantic C, both loops, ABI and whole image."""
from copy import deepcopy
import json,struct,unittest
from unittest.mock import patch
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as s
from tools.experiments import game_projection_filtered_draw_15035d6c_match as match
from tools.tests import game_projection_filtered_draw_15035d6c_oracle as guest
from tools.tests import game_projection_filtered_draw_15035d6c_native as native
from tools.tests import game_projection_filtered_draw_15035d6c_caller as caller
from tools.tests import game_projection_filtered_draw_15035d6c_proof as proof
from tools.tests import game_projection_filtered_draw_15035d6c_controls as controls
from tools.tests.game_projection_filtered_draw_15035d6c_normalizer import derive,independent_links
from tools import pad_c_object as pc,pad_generated_object as pg
class ProjectionFilteredDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen=s.screen();cls.blob,cls.refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION)
        cls.rom=(s.ROOT/'conker/conker.us.bin').read_bytes();cls.retail=struct.unpack_from('>159I',cls.rom,s.ROM)
    def test_01_complete_source_frame_neighbors_and_caller_census(self):
        r=self.screen;self.assertEqual((r['words'],r['frame'],r['neighbors']),(160,32,9))
        self.assertTrue(r['pools_unchanged']);self.assertTrue(r['submit_placeholder_unchanged'])
        for value,expected in((0x0D40D75B,[0x5ED64]),(0x0940D75B,[]),(s.ENTRY,[])):
            needle=struct.pack('>I',value);at=0;found=[]
            while True:
                at=self.rom.find(needle,at)
                if at<0:break
                if at%4==0:found.append(at)
                at+=1
            self.assertEqual(found,expected)
        self.assertIn('1u << (list & 31)',s.BODY)
    def test_02_original_assembly_independent_rebases_and_input_guards(self):
        r=independent_links();self.assertEqual(r['retail_words'],159);self.assertEqual(len(r['independent_links']),2)
        self.assertTrue(r['HI16_LO16_carry']);self.assertEqual(s.bind(*derive(self.blob,self.refs)[:2]),self.retail)
        self.assertEqual(r['raw_binding_negative_controls'],['payload','binding'])
    def test_03_inductive_outer_and_inner_loops_full_private_and_FCSR(self):
        r=proof.prove(s.bind(self.blob,self.refs),self.retail)
        self.assertEqual(r['paths'],dict(prefix=3,outer=12,inner=6));self.assertEqual(r['visited_words'],[160,159])
        self.assertEqual(r['full_private_bytes'],52);self.assertTrue(r['fifth_argument_home'])
        self.assertTrue(r['ordered_public_stores']);self.assertTrue(r['quiet_public_read_multiplicity'])
        self.assertTrue(r['opaque_full_FCSR']);self.assertEqual(r['alpha_range'],[0,254])
        self.assertEqual(r['alpha_domain_cases'],65536)
    def test_04_effective_symbolic_controls_and_alternate_scratch_allocation(self):
        r=controls.run();self.assertEqual(r['effective_controls'],8);self.assertTrue(r['positive_T6_T7_reallocation'])
    def test_05_guest_aliases_ordered_stores_and_complete_memory(self):
        r=guest.run();self.assertEqual((r['cases'],r['public_alias_cases']),(592,72))
        self.assertEqual(r['ordered_public_stores'],47074);self.assertEqual(r['visited_words'],[155,154])
        self.assertEqual(r['normal_unvisited_words'],[[106,107,108,109,110]]*2)
        self.assertEqual(r['complete_final_memory_equal_cases'],592)
    def test_06_defined_native_SDK32_objects_and_effective_controls(self):
        r=native.run();self.assertEqual([v['cases']for v in r['valid']],[520]*3)
        self.assertEqual(len(r['rejected']),6);self.assertTrue(r['SDK_macros'])
        self.assertEqual((r['record_extent'],r['list_extent']),(255,256))
    def test_07_original_caller_blue_delay_slot_and_cursor_consumption(self):
        r=caller.run();self.assertEqual(r['cases'],128);self.assertEqual(r['actual_original_caller_words'],8)
        self.assertTrue(r['original_JAL_and_blue_delay_store']);self.assertTrue(r['returned_cursor_consumed_by_original_S0_move'])
        self.assertFalse(r['full_caller_claim']);self.assertTrue(r['caller_C_body_still_unrecovered'])
    def test_08_both_padders_actual_Make_entire_image_and_stale_guards(self):
        r=match.qualify();self.assertEqual((r['guard_rows'],r['omissions'],r['insertions']),(29,1,0))
        self.assertEqual((r['changed_bytes'],r['exclusions'],r['function_slots']),(491,0,6051))
        self.assertTrue(r['strict_predicted_ELF_equal']);self.assertEqual(r['actual_Make']['commands'],3)
        self.assertEqual(r['unchanged_owner_functions'],9);self.assertTrue(r['protected_data']['exact'])
        path=match.WHERE/'proposed-guards.csv';counts={}
        for label,module in(('layout',pc),('assembly',pg)):
            guards=module.load_word_patches(path,'generated_61D10');rows={k:v for k,v in guards.items()if k[0]==s.FUNCTION};self.assertEqual(len(rows),29)
            def reject(changed,phrase):
                with patch.object(module,'load_word_patches',return_value=changed):
                    with self.assertRaisesRegex(ValueError,phrase):
                        if label=='layout':module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=path)
                        else:module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=path)
            words=bindings=0
            for key,row in rows.items():
                changed=deepcopy(guards);changed[key]['expected']^=1;reject(changed,'stale word patch');words+=1
                if row['expected_relocations']:
                    changed=deepcopy(guards);changed[key]['expected_relocations']=[('R_MIPS_26',s.FUNCTION)];reject(changed,'stale relocations');bindings+=1
            counts[label]=dict(expected_words_rejected=words,expected_bindings_rejected=bindings)
        (s.OUT/'guard-controls.json').write_text(json.dumps(counts,indent=2)+'\n')
if __name__=='__main__':unittest.main()
