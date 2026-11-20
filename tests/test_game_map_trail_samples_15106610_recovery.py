"""Private sample recovery and the independent loop-fold qualification."""
import csv,hashlib,io,json,struct,subprocess,sys,unittest
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_map_trail_samples_15106610_recovery as source
from tools.tests.game_map_trail_samples_15106610_normalizer import derive
from tools.tests import game_map_trail_samples_15106610_oracle as guest
from tools.tests import game_map_trail_samples_15106610_native as native
from tools.tests import game_map_trail_samples_15106610_connected as connected

from tools.experiments import game_map_trail_constructor_15105ce0_match as make_driver
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

class SampleRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=source.screen()
        cls.raw,cls.refs=source.payload(source.OUT/'screen/candidate.o',source.FUNCTION)
        cls.words=source.bind(cls.raw,cls.refs)
        cls.retail=struct.unpack_from('>106I',(source.ROOT/'conker/conker.us.bin').read_bytes(),source.ROM)

    def test_complete_owner(self):
        self.assertEqual((self.receipt['words'],self.receipt['frame']),(107,112))
        self.assertEqual(self.receipt['unchanged_neighbors'],36)
        self.assertTrue(self.receipt['pools_unchanged'])
        self.assertIn((source.ROOT/source.SOURCE).read_text(),source.source())
        (source.OUT/'caller-census.json').write_text(json.dumps(source.caller_census(),indent=2)+'\n')

    def test_closed_derivation(self):
        raw,refs,proof=derive(self.raw,self.refs)
        self.assertEqual((raw,refs),source.payload(source.OUT/'screen/before.o',source.FUNCTION))
        self.assertEqual(tuple(source.bind(raw,refs)),self.retail)
        self.assertEqual(proof['omitted_origins'],[94])
        (source.OUT/'derivation.json').write_text(json.dumps(proof,indent=2)+'\n')

    def test_bounded_guest(self):
        report=guest.run(self.words,self.retail)
        self.assertEqual(report['visited_words'],[107,106])
        self.assertEqual(report['angles'],256)
        (source.OUT/'guest.json').write_text(json.dumps(report,indent=2)+'\n')

    def test_native_sdk32(self):
        self.assertEqual(len(native.run()),3)

    def test_original_providers(self):
        report=connected.run(source.ROOT,source.OUT,self.words,self.retail)
        self.assertEqual(report['original_helper_words'],108)

    def test_effective_semantic_controls(self):
        controls={
            'output-home':(26,(self.words[26]&0xFFFF0000)|0x54),
            'angle-width':(49,(self.words[49]&0xFFFF0000)|127),
            'radius-operation':(51,self.words[51]&~63),
            'point-stride':(66,(self.words[66]&0xFFFF0000)|8),
            'endpoint':(self.words.index(0x8EC10038),0x8EC1002C),
        }
        rejected=[]
        for label,(index,replacement)in controls.items():
            words=list(self.words);self.assertNotEqual(words[index],replacement)
            words[index]=replacement
            with self.assertRaises((AssertionError,KeyError,ValueError),msg=label):guest.run(words,self.retail)
            rejected.append(label)
        (source.OUT/'negative-controls.json').write_text(json.dumps(rejected)+'\n')

    def test_real_padders_Make_image(self):
        root=source.ROOT;out=source.OUT/'qualification';out.mkdir(exist_ok=True)
        base=source.OUT/'baseline';obj=source.OUT/'screen/candidate.o'
        raw,refs,proof=derive(self.raw,self.refs)
        old=(base/'conker/retail_word_patches.us.csv').read_bytes()
        reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
        self.assertFalse([r for r in reader if r['function']==source.FUNCTION])
        before=list(struct.unpack('>107I',self.raw));after=list(struct.unpack('>106I',raw))
        rows=[]
        for index,a in enumerate(before):
            omitted=index>=len(after)
            b=a if omitted else after[index]
            if a==b and not omitted:continue
            row={k:''for k in fields}
            row.update(filename='generated_133190',function=source.FUNCTION,offset='0x%03X'%(index*4),
                expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',
                note='Normalize sample induction cycle and shared loop entry',omit='true'if omitted else'false')
            rows.append(row)
        self.assertEqual(len(rows),50)
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n')
        writer.writerows(rows)
        proposed=old+stream.getvalue().encode()
        current=(root/'conker/retail_word_patches.us.csv').read_bytes()
        self.assertIn(current,(old,proposed))
        guards=out/'proposed-guards.csv';guards.write_bytes(proposed)
        padded=[]
        for label,assembly in(('layout',pc.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt','generated_133190',rodata_symbol='D_800A2420',word_patches_path=guards)),
            ('asm',pg.emit_padded_assembly(obj,root/'conker/asm/133190.s',filename='generated_133190',rodata_symbol='D_800A2420',word_patches_path=guards))):
            path=out/(label+'.s');result=path.with_suffix('.o');path.write_text(assembly)
            subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(path)],capture_output=True,check=True)
            self.assertEqual(result.read_bytes(),(base/'conker/build/src/game/generated_133190.c.o').read_bytes())
            padded.append(result)
        _,selected=source.source()
        (out/'after-diagnostics.txt').write_text(self.receipt['diagnostics'])
        with patch.multiple(make_driver,ROOT=root,OUT=out,SPEC=dict(selected=selected)):
            make_report=make_driver.actual_Make(padded[0],obj,guards,selected=selected,functions=37)
        with patch.multiple(linker,FILENAME='generated_133190',OBJECT='conker/build/src/game/generated_133190.c.o',LINKER='conker/build/conker.ld'):
            elf=linker.link_image(root,out,padded[0],'image')
        self.assertEqual(elf.read_bytes(),(base/'conker/build/conker.us.elf').read_bytes())
        functions,_,_=load_elf_functions(elf,'mips-linux-gnu-objdump')
        self.assertEqual(len(functions),6051)
        report=dict(actual_Make=make_report,full_ELF_equal=True,whole_object_equal=True,
            ELF_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),function_slots=len(functions),
            protected_data_audit=audit_layout(elf,root/'conker'),source_installed=(root/source.SOURCE).read_text()==selected,
            appended_guard_rows=50,omission_rows=1,existing_guard_prefix_unchanged=True,proposed_guards_SHA256=hashlib.sha256(proposed).hexdigest())
        report['selected_source_SHA256']=hashlib.sha256(selected.encode()).hexdigest()
        (out/'integration.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':unittest.main(verbosity=2)
