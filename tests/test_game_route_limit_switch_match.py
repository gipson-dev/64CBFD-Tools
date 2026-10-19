"""Route limit switch: full-word selectors, real table, bindings and image gates."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_limit_switch_candidates as source
from tools.experiments import game_route_limit_switch_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_route_record_copy_match as copy
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_one_shot_timer_match import symbol_rows

LIMITS={3:750,9:5000,20:3200,21:500,22:100000,24:100000,25:500,
        33:500,34:500,35:10000,36:100000,55:1500,56:5000,63:1800,64:500,65:100000}


def cases():
    values=set(range(512))|{i&0xFFFFFFFF for i in range(-512,0)}
    for base in (0x100,0x10000,0x7FFF0000,0x80000000,0xFFFF0000):
        values.update((base+i)&0xFFFFFFFF for i in range(67))
    values.update((0x7FFFFFFF,0x80000000,0xFFFFFFFF))
    value=0x57ACD203
    for _ in range(512):
        value=(1664525*value+1013904223)&0xFFFFFFFF;values.add(value)
    return sorted(values)


def fixture(table):
    m={copy.STACK+i:(i*17+0xA5)&255 for i in range(-64,128)}
    m.update({source.TABLE+i:v for i,v in enumerate(table)})
    return m


class SwitchModel(copy.CopyModel):
    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected switch call')
        self.caller_args.append((self.r[4],))


class GameRouteLimitSwitchMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        cls.words=list(struct.unpack_from('>44I',sections(cls.obj.with_suffix('.elf'))['.text'][1]))
        rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>44I',rom,source.ROM))
        cls.table=rom[source.TABLE_ROM:source.TABLE_ROM+252];cls.cases=cases()

    def model(self,words,value,phase=0,table=None,entry=source.ENTRY,table_address=source.TABLE):
        memory=fixture(self.table if table is None else table)
        if table_address!=source.TABLE:
            for i,v in enumerate(self.table if table is None else table):memory[table_address+i]=v
        return SwitchModel(words,memory,(value,),phase=phase,entry=entry)

    def test_direct_code_and_complete_table(self):
        self.assertEqual((self.row['words'],self.row['word_differences'],self.row['table_equal'],self.row['diagnostics']),
            (44,0,True,''));self.assertEqual(self.words,self.retail);integration.checked(self.obj)
        for index,target in enumerate(struct.unpack('>63I',self.table)):
            at=(target-source.ENTRY)//4;word=self.retail[at+1]
            if self.retail[at]==0x3C020001 and self.retail[at+1]==0x03E00008:
                self.assertEqual(self.retail[at+2],0x344286A0);value=100000
            elif self.retail[at]==0x03E00008:value=word&65535
            else:
                self.assertEqual(self.retail[at:at+4],[0x3C020001,0x344286A0,0x03E00008,0]);value=100000
            self.assertEqual(value,LIMITS.get(index+3,100000))

    def test_full_word_domain_classes_and_complete_instruction_coverage(self):
        visits=set()
        for value in self.cases:
            for phase in (0,8):
                a=self.model(self.retail,value,phase).run();b=self.model(self.words,value,phase).run()
                self.assertEqual((a.r,a.f,a.lo,a.memory,a.events),(b.r,b.f,b.lo,b.memory,b.events))
                self.assertEqual(a.r[2],LIMITS.get(value,100000))
                self.assertEqual(a.memory,fixture(self.table));self.assertEqual(a.calls,[])
                reads=[e for e in a.events if e[0]=='R']
                self.assertEqual(len(reads),int(3<=value<=65))
                if reads:self.assertEqual(reads[0][1],source.TABLE+(value-3)*4)
                visits.update(a.visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+176,4))<=visits)
        (self.out/'connected-cases.json').write_text(json.dumps(dict(cases=len(self.cases),phases=2,
            all44_words_visited=True,all63_table_entries_used=True,full_word_boundary_classes=True))+'\n')

    def test_fired_table_access_cuts_and_mutated_retained_table(self):
        pairs=0
        for value in range(3,66):
            for phase in (0,8):
                states=[]
                for words in (self.retail,self.words):
                    model=self.model(words,value,phase);model.fault=0
                    with self.assertRaises(copy.AccessFault):model.run()
                    self.assertEqual(model.accesses,0)
                    states.append((model.r,model.f,model.memory,model.events))
                self.assertEqual(*states);pairs+=1
        table=bytearray(self.table);struct.pack_into('>I',table,0,source.ENTRY+36)
        for words in (self.retail,self.words):
            model=self.model(words,3,table=table).run();self.assertEqual(model.r[2],1800)
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=pairs,table_mutation_witness=True))+'\n')

    def test_native32_all_selector_cases_and_effective_negatives(self):
        fmt=lambda value:'0x%Xu'%(value&0xFFFFFFFF)
        prefix='typedef unsigned int u32;typedef int s32;\n'
        values=','.join(fmt(v) for v in self.cases);expected=','.join(fmt(LIMITS.get(v,100000)) for v in self.cases)
        driver='''
static const u32 inputs[]={INPUTS},expected[]={EXPECTED};
void _start(void) {
    u32 i,failure=0;
    for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++)if((u32)func_1508E6D0((s32)inputs[i])!=expected[i]){failure=21;break;}
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''.replace('INPUTS',values).replace('EXPECTED',expected)
        exits={}
        controls={
            'selected':source.SELECTED,
            'byte-selector':source.SELECTED.replace('switch (type)','switch ((unsigned char)type)'),
            'wrong-default':source.SELECTED.replace('default: return 100000;','default: return 0;'),
            'missing-case':source.SELECTED.replace('        case 63: return 1800;\n',''),
        }
        for name,opt,sanitize in (('o0','-O0',False),('o2','-O2',False),('ubsan','-O2',True)):
            controls[name]=controls['selected']
        del controls['selected']
        for name,unit in controls.items():
            opt='-O0' if name=='o0' else '-O2';sanitize=name not in ('o0','o2')
            path=self.out/('native-'+name+'.c');path.write_text(prefix+unit+driver);exe=path.with_suffix('')
            compiled=subprocess.run([*native_command(opt,sanitize),str(path),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual((compiled.returncode,compiled.stdout,compiled.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True);want=0 if name in ('o0','o2','ubsan') else 21
            self.assertEqual((result.returncode,result.stdout,result.stderr),(want,'',''),name);exits[name]=result.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(cases=len(self.cases),exits=exits))+'\n')

    def test_actual_caller_delay_slot_full_word_interface(self):
        entry=0x1509E4C8;rom=self.values['conker/conker.us.bin']
        window=list(struct.unpack_from('>2I',rom,0xCB978))+[0x02E00008,0]
        self.assertEqual(window[:2],[0x0D4239B4,0x8CC40008]);pairs=0
        for value in (0,3,20,63,65,66,0x103,0x80000003,0xFFFFFFFF):
            for phase in (0,8):
                states=[]
                for words in (self.retail,self.words):
                    memory=fixture(self.table);copy.put(memory,0x90008,value,4)
                    model=SwitchModel(window,memory,(0xA5000004,0xA5000005,0x90000),phase=phase,entry=entry)
                    model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+8
                    model.code.update(zip(range(source.ENTRY,source.ENTRY+176,4),words))
                    model.run();self.assertEqual(model.caller_args,[(value,)])
                    self.assertEqual(model.r[2],LIMITS.get(value,100000));states.append((model.r,model.memory,model.events))
                self.assertEqual(*states);pairs+=1
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_two_word_windows=pairs,
            synthetic_stop_trampoline=True,whole_caller_not_executed=True))+'\n')

    def test_profile_owner_actual_make_and_first_or_installed_image(self):
        row=integration.qualify(self.root,self.out);self.assertEqual(row['new_relocation_bindings'],2)
        integration.make_shadow(self.root,self.out);self.assertTrue(integration.predict(self.root,self.out)['exact_prediction'])
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,self.out)

    def test_expected_word_and_relocation_guard_corruption_controls(self):
        before=self.values['conker/retail_word_patches.us.csv'];obj=self.out/'after-primary.o'
        good=integration.guard_bytes(before,obj);reader=csv.DictReader(io.StringIO(good.decode()));rows=list(reader)
        self.assertEqual(len(rows[-2:]),2)
        for index in (-2,-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:func_1508E6D0'
                stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(stream.getvalue())
                message='stale word patch' if field=='expected' else 'stale relocations'
                with self.assertRaisesRegex(ValueError,message):emit_padded_assembly(obj,self.root/'conker/asm/B3020.s',
                    function_objects={'func_150891E8':self.out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)

    def test_independent_rebases_and_exact_image_mutation_controls(self):
        values=self.values;before=values['conker/build/conker.us.elf'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+176]
        expected=integration.predicted_image(before,truth)
        self.assertEqual(integration.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth),expected)
        for at in (64,copy.elf_slot_offset(before,source.ENTRY,176),len(before)-1):
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Switch image differs'):integration.check_image(before,bytes(bad),truth)
        original=self.out/'original.s';obj=original.with_suffix('.o')
        asm=values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        code=asm[start:end].replace('jtbl_8009DA94','switch_table')
        table=values['conker/asm/data/2424E0.rodata.s'].decode();start=table.index('dlabel jtbl_8009DA94\n');end=table.index('enddlabel jtbl_8009DA94',start)
        table=table[start:end].replace('jtbl_8009DA94','switch_table')
        original.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+
            '\n.text\n.type '+source.FUNCTION+', @function\n'+code+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n.section .rodata\n'+table)
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
            '-I',str(self.root/'conker/include'),'-o',str(obj),str(original)],check=True,capture_output=True)
        pairs=0
        for number,(entry,address) in enumerate(((source.ENTRY,source.TABLE),(0x1621FFF4,0x8010FFF4),(0x18FFF000,0x80728004))):
            images=[]
            for label,path in (('original',obj),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%number);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(entry,address))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '-o',str(elf),str(path)],check=True,capture_output=True)
                linked=sections(elf);self.assertEqual(linked['.rodata'][0],address)
                images.append((linked['.text'][1][:176],linked['.rodata'][1][:252]))
            self.assertEqual(*images)
            words=list(struct.unpack('>44I',images[0][0]));table=images[0][1]
            for value in (0,2,3,9,20,21,22,24,25,33,34,35,36,55,56,63,64,65,66,0x80000003,0xFFFFFFFF):
                a=self.model(words,value,table=table,entry=entry,table_address=address).run()
                self.assertEqual(a.r[2],LIMITS.get(value,100000));pairs+=1
        # Named symbol meanings remain fixed, except the declared target extent.
        old={r[1]:r[2][1:] for r in symbol_rows(before)};new={r[1]:r[2][1:] for r in symbol_rows(expected)}
        old[source.FUNCTION]=(source.ENTRY,176,*old[source.FUNCTION][2:]);self.assertEqual(old,new)
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,executed_mapped_cases=pairs,
            independently_assembled_code_and_all63_targets_equal=True,data_maps_executed=True))+'\n')


if __name__=='__main__':unittest.main()
