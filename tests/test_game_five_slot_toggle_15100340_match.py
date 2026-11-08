"""Direct-C slot callback, original ABI and literal complete-image qualification."""
import json,struct,subprocess,unittest
from unittest.mock import patch
from tools.experiments import game_five_slot_toggle_15100340_match as source
from tools.tests import game_five_slot_toggle_15100340_oracle as guest
class FiveSlotToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=source.ROOT;cls.out=cls.root/source.BUILD;cls.q=source.prepare(cls.root);cls.receipts={}
        cls.q['retail_words']=struct.unpack_from('>73I',(cls.root/'conker/conker.us.bin').read_bytes(),source.ROM)
    @classmethod
    def tearDownClass(cls):(cls.out/'suite-detail.json').write_text(json.dumps(cls.receipts,indent=2)+'\n')
    def test_01_direct_words_owner_pools_and_fail_closed_inputs(self):
        q=self.q['report'];self.assertEqual((q['words'],q['frame'],q['guards'],q['raw_neighbors'],q['padded_neighbors'],q['preserved_labels']),(73,80,0,1,1,0))
        self.assertEqual((q['functions'],q['strict_changed_bytes'],q['exclusions'],q['diagnostics']),(6053,207,0,0));self.assertTrue(q['direct_C'])
        raw,refs=self.q['raw'],self.q['refs'];self.assertEqual(source.normalize(raw,refs),(raw,refs));self.assertEqual(len(refs),10)
        for i in range(73):
            bad=bytearray(raw);bad[4*i+3]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),refs)
        for at in refs:
            bad=dict(refs);bad[at]=[('R_MIPS_LO16','wrong')]
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        prefix=(self.out/'frozen'/source.GUARDS).read_bytes();self.assertEqual(source.guard_rows(raw,refs),[]);self.assertEqual(source.guard_manifest(prefix,raw,refs),prefix)
        with self.assertRaises(ValueError):source.guard_manifest(prefix+b'\n',raw,refs)
        paths=[self.out/(n+'-owner.o')for n in('predecessor','qualified')];sections=[source.sections(p)for p in paths]
        for which in range(2):
            for at in range(24):
                entries=sections[:];changed=dict(entries[which]);row=list(changed['.reginfo']);v=bytearray(row[1]);v[at]^=1;row[1]=bytes(v);changed['.reginfo']=tuple(row);entries[which]=changed
                with patch.object(source,'sections',side_effect=entries):
                    with self.assertRaises(ValueError):source.owner_pools(*paths)
        self.receipts['scope']=dict(words=73,frame=80,guards=0,direct_C=True,raw_word_corruptions=73,altered_bindings=10,register_metadata_corruptions=48,raw_and_padded_neighbors=1,pools_and_reginfo_unchanged=True)
    def test_02_unsigned_rolls_live_byte_reloads_aliases_and_faults(self):self.receipts['guest']=guest.guest(source,self.q)
    def test_03_original_callback_registration_and_dispatcher(self):
        rom=(self.root/'conker/conker.us.bin').read_bytes();words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)//4*4])
        self.assertEqual([4*i for i,w in enumerate(words)if source.ENTRY<=w<source.ENTRY+292],[0x2317EC])
        self.assertEqual([4*i for i,w in enumerate(words)if w>>26 in(2,3)and source.ENTRY<=((w&0x3FFFFFF)<<2|0x10000000)<source.ENTRY+292],[])
        self.receipts['connections']=guest.connected(source,self.q)
    def test_04_native_profiles_and_effective_semantic_controls(self):self.receipts['native']=guest.native(source,self.out)
    def test_05_independent_links_rebased_execution_and_literal_image(self):
        names=('D_80088BC0','D_800DD405','D_800BE500','func_150ADA20','func_151616D0')
        maps=[dict(zip(names,(0x80088BC0,0x800DD405,0x800BE500,guest.RNG,guest.EVENT))),dict(zip(names,(0x81308004,0x8131FFF8,0x81327FFC,0x17501230,0x17408000))),dict(zip(names,(0x8050FFF8,0x80518008,0x80520003,0x1720FFF0,0x17308000)))]
        executed=0
        for i,symbols in enumerate(maps):
            p=self.out/('independent-link-'+str(i));entry=source.ENTRY if i==0 else 0x17508000;lines=['.set noreorder','.set noat','.text','.globl callback','callback:']
            for j,(w,)in enumerate(struct.iter_unpack('>I',self.q['raw'])):
                label='w%d'%j;lines.append(label+': .word 0x%08X'%w);lines+=['.reloc '+label+', '+kind+', '+name for kind,name in self.q['refs'].get(j*4,[])]
            p.with_suffix('.s').write_text('\n'.join(lines)+'\n');p.with_suffix('.ld').write_text('\n'.join(n+' = 0x%X;'%a for n,a in symbols.items())+'\nSECTIONS{.text 0x%X : SUBALIGN(4) { *(.text) }}\n'%entry)
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-no-pad-sections','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],check=True,capture_output=True)
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],check=True,capture_output=True)
            linked=struct.unpack('>73I',source.sections(p.with_suffix('.elf'))['.text'][1]);self.assertEqual(list(linked),list(source.bound_blob(self.q['raw'],self.q['refs'],symbols)))
            for c in(guest.Case(view=1),guest.Case(),guest.Case(states=(1,)*5,rolls=(0,)*5,mode=23)):
                initial=guest.fixture(c,symbols);wanted,calls=guest.reference(initial,c,symbols);m=guest.Oracle(linked,initial,c,entry=entry,s=symbols);m.run()
                expected=[(symbols['func_150ADA20']if t==guest.RNG else symbols['func_151616D0'],a)for t,a in calls]
                self.assertEqual((guest.public(m.memory),m.calls),(guest.public(wanted),expected));executed+=1
        before,after=self.q['predecessor_elf'].read_bytes(),self.q['qualified_elf'].read_bytes();truth=struct.pack('>73I',*self.q['retail_words']);self.assertEqual(source.strict_image(before,after,truth),207)
        row=next(row for row in source.symbol_rows(before)if row[1]==source.FUNCTION)
        for at in(64,source.elf_slot_offset(before,source.ENTRY,292),row[0]+8,source.elf_slot_offset(before,0x80082B20,4)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):source.strict_image(before,bytes(bad),truth)
        self.receipts['image']=dict(changed_bytes=207,exclusions=0,independent_links=3,rebased_guest_cases=executed,bindings=10,signed_low_half_carry=True,corruption_controls=4,metadata_permutations=0)
    def test_06_frozen_inputs_complete_owner_and_actual_make(self):
        hashes=source.freeze(self.root,self.out);self.assertEqual(len(hashes),109)
        before,after,installed=source.source_states((self.root/source.SOURCE).read_text());self.assertEqual(before,(self.out/'frozen'/source.SOURCE).read_text())
        self.assertEqual((self.root/source.GUARDS).read_bytes(),(self.out/'frozen'/source.GUARDS).read_bytes())
        self.assertEqual((self.root/source.OBJECT).read_bytes(),(self.out/('qualified-padded.o'if installed else'predecessor-padded.o')).read_bytes())
        self.assertEqual(self.q['report']['actual_Make']['commands'],5);self.assertTrue(self.q['report']['actual_Make']['padded_object_equal'])
        self.receipts['inputs']=dict(frozen_inputs=109,actual_Make_commands=5,complete_owner_functions=2,current_installed=installed,guards_unchanged=True)
if __name__=='__main__':unittest.main()
