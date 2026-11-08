"""Packed scalar semantic, scheduling, original ABI and literal ELF qualification."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_packed_scalar_15115f68_match as source
from tools.tests import game_packed_scalar_15115f68_oracle as guest
class PackedScalarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_owner_and_fail_closed_scheduling_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(60,0,4,83,83))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics'],q['preserved_labels']),(6053,156,0,0,42))
        raw,refs=self.q['raw'],self.q['refs'];normal,nrefs=source.normalize(raw,refs)
        self.assertEqual(nrefs,refs);self.assertEqual(normal[:28],raw[:28]);self.assertEqual(normal[44:],raw[44:])
        for i in range(60):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();manifest=source.guard_manifest(prefix,raw,refs)
        self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(manifest.startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        text,fs,relocs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/142560.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in source.guard_rows(raw,refs):
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,relocs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad=dict(relocs);bad[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        a=source.sections(self.out/'predecessor-owner.o');b=source.sections(self.out/'qualified-owner.o')
        for at in range(24):
            changed=dict(b);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row)
            with patch.object(source,'sections',side_effect=[a,changed]):
                with self.assertRaises(ValueError):source.owner_pools(self.out/'predecessor-owner.o',self.out/'qualified-owner.o')
        self.receipts['scope']=dict(words=60,frame=0,guards=4,raw_word_corruptions=60,binding_corruptions=2,
          stale_guard_words=4,stale_guard_relocations=4,register_metadata_corruptions=24,
          raw_and_padded_neighbors=83,retained_labels=42,unchanged_pools=True,unchanged_FP_instructions=True)
    def test_02_signed_bytes_FP_order_aliases_and_literal_fault_cuts(self):
        self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_installer_and_both_indirect_call_sites(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if w==source.ENTRY],[0x22D78C])
        self.assertFalse([i for i,w in enumerate(words)if w>>26 in(2,3)and(0x10000000|((w&0x3FFFFFF)<<2))in range(source.ENTRY,source.ENTRY+240)])
        self.receipts['connections']=guest.connections(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):
        self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_relocated_links_and_literal_full_image(self):
        for i,address in enumerate((0x800BE9E4,0x81238000,0x00347FFC)):
            refs=self.q['normal_refs'];p=self.out/('independent-link-'+str(i))
            lines=['.set noreorder','.set noat','.text','.globl scalar','scalar:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['normal'])):
                for kind,name in refs.get(j*4,[]):lines.append('.reloc ., '+kind+', '+name)
                lines.append('.word 0x%08X'%w)
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x17508000 : SUBALIGN(4) { *(.text) }}\n')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'--defsym=D_800BE9E4=0x%X'%address,'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=list(struct.unpack('>60I',source.sections(p.with_suffix('.elf'))['.text'][1]))
            self.assertEqual(linked,source.bound_blob(self.q['normal'],refs,{'D_800BE9E4':address}))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes()
        truth=(self.root/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+240]
        self.assertEqual(source.strict_image(before,after,truth),156)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,240),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=156,exclusions=0,independent_links=3,signed_LO16_carries=True,corruption_controls=4,metadata_permutations=0)
    def test_06_frozen_inputs_complete_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),104)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text())
        self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertEqual((self.root/source.GUARDS).read_bytes(),(self.out/('qualified-guards.csv'if installed else'predecessor-guards.csv')).read_bytes())
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],5)
        self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.assertEqual(source.same_functions(self.out/'predecessor-owner.o',self.out/'qualified-owner.o',(source.FUNCTION,)),83)
        self.receipts['inputs']=dict(frozen_inputs=104,actual_Make_commands=5,complete_owner_functions=84,current_installed=installed)
if __name__=='__main__':unittest.main()
