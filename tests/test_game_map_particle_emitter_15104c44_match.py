"""Map-particle scheduling guards, independent GNU rebases and full-image gates."""
import csv,subprocess,unittest
from tools.experiments import game_map_particle_emitter_15104c44_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.experiments.game_map_particle_emitter_15104c44_recovery import SYMS
from tools.tests import test_game_map_particle_emitter_15104c44_recovery as recovered
class MapParticleMatchTests(recovered.MapParticleRecoveryTests):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def test_01_owner_profile_homes_and_complete_fingerprints(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['frame'],r['guards'],r['unchanged_raw_neighbors']),(237,224,52,10))
        self.assertEqual(r['matching_credit'],int(r['source_installed']));self.assertEqual(r['new_diagnostics'],0)
        for i in range(948):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
    def test_07_guarded_layout_GNU_rebases_and_corruptions(self):
        p=self.prepared;out=p['out'];raw,refs=match.normalize(p['raw'],p['refs'])
        self.assertEqual((p['report']['guards'],p['report']['insertions'],p['report']['omissions']),(52,0,0))
        self.assertEqual(match.payload(p['after'],match.FUNCTION),(raw,refs));self.assertTrue(p['report']['Make']['mixed_GLOBAL_ASM_recipe'])
        assembly,missing=emit_function(raw,dict(value=0,size=948),refs,match.FUNCTION,SYMS);self.assertFalse(missing)
        obj=match.assemble('normalized-isolated',assembly);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,refs))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                command+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(command+[str(source)],check=True,capture_output=True)
                data=elf.read_bytes();at=elf_slot_offset(data,entry,948);bodies.append(data[at:at+948])
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
        self.receipt('GNU-rebases',dict(rebases=6,independent_links=12,body_bytes=948,guard_controls=4))
    def test_08_frozen_full_image_and_effective_corruptions(self):
        p=self.prepared;r=p['report'];image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),0)
        self.assertEqual((r['strict_changed_bytes'],r['exclusions'],r['conversion_rows']),(0,0,1));self.assertTrue(r['all_addresses_fixed'])
        at=elf_slot_offset(image,match.ENTRY,948)
        for pos in(0x80,len(image)-1,at,at+944):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
        self.receipt('strict-image-controls',dict(changed_bytes=0,exclusions=0,effective_controls=4,all_functions=r['functions']))
if __name__=='__main__':unittest.main()
