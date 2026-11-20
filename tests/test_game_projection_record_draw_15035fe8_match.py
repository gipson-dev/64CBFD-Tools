"""Complete record draw source, normal relation and strict linked-image gates."""
from copy import deepcopy
import json,struct,unittest
from unittest.mock import patch
from tools.experiments import game_projection_record_draw_15035fe8_recovery as s
from tools.experiments import game_projection_record_draw_15035fe8_match as match
from tools.tests import game_projection_record_draw_15035fe8_oracle as guest
from tools.tests import game_projection_record_draw_15035fe8_native as native
from tools.tests import game_projection_record_draw_15035fe8_caller as caller
from tools.tests.game_projection_record_draw_15035fe8_normalizer import derive,independent_links
from tools.tests.game_projection_record_draw_15035fe8_proof import prove,negative_controls,bound_lemma
from tools import pad_c_object as pc,pad_generated_object as pg

class ProjectionRecordDrawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.screen=s.screen();cls.blob,cls.refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION)
        cls.words=s.bind(cls.blob,cls.refs);cls.rom=(s.ROOT/'conker/conker.us.bin').read_bytes()
        cls.retail=struct.unpack_from('>88I',cls.rom,s.ROM)
    def test_01_complete_source_frame_owner_and_caller_ABI(self):
        r=self.screen;self.assertEqual((r['words'],r['frame'],r['parameters_offset'],r['neighbors']),(90,104,84,9))
        self.assertEqual(r['caller_functions_unchanged'],16);self.assertEqual(r['unchanged_caller_Warning_712_count'],3)
        self.assertTrue(r['pools_unchanged']);self.assertEqual(r['diagnostics'],'')
        for value,expected in((0x0D40D7FA,[0x46C54]),(s.ENTRY,[])):
            word=struct.pack('>I',value);self.assertEqual([i for i in range(0,len(self.rom)-3,4)if self.rom[i:i+4]==word],expected)
        self.assertEqual(struct.unpack_from('>3I',self.rom,0x46C50),(0x00402025,0x0D40D7FA,0x02202825))
    def test_02_closed_derivation_independent_links_and_bound_lemma(self):
        r=independent_links();self.assertEqual((r['raw_words'],r['retail_words'],r['retained_unique_origins']),(90,88,81))
        self.assertEqual(len(r['omitted_origins']),9);self.assertEqual(len(r['cloned_origins']),7)
        self.assertEqual(len(r['independent_links']),2);self.assertTrue(r['HI16_LO16_carry_context'])
        self.assertEqual(s.bind(*derive(self.blob,self.refs)[:2]),self.retail)
        b=bound_lemma();self.assertEqual(b['positive_byte_counts'],255);self.assertEqual(b['independent_checks'],1275)
    def test_03_prefix_and_inductive_loop_full_private_relation(self):
        r=prove(self.words,self.retail);self.assertEqual(r['paths'],dict(prefix=3,loop=4))
        self.assertEqual(r['visited_words'],[90,88]);self.assertEqual(r['full_private_bytes'],112)
        (s.OUT/'proof.json').write_text(json.dumps(r,indent=2)+'\n')
        c=negative_controls(self.words,self.retail);self.assertEqual(c['effective_controls'],9);self.assertTrue(c['positive_T0_T1_reallocation'])
    def test_04_guest_mutable_records_aliases_and_complete_RAM(self):
        r=guest.run();self.assertEqual((r['cases'],r['calls'],r['public_alias_cases']),(1080,4170,48))
        self.assertEqual(r['visited_words'],[90,88]);self.assertEqual(r['complete_final_memory_equal_cases'],1080)
        self.assertEqual(r['private_boundaries_equal'],4170);self.assertEqual(r['private_bytes'],112)
    def test_05_defined_native_SDK32_and_controls(self):
        r=native.run();self.assertEqual([v['cases']for v in r['valid']],[1024]*3);self.assertEqual(len(r['rejected']),4)
    def test_06_original_caller_window_consumes_returned_cursor(self):
        r=caller.run();self.assertEqual((r['cases'],r['logical_draw_calls'],r['actual_original_caller_words']),(96,381,10))
        self.assertTrue(r['returned_cursor_consumed_by_original_matrix_stores']);self.assertFalse(r['full_caller_claim'])
    def test_07_both_target_padders_actual_Make_and_whole_image(self):
        r=match.qualify();self.assertEqual((r['guard_rows'],r['insertions'],r['omissions'],r['changed_bytes'],r['exclusions']),(46,7,9,286,0))
        self.assertTrue(r['strict_predicted_ELF_equal']);self.assertTrue(r['caller_complete_padded_object_unchanged'])
        self.assertEqual([r['actual_Make'][n]['commands']for n in('target','caller')],[3,3])
        path=match.WHERE/'proposed-guards.csv';counts={}
        for label,module in(('layout',pc),('assembly',pg)):
            guards=module.load_word_patches(path,'generated_61D10');rows={k:v for k,v in guards.items()if k[0]==s.FUNCTION}
            self.assertEqual(len(rows),46);words=bindings=0
            def reject(changed,phrase):
                with patch.object(module,'load_word_patches',return_value=changed):
                    with self.assertRaisesRegex(ValueError,phrase):
                        if label=='layout':module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=path)
                        else:module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=path)
            for key,row in rows.items():
                changed=deepcopy(guards);changed[key]['expected']^=1;reject(changed,'stale word patch');words+=1
                if row['expected_relocations']:
                    changed=deepcopy(guards);changed[key]['expected_relocations']=[('R_MIPS_26',s.FUNCTION)];reject(changed,'stale relocations');bindings+=1
            counts[label]=dict(expected_words_rejected=words,expected_bindings_rejected=bindings)
        (s.OUT/'guard-controls.json').write_text(json.dumps(counts,indent=2)+'\n')

if __name__=='__main__':unittest.main()
