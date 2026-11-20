"""Behavioral recovery gates; intentionally no byte-match/install credit."""
import json,struct,unittest
from tools.experiments import game_list_render_1517e28c_recovery as s
from tools.tests import game_list_render_1517e28c_oracle as guest
from tools.tests import game_list_render_1517e28c_native as native
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset

class ListRenderRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=s.screen()
        raw,refs=s.payload(s.OUT/'banked-screen/candidate.o',s.FUNCTION)
        cls.words=s.bind(raw,refs)
        cls.retail=struct.unpack_from('>135I',(s.ROOT/'conker/conker.us.bin').read_bytes(),s.ROM)

    def test_01_complete_owner_and_typed_caller(self):
        r=self.receipt
        self.assertEqual((r['words'],r['frame'],r['positional_differences']),(132,120,76))
        self.assertEqual(r['unchanged_neighbors'],7)
        self.assertGreater(r['typed_caller_functions_unchanged'],0)
        self.assertEqual(r['caller_existing_warnings_unchanged'],3)
        self.assertTrue(r['pools_unchanged'])
        self.assertEqual((r['installed'],r['matching_credit']),(False,0))
        self.assertNotEqual(self.words,self.retail)

    def test_02_bounded_guest_with_retained_depth_and_helper_mutation(self):
        report=guest.run(self.words,self.retail)
        self.assertEqual(report['cases'],1024)
        self.assertEqual(report['complete_private_equal_cases'],1024)
        self.assertEqual(report['visited_words'],[132,134])
        self.assertEqual(report['retail_unreachable_word_indices'],[91])
        (s.OUT/'banked-guest.json').write_text(json.dumps(report,indent=2)+'\n')

    def test_03_effective_instruction_controls(self):
        def one(predicate):
            hits=[i for i,w in enumerate(self.words)if predicate(w)]
            self.assertEqual(len(hits),1,hits)
            return hits[0]
        threshold=one(lambda w:w>>26==10 and w&65535==30)
        output=one(lambda w:w>>26==9 and w>>21&31==29 and w>>16&31==5 and w&65535==0x6C)
        flags=[i for i,w in enumerate(self.words)if w>>26==12 and w>>21&31==2 and w&65535==2]
        self.assertEqual(flags,[76,89])
        clear=one(lambda w:w>>26==40 and w>>21&31==3 and w>>16&31==0)
        controls={'inclusive-depth':[(threshold,self.words[threshold]+1)],
            'wrong-output-home':[(output,self.words[output]+4)],
            'wrong-intensity-mask':[(i,(self.words[i]&0xFFFF0000)|1)for i in flags],
            'missing-intensity-clear':[(clear,0)]}
        for name,changes in controls.items():
            words=list(self.words)
            for index,value in changes:self.assertNotEqual(words[index],value);words[index]=value
            with self.assertRaises(AssertionError,msg=name):guest.run(words,self.retail)
        (s.OUT/'banked-instruction-controls.json').write_text(json.dumps(list(controls))+'\n')

    def test_04_native_sdk32_defined_initial_output_domain(self):
        report=native.run()
        self.assertEqual(len(report['valid']),3)
        self.assertEqual(len(report['rejected']),3)

    def test_05_original_readonly_tables_and_caller_census(self):
        census=s.census()
        self.assertEqual(census['readonly_selector_words'],[0,0x8008CFF0])
        self.assertEqual(census['readonly_palette_bytes'],'0001000007030000011e0000')
        self.assertEqual(len(census['aligned_JAL_ROM_offsets']),1)
        self.assertEqual(census['aligned_literal_ROM_offsets'],[])
        image=(s.ROOT/'conker/build/conker.us.elf').read_bytes()
        offset=elf_slot_offset(image,0x8008CFF0,32)
        rom=(s.ROOT/'conker/conker.us.bin').read_bytes()
        self.assertEqual(image[offset:offset+32],rom[0x231AB0:0x231AD0])
        (s.OUT/'banked-caller-census.json').write_text(json.dumps(census,indent=2)+'\n')

if __name__=='__main__':unittest.main()
