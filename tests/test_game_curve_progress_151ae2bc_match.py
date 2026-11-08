"""Curve progress semantic, scheduling, original ABI and literal ELF qualification."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_curve_progress_151ae2bc_match as source
from tools.tests import game_curve_progress_151ae2bc_oracle as guest
class CurveProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_owner_and_fail_closed_scheduling_guards(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors']),(59,0,23,32,32))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics'],q['preserved_labels']),(6053,183,0,0,0))
        raw,refs=self.q['raw'],self.q['refs'];normal,nrefs=source.normalize(raw,refs)
        self.assertEqual(nrefs,refs);self.assertEqual(refs,{})
        def key(w):return w&0xFFFF0000 if w>>26 in(1,4,5,6,7,20,21,22,23)or w>>26==17 and(w>>21&31)==8 else w
        self.assertEqual(source.Counter(map(key,struct.unpack('>59I',normal))),source.Counter(map(key,struct.unpack('>59I',raw))))
        with self.assertRaises(ValueError):source.normalize(raw,{0:[('R_MIPS_HI16','wrong')]})
        for i in range(59):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();manifest=source.guard_manifest(prefix,raw,refs)
        self.assertEqual(manifest,(self.out/'qualified-guards.csv').read_bytes());self.assertTrue(manifest.startswith(prefix))
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        text,fs,relocs=source.parse_object(self.out/'qualified-owner.o');start=fs[source.FUNCTION]['value']
        def emit():return source.pad_generated_object.emit_padded_assembly(self.out/'qualified-owner.o',self.root/'conker/asm/1D92F0.s',word_patches_path=self.out/'qualified-guards.csv',filename=source.OWNER)
        for row in source.guard_rows(raw,refs):
            at=int(row[2],16);bad=bytearray(text);bad[start+at+3]^=1
            with patch.object(source.pad_generated_object,'parse_object',return_value=(bytes(bad),fs,relocs)):
                with self.assertRaisesRegex(ValueError,'stale word patch'):emit()
            bad=dict(relocs);bad[start+at]=[('R_MIPS_HI16','wrong')]
            with patch.object(source.pad_generated_object,'parse_object',return_value=(text,fs,bad)):
                with self.assertRaisesRegex(ValueError,'stale relocations'):emit()
        paths=[self.out/(n+'.o')for n in('predecessor-owner','qualified-owner','qualified-isolated')]
        sections=[source.sections(p)for p in paths]
        for which in range(3):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.assertEqual(q['register_metadata']['CPR1_added_bits'],'0x00000280')
        self.receipts['scope']=dict(words=59,frame=0,guards=23,raw_word_corruptions=59,unexpected_binding_corruptions=1,
          stale_guard_words=23,stale_guard_relocations=23,register_metadata_corruptions=72,
          raw_and_padded_neighbors=32,retained_labels=0,unchanged_pools=True,closed_instruction_multiset=True,
          register_metadata=q['register_metadata'])
    def test_02_signed_bytes_FP_order_aliases_and_literal_fault_cuts(self):
        self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_caller_and_five_word_argument_packet(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if w==source.ENTRY],[])
        self.assertEqual([4*i for i,w in enumerate(words)if w==(0x0C000000|(source.ENTRY>>2&0x3FFFFFF))],[0x1DB5FC])
        self.receipts['connections']=guest.connected(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):
        self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_position_rebases_and_literal_full_image(self):
        for i,entry in enumerate((source.ENTRY,0x17508000,0x1000FFF0)):
            p=self.out/('independent-link-'+str(i));lines=['.set noreorder','.set noat','.text','.globl curve','curve:']
            lines += ['.word 0x%08X'%w for(w,)in struct.iter_unpack('>I',self.q['normal'])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('SECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=list(struct.unpack('>59I',source.sections(p.with_suffix('.elf'))['.text'][1]));self.assertEqual(linked,list(struct.unpack('>59I',self.q['normal'])))
            for c in(guest.Case(0),guest.Case(),guest.Case(mutation=1)):
                initial=guest.fixture(c);m=guest.Oracle(linked,initial,c,entry=entry);m.run();self.assertEqual(m.memory,guest.reference(initial,c))
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes()
        truth=(self.root/'conker/conker.us.bin').read_bytes()[source.ROM:source.ROM+236]
        self.assertEqual(source.strict_image(before,after,truth),183)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,236),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=183,exclusions=0,independent_links=3,rebased_guest_cases=9,bindings=0,corruption_controls=4,metadata_permutations=0)
    def test_06_frozen_inputs_complete_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),107)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text())
        self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertEqual((self.root/source.GUARDS).read_bytes(),(self.out/('qualified-guards.csv'if installed else'predecessor-guards.csv')).read_bytes())
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],5)
        self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.assertEqual(source.same_functions(self.out/'predecessor-owner.o',self.out/'qualified-owner.o',(source.FUNCTION,)),32)
        self.receipts['inputs']=dict(frozen_inputs=107,actual_Make_commands=5,complete_owner_functions=33,current_installed=installed)
if __name__=='__main__':unittest.main()
