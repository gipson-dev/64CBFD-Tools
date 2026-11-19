"""Camera preset matching gates, independent behavior and native ABI."""
import json
import struct
import subprocess
import unittest
from tools.experiments import game_camera_preset_15123568_match as match
from tools.tests import game_camera_preset_15123568_oracle as guest
from tools.tests import game_camera_preset_15123568_native as native


class CameraPresetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.prepared=match.prepare()
    def receipt(self,name,report):
        (self.prepared['out']/(name+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    def test_01_entire_owner_Make_and_strict_image(self):
        p=self.prepared;r=p['report'];self.assertEqual((r['words'],r['frame'],r['guards'],r['raw_neighbors'],r['padded_neighbors']),(90,24,7,44,44))
        self.assertEqual(r['exclusions'],0)
        for i in range(len(p['raw'])):
            wrong=bytearray(p['raw']);wrong[i]^=1
            with self.assertRaises(ValueError):match.derive_guards(bytes(wrong),p['refs'])
        truth=(match.ROOT/'conker/conker.us.bin').read_bytes()[match.ROM:match.ROM+match.SIZE]
        image=p['elf'].read_bytes()
        for pos in (0x80,len(image)-1,match.elf_slot_offset(image,match.ENTRY,match.SIZE)):
            wrong=bytearray(image);wrong[pos]^=1
            with self.assertRaises(ValueError):match.strict_image(p['oldelf'].read_bytes(),bytes(wrong),truth)
    def test_02_guest_semantics_faults_and_original_caller_windows(self):
        self.receipt('guest-contract',guest.guest_checks(self.prepared))
    def test_03_native32_layout_aliasing_and_semantic_controls(self):
        self.receipt('native-contract',native.native_checks(self.prepared['out']))
    def test_04_independent_GNU_relocation_rebases(self):
        p=self.prepared;out=p['out'];rows=match.derive_guards(p['raw'],p['refs'])
        original=p['retail']
        for i in range(6):
            entry=match.ENTRY+i*0x10000
            syms={n:v+(i+1)*0x20004 for n,v in guest.SYMS.items()}
            script=out/('rebase-%d.ld'%i);script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            linked=[]
            for label,obj in [('C',out/'isolated.o'),('retail',original)]:
                elf=out/('rebase-%d-%s.elf'%(i,label))
                cmd=['mips-linux-gnu-ld','--no-warn-mismatch','-T',str(script),'-o',str(elf)]
                cmd += ['--defsym='+n+'=0x%X'%v for n,v in syms.items()]
                subprocess.run(cmd+[str(obj)],check=True,capture_output=True)
                image=elf.read_bytes();at=match.elf_slot_offset(image,entry,360);linked.append(bytearray(image[at:at+360]))
            for row in rows:
                at=int(row['offset'],0);self.assertEqual(struct.unpack_from('>I',linked[0],at)[0],int(row['expected'],0))
                struct.pack_into('>I',linked[0],at,int(row['replacement'],0))
            self.assertEqual(*linked)
        self.receipt('GNU-rebases',dict(independent_links=12,rebases=6,full_target_bytes=360,all_bindings=True))


if __name__=='__main__':unittest.main()
