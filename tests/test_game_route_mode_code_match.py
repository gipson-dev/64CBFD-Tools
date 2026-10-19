"""Mode-code switch: complete selector paths, halfword domain and literal image."""
import csv
import io
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_route_mode_code_candidates as source
from tools.experiments import game_route_mode_code_integration as integration
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import emit_padded_assembly
from tools.tests import test_game_route_limit_switch_match as previous
from tools.tests import test_game_route_record_copy_match as copy
from tools.tests.test_game_projected_packet_draw import native_command

NORMAL={20:0x28,63:0x2F,34:0x56,35:0x16,22:0x24,21:0x4B,33:0x58,36:0x63,
        25:0x57,64:0x21,9:0x1D,56:0x7B,57:0x82,55:0x85,24:0x55,65:0x2E,37:0x1060}
SPECIAL={1:0x105C,2:0x1059,16:0x1019}
MODES=(0,0xB7,0xB8,0xB9,0x1B8,0x7FFF,0x8000,0xFFB8,0xFFFF)
ARENA,OFFSET=0x90000,0x16BC


def expected(value,mode):return (SPECIAL if mode==0xB8 else NORMAL).get(value,0xFFFFFFFF)


def fixture(table,mode,table_address=source.TABLE,global_address=source.GLOBAL):
    memory={copy.STACK+i:(i*17+0xA5)&255 for i in range(-64,128)}
    memory.update({table_address+i:v for i,v in enumerate(table)})
    memory.update({ARENA+OFFSET+i:0xA5 for i in range(-8,12)})
    copy.put(memory,global_address,ARENA,4);copy.put(memory,ARENA+OFFSET,mode,2)
    return memory


class ModeModel(copy.CopyModel):
    def record_call(self,target):
        if target!=source.ENTRY:raise ValueError('Unexpected mode-code call')
        self.caller_args.append((self.r[4],))


NATIVE='''typedef unsigned char u8;typedef unsigned short u16;typedef short s16;typedef unsigned int u32;typedef int s32;
static u8 state[0x16C0] __attribute__((aligned(16)));s32 D_800D23B0;
SOURCE_BODY
static const u32 inputs[]={INPUTS};
static const u32 ordinary[]={ORDINARY},special[]={SPECIAL};
static u32 normal(u32 v) { switch(v) { NORMAL_CASES default:return 0xFFFFFFFFU; } }
static u32 alternate(u32 v) { switch(v) { SPECIAL_CASES default:return 0xFFFFFFFFU; } }
void _start(void) {
    u32 mode,i,value,want,failure=0,probes[]={1,2,8,16,20,37};
    if(sizeof(void*)!=4 || sizeof(s16)!=2)failure=29;
    D_800D23B0=(s32)state;
    for(i=0;i<sizeof(state);i++)state[i]=0xA5;
    for(mode=0;!failure && mode<65536;mode++) {
        *(s16 *)(state+0x16BC)=(s16)mode;
        for(i=0;i<6;i++) {
            value=probes[i];want=mode==0xB8?alternate(value):normal(value);
            if((u32)func_1508E780((s32)value)!=want)failure=21;
        }
        if((u16)*(s16 *)(state+0x16BC)!=mode || D_800D23B0!=(s32)state)failure=22;
    }
    for(mode=0;!failure && mode<2;mode++) {
        *(s16 *)(state+0x16BC)=mode?0xB8:0;
        for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++) {
            want=mode?special[i]:ordinary[i];
            if((u32)func_1508E780((s32)inputs[i])!=want)failure=21;
        }
    }
    for(i=0;i<sizeof(state);i++)if(i!=0x16BC && i!=0x16BD && state[i]!=0xA5)failure=22;
    __asm__ volatile("int $0x80"::"a"(1),"b"(failure));__builtin_unreachable();
}
'''


class GameRouteModeCodeMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.values=source.freeze(cls.root,cls.out);cls.obj,cls.row=source.compile_candidate(cls.root,cls.out,'test-selected')
        cls.words=list(struct.unpack_from('>71I',sections(cls.obj.with_suffix('.elf'))['.text'][1]))
        rom=cls.values['conker/conker.us.bin'];cls.retail=list(struct.unpack_from('>71I',rom,source.ROM))
        cls.table=rom[source.TABLE_ROM:source.TABLE_ROM+228];cls.cases=previous.cases()
        integration.qualify(cls.root,cls.out);integration.predict(cls.root,cls.out)

    def model(self,words,value,mode,phase=0,table=None,entry=source.ENTRY,table_address=source.TABLE,global_address=source.GLOBAL):
        memory=fixture(self.table if table is None else table,mode,table_address,global_address)
        return ModeModel(words,memory,(value,),phase=phase,entry=entry)

    def test_direct_code_and_all57_table_targets(self):
        self.assertEqual((self.row['words'],self.row['word_differences'],self.row['table_equal'],self.row['diagnostics']),
            (71,0,True,''));self.assertEqual(self.words,self.retail);integration.checked(self.obj)
        for i,target in enumerate(struct.unpack('>57I',self.table)):
            at=(target-source.ENTRY)//4;self.assertEqual(self.retail[at],0x03E00008)
            value=self.retail[at+1]&65535;value=(value-65536 if value&32768 else value)&0xFFFFFFFF
            self.assertEqual(value,NORMAL.get(i+9,0xFFFFFFFF))
        self.assertEqual(self.values['conker/conker.us.bin'][source.TABLE_ROM+228:source.TABLE_ROM+240],bytes(12))

    def test_both_modes_full_word_selectors_and_complete_coverage(self):
        coverage=set();pairs=0
        for mode in MODES:
            for value in self.cases:
                for phase in (0,8):
                    a=self.model(self.retail,value,mode,phase).run();b=self.model(self.words,value,mode,phase).run()
                    self.assertEqual((a.r,a.f,a.lo,a.memory,a.events),(b.r,b.f,b.lo,b.memory,b.events))
                    self.assertEqual(a.r[2],expected(value,mode));self.assertEqual(a.memory,fixture(self.table,mode))
                    reads=[e[1] for e in a.events if e[0]=='R']
                    self.assertEqual(reads[:2],[source.GLOBAL,ARENA+OFFSET])
                    self.assertEqual(reads[2:],[source.TABLE+(value-9)*4] if mode!=0xB8 and 9<=value<=65 else [])
                    coverage.update(a.visits);pairs+=1
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+284,4))<=coverage)
        (self.out/'connected-cases.json').write_text(json.dumps(dict(selectors=len(self.cases),modes=len(MODES),
            phases=2,paired_runs=pairs,all71_words_and57_entries_visited=True))+'\n')

    def test_fired_access_cuts_and_retained_table_mutation(self):
        pairs=0
        for mode in (0,0xB8,0xFFB8):
            for value in range(68):
                for phase in (0,8):
                    complete=self.model(self.retail,value,mode,phase).run()
                    for cut in range(complete.accesses):
                        states=[]
                        for words in (self.retail,self.words):
                            model=self.model(words,value,mode,phase);model.fault=cut
                            with self.assertRaises(copy.AccessFault):model.run()
                            self.assertEqual(model.accesses,cut);states.append((model.r,model.f,model.memory,model.events))
                        self.assertEqual(*states);pairs+=1
        table=bytearray(self.table);struct.pack_into('>I',table,0,source.ENTRY+56)
        for words in (self.retail,self.words):self.assertEqual(self.model(words,9,0,table=table).run().r[2],0x28)
        (self.out/'access-cuts.json').write_text(json.dumps(dict(fired_pairs=pairs,table_mutation_witness=True))+'\n')

    def test_native32_entire_halfword_domain_and_source_negatives(self):
        fmt=lambda v:'0x%Xu'%(v&0xFFFFFFFF)
        base=NATIVE.replace('INPUTS',','.join(fmt(v) for v in self.cases)).replace('ORDINARY',','.join(fmt(expected(v,0)) for v in self.cases)).replace(
            'SPECIAL_CASES',' '.join('case %d:return %s;'%(k,fmt(v)) for k,v in SPECIAL.items())).replace(
            'NORMAL_CASES',' '.join('case %d:return %s;'%(k,fmt(v)) for k,v in NORMAL.items())).replace(
            'SPECIAL',','.join(fmt(expected(v,0xB8)) for v in self.cases))
        controls={
            'byte-selector':source.SELECTED.replace('switch (type)','switch ((u8)type)'),
            'low-byte-mode':source.SELECTED.replace('*(s16 *)((u8 *)D_800D23B0 + 0x16BC)','(*(u16 *)((u8 *)D_800D23B0 + 0x16BC) & 255)'),
            'wrong-normal':source.SELECTED.replace('case 20: return 0x28;','case 20: return 0x29;'),
            'missing-special':source.SELECTED.replace('            case 1: return 0x105C;\n',''),
            'lost-flag':source.SELECTED.replace('0x1060','0x60'),
            'o0':source.SELECTED,'o2':source.SELECTED,'ubsan':source.SELECTED}
        exits={}
        for name,unit in controls.items():
            path=self.out/('native-'+name+'.c');path.write_text(base.replace('SOURCE_BODY',unit));exe=path.with_suffix('')
            command=[*native_command('-O0' if name=='o0' else '-O2',name not in ('o0','o2')),
                '-mstackrealign','-fno-strict-aliasing',str(path),'-o',str(exe)]
            result=subprocess.run(command,cwd=self.root,capture_output=True,text=True)
            (self.out/('native-'+name+'-compile.json')).write_text(json.dumps(dict(command=command,
                exit=result.returncode,diagnostics=result.stdout+result.stderr),indent=2)+'\n')
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''),name)
            result=subprocess.run([str(exe)],capture_output=True,text=True);want=0 if name in ('o0','o2','ubsan') else 21
            self.assertEqual((result.returncode,result.stdout,result.stderr),(want,'',''),name);exits[name]=result.returncode
        (self.out/'native-cases.json').write_text(json.dumps(dict(halfword_values=65536,probes_per_mode=6,
            full_word_selectors=len(self.cases),selector_modes=2,exits=exits))+'\n')

    def test_three_actual_caller_windows_and_return_codes(self):
        rom=self.values['conker/conker.us.bin'];pairs=0
        for entry,offset,register in ((0x1508DDB8,0xBB268,17),(0x1508DE00,0xBB2B0,16),(0x1508DF58,0xBB408,None)):
            window=list(struct.unpack_from('>2I',rom,offset))+[0x02E00008,0]
            self.assertEqual(window[0],0x0D4239E0)
            for mode in (0,0xB8):
                for value in (0,1,2,8,9,16,20,37,65,0x10000001):
                    for phase in (0,8):
                        states=[]
                        for words in (self.retail,self.words):
                            model=ModeModel(window,fixture(self.table,mode),(value,),phase=phase,entry=entry)
                            model.r[23]=model.before[23]=0xDEAD0000;model.before[31]=entry+8
                            if register is not None:model.r[register]=model.before[register]=value
                            else:model.before[21]=0
                            model.code.update(zip(range(source.ENTRY,source.ENTRY+284,4),words));model.run()
                            self.assertEqual(model.caller_args,[(value,)]);self.assertEqual(model.r[2],expected(value,mode))
                            if register is None:self.assertEqual(model.r[21],0)
                            states.append((model.r,model.memory,model.events))
                        self.assertEqual(*states);pairs+=1
        (self.out/'caller-cases.json').write_text(json.dumps(dict(actual_two_word_windows=pairs,caller_sites=3,
            third_site_uses_explicit_live_in_A0=True,synthetic_stop_trampoline=True,whole_caller_not_executed=True))+'\n')

    def test_binding_corruption_rejects_actual_word_and_relocation(self):
        good=integration.guard_bytes(self.values['conker/retail_word_patches.us.csv'],self.out/'after-primary.o')
        reader=csv.DictReader(io.StringIO(good.decode()));rows=list(reader)
        for index in (-2,-1):
            for field in ('expected','expected_relocations'):
                bad=[dict(r) for r in rows];bad[index][field]='0xFFFFFFFF' if field=='expected' else 'R_MIPS_26:func_1508E780'
                text=io.StringIO();writer=csv.DictWriter(text,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
                path=self.out/('bad-%d-%s.csv'%(index,field));path.write_text(text.getvalue())
                with self.assertRaisesRegex(ValueError,'stale word patch' if field=='expected' else 'stale relocations'):
                    emit_padded_assembly(self.out/'after-primary.o',self.root/'conker/asm/B3020.s',
                        function_objects={'func_150891E8':self.out/'after-normal.o'},word_patches_path=path,filename=source.OWNER)

    def test_profile_owner_actual_make_and_first_or_installed_image(self):
        integration.make_shadow(self.root,self.out)
        self.assertTrue(integration.predict(self.root,self.out)['exact_prediction'])
        if (self.root/source.SOURCE).read_bytes()!=self.values[source.SOURCE]:integration.audit(self.root,self.out)

    def test_independent_maps_and_strict_image_corruption_gates(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.values['conker/conker.us.bin'][source.ROM:source.ROM+284]
        expected_image=integration.check_image(before,(self.out/'first-linked.elf').read_bytes(),truth)
        for at in (64,copy.elf_slot_offset(before,source.ENTRY,284),len(before)-1):
            bad=bytearray(expected_image);bad[at]^=1
            with self.assertRaisesRegex(ValueError,'Mode-code image differs'):integration.check_image(before,bytes(bad),truth)
        asm=self.values['conker/asm/B3020.s'].decode();start=asm.index('glabel '+source.FUNCTION+'\n');end=asm.index('endlabel '+source.FUNCTION,start)
        code=asm[start:end].replace('jtbl_8009DB90','switch_table')
        asm=self.values['conker/asm/data/2424E0.rodata.s'].decode();start=asm.index('dlabel jtbl_8009DB90\n');end=asm.index('enddlabel jtbl_8009DB90',start)
        table=asm[start:end].replace('jtbl_8009DB90','switch_table');path=self.out/'original.s';obj=path.with_suffix('.o')
        path.write_text((self.root/'conker/include/asm_processor_prelude.inc').read_text()+'\n.text\n.type '+source.FUNCTION+', @function\n'+
            code+'\n.size '+source.FUNCTION+', .-'+source.FUNCTION+'\n.section .rodata\n'+table)
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(self.root/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True)
        count=0
        for n,(entry,address,global_address) in enumerate(((source.ENTRY,source.TABLE,source.GLOBAL),
                (0x1621FFF4,0x8010FFF4,0x80218008),(0x18FFF000,0x80728004,0x8033FFFC))):
            images=[]
            for label,object_path in (('original',obj),('source',self.obj)):
                script=self.out/(label+'-map-%d.ld'%n);elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(entry,address))
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    '--defsym=D_800D23B0=0x%X'%global_address,'-o',str(elf),str(object_path)],check=True,capture_output=True)
                data=sections(elf);images.append((data['.text'][1][:284],data['.rodata'][1][:240]))
            self.assertEqual(*images);words=list(struct.unpack('>71I',images[0][0]))
            for mode in (0,0xB8):
                for value in (0,1,2,8,9,16,20,21,22,24,25,33,34,35,36,37,55,56,57,63,64,65,66,0x10000001,0xFFFFFFFF):
                    model=self.model(words,value,mode,table=images[0][1][:228],entry=entry,table_address=address,global_address=global_address).run()
                    self.assertEqual(model.r[2],expected(value,mode));count+=1
        (self.out/'relocation-maps.json').write_text(json.dumps(dict(GNU_maps=3,executed_mapped_cases=count,
            independent_assembly_and57_targets_equal=True,code_table_and_global_maps_executed=True))+'\n')


if __name__=='__main__':unittest.main()
