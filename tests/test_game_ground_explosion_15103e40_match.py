"""Ground explosion source, closed frame cell, full callers and strict image."""
import json
import struct
import subprocess
import unittest
from tools.experiments import game_ground_explosion_15103e40_match as match
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.tests import game_ground_explosion_15103e40_oracle as guest
from tools.tests import game_ground_explosion_15103e40_native as native

class GroundExplosionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,report):(self.prepared['out']/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    def test_01_owner_two_padders_actual_Make_strict_identical_image(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['body_words'],r['slot_words'],r['frame'],r['guards']),(202,204,152,4))
        self.assertTrue(r['ELF_identical']);self.assertEqual(r['exclusions'],0)
        for i in range(808):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.checked(bytes(wrong),p['refs'])
        for at in p['refs']:
            wrong=dict(p['refs']);wrong[at]=[('R_MIPS_26','wrong')]
            with self.assertRaises(ValueError):match.checked(p['raw'],wrong)
        normalized=match.normalize(p['raw']);self.assertEqual(sum(a!=b for a,b in zip(struct.unpack('>202I',p['raw']),struct.unpack('>202I',normalized))),4)
        truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE];image=p['elf'].read_bytes()
        self.assertEqual(truth[-8:],b'\0'*8)
        for pos in(0x80,len(image)-1,match.elf_slot_offset(image,match.ENTRY,match.SIZE)+808):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(p['oldelf'].read_bytes(),bytes(wrong),truth)
    def test_02_guest_contract_raw_cell_bijection_faults_and_CFG(self):self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_actual_native32_C_and_effective_source_controls(self):self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_independent_GNU_relocation_rebases(self):
        p=self.prepared;out=p['out'];raw=match.normalize(p['raw']);refs={int(k):v for k,v in p['refs'].items()}
        asm,missing=emit_function(raw,dict(value=0,size=808),refs,match.FUNCTION,guest.SYMS);self.assertFalse(missing)
        obj=match.assemble(out,'normalized-isolated',asm);self.assertEqual(match.payload(obj,match.FUNCTION),(raw,p['refs']))
        for i in range(6):
            entry=match.ENTRY+i*0x10000;syms={n:v+(i+1)*0x28004 for n,v in guest.SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);bodies=[]
            for label,source in(('C',obj),('retail',p['retail'])):
                elf=out/('rebase-%d-%s.elf'%(i,label));cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd+=['--defsym='+n+'=0x%X'%v for n,v in syms.items()];subprocess.run(cmd+[str(source)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,808);bodies.append(image[at:at+808])
            self.assertEqual(*bodies)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,body_bytes=808,guards=4))
    def test_05_three_complete_original_callers(self):self.receipt('original-callers',guest.caller_checks(self.prepared))

if __name__=='__main__':unittest.main()
