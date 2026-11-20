"""Actor effect source, ABI, normal relation, native and strict image gates."""
import json,struct,unittest
from copy import deepcopy
from unittest.mock import patch
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as s
from tools.experiments import game_actor_randomized_effect_150f97ec_match as match
from tools.tests import game_actor_randomized_effect_150f97ec_oracle as guest
from tools.tests import game_actor_randomized_effect_150f97ec_native as native
from tools.tests.game_actor_randomized_effect_150f97ec_normalizer import independent_links,derive
from tools.tests.game_actor_randomized_effect_150f97ec_proof import prove,negative_controls
from tools import pad_c_object as pc,pad_generated_object as pg

class ActorRandomizedEffectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=s.screen();cls.blob,cls.refs=s.payload(s.WHERE/'candidate.o',s.FUNCTION);cls.words=s.bind(cls.blob,cls.refs)
        cls.rom=(s.ROOT/'conker/conker.us.bin').read_bytes();cls.retail=struct.unpack_from('>89I',cls.rom,s.ROM)
    def test_01_source_frame_neighbors_and_caller(self):
        r=self.report;self.assertEqual((r['words'],r['frame'],r['differences'],r['neighbors']),(88,112,77,16));self.assertTrue(r['pools_unchanged'])
        jal=struct.pack('>I',0x0C000000|((s.ENTRY>>2)&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom)-3,4)if self.rom[i:i+4]==jal],[0x55DC0])
        self.assertEqual([i for i in range(0,len(self.rom)-3,4)if self.rom[i:i+4]==struct.pack('>I',s.ENTRY)],[])
        self.assertEqual(struct.unpack_from('>5I',self.rom,0x55DBC),(0x93A50773,0x0D43E5FB,0x24060001,0x100004A2,0x24020001))
        self.assertEqual(struct.unpack_from('>I',self.rom,0x55CC0)[0],0x8FA40764)
        self.assertEqual(tuple(struct.unpack_from('>6I',self.rom,0x246708)),guest.VECS)
    def test_02_guest_full_private_and_provider_effects(self):
        r=guest.run(self.words);self.assertEqual((r['cases'],r['calls'],r['visited_words']),(768,4298,[88,89]))
        self.assertEqual(r['complete_final_memory_equal_cases'],768);self.assertEqual(r['private_boundaries_equal'],4298)
    def test_03_defined_native_sdk32(self):
        r=native.run();self.assertEqual(len(r['valid']),3);self.assertEqual(len(r['rejected']),3)
    def test_04_independent_derivation_and_normal_relation(self):
        r=independent_links();self.assertEqual((r['raw_words'],r['normalized_words'],r['retained_source_origins']),(88,89,88))
        self.assertEqual(len(r['independent_links']),2);self.assertEqual(r['duplicate_output_index'],13)
        self.assertEqual(s.bind(*derive(self.blob,self.refs)[:2]),self.retail)
        p=prove(self.words,self.retail);self.assertEqual(p['paths'],2);self.assertEqual(p['visited_words'],[88,89]);self.assertEqual(p['private_bytes'],124)
        (s.OUT/'proof.json').write_text(json.dumps(p,indent=2)+'\n')
        c=negative_controls(self.words,self.retail);self.assertEqual(c['effective_controls'],8);self.assertTrue(c['positive_T0_T1_reallocation'])
    def test_05_both_padders_actual_Make_and_strict_image(self):
        r=match.qualify();self.assertEqual((r['guard_rows'],r['insertions'],r['exclusions'],r['changed_bytes']),(28,1,0,310))
        self.assertTrue(r['strict_predicted_ELF_equal']);self.assertEqual(r['actual_Make']['commands'],5)
        path=match.WHERE/'proposed-guards.csv';report={}
        for name,module in(('layout',pc),('assembly',pg)):
            guards=module.load_word_patches(path,'generated_124920');rows={k:v for k,v in guards.items()if k[0]==s.FUNCTION};self.assertEqual(len(rows),28)
            controls=bindings=0
            def reject(changed,phrase):
                with patch.object(module,'load_word_patches',return_value=changed):
                    with self.assertRaisesRegex(ValueError,phrase):
                        if name=='layout':module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/retail_layout.us.txt','generated_124920',word_patches_path=path)
                        else:module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/asm/124920.s',filename='generated_124920',word_patches_path=path)
            for key,row in rows.items():
                bad=deepcopy(guards);bad[key]['expected']^=1;reject(bad,'stale word patch');controls+=1
                if row['expected_relocations']:
                    bad=deepcopy(guards);bad[key]['expected_relocations']=[('R_MIPS_26','func_150F97EC')];reject(bad,'stale relocations');bindings+=1
            report[name]=dict(expected_words_rejected=controls,expected_bindings_rejected=bindings)
        (s.OUT/'guard-controls.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main()
