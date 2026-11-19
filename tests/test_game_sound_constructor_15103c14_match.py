"""Sound constructor source, two ADDU guards, real ABI windows and full image."""
import json,struct,subprocess,unittest
from tools.experiments import game_sound_constructor_15103c14_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_sound_constructor_15103c14_oracle as guest
from tools.tests import game_sound_constructor_15103c14_native as native

class SoundConstructorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,report):(self.prepared['out']/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    def test_01_complete_owner_two_padders_Make_and_strict_image(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['slot_words'],r['frame'],r['guards'],r['neighbors']),(137,139,80,2,4))
        self.assertTrue(r['independent_padders']);self.assertEqual(r['exclusions'],0)
        for i in range(548):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
        normalized=match.normalize(p['raw']);self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>137I',p['raw']),struct.unpack('>137I',normalized))),2)
        truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE];image=p['elf'].read_bytes()
        self.assertEqual(truth[-8:],b'\0'*8)
        for pos in(0x80,len(image)-1,match.elf_slot_offset(image,match.ENTRY,match.SIZE)+548):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(p['oldelf'].read_bytes(),bytes(wrong),truth)
    def test_02_independent_guest_contract_faults_and_raw_guarded_equivalence(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_native32_C_and_effective_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_independent_GNU_relocation_rebases(self):
        p=self.prepared;out=p['out'];raw=match.normalize(p['raw']);refs={int(k):v for k,v in p['refs'].items()}
        asm,missing=emit_function(raw,dict(value=0,size=548),refs,match.FUNCTION,guest.SYMS);self.assertFalse(missing)
        obj=match.assemble(out,'normalized-isolated',asm);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,p['refs']))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in guest.SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(cmd+[str(source)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,548);bodies.append(image[at:at+548])
            self.assertEqual(*bodies)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,body_bytes=548,guards=2))
    def test_05_original_caller_and_registration_callee_homes(self):self.receipt('original-ABI-windows',guest.caller_checks(self.prepared))

if __name__=='__main__':unittest.main()
