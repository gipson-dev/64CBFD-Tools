"""Keyed lookup C, closed GPR/schedule guards, original reset/caller and literal ELF."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_keyed_record_reuse_150234a4_match as source
from tools.tests import game_keyed_record_reuse_150234a4_oracle as guest
class KeyedRecordReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>78I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
        guest.original_object(source,cls.q,cls.out)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_words_frame_closed_roles_and_effective_scope_controls(self):
        q=self.q['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['preserved_labels']),(78,78,40,13,56,56,0))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6052,227,0,0))
        raw,refs=self.q['raw'],self.q['refs'];self.assertEqual(source.normalize(raw,refs),(self.q['normal'],self.q['normal_refs']))
        for i in range(78):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();self.assertEqual(len(source.guard_rows(raw,refs)),13)
        self.assertTrue(source.guard_manifest(prefix,raw,refs).startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        paths=[self.out/(n+'.o')for n in('predecessor-owner','qualified-owner','qualified-isolated')];sections=[source.sections(p)for p in paths]
        for which in range(3):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        certificate=source.certificate(raw);self.assertEqual(certificate['schedule']['independent_adjacent_swaps'],6)
        with self.assertRaises(AssertionError):source.closure(struct.unpack('>78I',raw),16,18,{15:7},(4,5,6,7,8,9,29,31))
        bad=source.ORDER[:];bad[4],bad[8]=bad[8],bad[4]
        with self.assertRaises(AssertionError):source.schedule(struct.unpack('>78I',raw),bad)
        self.receipts['scope']=dict(words=78,frame=40,guards=13,direct_C=False,raw_word_corruptions=78,altered_bindings=13,register_metadata_corruptions=72,raw_and_padded_neighbors=56,diagnostics=0)
    def test_02_mutable_guest_snapshots_aliases_and_literal_fault_prefixes(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_reset_helper_and_pointer_consumer(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+312],[])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+312],[0x51BEC])
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
            linked=struct.unpack('>78I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['normal'],self.q['normal_refs'],symbols)))
            for c in(guest.Case(reset=0),guest.Case(key=0xFFFFFFFF),guest.Case(mutation=15),guest.Case(keys=(1,2,3),key=3)):
                initial=guest.fixture(c,symbols);m=guest.Oracle(linked,initial,c,entry=entry,s=symbols).run()
                wanted,calls,value=guest.reference(initial,c,symbols)
                self.assertEqual((m.memory,m.calls,m.r[2]),(wanted,calls,value));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>78I',*self.q['retail_words'])
        self.assertEqual(source.strict_image(before,after,truth),227)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        at=[64,source.elf_slot_offset(before,source.ENTRY,312),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)]
        for offset in at:
            bad=bytearray(after);bad[offset]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=227,exclusions=0,independent_links=3,rebased_guest_cases=executed,bindings=13,corruption_controls=4,named_metadata_rows=0)
    def test_06_frozen_inputs_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),104)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertTrue((self.out/'qualified-guards.csv').read_bytes().startswith((self.out/'frozen'/source.GUARDS).read_bytes()))
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],3);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=104,actual_Make_commands=3,complete_owner_functions=57,current_installed=installed,guard_history_unchanged=True)
if __name__=='__main__':unittest.main()
