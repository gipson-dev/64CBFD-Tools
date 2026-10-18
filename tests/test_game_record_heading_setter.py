"""Mode-byte and unordered float predicates, captured records and caller gates."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_heading_setter as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
RECORDS,OTHER,ACTOR=0x30000,0x70000,0x50000
SPEEDS=(0,0x80000000,1,0x80000001,0x00800000,0x80800000,0x3EFFFFFF,
    0x3F000000,0x3F000001,0xBF000000,0x3F800000,0x7F7FFFFF,0xFF7FFFFF,
    0x7F800000,0xFF800000,0x7FC12345,0xFFC0ABCD)
ANGLES=(0,1,0x7FFF,0xB5FF,0xB600,0xC9FF,0xCA00,0xFFFF)
HEADER='#include <ultra64.h>\nextern u8 *D_800872A0;\nextern s8 D_800D23A8;\n'


def addr(a):return a&0xFFFFFFFF


def low(bits):return bits&0x7FFFFFFF<=0x7F800000 and (bits&0x80000000!=0 or bits<0x3F000000)


def high(bits):return bits&0x7FFFFFFF<=0x7F800000 and bits&0x80000000==0 and bits>=0x3F000000


def opposite(bits):return 0x3F000001 if low(bits) else 0x3EFFFFFF


def heading(angle,mode,speed):return (angle+(0x4A00 if (low(speed) if mode==0 else high(speed)) else 0x3600))&65535


def public(memory):return {a:v for a,v in memory.items() if not STACK-0x100<=a<STACK+0x400}


def fixture(index=0,mode=0,speed=0,active=True,phase=0,table=source.TABLE,mode_address=source.MODE):
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x100,0x400)}
    for a,n in ((table,4),(mode_address,1),(ACTOR,0x100)):
        memory.update({a+i:0xA5 for i in range(n)})
    for bank in (RECORDS,OTHER):
        row=addr(bank+index*0x84)
        memory.update({addr(row+i):0xA5 for i in range(-0x20,0xA4)})
        put(memory,row,speed if bank==RECORDS else opposite(speed))
        put(memory,row+0x10,0x3F800000^(index&65535));put(memory,row+0xC,0xC0000000^(index&65535))
    put(memory,table,RECORDS if active else 0);put(memory,mode_address,mode,1)
    return memory,(index&0xFFFFFFFF,ACTOR)


def effects(memory,row,pattern,table,mode_address):
    if pattern==1:put(memory,mode_address,0x80 if read(memory,mode_address,1)==0 else 0,1)
    elif pattern==2:put(memory,row,opposite(read(memory,row)))
    elif pattern==3:put(memory,table,OTHER)


def reference(initial,args,angle,pattern=0,table=source.TABLE,mode_address=source.MODE,provider=source.PROVIDER):
    memory=dict(initial);calls=[];reads=[(table,4,read(memory,table))]
    if read(memory,table):
        row=addr(read(memory,table)+args[0]*0x84)
        x,z=read(memory,row+0x10),read(memory,row+0xC)
        calls=[(provider,(x,z,0))];reads.extend(((row+0x10,4,x),(row+0xC,4,z)))
        effects(memory,row,pattern,table,mode_address)
        mode,speed=read(memory,mode_address,1),read(memory,row)
        reads.extend(((mode_address,1,mode),(row,4,speed)))
        put(memory,args[1]+0x76,heading(angle,mode,speed),2)
    return public(memory),calls,reads


class SetterOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,angle,pattern=0,phase=0,table=source.TABLE,
            mode_address=source.MODE,provider=source.PROVIDER,entry=source.ENTRY,connected=None):
        self.angle,self.setter_pattern,self.table,self.mode_address,self.provider=angle,pattern,table,mode_address,provider
        self.row=addr(read(memory,table)+args[0]*0x84);self.forwarded=[]
        self.setter_reads=[];self.setter_writes=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if word>>26!=0x20:return super().execute(word)
        self.dispatched_word=word;self.own_instruction=True
        try:
            rs,rt=(word>>21)&31,(word>>16)&31
            value=self.get(addr(self.r[rs]+((word&65535)^32768)-32768),1)
            self.r[rt]=(value-256 if value&128 else value)&0xFFFFFFFF
            self.r[0]=0
        finally:self.own_instruction=False

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction and not STACK-0x100<=address<STACK+0x400:
            self.setter_reads.append((address,size,value))
        return value

    def put(self,address,value,size):
        if self.own_instruction and not STACK-0x100<=address<STACK+0x400:
            self.setter_writes.append((address,size,value&((1<<(size*8))-1)))
        super().put(address,value,size)

    def record_call(self,target):
        if target==source.ENTRY:
            self.forwarded.append(self.arguments(2));return
        if target!=self.provider:raise AssertionError('Unexpected heading setter helper '+hex(target))
        self.calls.append((target,(self.f[12],self.f[14],self.r[6])))

    def hook(self,target):
        effects(self.memory,self.row,self.setter_pattern,self.table,self.mode_address)
        for j in range(4):put(self.memory,self.r[29]+j*4,0xB5000000+j)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=self.angle


def controls():
    b=source.SELECTED
    return {
        'zero-mode-inclusive':b.replace('record < 0.5f','record <= 0.5f'),
        'nonzero-mode-exclusive':b.replace('record >= 0.5f','record > 0.5f'),
        'unordered-negation':b.replace('*(f32 *)record >= 0.5f','!(*(f32 *)record < 0.5f)'),
        'cached-mode':b.replace('    u16 heading;','    u16 heading;\n    s8 cachedMode = D_800D23A8;').replace(
            'if (D_800D23A8 == 0)','if (cachedMode == 0)'),
        'cached-speed':b.replace('    u16 heading;','    u16 heading;\n    f32 speed;').replace(
            'record = D_800872A0 + recordIndex * 0x84;',
            'record = D_800872A0 + recordIndex * 0x84;\n        speed = *(f32 *)record;').replace(
            '*(f32 *)record < 0.5f','speed < 0.5f').replace('*(f32 *)record >= 0.5f','speed >= 0.5f'),
        'reloaded-record':b.replace('        if (D_800D23A8 == 0)',
            '        record = D_800872A0 + recordIndex * 0x84;\n        if (D_800D23A8 == 0)'),
        'wrong-record-stride':b.replace('recordIndex * 0x84','recordIndex * 0x80'),
        'wrong-offset':b.replace('0x4A00','0x4B00'),
        'swapped-floats':b.replace('record + 0x10','record + SWAP').replace(
            'record + 0x0C','record + 0x10').replace('record + SWAP','record + 0x0C'),
    }


NATIVE=HEADER+r'''
typedef struct {f32 speed;u8 pad[8];f32 z,x;u8 tail[112];} Record;
typedef struct {u8 pad[0x76];u16 heading;u8 tail[8];} Actor;
static Record records[4],other[4];static Actor actor;
u8 *D_800872A0;s8 D_800D23A8;
static u32 result,pattern,calls,error,which;
static u32 failure[12];
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 low(u32 s){return (s&0x7FFFFFFFu)<=0x7F800000u&&((s&0x80000000u)||s<0x3F000000u);}
static u32 high(u32 s){return (s&0x7FFFFFFFu)<=0x7F800000u&&!(s&0x80000000u)&&s>=0x3F000000u;}
static u32 opposite(u32 s){return low(s)?0x3F000001u:0x3EFFFFFFu;}
u16 func_1505A630(f32 x,f32 z,s32 zero){
 if(word(x)!=word(records[which].x)||word(z)!=word(records[which].z)||zero)error=1;
 calls++;if(pattern==1)*(u8*)&D_800D23A8=D_800D23A8==0?0x80:0;
 else if(pattern==2)records[which].speed=real(opposite(word(records[which].speed)));
 else if(pattern==3)D_800872A0=(u8*)other;return (u16)result;}
void func_15087EF0(s32,u8*);
static int fail(u32 tag,u32 a,u32 m,u32 s,u32 i,u32 p,u32 active,u32 wanted){
 failure[0]=tag;failure[1]=a;failure[2]=m;failure[3]=s;failure[4]=i;failure[5]=p;
 failure[6]=active;failure[7]=wanted;failure[8]=actor.heading;failure[9]=calls;
 failure[10]=error;failure[11]=(u8)D_800D23A8;return 23;}
static int check(u32 angle,u32 m,u32 s,u32 index,u32 p,u32 active){
 u32 i,j,wm=m,ws=s;u16 wanted=0xA5A5;u8*a=(u8*)&actor;
 result=angle;pattern=p;which=index;calls=error=0;
 D_800872A0=active?(u8*)records:0;*(u8*)&D_800D23A8=(u8)m;
 for(i=0;i<4;i++){records[i].speed=real(s);other[i].speed=real(opposite(s)^i);}
 records[index].speed=real(s);for(i=0;i<sizeof(actor);i++)a[i]=0xA5;
 if(active){if(p==1)wm=m==0?0x80:0;else if(p==2)ws=opposite(s);
 wanted=(u16)(angle+((wm==0?low(ws):high(ws))?0x4A00u:0x3600u));}
 func_15087EF0((s32)index,a);
 if(error||calls!=active||actor.heading!=wanted||(u8)D_800D23A8!=wm)return fail(1,angle,m,s,index,p,active,wanted);
 if(D_800872A0!=(active?(p==3?(u8*)other:(u8*)records):0))return fail(2,angle,m,s,index,p,active,wanted);
 for(i=0;i<sizeof(actor);i++)if(i!=0x76&&i!=0x77&&a[i]!=0xA5)return fail(3,angle,m,s,index,p,active,wanted);
 for(i=0;i<4;i++){
 if(word(records[i].speed)!=(i==index?ws:s)||word(other[i].speed)!=(opposite(s)^i))return fail(4,angle,m,s,index,p,active,wanted);
 if(word(records[i].x)!=(0x3F800000u+i*0x10000u)||word(records[i].z)!=(0xC0000000u+i*0x10000u))return fail(5,angle,m,s,index,p,active,wanted);
 if(word(other[i].x)!=word(records[i].x)||word(other[i].z)!=word(records[i].z))return fail(6,angle,m,s,index,p,active,wanted);
 for(j=0;j<sizeof(Record);j++)if((j>=4&&j<12)||j>=20){
 if(((u8*)(records+i))[j]!=0xA5||((u8*)(other+i))[j]!=0xA5)return fail(7,angle,m,s,index,p,active,wanted);}}
 return 0;}
static int run(void){u32 a,m,s,i,p,n=0;int status;
 static const u32 speeds[]={0,0x80000000,1,0x80000001,0x00800000,0x80800000,
 0x3EFFFFFF,0x3F000000,0x3F000001,0xBF000000,0x3F800000,0x7F7FFFFF,0xFF7FFFFF,
 0x7F800000,0xFF800000,0x7FC12345,0xFFC0ABCD};
 static const u32 angles[]={0,1,0x7FFF,0xB5FF,0xB600,0xC9FF,0xCA00,0xFFFF};
 if(sizeof(void*)!=4||sizeof(Record)!=0x84||sizeof(Actor)!=0x80)return 29;
 for(i=0;i<sizeof(records);i++){((u8*)records)[i]=0xA5;((u8*)other)[i]=0xA5;}
 for(i=0;i<4;i++){records[i].x=other[i].x=real(0x3F800000u+i*0x10000u);
 records[i].z=other[i].z=real(0xC0000000u+i*0x10000u);}
 for(m=0;m<256;m++)for(s=0;s<17;s++)for(a=0;a<8;a++)for(i=0;i<4;i++){
 status=check(angles[a],m,speeds[s],i,0,1);if(status)return status;n++;}
 for(a=0;a<65536;a++)for(m=0;m<4;m++){
 status=check(a,m<2?0:0x80,m&1?0x3F000000u:0x3EFFFFFFu,a&3,0,1);if(status)return status;n++;}
 for(s=0;s<17;s++)for(a=0;a<8;a++)for(i=0;i<4;i++)for(p=0;p<4;p++){
 status=check(angles[a],i&1?0:0xFF,speeds[s],i,p,1);if(status)return status;n++;}
 for(a=0;a<8;a++)for(i=0;i<4;i++)for(p=0;p<4;p++){
 status=check(angles[a],i&1?0:0xFF,0x7FC12345,i,p,0);if(status)return status;n++;}
 return n==403712?0:29;}
void _start(void){int status=run();if(status==23){
 __asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(failure),"d"(sizeof(failure)):"memory");}
 __asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class HeadingSetterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>53I',cls.rom,source.ROM)

    def receipt(self,name,**row):
        (self.out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

    def test_01_mode_bytes_float_bits_captured_record_and_saved_state(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(53,32,0,72))
        def cases():
            yield from ((0,m,s,0xFFFF,0,True,p) for m,s,p in itertools.product(range(256),(0x3EFFFFFF,0x3F000000,0x7FC12345),(0,8)))
            yield from ((i,m,s,a,0,True,p) for i,m,s,a,p in itertools.product((0,3,255),(0,1,128,255),SPEEDS,(0,0xB600,0xCA00,0xFFFF),(0,8)))
        count=0;seen=set()
        for index,mode,speed,angle,pattern,active,phase in cases():
            memory,args=fixture(index,mode,speed,active,phase);expected,calls,reads=reference(memory,args,angle,pattern)
            models=[SetterOracle(w,memory,args,angle,pattern,phase).run() for w in (self.words,self.truth)]
            for m in models:
                self.assertEqual((public(m.memory),m.calls,m.setter_reads),(expected,calls,reads))
                self.assertEqual(m.setter_writes,[(ACTOR+0x76,2,read(expected,ACTOR+0x76,2))])
                self.assertEqual(m.r[15],(mode-256 if mode&128 else mode)&0xFFFFFFFF)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            self.assertEqual((models[0].memory,models[0].r,models[0].f),(models[1].memory,models[1].r,models[1].f))
            seen.update(models[0].visits);count+=1
        extra=0
        for index,active,pattern,phase in itertools.product((-1,0x10001),(False,True),range(4),(0,8)):
            memory,args=fixture(index,0,0x3EFFFFFF,active,phase);expected,calls,reads=reference(memory,args,0xCA00,pattern)
            m=SetterOracle(self.words,memory,args,0xCA00,pattern,phase).run()
            self.assertEqual((public(m.memory),m.calls,m.setter_reads),(expected,calls,reads));extra+=1
        self.assertEqual(count,3168);self.assertEqual(extra,32)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+212,4))<=seen)
        self.receipt('guest',paired_cases=count,additional_null_wide_index_helper_effect_cases=extra,
            all53_words=True,all256_mode_bytes=True,exact_public_read_write_traces=True,helper_scripted=True)

    def test_02_native32_O2_O0_UBSan_all_angles_modes_and_result_controls(self):
        harness=self.out/'native-driver.c';harness.write_text(NATIVE)
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            unit=self.out/('native-'+name+'.c');unit.write_text(HEADER+body);exe=unit.with_suffix('')
            result=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],timeout=90,capture_output=True)
            detail=struct.unpack('<12I',run.stderr) if len(run.stderr)==48 else run.stderr.hex()
            self.assertEqual(run.returncode,status,(name,detail))
        self.receipt('native',cases_per_profile=403712,all65536_angles=True,all256_mode_bytes=True,
            speed_bit_patterns=17,UBSan=True,native_indices=[0,1,2,3],effective_observable_controls=9,control_exit=23)

    def test_03_guest_controls_change_memory_or_helper_observations(self):
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,HEADER+body,'negative-'+name)
            self.assertFalse(diagnostics)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
            for mode,speed,index,pattern in itertools.product((0,1,128),(0x3EFFFFFF,0x3F000000,0x7FC12345),(0,3),range(4)):
                memory,args=fixture(index,mode,speed);expected,calls,_=reference(memory,args,0xB600,pattern)
                m=SetterOracle(words,memory,args,0xB600,pattern).run()
                if (public(m.memory),m.calls)!=(expected,calls):break
            else:self.fail('Ineffective guest control: '+name)

    def test_04_original_and_C_independent_rebased_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-setter',
            source.raw_text(self.root/'conker/asm/B3020.s'),source.FUNCTION)
        raw,bindings=source.checked_object(self.obj);count=0
        placements=((source.ENTRY,source.TABLE,source.MODE,source.PROVIDER),
            (0x16218004,0x12347FFC,0x800D8004,0x18228004),(0x18FFF000,0x12348004,0x800D7FFC,0x15507FFC))
        for i,(entry,table,mode_address,provider) in enumerate(placements):
            anchors=dict(D_800872A0=table,D_800D23A8=mode_address,func_1505A630=provider)
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
                bodies.append(list(struct.unpack_from('>53I',sections(elf)['.text'][1])))
            self.assertEqual(*bodies)
            for mode,speed,active,pattern,phase in itertools.product((0,128),(0x3EFFFFFF,0x3F000000,0x7FC12345),
                    (False,True),range(4),(0,8)):
                memory,args=fixture(3,mode,speed,active,phase,table,mode_address)
                expected,calls,reads=reference(memory,args,0xCA00,pattern,table,mode_address,provider)
                for words in bodies:
                    m=SetterOracle(words,memory,args,0xCA00,pattern,phase,table,mode_address,provider,entry).run()
                    self.assertEqual((public(m.memory),m.calls,m.setter_reads),(expected,calls,reads))
                count+=1
        self.receipt('rebases',independent_original_C_links=6,paired_cases=count,five_bindings=True)

    def test_05_target_access_fault_prefixes(self):
        count=states=0
        for mode,speed,active,pattern,phase in itertools.product((0,255),(0x3F000000,0x7FC12345),
                (False,True),range(4),(0,8)):
            memory,args=fixture(3,mode,speed,active,phase)
            complete=SetterOracle(self.words,memory,args,0xCA00,pattern,phase).run()
            for fault in range(complete.all_accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    m=SetterOracle(words,memory,args,0xCA00,pattern,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    self.assertEqual(m.all_accesses,fault)
                    pairs.append((m.memory,m.r,m.f,m.events,m.calls,m.setter_reads,m.setter_writes,
                        m.current_pc,m.delay_of,m.all_accesses))
                self.assertEqual(*pairs);count+=1
            states+=1
        self.receipt('faults',states=states,equal_fault_prefixes=count,helper_internals_excluded=True)

    def test_06_retail_caller_setup_gate_call_and_float_reset(self):
        entry,stop=0x15051678,0x15051698
        caller=struct.unpack_from('>8I',self.rom,entry-0x14FD2B50)
        self.assertEqual(caller[1:3],(0x3C04800C,0x02002825));self.assertEqual(caller[5:7],(0x0D421FBC,0x90843E78))
        refs={n:[i for i in range(0,len(self.rom)-3,4) if struct.unpack_from('>I',self.rom,i)[0]==v]
            for n,v in dict(pointer=source.ENTRY,jal=0x0D421FBC,jump=0x09421FBC).items()}
        self.assertEqual(refs,dict(pointer=[],jal=[0x7EB3C],jump=[]))
        elf=source.raw_read(self.root/'conker/build/conker.us.elf');at=source.elf_slot_offset(elf,source.PROVIDER,200)
        self.assertEqual(elf[at:at+200],self.rom[0x87AE0:0x87BA8])
        parent=source.raw_text(self.root/'conker/src/game_77AD0.c');lo,hi=source.function_span(parent,'func_15051558')
        self.assertEqual(parent[lo:hi],'s32 func_15051558() {\n    return 0;\n}')
        class Boundary(Exception):pass
        class StopCode(dict):
            def __getitem__(self,pc):
                if pc==stop:raise Boundary
                return tracked[0].__getitem__(pc)
        connected=dict(zip(range(source.ENTRY,source.ENTRY+212,4),self.words));count=0
        for gate,index,mode,speed,active,pattern,phase in itertools.product((0,1,255),(0,3,255),(0,128),
                (0x3F000000,0x7FC12345),(False,True),(0,1,2,3),(0,8)):
            memory,args=fixture(index,mode,speed,active,phase);put(memory,ACTOR+0x89,gate,1);put(memory,0x800C3E78,index,1)
            expected,calls,_=reference(memory,args,0xB600,pattern) if gate==0 else (public(memory),[],[])
            m=SetterOracle(caller,memory,args,0xB600,pattern,phase,entry=entry,connected=connected)
            m.r[4]=m.r[5]=0x12345678;m.r[16]=ACTOR;m.f[0]=0xFFC12345
            tracked=[m.code];m.code=StopCode(m.code)
            with self.assertRaises(Boundary):m.run()
            self.assertEqual(m.forwarded,[args] if gate==0 else []);self.assertEqual((public(m.memory),m.calls),(expected,calls))
            self.assertEqual(m.r[16],ACTOR);self.assertEqual(m.f[0],0);count+=1
        self.receipt('caller',bounded_windows=count,actual_setup_and_gate_and_call_delay=True,
            parent_production_stub=True,helper200bytes_retail_exact=True,whole_parent_or_helper_not_executed=True)

    def test_07_words_bindings_inputs_and_installed_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,bindings=source.checked_object(self.obj)
        for i in range(53):
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
