"""Actor/list query source, original ABI, relocation and literal image gates."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_actor_list_query_150229e4_match as source
from tools.tests import game_actor_list_query_150229e4_oracle as guest

class ActorListQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')

    def test_01_complete_owners_and_fail_closed_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['caller_functions']),(73,0,55,56,56,38))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics'],q['caller_diagnostics']),(6053,222,0,0,0))
        raw,refs=self.q['raw'],self.q['refs'];normal,nrefs=source.normalize(raw,refs)
        self.assertEqual((len(refs),len(nrefs)),(8,10))
        for i in range(73):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();manifest=source.guard_manifest(prefix,raw,refs)
        self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(manifest.startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        text,fs,relocs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/49D30.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in source.guard_rows(raw,refs):
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,relocs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad=dict(relocs);bad[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        for label in('owner','caller'):
            paths=[self.out/(n+'-'+label+'.o')for n in('predecessor','qualified')];sections=[source.sections(p)for p in paths]
            for which in range(2):
                for at in range(24):
                    entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                    with patch.object(source,'sections',side_effect=entries):
                        with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=73,guards=55,raw_word_corruptions=73,altered_bindings=8,stale_guard_words=55,stale_guard_relocations=55,register_metadata_corruptions=96,
          raw_and_padded_neighbors=56,unchanged_caller_functions=38,unchanged_pools_and_reginfo=True,raw_bindings=8,normalized_bindings=10,address_rematerialization=True)

    def test_02_guest_reads_aliases_and_literal_fault_cuts(self):self.receipts['guest']=guest.guest(source,self.q)

    def test_03_original_call_census_and_return_branches(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        sites=[0x4B360,0x4C050,0x50CB0,0x59720,0x59E8C,0x5BA18,0x7FAD4,0x84004,0x8BB48,0x8F954,0xA976C]
        self.assertEqual([4*i for i,w in enumerate(words)if w==(0x0C000000|(source.ENTRY>>2&0x3FFFFFF))],sites)
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+292],[])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+292],[])
        self.receipts['connections']=guest.caller_suite(source,self.q)

    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)

    def test_05_independent_symbol_links_and_literal_image(self):
        names=('D_800C35C8','D_800C35F0','D_800C363A','D_800CBFDF')
        maps=[{n:int(n.split('_')[1],16)for n in names},dict(zip(names,(0x81308004,0x8131FFF8,0x81327FFF,0x81338000))),dict(zip(names,(0x8050FFF8,0x80518008,0x80520003,0x80537FFE)))]
        for i,symbols in enumerate(maps):
            p=self.out/('independent-link-'+str(i));lines=['.set noreorder','.set noat','.text','.globl query','query:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w)
                lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['normal_refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>73I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['normal'],self.q['normal_refs'],symbols)))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=(self.root/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+292]
        self.assertEqual(source.strict_image(before,after,truth),222);row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,292),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=222,exclusions=0,independent_links=3,bindings=10,signed_low_half_carry=True,corruption_controls=4,metadata_permutations=0)

    def test_06_frozen_inputs_both_owners_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),108)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());cb,ca,ci=source.caller_states((self.root/source.CALLER_SOURCE).read_text())
        self.assertEqual(installed,ci);self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text());self.assertEqual(cb,(self.out/'frozen'/source.CALLER_SOURCE).read_text())
        self.assertEqual((self.root/source.GUARDS).read_bytes(),(self.out/('qualified-guards.csv'if installed else'predecessor-guards.csv')).read_bytes())
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual((self.root/source.CALLER_OBJECT).read_bytes(),(self.out/'qualified-caller-padded.o').read_bytes())
        q=self.q['report'];self.assertEqual((q['actual_Make']['commands'],q['caller_actual_Make']['commands']),(3,5));self.assertTrue(q['actual_Make']['padded_object_equal']and q['caller_actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=108,actual_Make_commands=[3,5],complete_owner_functions=[57,38],current_installed=installed,caller_object_byte_identical=True)

if __name__=='__main__':unittest.main()
