"""Signed sound countdown: exact C, o32 callback, native aliases and whole image."""
import json
import subprocess
import unittest
from tools.experiments import game_sound_countdown_15103910_match as match
from tools.tests import game_sound_countdown_15103910_oracle as guest
from tools.tests import game_sound_countdown_15103910_native as native


class SoundCountdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,report):(self.prepared['out']/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    def test_01_entire_owner_two_padders_Make_and_strict_image(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['words'],r['frame'],r['guards'],r['neighbors']),(100,48,0,4))
        self.assertTrue(r['independent_padders']);self.assertEqual(r['exclusions'],0)
        for i in range(400):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
        truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE]
        image=p['elf'].read_bytes()
        for pos in(0x80,len(image)-1,match.elf_slot_offset(image,match.ENTRY,match.SIZE)):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(p['oldelf'].read_bytes(),bytes(wrong),truth)
    def test_02_independent_guest_semantics_faults_and_homes(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_native32_C_layout_aliases_and_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_independent_GNU_relocation_rebases(self):
        p=self.prepared;out=p['out']
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in guest.SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            bodies=[]
            for label,obj in [('C',out/'isolated.o'),('retail',p['retail'])]:
                elf=out/('rebase-%d-%s.elf'%(i,label));cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()]
                subprocess.run(cmd+[str(obj)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,400);bodies.append(image[at:at+400])
            self.assertEqual(*bodies)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,full_bytes=400,guards=0))
    def test_05_original_callback_call_window(self):self.receipt('original-caller',guest.caller_checks(self.prepared))


if __name__=='__main__':unittest.main()
