"""Direct randomized packet C, original callback/factory ABI and literal ELF."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_randomized_effect_packet_15014f6c_match as source
from tools.tests import game_randomized_effect_packet_15014f6c_oracle as guest
class RandomizedEffectPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>78I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
        guest.original_object(source,cls.q,cls.out)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_direct_words_frame_and_effective_scope_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['preserved_labels']),(78,78,152,0,31,31,0))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6052,229,0,0))
        raw,refs=self.q['raw'],self.q['refs'];self.assertEqual(source.normalize(raw,refs),(raw,refs))
        for i in range(78):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();self.assertEqual(source.guard_rows(raw,refs),[])
        self.assertEqual(source.guard_manifest(prefix,raw,refs),prefix)
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        paths=[self.out/(n+'.o')for n in('predecessor-owner','qualified-owner','qualified-isolated')];sections=[source.sections(p)for p in paths]
        for which in range(3):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=78,frame=152,guards=0,direct_C=True,raw_word_corruptions=78,altered_bindings=4,register_metadata_corruptions=72,raw_and_padded_neighbors=31,diagnostics=0)
    def test_02_mutable_guest_snapshots_aliases_and_literal_fault_prefixes(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_factory_copy_and_registered_caller(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+312],[0x22794C])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+312],[])
        self.receipts['connections']=guest.connections(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_links_rebased_execution_and_literal_image(self):
        executed=0
        for i,symbols in enumerate(guest.symbols(i)for i in range(3)):
            p=self.out/('independent-link-'+str(i));entry=source.ENTRY if i==0 else 0x17508000;lines=['.set noreorder','.set noat','.text','.globl selection','selection:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w)
                lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['normal_refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>78I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['raw'],self.q['refs'],symbols)))
            for c in(guest.Case(outcome=0),guest.Case(range=0,rng=0x80000000),guest.Case(mutation=15),guest.Case(range=0xFFFFFFFF,rng=0xFFFFFFFF)):
                initial=guest.fixture(c);m=guest.Oracle(linked,initial,c,entry=entry,s=symbols).run()
                wanted,calls,obs=guest.reference(initial,c,symbols,saved_s0=m.before[16])
                self.assertEqual((m.memory,m.calls,m.observations),(wanted,calls,obs));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>78I',*self.q['retail_words'])
        self.assertEqual(source.strict_image(before,after,truth),229)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        at=[64,source.elf_slot_offset(before,source.ENTRY,312),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)]
        for offset in at:
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=229,exclusions=0,independent_links=3,rebased_guest_cases=executed,bindings=4,corruption_controls=4,named_metadata_rows=0)
    def test_06_frozen_inputs_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),107)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertEqual((self.out/'qualified-guards.csv').read_bytes(),(self.out/'frozen'/source.GUARDS).read_bytes())
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],5);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=107,actual_Make_commands=5,complete_owner_functions=32,current_installed=installed,guard_history_unchanged=True)
if __name__=='__main__':unittest.main()
