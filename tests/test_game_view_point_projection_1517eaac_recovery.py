"""Qualify direct C projection before adoption and repeat on installed inputs."""
import csv,hashlib,json,struct,subprocess,sys,unittest
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_view_point_projection_1517eaac_recovery as s
from tools.tests import game_view_point_projection_1517eaac_oracle as guest
from tools.tests import game_view_point_projection_1517eaac_native as native
from tools.experiments import game_map_trail_constructor_15105ce0_match as make_driver
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

class ProjectionRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=s.screen();cls.raw,cls.refs=s.payload(s.OUT/'qualified-screen/candidate.o',s.FUNCTION)
        cls.words=s.bind(cls.raw,cls.refs)
        cls.retail=struct.unpack_from('>92I',(s.ROOT/'conker/conker.us.bin').read_bytes(),s.ROM)
    def test_01_complete_owner_and_caller(self):
        self.assertEqual((self.receipt['words'],self.receipt['frame'],self.receipt['differences']),(92,152,0))
        self.assertEqual(self.receipt['unchanged_neighbors'],7)
        self.assertIn((s.ROOT/s.SOURCE).read_text(),s.source())
        report=s.caller_census();(s.OUT/'caller-census.json').write_text(json.dumps(report,indent=2)+'\n')
        self.assertEqual(self.words,list(self.retail))
    def test_02_bounded_guest(self):
        report=guest.run(self.words,self.retail)
        self.assertEqual(report['cases'],896)
        self.assertEqual(report['unreachable_word_indices'],[83])
        (s.OUT/'guest.json').write_text(json.dumps(report,indent=2)+'\n')
    def test_03_effective_instruction_controls(self):
        controls={'inclusive-depth':(58,(self.words[58]&~63)|62),
            'wrong-y-sign':(78,(self.words[78]&~63)|0),
            'wrong-width-home':(56,(self.words[56]&0xFFFF0000)|0x30),
            'wrong-camera-rotation':(18,(self.words[18]&0xFFFF0000)|0x380)}
        rejected=[]
        corpus=[guest.Case(0,p,m,a,0)for p in(1,2,3)for m in(0,3)for a in(0,1)]
        for name,(index,value)in controls.items():
            body=list(self.words);self.assertNotEqual(body[index],value);body[index]=value
            with self.assertRaises(AssertionError):guest.run(body,self.retail,corpus)
            rejected.append(name)
        (s.OUT/'negative-controls.json').write_text(json.dumps(rejected)+'\n')
    def test_04_native_sdk32(self):self.assertEqual(len(native.run()['valid']),3)
    def test_06_original_caller_boundary(self):
        report=guest.run_caller(self.words,self.retail,(s.ROOT/'conker/conker.us.bin').read_bytes())
        self.assertEqual(report['cases'],160)
        (s.OUT/'caller-execution.json').write_text(json.dumps(report,indent=2)+'\n')
    def test_05_padders_actual_Make_and_strict_image(self):
        root=s.ROOT;out=s.OUT/'qualification';out.mkdir(exist_ok=True);base=s.OUT/'baseline'
        obj=s.OUT/'qualified-screen/candidate.o';guards=root/'conker/retail_word_patches.us.csv'
        self.assertEqual(guards.read_bytes(),(base/'conker/retail_word_patches.us.csv').read_bytes())
        with guards.open() as stream:self.assertFalse([r for r in csv.DictReader(stream)if r['function']==s.FUNCTION])
        padded=[]
        for label,text in(('layout',pc.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',s.OWNER,word_patches_path=guards)),
            ('asm',pg.emit_padded_assembly(obj,root/'conker/asm/1AB530.s',filename=s.OWNER,word_patches_path=guards))):
            p=out/(label+'.s');p.write_text(text);result=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(p)],capture_output=True,check=True)
            padded.append(result)
        self.assertEqual(padded[0].read_bytes(),padded[1].read_bytes())
        old=pg.parse_object(base/s.OBJECT);new=pg.parse_object(padded[0])
        self.assertEqual(set(old[1]),set(new[1]))
        changed=[]
        for name,a in old[1].items():
            b=new[1][name];self.assertEqual(a|({'size':368}if name==s.FUNCTION else{}),b)
            def value(p,f):return(p[0][f['value']:f['value']+f['size']],{i-f['value']:v for i,v in p[2].items()if f['value']<=i<f['value']+f['size']})
            if value(old,a)!=value(new,b):changed.append(name)
        self.assertEqual(changed,[s.FUNCTION])
        _,selected=s.source();(out/'after-diagnostics.txt').write_text(self.receipt['diagnostics'])
        with patch.multiple(make_driver,ROOT=root,OUT=out,SOURCE=s.SOURCE,OBJECT=s.OBJECT,SPEC=dict(selected=selected)):
            route=make_driver.actual_Make(padded[0],obj,guards,source=s.SOURCE,object_path=s.OBJECT,selected=selected,functions=8)
        with patch.multiple(linker,FILENAME=s.OWNER,OBJECT=s.OBJECT,LINKER='conker/build/conker.ld'):
            elf=linker.link_image(root,out,padded[0],'image')
        expected=bytearray((base/'conker/build/conker.us.elf').read_bytes())
        offset=elf_slot_offset(expected,s.ENTRY,368);expected[offset:offset+368]=struct.pack('>92I',*self.retail)
        symbols=[(at,row)for at,name,row,_ in symbol_rows(expected)if name==s.FUNCTION]
        self.assertEqual(len(symbols),1);at,row=symbols[0]
        self.assertEqual((row[1],row[2]),(s.ENTRY,12));struct.pack_into('>I',expected,at+8,368)
        self.assertEqual(elf.read_bytes(),bytes(expected))
        (out/'predicted.elf').write_bytes(expected)
        fs,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');self.assertEqual(len(fs),6051)
        report=dict(actual_Make=route,strict_predicted_ELF_equal=True,exclusions=0,
            changed_bytes=sum(a!=b for a,b in zip((base/'conker/build/conker.us.elf').read_bytes(),expected)),
            changed_function=s.FUNCTION,function_slots=6051,protected_data_audit=audit_layout(elf,root/'conker'),
            source_installed=(root/s.SOURCE).read_text()==selected,appended_guard_rows=0,
            selected_source_SHA256=hashlib.sha256(selected.encode()).hexdigest(),ELF_sha256=hashlib.sha256(expected).hexdigest())
        (out/'integration.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main()
