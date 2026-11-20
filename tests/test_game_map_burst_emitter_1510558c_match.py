"""Map-burst paired-path guards, actual SDK32 semantics and full-image audit."""
import csv,json,subprocess,unittest
from tools.experiments import game_map_burst_emitter_1510558c_match as match
from tools.tests import game_map_burst_emitter_1510558c_oracle as guest
from tools.tests.game_map_burst_emitter_1510558c_native import native_checks
from tools.tests.game_map_burst_emitter_1510558c_relation import prove,negative_controls
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
SYMS={n:int(n.split('_')[1],16)for bindings in match.SPEC['refs'].values()for _,n in bindings}
class MapBurstMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.p=match.prepare()
    def receipt(self,name,value):
        (self.p['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_complete_owner_profile_pools_neighbors_and_inputs(self):
        q=self.p['report'];self.assertEqual((q['body_words'],q['raw_words'],q['frame'],q['guards'],q['insertions'],q['omissions'],q['unchanged_raw_neighbors']),(175,175,184,57,0,0,10))
        self.assertTrue(q['ELF_identical']);self.assertEqual(q['matching_credit'],int(q['source_installed']));self.assertEqual(q['new_diagnostics'],0)
    def test_02_guest_public_state_packet_fields_and_ordered_FP(self):
        result=guest.guest_checks(self.p['truth'],self.p['words']);self.assertEqual(result['cases'],368);self.receipt('guest',result)
    def test_03_actual_expiry_callback_dispatcher(self):
        result=guest.caller_checks(self.p['truth'],self.p['words'],match.ROOT);self.assertEqual(result['scenarios'],31);self.receipt('caller',result)
    def test_04_fired_public_prefixes(self):
        result=guest.prefix_checks(self.p['truth'],self.p['words']);self.assertEqual(result['public_prefixes'],55);self.receipt('prefixes',result)
    def test_05_actual_native_SDK32_and_effective_source_controls(self):
        result=native_checks(self.p['out']);self.assertEqual((result['cases_each_positive_profile'],result['controls']),(180,8));self.receipt('native',result)
    def test_07_complete_paired_path_relation_and_effective_controls(self):
        a,b=self.p['truth'],self.p['words'];result=prove(a,b);self.assertEqual((result['paths'],result['all_words_covered']),(6,175))
        for words in(a,b):self.assertEqual(prove(words,words)['paths'],6)
        controls=negative_controls(a,b);self.receipt('relation-controls',controls)
    def test_06_guarded_layout_GNU_rebases_and_corruptions(self):
        p=self.p;out=p['out'];raw,refs=match.normalize(p['raw'],p['refs'])
        self.assertEqual((p['report']['guards'],p['report']['insertions'],p['report']['omissions']),(57,0,0))
        self.assertEqual(match.payload(p['after'],match.FUNCTION),(raw,refs));self.assertTrue(p['report']['Make']['mixed_GLOBAL_ASM_recipe'])
        assembly,missing=emit_function(raw,dict(value=0,size=700),refs,match.FUNCTION,SYMS);self.assertFalse(missing)
        obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,refs))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                command+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(command+[str(source)],check=True,capture_output=True)
                data=elf.read_bytes();at=elf_slot_offset(data,entry,700);bodies.append(data[at:at+700])
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
        self.receipt('GNU-rebases',dict(rebases=6,independent_links=12,body_bytes=700,guard_controls=4))
    def test_08_frozen_full_image_and_effective_corruptions(self):
        p=self.p;r=p['report'];image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),0)
        self.assertEqual((r['strict_changed_bytes'],r['exclusions'],r['conversion_rows']),(0,0,1));self.assertTrue(r['all_addresses_fixed'])
        at=elf_slot_offset(image,match.ENTRY,700)
        for pos in(0x80,len(image)-1,at,at+696):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
        self.receipt('strict-image-controls',dict(changed_bytes=0,exclusions=0,effective_controls=4,all_functions=r['functions']))
if __name__=='__main__':unittest.main()
