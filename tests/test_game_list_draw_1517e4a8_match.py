"""Full private matching gates; source adoption is a separate production gate."""
import json,struct
from tools.tests.test_game_list_draw_1517e4a8_recovery import ListDrawRecoveryTests
from tools.tests.game_list_draw_1517e4a8_normalizer import independent_links,derive,OUT
from tools.tests.game_list_draw_1517e4a8_proof import prove,negative_controls
from tools.experiments import game_list_draw_1517e4a8_recovery as s
from tools.experiments.game_list_draw_1517e4a8_match import qualify,guard_controls
from tools.tests import game_list_draw_1517e4a8_oracle as guest

class ListDrawMatchTests(ListDrawRecoveryTests):
    def test_06_closed_derivation_and_independent_links(self):
        r=independent_links()
        self.assertEqual((r['raw_words'],r['output_words'],r['retained_unique_origins']),(361,361,359))
        self.assertEqual(r['omitted_origins'],[42,85]);self.assertEqual(len(r['independent_GNU_links']),2)
    def test_07_inductive_normal_execution_relation(self):
        truth=struct.unpack_from('>361I',(s.ROOT/'conker/conker.us.bin').read_bytes(),s.ROM)
        r=prove(self.words,truth,('prefix','symbolic-loop','loop'))
        self.assertEqual([r['paths'][f'prefix/g{g}/k{k}/i0/n1']for g in(0,1)for k in(0,1)],[432,6048,432,6048])
        self.assertEqual(r['visited_words'],[352,352]);self.assertTrue(all(x['unvisited_words_accounted_for']for x in r['coverage_accounting']))
        c=negative_controls(self.words,truth);self.assertEqual(c['effective_semantic_controls'],9)
    def test_08_padders_actual_Make_and_whole_image(self):
        r=qualify();self.assertTrue(r['strict_predicted_ELF_equal'])
        self.assertEqual((r['guard_rows'],r['exclusions'],r['function_slots'],r['changed_bytes']),(162,0,6051,1068))
        self.assertTrue(r['helper_complete_padded_object_unchanged'])
        c=guard_controls();self.assertTrue(c['all_controls_rejected'])
        self.assertEqual(c['padders'],{x:{'expected_word_controls':162,'expected_binding_controls':12}for x in('layout','assembly')})
    def test_09_normalized_full_guest_memory(self):
        raw,refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION);derived,bindings,_=derive(raw,refs)
        r=guest.run(s.bind(derived,bindings));self.assertEqual(r['complete_private_equal_cases'],1104)
        self.assertIsNone(r['first_private_difference'])
        (OUT/'normalized-guest.json').write_text(json.dumps(r,indent=2)+'\n')

del ListDrawRecoveryTests
if __name__=='__main__':
    import unittest
    unittest.main()
