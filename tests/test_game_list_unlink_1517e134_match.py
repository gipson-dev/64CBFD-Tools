"""Unlink source/ABI, dead-home refinement, guest/native and full image gates."""
from copy import deepcopy
import json,struct,subprocess,unittest
from tools.experiments import game_list_unlink_1517e134_match as s
from tools.tests import game_list_unlink_1517e134_oracle as guest
from tools.tests import game_list_unlink_1517e134_native as native
from tools.experiments.game_actor_classifier_candidates import sections

class ListUnlinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obj,cls.raw,cls.refs,cls.retail,cls.caller=s.prepare()
        cls.derived,cls.bindings=s.derive(cls.raw,cls.refs)
        cls.words=s.bind(cls.raw,cls.refs);cls.normal=s.bind(cls.derived,cls.bindings)
    def test_01_closed_omission_and_independent_rebases(self):
        self.assertEqual(len(self.raw),124);self.assertEqual(len(self.derived),120)
        self.assertEqual(self.normal,self.retail)
        rom=(s.ROOT/'conker/conker.us.bin').read_bytes()
        jal=struct.pack('>I',0x0C000000|((s.ENTRY>>2)&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal],[0x16E6B0,0x16E71C])
        literal=struct.pack('>I',s.ENTRY)
        self.assertEqual([i for i in range(0,len(rom)-3,4)if rom[i:i+4]==literal],[])
        bad=bytearray(self.raw);bad[19]^=1
        with self.assertRaisesRegex(ValueError,'payload'):s.derive(bytes(bad),self.refs)
        refs=deepcopy(self.refs);refs[100]=[('R_MIPS_26','func_1517E134')]
        with self.assertRaisesRegex(ValueError,'bindings'):s.derive(self.raw,refs)
        for n,(entryshift,codeshift,datashift)in enumerate(((0,0,0),(0x1000,0x2000,0x12348))):
            outputs=[]
            for label,blob,relocs in(('derived',self.derived,self.bindings),('original',*s.payload(s.WHERE/'original.o',s.FUNCTION))):
                text=['.set noat','.set noreorder','.text','.globl '+s.FUNCTION,s.FUNCTION+':']
                for i,w in enumerate(struct.unpack('>30I',blob)):
                    for kind,name in relocs.get(i*4,[]):text.append('.reloc ., '+kind+', '+name)
                    text.append('.word 0x%08X'%w)
                obj=s.assemble(label+'-rebase-'+str(n),'\n'.join(text)+'\n');script=obj.with_suffix('.ld')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%(s.ENTRY+entryshift))
                anchors={name:int(name.split('_')[1],16)+(codeshift if name.startswith('func_')else datashift)for rows in relocs.values()for _,name in rows}
                elf=obj.with_suffix('.elf');subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',s.FUNCTION,*['--defsym=%s=0x%X'%item for item in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                outputs.append(sections(elf)['.text'][1])
            self.assertEqual(*outputs)
    def test_02_guest_lists_and_unobserved_home(self):
        r=guest.run(self.words,self.normal,self.retail);self.assertEqual(r['visited_words'],[31,30,30]);self.assertEqual(r['cases'],2184)
        (s.OUT/'guest.json').write_text(json.dumps(r,indent=2)+'\n')
    def test_03_connected_retail_callers(self):
        r=guest.callers(self.words,self.normal,self.retail);self.assertEqual(r['cases'],2184)
        (s.OUT/'callers.json').write_text(json.dumps(r,indent=2)+'\n')
    def test_04_effective_instruction_controls(self):
        controls={'wrong-next-offset':{7:self.normal[7]+4},'missing-head-store':{9:0},'wrong-free-argument':{25:0x00A02025}}
        for name,changes in controls.items():
            other=list(self.normal)
            for i,w in changes.items():self.assertNotEqual(other[i],w);other[i]=w
            with self.assertRaises(AssertionError,msg=name):guest.run(tuple(other),self.normal,self.retail)
        (s.OUT/'instruction-controls.json').write_text(json.dumps(list(controls))+'\n')
    def test_05_native_sdk32(self):
        r=native.run();self.assertEqual(len(r['valid']),3);self.assertEqual(len(r['rejected']),3)
    def test_06_padders_actual_Make_and_literal_image(self):
        r=s.qualify();self.assertEqual((r['changed_bytes'],r['exclusions'],r['function_slots']),(0,0,6051))
        self.assertEqual(r['actual_Make']['commands'],5);self.assertEqual(r['caller_actual_Make']['commands'],3)

if __name__=='__main__':unittest.main()
