"""Direct Tank camera match, exact padding/image and original dispatch/child."""
import json,struct,subprocess,unittest
from tools.experiments import game_tank_camera_15104520_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_tank_camera_15104520_oracle as guest
from tools.tests import game_tank_camera_15104520_native as native

class TankCameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,report):(self.prepared['out']/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    def test_01_direct_owner_two_padders_actual_Make_strict_image(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['slot_words'],r['frame'],r['guards']),(45,48,24,0))
        self.assertEqual((r['strict_changed_bytes'],r['exclusions']),(1,0));self.assertTrue(r['all_instruction_vectors_identical'])
        for i in range(180):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
        truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE];image=p['elf'].read_bytes();self.assertEqual(truth[-12:],b'\0'*12)
        for pos in(0x80,len(image)-1,match.elf_slot_offset(image,match.ENTRY,match.SIZE)+180):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(p['oldelf'].read_bytes(),bytes(wrong),truth)
    def test_02_independent_guest_contract_aliases_and_faults(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_native32_C_and_effective_source_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_independent_GNU_relocation_rebases(self):
        p=self.prepared;out=p['out'];raw=p['raw'];refs={int(k):v for k,v in p['refs'].items()}
        asm,missing=emit_function(raw,dict(value=0,size=180),refs,match.FUNCTION,guest.SYMS);self.assertFalse(missing)
        obj=match.assemble(out,'isolated',asm);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,p['refs']))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in guest.SYMS.items()};script=out/('rebase-%d.ld'%i)
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(cmd+[str(source)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,180);bodies.append(image[at:at+180])
            self.assertEqual(*bodies)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,body_bytes=180,guards=0))
    def test_05_original_indirect_dispatcher_and_real_child(self):self.receipt('original-connections',guest.connected_checks(self.prepared))

if __name__=='__main__':unittest.main()
