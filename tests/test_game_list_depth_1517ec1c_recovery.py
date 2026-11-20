"""Qualify list-depth recovery without assuming alias or conversion equivalence."""
import csv,hashlib,io,json,struct,subprocess,sys,unittest
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_list_depth_1517ec1c_recovery as s
from tools.tests.game_list_depth_1517ec1c_normalizer import derive
from tools.tests import game_list_depth_1517ec1c_oracle as guest
from tools.tests import game_list_depth_1517ec1c_native as native
from tools.experiments import game_map_trail_constructor_15105ce0_match as make_driver
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

class ListDepthRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=s.screen();cls.raw,cls.refs=s.payload(s.OUT/'qualified-screen/candidate.o',s.FUNCTION)
        cls.words=s.bind(cls.raw,cls.refs)
        cls.retail=struct.unpack_from('>135I',(s.ROOT/'conker/conker.us.bin').read_bytes(),s.ROM)
    def test_01_complete_owner_closed_derivation_and_caller(self):
        self.assertEqual((self.receipt['words'],self.receipt['frame'],self.receipt['differences']),(135,72,9))
        self.assertEqual(self.receipt['unchanged_neighbors'],7)
        self.assertIn((s.ROOT/s.SOURCE).read_text(),s.source())
        raw,refs,proof=derive(self.raw,self.refs)
        self.assertEqual((raw,refs),s.original())
        self.assertEqual(tuple(s.bind(raw,refs)),self.retail)
        (s.OUT/'derivation.json').write_text(json.dumps(proof,indent=2)+'\n')
        (s.OUT/'caller-census.json').write_text(json.dumps(s.caller_census(),indent=2)+'\n')
    def test_02_bounded_guest(self):
        report=guest.run(self.words,self.retail)
        self.assertEqual(report['cases'],1024)
        self.assertEqual(report['unreachable_word_indices'],[123])
        self.assertEqual(report['conversion_path_lengths'],[1,2])
        (s.OUT/'guest.json').write_text(json.dumps(report,indent=2)+'\n')
    def test_03_effective_instruction_controls(self):
        controls={'wrong-sample-shift':(72,(self.words[72]&~(31<<6))|(2<<6)),
            'wrong-depth-store':(129,(self.words[129]&0xFFFF0000)|0x2A),
            'wrong-helper-limit':(6,(self.words[6]&0xFFFF0000)|0x44FA),
            'missing-control-restore':(127,0),
            'inclusive-facing':(53,(self.words[53]&~63)|62)}
        rejected=[];corpus=list(guest.cases())[::7]
        for name,(index,value)in controls.items():
            body=list(self.words);self.assertNotEqual(body[index],value);body[index]=value
            with self.assertRaises(AssertionError):guest.run(body,self.retail,corpus)
            rejected.append(name)
        (s.OUT/'negative-controls.json').write_text(json.dumps(rejected)+'\n')
    def test_06_original_caller_boundary(self):
        report=guest.run_caller(self.words,self.retail,(s.ROOT/'conker/conker.us.bin').read_bytes())
        self.assertEqual(report['cases'],112)
        (s.OUT/'caller-execution.json').write_text(json.dumps(report,indent=2)+'\n')
    def test_04_native_sdk32(self):self.assertEqual(len(native.run()['valid']),3)
    def test_05_padders_actual_Make_and_strict_image(self):
        root=s.ROOT;out=s.OUT/'qualification';out.mkdir(exist_ok=True);base=s.OUT/'baseline'
        obj=s.OUT/'qualified-screen/candidate.o';raw,refs,proof=derive(self.raw,self.refs)
        old=(base/'conker/retail_word_patches.us.csv').read_bytes()
        reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
        self.assertFalse([r for r in reader if r['function']==s.FUNCTION])
        before=list(struct.unpack('>135I',self.raw));after=list(struct.unpack('>135I',raw));rows=[]
        for index,(a,b)in enumerate(zip(before,after)):
            if a==b:continue
            row={k:''for k in fields}
            row.update(filename=s.OWNER,function=s.FUNCTION,offset='0x%03X'%(index*4),
                expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
                note='Normalize commutative facing operands and closed dead-boundary FP scratch roles',omit='false')
            rows.append(row)
        self.assertEqual(len(rows),9)
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
        proposed=old+stream.getvalue().encode();guards=out/'proposed-guards.csv';guards.write_bytes(proposed)
        self.assertIn((root/'conker/retail_word_patches.us.csv').read_bytes(),(old,proposed))
        padded=[]
        for label,text in(('layout',pc.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',s.OWNER,word_patches_path=guards)),
            ('asm',pg.emit_padded_assembly(obj,root/'conker/asm/1AB530.s',filename=s.OWNER,word_patches_path=guards))):
            p=out/(label+'.s');p.write_text(text);result=p.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(p)],capture_output=True,check=True)
            padded.append(result)
        self.assertEqual(padded[0].read_bytes(),padded[1].read_bytes())
        a,b=pg.parse_object(base/s.OBJECT),pg.parse_object(padded[0]);self.assertEqual(set(a[1]),set(b[1]));changed=[]
        for name,f in a[1].items():
            g=b[1][name];self.assertEqual(f|({'size':540}if name==s.FUNCTION else{}),g)
            def value(p,h):return(p[0][h['value']:h['value']+h['size']],{i-h['value']:v for i,v in p[2].items()if h['value']<=i<h['value']+h['size']})
            if value(a,f)!=value(b,g):changed.append(name)
        self.assertEqual(changed,[s.FUNCTION])
        f=b[1][s.FUNCTION];self.assertEqual(b[0][f['value']+540:f['value']+548],b'\0'*8)
        _,selected=s.source();(out/'after-diagnostics.txt').write_text(self.receipt['diagnostics'])
        with patch.multiple(make_driver,ROOT=root,OUT=out,SOURCE=s.SOURCE,OBJECT=s.OBJECT,SPEC=dict(selected=selected)):
            route=make_driver.actual_Make(padded[0],obj,guards,source=s.SOURCE,object_path=s.OBJECT,selected=selected,functions=8)
        with patch.multiple(linker,FILENAME=s.OWNER,OBJECT=s.OBJECT,LINKER='conker/build/conker.ld'):
            elf=linker.link_image(root,out,padded[0],'image')
        expected=bytearray((base/'conker/build/conker.us.elf').read_bytes());offset=elf_slot_offset(expected,s.ENTRY,548)
        expected[offset:offset+548]=struct.pack('>135I',*self.retail)+b'\0'*8
        symbols=[(at,row)for at,name,row,_ in symbol_rows(expected)if name==s.FUNCTION]
        self.assertEqual(len(symbols),1);at,row=symbols[0];self.assertEqual((row[1],row[2]),(s.ENTRY,12));struct.pack_into('>I',expected,at+8,540)
        expected=s.reorder_metadata(expected)
        self.assertEqual(elf.read_bytes(),bytes(expected));(out/'predicted.elf').write_bytes(expected)
        fs,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump');self.assertEqual(len(fs),6051)
        report=dict(actual_Make=route,strict_predicted_ELF_equal=True,exclusions=0,
            changed_bytes=sum(x!=y for x,y in zip((base/'conker/build/conker.us.elf').read_bytes(),expected)),
            changed_function=s.FUNCTION,function_slots=6051,protected_data_audit=audit_layout(elf,root/'conker'),
            metadata_rotation=['D_800B06BC','func_1505A630','func_15073C48'],metadata_named_definitions_unchanged=True,
            source_installed=(root/s.SOURCE).read_text()==selected,appended_guard_rows=9,
            selected_source_SHA256=hashlib.sha256(selected.encode()).hexdigest(),ELF_sha256=hashlib.sha256(expected).hexdigest(),
            proposed_guards_SHA256=hashlib.sha256(proposed).hexdigest())
        (out/'integration.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main()
