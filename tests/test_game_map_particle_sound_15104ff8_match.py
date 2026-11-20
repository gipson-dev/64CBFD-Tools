"""Sound activation: public access order, ABI, real dispatcher, padders and strict image."""
import csv,json,struct,subprocess,unittest
from tools.experiments import game_map_particle_sound_15104ff8_match as match
from tools.tests import game_map_particle_sound_15104ff8_oracle as guest
from tools.tests.game_map_particle_sound_15104ff8_native import native_checks
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
class MapParticleSoundMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,value):
        (self.prepared['out']/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
    def test_01_owner_profile_complete_fingerprints_and_private_relation(self):
        p=self.prepared;r=p['report']
        self.assertEqual((r['body_words'],r['frame'],r['guards'],r['unchanged_raw_neighbors']),(46,72,4,10))
        self.assertEqual((r['insertions'],r['omissions'],r['new_diagnostics']),(0,0,0));self.assertTrue(r['ELF_identical'])
        report=match.relation(p['truth'],p['words']);self.assertEqual(report['paired_stores_loads'],4)
        controls=[]
        for offset in(0,0x1C,0x24,0x30,0x44,0x48,0x50,0x58,0x5C,0xA0,0xA8):
            wrong=p['words'][:];wrong[offset//4]^=4
            with self.assertRaises(ValueError):match.relation(p['truth'],wrong)
            controls.append(offset)
        self.receipt('private-relation-controls',dict(effective_controls=controls,all_paths_instruction_relation=report))
    def test_02_independent_guest_all_commands_states_aliases_and_reload(self):
        self.receipt('guest',guest.guest_checks(self.prepared['truth'],self.prepared['words']))
    def test_03_public_prefixes_and_original_dispatcher(self):
        p=self.prepared;self.receipt('public-prefix',guest.fault_checks(p['truth'],p['words']));self.receipt('caller',guest.caller_checks(p['truth'],p['words'],match.ROOT))
    def test_04_actual_native32_SDK_dispatcher_and_source_controls(self):
        self.receipt('native',native_checks(self.prepared['out']))
    def test_05_effective_guest_instruction_controls(self):
        truth=self.prepared['truth'];controls={
          'command':(0x18,1),'source-state':(0x30,1),'timer':(0x34,1),'stop-helper':(0x50,1),
          'signed-coordinate':(0x70,1<<26),'coordinate-offset':(0x78,2),'flags':(0x7C,1),'sound-ID':(0x98,1)}
        tested=[]
        for name,(offset,mask)in controls.items():
            wrong=truth[:];wrong[offset//4]^=mask;effective=False
            for c in(guest.Case(),guest.Case(command=0x39),guest.Case(state=0),guest.Case(mutation=7)):
                try:
                    initial=guest.fixture(c);m=guest.Oracle(wrong,initial,c).run();assert(guest.public(m.memory),m.calls)==guest.reference(initial,c);guest.preserved(m,c)
                except(AssertionError,ValueError,KeyError):effective=True;break
            self.assertTrue(effective,name);tested.append(name)
        self.receipt('instruction-controls',dict(effective_controls=tested))
    def test_06_independent_GNU_rebases_and_fail_closed_guards(self):
        p=self.prepared;out=p['out'];raw,refs=match.normalize(p['raw'],p['refs']);syms={n:int(n.split('_')[1],16)for bindings in refs.values()for _,n in bindings}
        assembly,missing=emit_function(raw,dict(value=0,size=184),refs,match.FUNCTION,syms);self.assertFalse(missing)
        obj=match.assemble('isolated-normalized',assembly)
        for i in range(6):
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(match.ENTRY+i*0x10000));bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));command=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                command+=['--defsym='+n+'=0x%X'%(v+(i+1)*0x28004)for n,v in syms.items()];subprocess.run(command+[str(source)],check=True,capture_output=True)
                data=elf.read_bytes();at=elf_slot_offset(data,match.ENTRY+i*0x10000,184);bodies.append(data[at:at+184])
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
        self.receipt('GNU-rebases',dict(rebases=6,independent_links=12,guard_controls=4))
    def test_07_literal_full_image_and_effective_corruptions(self):
        p=self.prepared;image=p['elf'].read_bytes();self.assertEqual(match.strict_image(image),0)
        at=elf_slot_offset(image,match.ENTRY,184)
        for pos in(0x80,len(image)-1,at,at+180):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(bytes(wrong))
        self.receipt('strict-image-controls',dict(changed_bytes=0,exclusions=0,effective_controls=4,functions=p['report']['functions']))
if __name__=='__main__':unittest.main()
