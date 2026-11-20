"""Map-edge CFG/FCSR guards, native semantics and strict full-image integration."""
import csv,json,subprocess,unittest
from tools.experiments import game_map_edge_emitter_151050b0_match as match
from tools.tests import test_game_map_edge_emitter_151050b0_recovery as recovered
from tools.tests.game_map_edge_emitter_151050b0_relation import Relation,negative_controls
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
SYMS={n:int(n.split('_')[1],16)for bindings in match.SPEC['refs'].values()for _,n in bindings}
class MapEdgeMatchTests(unittest.TestCase):
    # Reuse the four semantic checks. The recovery-only "layout still open"
    # boundary is replaced by the matching, installed-state and image gates.
    receipt=recovered.MapEdgeRecoveryTests.receipt
    test_02_guest_public_state_packet_fields_and_ordered_FP=recovered.MapEdgeRecoveryTests.test_02_guest_public_state_packet_fields_and_ordered_FP
    test_03_connected_original_callback_dispatcher=recovered.MapEdgeRecoveryTests.test_03_connected_original_callback_dispatcher
    test_04_fired_public_prefixes_and_effective_instruction_controls=recovered.MapEdgeRecoveryTests.test_04_fired_public_prefixes_and_effective_instruction_controls
    test_05_actual_native_SDK32_and_exhaustive_RNG_index_domain=recovered.MapEdgeRecoveryTests.test_05_actual_native_SDK32_and_exhaustive_RNG_index_domain
    @classmethod
    def setUpClass(cls):cls.p=match.prepare()
    def test_01_complete_owner_profile_pools_neighbors_and_inputs(self):
        q=self.p['report'];self.assertEqual((q['body_words'],q['raw_words'],q['frame'],q['guards'],q['insertions'],q['omissions'],q['unchanged_raw_neighbors']),(279,275,208,43,4,0,10))
        self.assertEqual(q['matching_credit'],int(q['source_installed']));self.assertTrue(q['ELF_identical']);self.assertEqual(q['new_diagnostics'],0)
        self.receipt('packing-certificate',match.packing_certificate(self.p['truth'],self.p['words']))
    def test_07_complete_CFG_FCSR_relation_and_effective_controls(self):
        a,b=self.p['truth'],self.p['words'];v=Relation(a,b).run()
        self.assertEqual((v['CFG_nodes'],v['CFG_edges'],v['worklist_steps']),(113,122,160))
        self.assertEqual(v['structurally_reachable_words'],[276,272]);self.assertEqual(v['unreachable_offsets'],[[96,584,768],[92,572,756]])
        for words in(a,b):self.assertTrue(Relation(words,words).run()['complete_loop_fixed_point'])
        control=negative_controls(a,b);self.assertEqual(len(control['effective_controls']),81);self.receipt('relation-controls',control)
    def test_06_guarded_layout_GNU_rebases_and_corruptions(self):
        p=self.p;out=p['out'];raw,refs=match.normalize(p['raw'],p['refs'])
        self.assertEqual((p['report']['guards'],p['report']['insertions'],p['report']['omissions']),(43,4,0))
        self.assertEqual(match.payload(p['after'],match.FUNCTION),(raw,refs));self.assertTrue(p['report']['Make']['mixed_GLOBAL_ASM_recipe'])
        assembly,missing=emit_function(raw,dict(value=0,size=1116),refs,match.FUNCTION,SYMS);self.assertFalse(missing)
        obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,refs))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                command+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(command+[str(source)],check=True,capture_output=True)
                data=elf.read_bytes();at=elf_slot_offset(data,entry,1116);bodies.append(data[at:at+1116])
            self.assertEqual(*bodies)
        with(out/'proposed-guards.csv').open(newline='')as stream:
            reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
        for kind in('expected-word','expected-relocation'):
            broken=[dict(v)for v in rows];row=next(v for v in broken if v['function']==match.FUNCTION)
            row['expected'if kind=='expected-word'else'expected_relocations']='0x%08X'%(int(row['expected'],0)^1)if kind=='expected-word'else'R_MIPS_HI16:wrong_symbol'
            path=out/('bad-'+kind+'.csv')
            with path.open('w',newline='')as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(broken)
            with self.assertRaises(ValueError):match.pc.emit_padded_assembly(out/'after.o',match.ROOT/'conker/retail_layout.us.txt',match.SPEC['owner'],word_patches_path=path)
            with self.assertRaises(ValueError):match.pg.emit_padded_assembly(out/'after.o',p['fullasm'],filename=match.SPEC['owner'],word_patches_path=path)
        self.receipt('GNU-rebases',dict(rebases=6,independent_links=12,body_bytes=1116,guard_controls=4))
    def test_08_frozen_full_image_and_effective_corruptions(self):
        p=self.p;r=p['report'];image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),0)
        self.assertEqual((r['strict_changed_bytes'],r['exclusions'],r['conversion_rows']),(0,0,1));self.assertTrue(r['all_addresses_fixed'])
        at=elf_slot_offset(image,match.ENTRY,1116)
        for pos in(0x80,len(image)-1,at,at+1112):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
        self.receipt('strict-image-controls',dict(changed_bytes=0,exclusions=0,effective_controls=4,all_functions=r['functions']))
if __name__=='__main__':unittest.main()
