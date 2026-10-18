"""Qualify every neighbor slot, ordinary-memory CFG, private homes and rebases."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_neighbor_preference as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
COUNT,GLOBAL,TABLE,ACTOR=0x80087290,0x800D2350,0x30000,0x50000
HEADER='#include <ultra64.h>\nextern s16 D_80087290;\nextern u8 *D_800D2350;\n'


def fixture(pattern=0,dtype=4,count=1,node=0,upper=0,alias=0,count_address=COUNT,global_address=GLOBAL):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x500)}
    table=(TABLE,STACK-0x40,global_address-16,global_address-12,count_address-12,STACK-12)[alias]
    for at,length in ((table,4096),(count_address-4,12),(global_address-4,12),(ACTOR,132)):
        memory.update({(at+i)&0xFFFFFFFF:0xA5 for i in range(length)})
    for j in range(5):
        category=(pattern//5**j)%5;candidate=255 if category==0 else 250 if category==1 else j+1
        put(memory,table+node*16+9+j,candidate,1)
        if category>=2:
            put(memory,table+(j+1)*16+14,1 if category==2 else 4,1)
            put(memory,table+(j+1)*16+15,7 if category==4 else 9,1)
    put(memory,count_address,count,2);put(memory,global_address,table)
    args=tuple(upper|v for v in (node,dtype,250,7))
    return memory,args


def reference(initial,args,saved,phase=0,count_address=COUNT,global_address=GLOBAL):
    memory=dict(initial);trace=[];sp=STACK+phase
    def store(at,value):put(memory,at,value);trace.append(('W',at,4,value&0xFFFFFFFF))
    def get(at,n=4):value=read(memory,at,n);trace.append(('R',at,n,value));return value
    for i,value in enumerate(args):store(sp+i*4,value)
    store(sp-4,saved)
    node,dtype,excluded,preferred=(v&255 for v in args);count=base.half(get(count_address,2));result=255
    if node<count:
        table=get(global_address);route=(table+node*16)&0xFFFFFFFF
        for i in range(5):
            candidate=get(route+9+i,1)
            if candidate==255 or candidate==excluded:continue
            selected=(table+candidate*16)&0xFFFFFFFF
            kind=get(selected+14,1)
            if kind==dtype or dtype==255:
                result=candidate
                if get(selected+15,1)==preferred:break
    get(sp-4)
    return memory,result,trace


class NeighborOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY,connected=None):
        self.trace=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def get(self,at,n):
        value=super().get(at,n)
        if self.own_instruction:self.trace.append(('R',at,n,value))
        return value

    def put(self,at,value,n):
        super().put(at,value,n)
        if self.own_instruction:self.trace.append(('W',at,n,value&((1<<(n*8))-1)))

    def record_call(self,target):raise AssertionError('Neighbor selector has no helpers')
    def hook(self,target):raise AssertionError('Neighbor selector has no opaque providers')


def corpus():
    for pattern,dtype in itertools.product(range(3125),(4,255)):yield (pattern,dtype,1,0,0,0)
    for count,node,upper in itertools.product((-32768,-1,0,1,127,128,255,256,32767),
            (0,1,127,128,254,255),(0,0x100,0x80000000,0xFFFFFF00)):
        yield (3124,4,count,node,upper,0)
    for alias,pattern,dtype,upper in itertools.product(range(1,6),(0,4,124,3124),(4,255),(0,0xFFFFFF00)):
        yield (pattern,dtype,1,0,upper,alias)


def controls():
    b=source.SELECTED
    return {
        'no-wildcard':b.replace(' || type == 0xFF',''),
        'no-exclusion':b.replace(' && first != excluded','').replace(' && candidate != excluded','').replace(' && next != excluded',''),
        'type-as-class':b.replace('[0xF]','[0xE]'),
        'unsigned-count':b.replace('id >= D_80087290','id >= (u16)D_80087290'),
        'first-fallback':b.replace('        result = first;','        if (result == 0xFF) result = first;').replace(
            '            result = candidate;','            if (result == 0xFF) result = candidate;').replace(
            '            result = next;','            if (result == 0xFF) result = next;'),
        'wrong-sentinel':b.replace('!= 0xFF','!= 0xFE'),
        'missing-even-slots':b.replace('        next = cursor[10];','        next = 0xFF;'),
    }


NATIVE=HEADER+r'''
u8 *D_800D2350;s16 D_80087290;
u8 func_1508907C(u8,u8,u8,u8);
static u8 data[4128],saved[4128];
static void fill(void){u32 i;for(i=0;i<sizeof(data);i++)data[i]=0xA5;D_800D2350=data+16;}
static int same(void){u32 i;for(i=0;i<sizeof(data);i++)if(data[i]!=saved[i])return 0;return D_800D2350==data+16;}
static void save(void){u32 i;for(i=0;i<sizeof(data);i++)saved[i]=data[i];}
static int run(void){u32 p,t,j,n,c,id,expected,k,cases=0;u8 *table,*selected;s16 count;
 for(p=0;p<3125;p++)for(t=0;t<2;t++){
  fill();table=data+16;D_80087290=1;
  for(j=0,k=1;j<5;j++,k*=5){c=p/k%5;id=c==0?255:c==1?250:j+1;table[9+j]=id;
   if(c>=2){table[(j+1)*16+14]=c==2?1:4;table[(j+1)*16+15]=c==4?7:9;}}
  expected=255;
  for(j=0;j<5;j++){id=table[9+j];if(id==255||id==250)continue;selected=table+id*16;
   if(selected[14]==4||t){expected=id;if(selected[15]==7)break;}}
  save();count=D_80087290;
  if(func_1508907C(0,t?255:4,250,7)!=expected||!same()||D_80087290!=count)return 23;cases++;
 }
 for(n=0;n<65536;n++){
  fill();table=data+16;for(j=0;j<5;j++)table[9+j]=255;
  table[9]=1;table[30]=4;table[31]=7;D_80087290=(s16)((s32)n-32768);count=D_80087290;save();
  if(func_1508907C(0,4,250,7)!=(count>0?1:255)||!same()||D_80087290!=count)return 23;cases++;
 }
 return cases==71786?0:29;
}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class NeighborPreferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.installed=bool(source.AFTER) and source.raw_read(cls.root/'conker/src/game/generated_B3020.c')==source.expected_inputs(cls.root,cls.out)['conker/src/game/generated_B3020.c']
        view=source.historical_view(cls.root,cls.out) if cls.installed else __import__('contextlib').nullcontext()
        with view:cls.obj,cls.padded,cls.raw_words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=list(struct.unpack_from('>91I',cls.rom,source.ROM))
        data,functions=source.baseline.model.link_owner(cls.root,cls.out,cls.padded,source.OWNER);f=functions[source.FUNCTION]
        cls.words=list(struct.unpack_from('>91I',data,f['value']))
        if cls.words!=cls.truth:raise ValueError('Padded neighbor preference is not retail')

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY,count_address=COUNT,global_address=GLOBAL):
        machines=[]
        for words in bodies or (self.raw_words,self.words,self.truth):
            m=NeighborOracle(words,memory,args,phase,entry);floating=list(m.f)
            expected,value,trace=reference(memory,args,m.before[16],phase,count_address,global_address)
            m.run();self.assertEqual((m.memory,m.r[2],m.trace),(expected,value,trace));self.assertEqual(m.calls,[])
            self.assertEqual(m.f,floating)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            machines.append(m)
        return machines

    def test_01_all_outcome_patterns_widths_aliases_and_complete_slot(self):
        seen=[set(),set(),set()];count=0
        for p in corpus():
            models=self.compare(*fixture(*p),(count&1)*8)
            for visits,m in zip(seen,models):visits.update(m.visits)
            count+=1
        for value in range(256):
            cases=[fixture(3124,count=256,node=value),fixture(3124,dtype=value)]
            for axis in (2,3):
                memory,args=fixture(3124);args=list(args);args[axis]=value;cases.append((memory,tuple(args)))
            memory,args=fixture(3124,dtype=value);args=list(args);args[3]=value
            put(memory,TABLE+16+14,value,1);put(memory,TABLE+16+15,value,1);cases.append((memory,tuple(args)))
            for memory,args in cases:
                self.compare(memory,args,(value&1)*8);count+=1
        self.assertEqual(self.words,self.truth)
        self.receipt('guest',three_way_cases=count,patterns_per_type=3125,type_filters=2,
            full_memory_including_private_homes_and_ordered_trace=True,guest_aliases=5,
            visited=[len(s) for s in seen],all256_values_each_argument_and_type_class_fields=True,
            hardware_concurrent_memory_not_claimed=True)

    def test_02_native_O2_O0_UBSan_and_seven_effective_controls(self):
        driver=self.out/'native-driver.c';driver.write_text(NATIVE)
        exits={}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(driver),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=120);exits[name]=result.returncode
            self.assertEqual(result.returncode,status,(name,result.stderr))
        self.receipt('native',cases_per_profile=71786,all65536_signed_counts=True,UBSan=True,
            profiles=['O2','O0'],seven_controls=True,exits=exits,guest_stack_aliases_excluded=True)

    def test_03_symbolic_proof_and_independent_effective_word_controls(self):
        raw,bindings=source.checked_object(self.obj);row=source.normalization_proof(raw,bindings,self.truth)
        self.assertEqual(row['symbolic_paths'],4688)
        original=source.symbolic_paths(self.truth)
        for name,at,word in (
                ('type-field',34,self.truth[34]+1),
                ('class-field',37,self.truth[37]-1),
                ('wrong-fallback',41,self.truth[41]&~(31<<21)),
                ('wrong-loop-limit',28,self.truth[28]-1),
                ('wrong-saved-register',13,0xAFB10004),
                ('lost-likely-annul',49,self.truth[49]&~(16<<26))):
            mutant=list(self.truth);mutant[at]=word
            try:proof=source.symbolic_paths(mutant)
            except ValueError:proof=None
            self.assertNotEqual(proof,original,name)
        for i in range(91):
            bad=bytearray(raw);bad[i*4]^=1
            with self.assertRaises(ValueError):source.normalize(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad.pop(at)
            with self.assertRaises(ValueError):source.normalize(raw,bad)
        mutant=list(self.truth);mutant[20]^=1
        with self.assertRaises(ValueError):source.normalization_proof(raw,bindings,mutant)
        tiny=[0xAFA40000,0x93A20001,0x03E00008,0]
        left=next(iter(source.symbolic_paths(tiny).values()))[0]
        tiny[0]=0xAFA50000
        right=next(iter(source.symbolic_paths(tiny).values()))[0]
        self.assertNotEqual(left,right)
        self.assertEqual((left[0],left[2],left[3]),('read',1,False))
        self.assertNotEqual(left[-1],right[-1])
        self.receipt('proof',**row,word_corruptions_rejected=91,binding_corruptions_rejected=4,effective_symbolic_controls=6)

    def test_04_all_access_fault_prefix_memory_and_trace(self):
        count=fixtures=0;register_difference=False
        for pattern,alias,phase in itertools.product((0,4,124,3124),range(6),(0,8)):
            memory,args=fixture(pattern,alias=alias);full=NeighborOracle(self.truth,memory,args,phase).run()
            for fault in range(full.all_accesses):
                machines=[]
                for words in (self.raw_words,self.words,self.truth):
                    m=NeighborOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    machines.append(m)
                for m in machines[1:]:self.assertEqual((m.memory,m.trace),(machines[0].memory,machines[0].trace))
                register_difference|=machines[0].r!=machines[2].r;count+=1
            fixtures+=1
        self.assertTrue(register_difference)
        self.receipt('faults',fixtures=fixtures,three_way_equal_memory_trace_prefixes=count,
            raw_dead_GPR_fault_state_differs=register_difference,private_frame_stores_included=True)

    def test_05_actual_padder_and_nine_independent_carry_rebases(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-preference',source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        count=0
        for placement,(entry,count_address,global_address) in enumerate(((source.ENTRY,COUNT,GLOBAL),
                (0x16218004,0x23457FFC,0x34567FFC),(0x18FFF000,0x23458004,0x34568004))):
            anchors={'D_80087290':count_address,'D_800D2350':global_address};bodies=[]
            for label,obj in (('original',original),('raw',self.obj),('padded',self.padded)):
                if label!='original':
                    text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
                    emitted,missing=emit_function(text,f,rel,source.FUNCTION,anchors);self.assertFalse(missing)
                    path=self.out/('rebase-%s-%d.s'%(label,placement));path.write_text(emitted);obj=path.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
                ld=self.out/('rebase-%s-%d.ld'%(label,placement));elf=ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>91I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);self.assertNotEqual(bodies[0],bodies[1])
            raw,bindings=source.checked_object(self.obj);self.assertEqual(source.normalization_proof(raw,bindings,bodies[0],anchors)['symbolic_paths'],4688)
            for pattern,dtype,alias,phase in itertools.product((0,4,124,3124),(4,255),range(6),(0,8)):
                memory,args=fixture(pattern,dtype,alias=alias,count_address=count_address,global_address=global_address)
                self.compare(memory,args,phase,bodies,entry,count_address,global_address);count+=1
        self.receipt('rebases',links=9,three_way_cases=count,HI16_LO16_carry_boundaries=True,actual_padder=True)

    def test_06_seven_actual_call_and_delay_windows(self):
        sites=(0x1508947C,0x150895B8,0x15089810,0x15089828,0x15089840,0x15089908,0x15089970)
        class Returned(Exception):pass
        class StopCode(dict):
            def __getitem__(self,at):
                if at==self.stop:raise Returned
                return super().__getitem__(at)
        class WindowOracle(NeighborOracle):
            def record_call(self,target):
                if target!=source.ENTRY:raise AssertionError('Unexpected retained window provider')
                self.forwarded=tuple(self.r[4:8]);self.entered_memory=dict(self.memory);self.entered=list(self.r)
        count=0
        for site,pattern,dtype,upper in itertools.product(sites,(0,4,124,3124),(4,255),(0,0xFFFFFF00)):
            words=struct.unpack_from('>2I',self.rom,site-0x14FD2B50)
            self.assertEqual(words[0],0x0D42241F)
            memory,args=fixture(pattern,dtype,upper=upper)
            for body in (self.raw_words,self.words,self.truth):
                code=dict(zip(range(source.ENTRY,source.ENTRY+364,4),body));code[site+8]=0
                m=WindowOracle(words,memory,args,entry=site,connected=code);m.r[23]=ACTOR;m.r[25]=250
                m.code=StopCode(m.code);m.code.stop=site+8
                with self.assertRaises(Returned):m.run()
                expected,value,_=reference(m.entered_memory,m.forwarded,m.entered[16])
                self.assertEqual((m.memory,m.r[2]),(expected,value))
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.entered[r])
            count+=1
        self.receipt('caller-windows',sites=7,three_way_windows=count,actual_JAL_and_delay=True,
            real_helper_no_opaque_provider=True,complete_parent_or_gameplay_not_claimed=True)

    def test_07_input_history_and_whole_image_prediction(self):
        if source.AFTER:
            source.verify(self.root,self.out,self.installed)
            if self.installed:source.audit(self.root,self.out)
        raw=source.raw_read;paths=list(source.INPUTS);checks=0
        view=source.historical_view(self.root,self.out) if self.installed else __import__('contextlib').nullcontext()
        with view:
            source.freeze(self.root,self.out)
            for index,path in enumerate(paths):
                for target in (self.root/path,self.out/('before-%02d'%index)):
                    original=Path.read_bytes
                    def corrupt(p,*args,**kwargs):
                        data=original(p,*args,**kwargs);return data+b'\0' if p==target else data
                    with patch.object(Path,'read_bytes',corrupt),self.assertRaises(ValueError):source.freeze(self.root,self.out)
                    checks+=1
        self.assertEqual(checks,26)
        if (self.out/'first-predicted.elf').exists():
            expected=source.predicted_image(raw(self.out/'before-01'),self.rom)
            self.assertEqual(raw(self.out/'first-predicted.elf'),expected)
        self.receipt('input-audit',input_corruptions_rejected=checks,installed=self.installed,other_ELF_bytes_fixed=True)


if __name__=='__main__':unittest.main()
