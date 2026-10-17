"""Qualify the full uninstalled burst while keeping private/padding gaps visible."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_owner_burst_emitter as source
from tools.tests import test_game_actor_scale_timer as scale
from tools.tests import test_game_actor_burst_consumer_match as faults
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_actor_buffer_copy_match import CopyOracle
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

STACK,ACTOR,OWNER,MODEL,CREATED=scale.STACK,0x20000,0x22000,0x24000,0x30000
PAYLOAD_HOLES=(5,6,7)
DESCRIPTOR_HOLES=(6,7,0x4D,0x4E,0x4F)


def rounded(value):return floating(bits(value))
def signed_byte(v):return (v&255)-256 if v&128 else v&255
def unsigned(v):return math.trunc(v)&255 if math.isfinite(v) and -1.<v<2**32 else 255
def public(memory):return {a:v for a,v in memory.items() if not STACK-0x600<=a<STACK+0x140}
def blob(memory,at,n):return bytes(memory[at+i] for i in range(n))
def word(memory,at,value):put(memory,at,value if isinstance(value,int) else bits(value))


def fixture(gate=0,state=0,previous=0,count=3,time=4.5,step=1.,basis=True,allocate=True,
            samples=(.5,.25),mode=0,pattern=0,phase=0,symbols=None,base_override=1025.75):
    s=symbols or source.SYMBOLS
    case=dict(gate=gate,state=state,previous=previous,count=count,time=time,step=step,basis=basis,
        allocate=allocate,samples=samples,mode=mode,pattern=pattern,phase=phase,symbols=s,base_override=base_override)
    memory={STACK+i:((i*17+0xA5)&255 if pattern else 0xA5) for i in range(-0x600,0x140)}
    for at,n in ((ACTOR,0x100),(OWNER,0x240),(CREATED,0x800)):
        memory.update({at+i:0xA5 for i in range(n)})
    put(memory,ACTOR+1,2,1);put(memory,ACTOR+0xC,0x44,1);put(memory,ACTOR+0xE,0x1234,2)
    put(memory,ACTOR+0x28,OWNER);put(memory,ACTOR+0x2C,0x7F,1)
    put(memory,ACTOR+0x2D,previous,1);word(memory,ACTOR+0x30,time);put(memory,ACTOR+0x34,count,1)
    put(memory,OWNER,0 if gate==2 else 1);put(memory,OWNER+0x3B,0xFF if gate==3 else 0x7F,1)
    put(memory,OWNER+0x1D4,0 if gate==4 else MODEL);put(memory,OWNER+0x222,state,1)
    put(memory,s['D_800C35EA'],1 if gate==1 else 0,1)
    word(memory,s['D_800A1968'],.5);word(memory,s['D_800BE9A4'],step);word(memory,s['D_800A196C'],1.25)
    for i,v in enumerate((.125,-.25,.5)):word(memory,s['D_800A5480']+i*4,v)
    return memory,case


def mutation(memory,case,name,ordinal,payload_base=None):
    s=case['symbols'];mode=case['mode']
    if name=='fade' and mode==1:put(memory,OWNER+0x1D4,0)
    if name=='random' and ordinal==1 and mode==2:
        word(memory,s['D_800A196C'],7.5);put(memory,OWNER+0x3B,0xE1,1)
        for i,v in enumerate((3.5,-4.25,5.)):word(memory,s['D_800A5480']+i*4,v)
    if name=='basis' and mode==3 and payload_base is not None:word(memory,payload_base+0x14,case['base_override'])
    if name=='create' and ordinal==1 and mode==4:
        word(memory,ACTOR+0x30,2.);put(memory,ACTOR+0x34,2,1)


def descriptor(initial,case,position,base):
    stack=STACK+case['phase']-0x150
    data=bytearray(blob(initial,stack+0xF0,0x58))
    def setv(at,v,n=4):data[at:at+n]=(v&((1<<(8*n))-1)).to_bytes(n,'big')
    for at,v,n in ((0,0x79,1),(1,0xC,1),(2,0x4405,2),(4,0x12C,2),
            (8,0,4),(12,0,4),(0x10,0xD5DBFFFF,4),(0x14,0,4),(0x18,0,4),
            (0x40,0x04EC0000,4),(0x44,unsigned(base),1),(0x45,255,1),(0x46,0,1),(0x47,6,1),
            (0x48,0,4),(0x4C,255,1),(0x50,0,4),(0x54,1,2),(0x56,255,2)):
        setv(at,v,n)
    for i,v in enumerate(position):setv(0x1C+i*4,v)
    for i in range(3):
        setv(0x28+i*4,read(initial,case['symbols']['D_800A5480']+i*4));setv(0x34+i*4,bits(1.))
    return bytes(data)


def reference(initial,case):
    memory=dict(initial);s=case['symbols'];calls=[];iterations=0;randoms=0
    data=ACTOR+0x28
    if read(memory,s['D_800C35EA'],1)==1:return memory,calls,iterations
    owner=read(memory,data)
    if read(memory,owner)==0 or read(memory,data+4,1)!=read(memory,owner+0x3B,1):
        put(memory,ACTOR+0xE,65535,2);return memory,calls,iterations
    if read(memory,owner+0x222,1)!=read(memory,data+5,1) and read(memory,owner+0x222,1):
        put(memory,data+12,3,1);word(memory,data+8,0.)
    put(memory,data+5,read(memory,owner+0x222,1),1)
    if read(memory,owner+0x222,1):
        calls.append(('fade',(s['D_800CC2D0']+read(memory,owner+0x222,1)*0x32C,255,0,0,80,0,15)))
        mutation(memory,case,'fade',1)
    if read(memory,owner+0x1D4)==0 or signed_byte(read(memory,data+12,1))<=0:return memory,calls,iterations
    clock=rounded(floating(read(memory,s['D_800A1968']))*floating(read(memory,s['D_800BE9A4'])))
    word(memory,data+8,rounded(floating(read(memory,data+8))+clock))
    if not floating(read(memory,data+8))>1.:return memory,calls,iterations
    multiplier=read(memory,s['D_800A196C'])
    for _ in range(128):
        stack=STACK+case['phase']-0x150;payload=bytearray(blob(memory,stack+0xBC,52))
        def setv(at,v,n=4):payload[at:at+n]=(v&((1<<(8*n))-1)).to_bytes(n,'big')
        setv(0,owner);setv(4,read(memory,owner+0x3B,1),1);setv(8,0)
        calls.append(('random',()));randoms+=1;first=rounded(case['samples'][(randoms-1)%2]);mutation(memory,case,'random',randoms)
        limit=rounded(rounded(first*6.)+13.);setv(12,bits(limit));setv(16,multiplier)
        calls.append(('random',()));randoms+=1;second=rounded(case['samples'][(randoms-1)%2]);mutation(memory,case,'random',randoms)
        base=rounded(rounded(second*40.)+60.);denom=rounded(limit*limit)
        decay=rounded(base/denom if denom else (math.nan if not base else math.copysign(math.inf,base)))
        setv(20,bits(base));setv(24,bits(decay))
        calls.append(('transform',((s['D_800A1950'],s['D_800A195C']),read(memory,owner+0x1D4)+0x3C0,2)))
        position=tuple(map(bits,(1.,2.,3.)));delta=tuple(map(bits,(4.,5.,8.)))
        calls.append(('basis',(delta,)))
        if not case['basis']:return memory,calls,iterations
        for at,values in ((28,(0.,1.,0.)),(40,(1.,0.,0.))):
            for i,v in enumerate(values):setv(at+i*4,bits(v))
        if case['mode']==3:base=case['base_override'];setv(20,bits(base))
        request=descriptor(memory,case,position,base)
        args=(request,s['D_800A4AA0'],0x26,0,0,0x25,0,0,0,52,read(memory,ACTOR+0xC,1),read(memory,ACTOR+1,1))
        calls.append(('create',args));iterations+=1;mutation(memory,case,'create',iterations)
        if case['allocate']:
            dest=CREATED+(iterations-1)*0x180+0x110
            calls.append(('copy',(dest,bytes(payload),52)))
            for i,v in enumerate(payload):memory[dest+i]=v
        put(memory,data+12,read(memory,data+12,1)-1,1)
        word(memory,data+8,rounded(floating(read(memory,data+8))-1.))
        if not (floating(read(memory,data+8))>1. and signed_byte(read(memory,data+12,1))>0):return memory,calls,iterations
    raise AssertionError('Reference exceeded bounded counter domain')


class Oracle(scale.Oracle):
    def __init__(self,words,memory,case,entry=source.ENTRY):
        super().__init__(words,memory,ACTOR,phase=case['phase'],fcsr=3,entry=entry,symbols=case['symbols'])
        self.case=case;self.counts={};self.private_calls=[]
        self.names={case['symbols'][n]:k for k,n in (
            ('fade','func_1502EA98'),('random','func_150ADA68'),('transform','func_15145EA4'),
            ('basis','func_15146078'),('create','func_1513D2F0'),('copy','memcpy'))}

    def execute(self,word):
        if word>>26==32:
            self.own_instruction=True
            try:CopyOracle.execute(self,word)
            finally:self.own_instruction=False
        else:super().execute(word)

    def record_call(self,target):
        name=self.names[target];n={'fade':7,'random':0,'transform':4,'basis':3,'create':12,'copy':3}[name]
        args=self.arguments(n);self.private_calls.append((target,args));self.counts[name]=self.counts.get(name,0)+1
        if name=='transform':
            self.inputs=tuple(read(self.memory,args[0]+i*4) for i in range(2))
            self.outputs=tuple(read(self.memory,args[1]+i*4) for i in range(2));value=(self.inputs,args[2],args[3])
        elif name=='basis':value=(tuple(read(self.memory,args[0]+i*4) for i in range(3)),)
        elif name=='create':value=(blob(self.memory,args[0],88),*args[1:])
        elif name=='copy':value=(args[0],blob(self.memory,args[1],args[2]),args[2])
        else:value=args
        self.calls.append((name,value))

    def hook(self,target):
        name=self.names[target];args=self.private_calls[-1][1];ordinal=self.counts[name]
        result=0;sample=None
        if name=='transform':
            for at,values in zip(self.outputs,((1.,2.,3.),(5.,7.,11.))):
                for i,v in enumerate(values):self.put(at+i*4,bits(v),4)
        elif name=='basis':
            result=int(self.case['basis'])
            if result:
                for at,values in zip(args[1:],((0.,1.,0.),(1.,0.,0.))):
                    for i,v in enumerate(values):self.put(at+i*4,bits(v),4)
        elif name=='create':result=CREATED+(ordinal-1)*0x180 if self.case['allocate'] else 0
        elif name=='copy':
            data=blob(self.memory,args[1],args[2])
            for i,v in enumerate(data):self.put(args[0]+i,v,1)
            result=args[0]
        elif name=='random':sample=bits(self.case['samples'][(ordinal-1)%2])
        mutation(self.memory,self.case,name,ordinal,args[1]-28 if name=='basis' else None)
        for r in (1,2,3,*range(4,16),24,25):self.r[r]=0xA5000000+r
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=result
        if sample is not None:self.f[0]=sample


def state(m):return scale.state(m),m.private_calls


class OwnerBurstRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.truth=list(struct.unpack_from('>288I',(cls.out/'before-retail_rom').read_bytes(),source.ROM))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,case,images=None,entry=source.ENTRY):
        expected,calls,iterations=reference(memory,case)
        machines=[Oracle(w,memory,case,entry).run() for w in (images or [self.truth,*self.images])]
        for m in machines:
            self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(m.fcsr,3)
        self.assertEqual(machines[-1].memory,machines[-2].memory)
        return machines,iterations

    def test_01_shape_and_original_isolation(self):
        for value in (0,1,127,128,254,255):
            memory,case=fixture(count=value);m=Oracle(self.truth,memory,case);before=m.all_accesses
            m.execute(0x80880034)
            self.assertEqual(m.r[8],signed_byte(value)&0xFFFFFFFF);self.assertEqual(m.r[0],0)
            self.assertEqual(m.all_accesses,before+1)
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences']),(288,0x158,85))
        self.assertEqual(self.row['unchanged_raw_padded_neighbors'],11);self.assertEqual(self.images[0],self.images[1])
        self.assertEqual(hashlib.sha256(source.parts(self.obj)[0]).hexdigest(),source.RAW_SHA)
        self.assertEqual(len(source.parts(self.obj)[1]),25)
        self.receipt('shape',words=288,frame=0x158,retail_frame=0x150,word_differences=85,new_guards=0,
            unchanged_raw_padded_neighbors=11,pools_unchanged=True,installed=False,matching_credit=0)

    def test_02_full_uniform_stack_public_protocol(self):
        count=0;emissions=0;seen=set()
        for gate,state,previous,counter,time,step,basis,allocate in itertools.product(range(5),(0,1),(0,1),
                (0,3,128),(1.,4.5),(0.,1.),(False,True),(False,True)):
            machines,n=self.compare(*fixture(gate,state,previous,counter,time,step,basis,allocate))
            count+=1;emissions+=n;seen.update(machines[0].visits)
        for mode,phase,samples in itertools.product(range(1,5),(0,8),((0.,0.),(.5,.25),(.875,.999))):
            self.compare(*fixture(state=1,previous=1,mode=mode,phase=phase,samples=samples));count+=1
        for counter in (1,127,255):
            self.compare(*fixture(count=counter,time=2.5,step=0.));count+=1
        edges=0
        for override in (-1.,-.5,2147483648.,4294967040.,4294967296.,math.inf,math.nan):
            machines,_=self.compare(*fixture(count=1,time=2.,step=0.,mode=3,base_override=override))
            seen.update(machines[0].visits);edges+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen,{source.ENTRY+0x8C})
        self.receipt('semantics',uniform_stack_cases=count,emissions=emissions,retail_reached_words=len(seen),
            unreachable_duplicate_word=0x8C,model_only_FP_edges=edges,full_public_memory_and_call_packets=True,
            opaque_providers=True,no_private_or_gameplay_match=True)

    def test_03_private_frame_and_nonuniform_packet_padding_are_not_hidden(self):
        memory,case=fixture(pattern=1)
        machines=[Oracle(w,memory,case).run() for w in (self.truth,*self.images)]
        changed={a for a in public(machines[0].memory) if machines[0].memory[a]!=machines[1].memory[a]}
        expected={CREATED+i*0x180+0x110+j for i in range(3) for j in PAYLOAD_HOLES}
        self.assertEqual(changed,expected)
        for a,b in zip(machines[0].calls,machines[1].calls):
            self.assertEqual(a[0],b[0])
            if a[0]=='create':
                self.assertEqual({i for i,(x,y) in enumerate(zip(a[1][0],b[1][0])) if x!=y},set(DESCRIPTOR_HOLES))
            elif a[0]=='copy':
                self.assertEqual({i for i,(x,y) in enumerate(zip(a[1][1],b[1][1])) if x!=y},set(PAYLOAD_HOLES))
            else:self.assertEqual(a,b)
        memory,case=fixture()
        prefix=[Oracle(w,memory,case) for w in (self.truth,*self.images)]
        for m in prefix:
            m.access_fault=0
            with self.assertRaises(faults.AccessBoundary):m.run()
        self.assertNotEqual(state(prefix[0]),state(prefix[1]))
        self.assertEqual(prefix[0].r[29]-prefix[1].r[29],8)
        self.receipt('private-gap',effective_first_fault_cut=0,SP_gap=8,public_copied_padding_differences=len(changed),
            payload_holes=list(PAYLOAD_HOLES),descriptor_holes=list(DESCRIPTOR_HOLES),not_installable=True)

    def test_04_rebased_symbols_and_call_protocol(self):
        count=0
        for group,entry in enumerate((0x15207FF0,0x15610000)):
            symbols={n:(0x80300000+group*0x100000+i*0x10000+(0x7FFC if (i+group)%2 else 0x8004))
                if v&0x80000000 else 0x15300000+group*0x100000+i*0x1000
                for i,(n,v) in enumerate(source.SYMBOLS.items())}
            words=source.linked(self.root,self.out,self.obj,'rebase-'+str(group),entry,symbols)
            for gate,state,mode in itertools.product((0,1,3),(0,1),(0,2)):
                self.compare(*fixture(gate,state,previous=state,mode=mode,symbols=symbols),images=[words,words],entry=entry);count+=1
        self.receipt('rebases',links=2,public_protocol_cases=count,signed_HI16_carries=True,literal_private_match=False)

    def historical(self,path):
        from tools.tests import owner_burst_checkpoint as latest
        return latest.previous_input((self.root/path).read_bytes(),path,self.root)

    def test_05_production_image_inputs_and_callback_unchanged(self):
        source.freeze(self.root,self.out)
        self.assertEqual(self.historical('conker/build/conker.us.elf'),(self.out/'before-elf').read_bytes())
        for key,path in source.PATHS.items():self.assertEqual(self.historical(path),(self.out/('before-'+key)).read_bytes())
        self.assertEqual(struct.unpack_from('>I',(self.out/'before-retail_rom').read_bytes(),0x22F118)[0],source.ENTRY)
        functions,_,_=load_elf_functions(str(self.root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
        data=audit_layout(self.root/'conker/build/conker.us.elf',self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),
            entire_ELF_unchanged=True,function_bodies=len(functions),game_data=data,callback_slot=0x8008A658,
            no_matching_credit_or_guard_changes=True)


    def test_06_native32_typed_fields_and_effective_controls(self):
        header='#include <ultra64.h>\n'+NATIVE_TYPES+'\n'+source.TYPE+'\n'
        driver=self.out/'native-driver.c';driver.write_text(header+NATIVE)
        controls={'equality':source.SELECTED.replace('data->value > 1.0f','data->value >= 1.0f'),
            'signed-counter':source.SELECTED.replace('(s8)data->mode > 0','data->mode > 0').replace(
                '(s8)savedData->mode > 0','savedData->mode > 0'),
            'payload-length':source.SELECTED.replace('sizeof(payload)','(sizeof(payload) - 4)')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                path=self.out/('native-'+label+'.c');path.write_text(header+body+'\n');exe=self.out/('native-'+label+opt)
                compiled=subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(path.relative_to(self.root)),str(driver.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
                self.assertEqual(compiled.returncode,0,compiled.stdout+compiled.stderr)
                result=subprocess.run([str(exe)],capture_output=True)
                if label=='selected':self.assertEqual(result.returncode,0,(opt,result.stderr))
                else:self.assertNotEqual(result.returncode,0,(opt,label))
        self.receipt('native',cases_per_profile=960,profiles=['O2','O0'],UBSan=True,effective_controls=6,
            typed_packet_defined_fields=True,padding_and_private_faults_not_native_qualified=True)


NATIVE_TYPES=r'''
typedef struct {u8 *owner;u8 owner_id,state,pad[2];f32 value;u8 mode,padD[3];} Generated11FF10Payload;
extern f32 D_800BE9A4,D_800A1950[];
void *memcpy(void *,const void *,u32);
'''
NATIVE=r'''
typedef struct {u8 head[0xE];s16 killed;u8 pad10[0x18];Generated11FF10Payload data;} NativeActor;
typedef struct {s32 active;u8 pad4[0x37];u8 epoch;u8 pad3C[0x198];u8 *model;u8 pad1D8[0x4A];u8 state;} NativeOwner;
typedef struct {u8 head[0x110];BurstPayload2D14 payload;} NativeProduct;
static NativeActor actor;static NativeOwner owner;static NativeProduct products[3];static u8 model[0x400];
u8 D_800C35EA,D_800CC2D0[0x1000],D_800A4AA0[4];
f32 D_800A1950[3],D_800A195C[3],D_800A1968,D_800A196C,D_800BE9A4;
BurstVector2D14 D_800A5480;
static int bad,fade_calls,rng_calls,basis_calls,create_calls,copy_calls,basis_ok,allocation_ok;
void func_150F2D14(u8 *);
void func_1502EA98(u8 *a,u8 b,u8 c,u8 d,u8 e,s32 f,u8 g){
if(a!=D_800CC2D0+owner.state*0x32C||b!=255||c||d||e!=80||f||g!=15)bad=1;fade_calls++;}
f32 func_150ADA68(void){return (++rng_calls&1)?.5f:.25f;}
void func_15145EA4(BurstVector2D14 **in,BurstVector2D14 **out,u8 *m,s32 n){
if((void*)in[0]!=(void*)D_800A1950||(void*)in[1]!=(void*)D_800A195C||m!=model+0x3C0||n!=2)bad=1;
out[0]->x=1.f;out[0]->y=2.f;out[0]->z=3.f;out[1]->x=5.f;out[1]->y=7.f;out[1]->z=11.f;}
s32 func_15146078(BurstVector2D14 *delta,BurstVector2D14 *a,BurstVector2D14 *b){
if(delta->x!=4.f||delta->y!=5.f||delta->z!=8.f)bad=1;basis_calls++;
if(!basis_ok)return 0;a->x=0.f;a->y=1.f;a->z=0.f;b->x=1.f;b->y=0.f;b->z=0.f;return 1;}
u8 *func_1513D2F0(BurstDescriptor2D14 *r,void *table,u8 a,u8 b,u8 c,u8 d,u8 e,s32 f,s32 g,s32 n,u8 epoch,s32 slot){
int i=create_calls++;if(i>=3){bad=1;return 0;}
if(table!=D_800A4AA0||a!=0x26||b||c||d!=0x25||e||f||g||n!=52||epoch!=0x44||slot!=2)bad=1;
if(r->byte00!=0x79||r->byte01!=12||r->half02!=0x4405||r->half04!=300||r->word08||r->word0C||
r->bytes10[0]!=0xD5||r->bytes10[1]!=0xDB||r->bytes10[2]!=255||r->bytes10[3]!=255||
r->float14!=0.f||r->float18!=0.f||r->position.x!=1.f||r->position.y!=2.f||r->position.z!=3.f||
r->vector28.x!=.125f||r->vector28.y!=-.25f||r->vector28.z!=.5f||
r->scale.x!=1.f||r->scale.y!=1.f||r->scale.z!=1.f||r->word40!=0x04EC0000||r->byte44!=70||
r->byte45!=255||r->byte46||r->byte47!=6||r->word48||r->byte4C!=255||r->word50||r->half54!=1||r->half56!=255)bad=1;
return allocation_ok?(u8 *)&products[i]:0;}
void *memcpy(void *destination,const void *source,u32 n){u8 *d=destination;const u8 *s=source;u32 i;
if(n==52){if(create_calls<=0||create_calls>3||d!=(u8 *)&products[create_calls-1].payload)bad=1;copy_calls++;}
for(i=0;i<n;i++)d[i]=s[i];return destination;}
static int run(void){int gate,state,previous,c,t,step,basis,allocation,i,n=0,left,attempts,emits,want_fade,want_state,want_kill;
f32 clock;static u8 counts[]={0,3,128};static f32 times[]={1.f,4.5f};
if(sizeof(void*)!=4||sizeof(BurstDescriptor2D14)!=88||sizeof(BurstPayload2D14)!=52||
__builtin_offsetof(BurstDescriptor2D14,position)!=0x1C||__builtin_offsetof(BurstDescriptor2D14,byte44)!=0x44||
__builtin_offsetof(NativeActor,data)!=0x28||__builtin_offsetof(NativeOwner,model)!=0x1D4||
__builtin_offsetof(NativeOwner,state)!=0x222)return 20;
for(gate=0;gate<5;gate++)for(state=0;state<2;state++)for(previous=0;previous<2;previous++)
for(c=0;c<3;c++)for(t=0;t<2;t++)for(step=0;step<2;step++)for(basis=0;basis<2;basis++)for(allocation=0;allocation<2;allocation++){
u8 *bytes=(u8 *)products;for(i=0;i<(int)sizeof(products);i++)bytes[i]=0xA5;
actor.head[1]=2;actor.head[12]=0x44;actor.killed=0x1234;actor.data.owner=(u8 *)&owner;
actor.data.owner_id=127;actor.data.state=previous;actor.data.value=times[t];actor.data.mode=counts[c];
owner.active=gate==2?0:1;owner.epoch=gate==3?255:127;owner.model=gate==4?0:model;owner.state=state;
D_800C35EA=gate==1?1:0;D_800A1968=.5f;D_800BE9A4=(f32)step;D_800A196C=1.25f;
D_800A5480.x=.125f;D_800A5480.y=-.25f;D_800A5480.z=.5f;
bad=fade_calls=rng_calls=basis_calls=create_calls=copy_calls=0;basis_ok=basis;allocation_ok=allocation;
clock=times[t];left=counts[c];attempts=emits=want_fade=0;want_state=previous;want_kill=0x1234;
if(gate!=1){if(gate==2||gate==3)want_kill=-1;else{
if(state!=previous&&state){left=3;clock=0.f;}want_state=state;want_fade=state!=0;
if(gate!=4&&(s8)left>0){clock+=.5f*(f32)step;while(clock>1.f&&(s8)left>0){attempts++;if(!basis)break;emits++;left=(left-1)&255;clock-=1.f;}}}}
func_150F2D14((u8 *)&actor);
if(bad||fade_calls!=want_fade||rng_calls!=attempts*2||basis_calls!=attempts||create_calls!=emits||copy_calls!=(allocation?emits:0)||
actor.killed!=want_kill||actor.data.state!=want_state||actor.data.mode!=left||actor.data.value!=clock)return 22;
for(i=0;i<emits&&allocation;i++){BurstPayload2D14 *p=&products[i].payload;
if(p->owner!=(u8 *)&owner||p->ownerId!=127||p->time!=0.f||p->limit!=16.f||p->multiplier!=1.25f||
p->byteBase!=70.f||p->decay!=70.f/256.f||p->vector1C.x!=0.f||p->vector1C.y!=1.f||p->vector1C.z!=0.f||
p->vector28.x!=1.f||p->vector28.y!=0.f||p->vector28.z!=0.f||products[i].head[0x10F]!=0xA5)return 23;}
n++;}return n==960?0:24;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


if __name__=='__main__':unittest.main()
