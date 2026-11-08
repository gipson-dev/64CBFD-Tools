"""Selector status C, original three-word ABI, bounded execution and whole ELF proof."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_selector_status_1509c7c8_match as source
from tools.tests import game_selector_status_1509c7c8_oracle as guest
class SelectorStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>77I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
        guest.original_object(source,cls.q,cls.out)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_words_owner_register_union_and_fail_closed_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['raw_words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['preserved_labels']),(77,77,0,0,2,2,12))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6052,223,0,0))
        raw,refs=self.q['raw'],self.q['refs'];self.assertEqual(source.normalize(raw,refs),(self.q['normal'],self.q['normal_refs']));self.assertEqual(len(refs),24)
        for i in range(77):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();rows=source.guard_rows(raw,refs)
        self.assertEqual((len(rows),sum(r[-1]=='true'for r in rows)),(0,0));self.assertTrue(source.guard_manifest(prefix,raw,refs).startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        paths=[self.out/(n+'.o')for n in('predecessor-owner','qualified-owner','qualified-isolated')];sections=[source.sections(p)for p in paths]
        for which in range(3):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        pools=[source.normalized_pools(p)for p in paths[:2]]
        for at in range(32):
            bad=dict(pools[1]);data,refs=bad['.rodata'];data=bytearray(data);data[at]^=1;bad['.rodata']=(bytes(data),refs)
            with patch.object(source,'normalized_pools',side_effect=[pools[0],bad]):
                with self.assertRaises(ValueError):source.owner_pools(*paths)
        for at in range(6):
            bad=dict(pools[1]);data,refs=bad['.rodata'];refs=list(refs);row=list(refs[at]);row[2]+=4;refs[at]=tuple(row);bad['.rodata']=(data,tuple(refs))
            with patch.object(source,'normalized_pools',side_effect=[pools[0],bad]):
                with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=77,raw_words=77,frame=0,guards=0,omissions=0,raw_word_corruptions=77,altered_bindings=24,register_metadata_corruptions=72,raw_and_padded_neighbors=2,exact_register_mask_union=True)
    def test_02_byte_gates_home_aliases_indeterminate_return_and_faults(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_registered_three_word_dispatcher_and_return(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+308],[0x22CF58,*range(0x242F18,0x242F30,4)])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+308],[])
        self.receipts['connections']=guest.connected(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_links_rebased_execution_and_literal_image(self):
        maps=[guest.symbols(i)for i in range(3)];executed=0
        for i,symbols in enumerate(maps):
            p=self.out/('independent-link-'+str(i));entry=source.ENTRY if i==0 else 0x17508000;lines=['.set noreorder','.set noat','.text','.globl selection','selection:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w);lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['normal_refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>77I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['normal'],self.q['normal_refs'],symbols)))
            for selector in range(8):
                c=guest.Case(selector=selector);initial=guest.fixture(c,symbols,entry);wanted,value,reads=guest.reference(initial,c,symbols,entry);m=guest.Oracle(linked,initial,c,entry=entry,s=symbols);m.run()
                self.assertEqual((m.memory,m.r[2],m.reads),(wanted,value,reads));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>77I',*self.q['retail_words']);self.assertEqual(source.strict_image(before,after,truth),223)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,308),row[0]+8,source.elf_slot_offset(before,0x8009E458,24),source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=223,exclusions=0,independent_links=3,rebased_guest_cases=executed,bindings=24,corruption_controls=5,metadata_exclusions=0)
    def test_06_frozen_inputs_complete_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),103)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertTrue((self.out/'qualified-guards.csv').read_bytes().startswith((self.out/'frozen'/source.GUARDS).read_bytes()))
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],3);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        old_make,new_make,make_installed=source.make_states((self.root/source.MAKE).read_text());self.assertEqual(make_installed,installed);self.assertEqual(old_make,(self.out/'frozen'/source.MAKE).read_text())
        self.receipts['inputs']=dict(frozen_inputs=103,actual_Make_commands=3,complete_owner_functions=3,current_installed=installed,guard_prefix_unchanged=True)
if __name__=='__main__':unittest.main()
