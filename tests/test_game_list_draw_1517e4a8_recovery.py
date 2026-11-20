"""Private recovery gates; no raw byte-match, adoption or gameplay credit."""
import json,struct,unittest
from tools.experiments import game_list_draw_1517e4a8_recovery as s
from tools.tests import game_list_draw_1517e4a8_oracle as guest
from tools.tests import game_list_draw_1517e4a8_native as native

class ListDrawRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=s.screen();raw,refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION);cls.words=s.bind(raw,refs)
    def test_01_complete_source_typed_helper_and_census(self):
        r=self.report;self.assertEqual((r['words'],r['frame'],r['positional_differences']),(361,184,162))
        self.assertEqual((r['unchanged_owner_neighbors'],r['unchanged_helper_functions']),(7,19));self.assertTrue(r['pools_unchanged'])
        self.assertFalse(r['source_installed']);self.assertEqual(r['matching_credit'],0)
        rom=(s.ROOT/'conker/conker.us.bin').read_bytes();jal=struct.pack('>I',0x0C000000|((s.ENTRY>>2)&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal],[0x1AB8F8])
        self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==struct.pack('>I',s.ENTRY)],[])
        self.assertEqual(rom[0x24BD10:0x24BD20],guest.TABLE)
    def test_02_guest_original_init_and_wrapper(self):
        r=guest.run(self.words);self.assertEqual((r['cases'],r['calls'],r['visited_words']),(1104,953,[347,347]))
        self.assertTrue(r['private_difference_only_unpassed_counter_homes']);self.assertEqual(r['packet_offsets'],[(0,-60),(1,-60)])
    def test_03_effective_instruction_controls(self):
        cutoff=[i for i,w in enumerate(self.words)if w==0x34210D40];self.assertEqual(len(cutoff),1)
        alpha=[i for i,w in enumerate(self.words)if w>>26==40 and w>>21&31==29 and w&65535==0x86];self.assertEqual(len(alpha),1)
        loads=[(i,w>>16&31)for i,w in enumerate(self.words)if w>>26==35 and w>>21&31==29 and w&65535==0xCC]
        self.assertGreater(len(loads),0);loaded,register=loads[0]
        strength=[i for i,w in enumerate(self.words)if i>loaded and w>>26 in(4,5)and w>>21&31==register and w>>16&31==1]
        self.assertGreater(len(strength),0)
        controls={'wrong-distance-cutoff':(cutoff[0],self.words[cutoff[0]]+1),'wrong-alpha-home':(alpha[0],self.words[alpha[0]]+1),
            'wrong-strength-gate':(strength[0],self.words[strength[0]]^(1<<26))}
        for name,(index,w)in controls.items():
            other=list(self.words);self.assertNotEqual(other[index],w);other[index]=w
            with self.assertRaises(AssertionError,msg=name):guest.run(tuple(other))
        (s.OUT/'instruction-controls.json').write_text(json.dumps(list(controls))+'\n')
    def test_04_defined_native_sdk32(self):
        r=native.run();self.assertEqual(len(r['valid']),3);self.assertEqual(len(r['rejected']),3)
    def test_05_both_padders_and_real_Make(self):
        r=s.integration();self.assertTrue(r['padders_equal']);self.assertTrue(r['helper_complete_padded_object_unchanged'])
        self.assertEqual(r['matching_credit'],0)

if __name__=='__main__':unittest.main()
