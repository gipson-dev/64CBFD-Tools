"""Direct heading-clamp emission, circular boundaries and observed caller ABI."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_heading_clamp as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORDS,ACTOR,NESTED=0x30000,0x50000,0x60000
DELTAS=(0,1,0x23FF,0x2400,0x2401,0x2402,0x7FFF,0x8000,0x8001,
    0xDBFD,0xDBFE,0xDBFF,0xDC00,0xDC01,0xFFFF)
TARGETS=(0,1,0x2400,0x3FFF,0x4000,0x7FFF,0x8000,0xDBFF,0xFFFF)
HEADER='#include <ultra64.h>\nextern u8 *D_800872A0;\n'


def addr(a):return a&0xFFFFFFFF


def limited(target,current):
    delta=(target-current)&65535
    if delta>0x7FFF:
        return (target+0x2400)&65535 if (delta^65535)>0x2400 else current
    return (target-0x2400)&65535 if delta>0x2400 else current


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x400}


def fixture(index=0,target=0,delta=0,active=True,phase=0,table=source.TABLE):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x400)}
    for a,n in ((table,4),(ACTOR,0x330),(NESTED,0x90)):
        memory.update({a+i:0xA5 for i in range(n)})
    row=addr(RECORDS+index*0x84)
    memory.update({addr(row+i):0xA5 for i in range(0x84)})
    put(memory,table,RECORDS if active else 0)
    put(memory,row+0x10,0x80000000^(index&65535));put(memory,row+0xC,0x7FC12345^(index&65535))
    put(memory,ACTOR+0x76,(target-delta)&65535,2)
    put(memory,ACTOR+0x31C,NESTED);put(memory,NESTED+0x4E,0x7B,1)
    return memory,(index&0xFFFFFFFF,ACTOR)


def effects(memory,actor,mode,table):
    if mode==1:put(memory,actor+0x76,0xDBFF,2)
    elif mode==2:put(memory,table,0)


def reference(initial,args,target,mode=0,table=source.TABLE,provider=source.PROVIDER):
    memory=dict(initial);calls=[]
    if read(memory,table):
        row=addr(read(memory,table)+args[0]*0x84)
        calls=[(provider,(read(memory,row+0x10),read(memory,row+0xC),0))]
        effects(memory,args[1],mode,table)
        old=read(memory,args[1]+0x76,2);new=limited(target,old)
        if new!=old:put(memory,args[1]+0x76,new,2)
    return public(memory),calls


class ClampOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,target,mode=0,phase=0,table=source.TABLE,
            provider=source.PROVIDER,entry=source.ENTRY,connected=None):
        self.target,self.clamp_mode,self.clamp_table,self.provider=target,mode,table,provider
        self.actor=args[1];self.forwarded=[];self.reads=[];self.clamp_writes=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.reads.append((address,size,value))
        return value

    def put(self,address,value,size):
        if self.own_instruction and not STACK-0x100<=address<STACK+0x400:
            self.clamp_writes.append((address,size,value&((1<<(size*8))-1)))
        super().put(address,value,size)

    def record_call(self,target):
        if target==source.ENTRY:
            self.forwarded.append(self.arguments(2));return
        if target!=self.provider:raise AssertionError('Unexpected clamp provider '+hex(target))
        self.calls.append((target,(self.f[12],self.f[14],self.r[6])))

    def hook(self,target):
        effects(self.memory,self.actor,self.clamp_mode,self.clamp_table)
        for j in range(4):put(self.memory,self.r[29]+j*4,0xB5000000+j)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=(self.target-0x4000)&65535


def controls():
    b=source.SELECTED
    return {
        'symmetric-negative':b.replace('delta < 0xDBFF','delta < 0xDC00'),
        'positive-off-by-one':b.replace('delta >= 0x2401','delta >= 0x2402'),
        'wrong-record-stride':b.replace('recordIndex * 0x84','recordIndex * 0x80'),
        'wrong-actor-field':b.replace('actor + 0x76','actor + 0x74'),
        'missing-quarter-turn':b.replace(' + 0x4000',' + 0'),
        'swapped-floats':b.replace('record + 0x10','record + SWAP').replace(
            'record + 0x0C','record + 0x10').replace('record + SWAP','record + 0x0C'),
        'cached-actor-heading':b.replace('    u16 delta;','    u16 delta;\n    u16 old = *(u16 *)(actor + 0x76);').replace(
            'delta = target - *(u16 *)(actor + 0x76);','delta = target - old;'),
    }


NATIVE=HEADER+r'''
typedef struct {u8 pad[12];f32 z,x;u8 tail[112];} Record;
typedef struct {u8 pad[0x76];u16 heading;u8 tail[8];} Actor;
static Record records[4];static Actor actor;
u8 *D_800872A0;static u32 target,mode,calls,error,which;
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
u16 func_1505A630(f32 x,f32 z,s32 zero){
 if(word(x)!=word(records[which].x)||word(z)!=word(records[which].z)||zero)error=1;
 calls++;if(mode==1)actor.heading=0xDBFF;else if(mode==2)D_800872A0=0;
 return (u16)(target-0x4000u);}
void func_15087E54(s32,u8*);
static u16 limited(u32 t,u32 old){u32 d=(t-old)&65535u;
 if(d>32767u){if((d^65535u)>9216u)return (u16)(t+9216u);}
 else if(d>9216u)return (u16)(t-9216u);return (u16)old;}
static int check(u32 d,u32 t,u32 index,u32 m,u32 active){
 u32 i;u16 wanted;u8 before[sizeof(actor)],*a=(u8*)&actor;
 target=t;mode=m;which=index;calls=error=0;D_800872A0=active?(u8*)records:0;
 for(i=0;i<sizeof(actor);i++)a[i]=0xA5;actor.heading=(u16)(t-d);
 wanted=active?limited(t,m==1?0xDBFF:actor.heading):actor.heading;
 for(i=0;i<sizeof(actor);i++)before[i]=a[i];
 func_15087E54((s32)index,a);
 if(error||calls!=active||actor.heading!=wanted)return 23;
 if(D_800872A0!=((active&&m!=2)?(u8*)records:0))return 23;
 for(i=0;i<sizeof(actor);i++)if(i!=0x76&&i!=0x77&&a[i]!=before[i])return 23;
 for(i=0;i<4;i++){
 if(word(records[i].x)!=(0x3F800000u+i*0x10000u)||word(records[i].z)!=(0xC0000000u+i*0x10000u))return 23;
 {u32 j;u8*r=(u8*)(records+i);for(j=0;j<sizeof(Record);j++)if((j<12||j>=20)&&r[j]!=0xA5)return 23;}}
 return 0;}
static int run(void){u32 d,t,i,m,n=0,j;int status;
 static const u32 targets[]={0,0x4000,0x8000,0xFFFF};
 static const u32 edges[]={0,1,0x23FF,0x2400,0x2401,0x2402,0x7FFF,0x8000,0x8001,
 0xDBFD,0xDBFE,0xDBFF,0xDC00,0xDC01,0xFFFF};
 if(sizeof(void*)!=4||sizeof(Record)!=0x84||sizeof(Actor)!=0x80)return 29;
 for(i=0;i<sizeof(records);i++)((u8*)records)[i]=0xA5;
 for(i=0;i<4;i++){records[i].x=real(0x3F800000u+i*0x10000u);records[i].z=real(0xC0000000u+i*0x10000u);}
 for(d=0;d<65536;d++)for(t=0;t<4;t++){
 status=check(d,targets[t],(d>>12)&3,(d>>14)&1,1);if(status)return status;n++;}
 for(j=0;j<15;j++)for(t=0;t<4;t++)for(i=0;i<4;i++)for(m=0;m<3;m++){
 status=check(edges[j],targets[t],i,m,1);if(status)return status;n++;}
 for(i=0;i<4;i++)for(m=0;m<3;m++){
 status=check(0x8000,0x4000,i,m,0);if(status)return status;n++;}
 return n==262876?0:29;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class HeadingClampTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>39I',cls.rom,source.ROM)

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_direct_slot_circular_boundaries_saved_actor_and_helper_effects(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(39,24,0,72))
        count=0;seen=set()
        for target,delta,index,phase in itertools.product(TARGETS,DELTAS,(0,3,255),(0,8)):
            memory,args=fixture(index,target,delta,phase=phase)
            expected,calls=reference(memory,args,target)
            models=[ClampOracle(w,memory,args,target,phase=phase).run() for w in (self.words,self.truth)]
            for m in models:
                self.assertEqual((public(m.memory),m.calls),(expected,calls))
                old=read(memory,ACTOR+0x76,2);new=read(expected,ACTOR+0x76,2)
                self.assertEqual(m.clamp_writes,[(ACTOR+0x76,2,new)] if old!=new else [])
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual((models[0].memory,models[0].r,models[0].f,models[0].reads),
                (models[1].memory,models[1].r,models[1].f,models[1].reads))
            seen.update(models[0].visits);count+=1
        extra=0
        for index,active,mode,phase in itertools.product((-1,0x10001),(False,True),range(3),(0,8)):
            memory,args=fixture(index,0x4000,0x8000,active,phase)
            expected,calls=reference(memory,args,0x4000,mode)
            m=ClampOracle(self.words,memory,args,0x4000,mode,phase).run()
            self.assertEqual((public(m.memory),m.calls),(expected,calls));extra+=1
        self.assertEqual(count,810);self.assertEqual(extra,24)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+156,4))<=seen)
        self.receipt('guest',paired_cases=count,additional_null_wide_index_helper_effect_cases=extra,
            all39_words=True,provider_float_arguments_are_exact_bits=True,helper_scripted=True)

    def test_02_native32_all65536_deltas_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        cases=[('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
            (n,'-O2',b,23) for n,b in controls().items()]
        for name,opt,body,status in cases:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=90).returncode,status,name)
        self.receipt('native',cases_per_profile=262876,all65536_deltas=True,UBSan=True,
            native_indices=[0,1,2,3],effective_result_controls=7,control_exit=23)

    def test_03_guest_controls_change_memory_or_observed_helper_arguments(self):
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name)
            self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for target,delta,index,mode in itertools.product((0,0x4000,0xFFFF),DELTAS,(0,3),range(3)):
                memory,args=fixture(index,target,delta);expected,calls=reference(memory,args,target,mode)
                try:m=ClampOracle(words,memory,args,target,mode).run()
                except AssertionError as error:
                    if 'unmapped read' not in str(error):raise
                    continue
                if (public(m.memory),m.calls)!=(expected,calls):break
            else:self.fail('Ineffective guest control: '+name)

    def test_04_independent_original_C_rebased_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-clamp',
            source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raw,bindings=source.checked_object(self.obj);count=0
        placements=((source.ENTRY,source.TABLE,source.PROVIDER),
            (0x16218004,0x12347FFC,0x18228004),(0x18FFF000,0x12348004,0x15507FFC))
        for i,(entry,table,provider) in enumerate(placements):
            anchors=dict(D_800872A0=table,func_1505A630=provider)
            text,unresolved=emit_function(raw,dict(value=0,size=len(raw)),bindings,source.FUNCTION,anchors)
            self.assertFalse(unresolved)
            path=self.out/('rebase-C-%d.s'%i);path.write_text(text);obj=path.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
            bodies=[]
            for label,target in (('original',original),('C',obj)):
                script=self.out/('rebase-%d-%s.ld'%(i,label));elf=script.with_suffix('.elf')
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%v for v in anchors.items()],'-o',str(elf),str(target)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>39I',sections(elf)['.text'][1])))
            self.assertEqual(*bodies)
            for delta,active,mode,phase in itertools.product(DELTAS,(False,True),range(3),(0,8)):
                memory,args=fixture(3,0xFFFF,delta,active,phase,table)
                expected,calls=reference(memory,args,0xFFFF,mode,table,provider)
                for words in bodies:
                    m=ClampOracle(words,memory,args,0xFFFF,mode,phase,table,provider,entry).run()
                    self.assertEqual((public(m.memory),m.calls),(expected,calls))
                count+=1
        self.receipt('rebases',independent_original_C_links=6,paired_cases=count,three_bindings=True)

    def test_05_target_access_fault_prefixes(self):
        count=states=0
        for delta,active,mode,phase in itertools.product((0,0x2401,0xDBFE,0xDBFF),(False,True),range(3),(0,8)):
            memory,args=fixture(3,0xFFFF,delta,active,phase)
            complete=ClampOracle(self.words,memory,args,0xFFFF,mode,phase).run()
            for fault in range(complete.all_accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    m=ClampOracle(words,memory,args,0xFFFF,mode,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault)
                    pairs.append((m.memory,m.r,m.f,m.events,m.calls,m.reads,m.current_pc,m.delay_of,m.all_accesses))
                self.assertEqual(*pairs);count+=1
            states+=1
        self.receipt('faults',states=states,equal_fault_prefixes=count,helper_internals_excluded=True)

    def test_06_retail_caller_delivery_and_updated_angle_consumer(self):
        entry,stop=0x1504D384,0x1504D3A8
        caller=struct.unpack_from('>9I',self.rom,entry-0x14FD2B50)
        self.assertEqual(caller[:2],(0x0D421F95,0x90843E78))
        setup=struct.unpack_from('>2I',self.rom,0x1504D268-0x14FD2B50)
        self.assertEqual(setup,(0x3C04800C,0x02002825))
        refs={n:[i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==v]
            for n,v in dict(pointer=source.ENTRY,jal=0x0D421F95,jump=0x09421F95).items()}
        self.assertEqual(refs,dict(pointer=[],jal=[0x7A834],jump=[]))
        elf=source.raw_read(self.root/'conker/build/conker.us.elf')
        at=source.elf_slot_offset(elf,source.PROVIDER,200)
        self.assertEqual(elf[at:at+200],self.rom[0x87AE0:0x87BA8])
        parent=source.raw_text(self.root/'conker/src/game_77AD0.c')
        lo,hi=source.function_span(parent,'func_1504CB98')
        self.assertEqual(parent[lo:hi],'s32 func_1504CB98() {\n    return 0;\n}')
        class Boundary(Exception):pass
        class StopCode(dict):
            def __getitem__(self,pc):
                if pc==stop:raise Boundary
                return tracked[0].__getitem__(pc)
        connected=dict(zip(range(source.ENTRY,source.ENTRY+156,4),self.words));count=0
        for index,delta,target,active,phase in itertools.product((0,3,255),(0,0x2401,0xDBFF,0x8000),
                (0,0xFFFF),(False,True),(0,8)):
            memory,args=fixture(index,target,delta,active,phase)
            put(memory,0x800C3E78,index,1);put(memory,0x800CC280,0x12345678)
            expected,calls=reference(memory,args,target)
            expectedAngle=read(expected,ACTOR+0x76,2)
            m=ClampOracle(caller,memory,args,target,phase=phase,entry=entry,connected=connected)
            m.r[4]=0x800C0000;m.r[5]=m.r[16]=ACTOR
            tracked=[m.code];m.code=StopCode(m.code)
            with self.assertRaises(Boundary):m.run()
            self.assertEqual(m.forwarded,[args]);self.assertEqual((public(m.memory),m.calls),(expected,calls))
            self.assertEqual(read(m.memory,STACK+phase+0x1BC,2),(expectedAngle-0x12345678)&65535)
            self.assertEqual(m.r[2],0x7B);self.assertEqual(m.r[16],ACTOR);count+=1
        self.receipt('caller',bounded_windows=count,static_setup_checked=True,parent_production_stub=True,
            helper200bytes_retail_exact=True,whole_parent_or_helper_not_executed=True)

    def test_07_raw_words_bindings_inputs_and_installed_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        for i in range(39):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with source.historical_view(self.root,self.out):
            read_bytes=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read_bytes(x)+b'\n' if x==path else read_bytes(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
