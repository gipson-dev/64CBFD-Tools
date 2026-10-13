"""Complete two-channel recovery, aliases, native32 and immutable image gates."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_command_finalizer_candidates as screen
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools
from tools.tests import test_game_actor_command_stream_match as stream
from tools.tests import test_game_actor_renderer_install_match as native
from tools.tests import test_game_owner_descriptor_match as descriptor
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.check_game_data_layout import audit_layout
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_one_shot_timer_match import symbol_rows

ACTOR, OUTPUT, STACK = 0x100000, 0x20000, stream.STACK
CONSTANT_BASE=0x80097D40
RANDOM, TIMER, VALUE = (screen.SYMBOLS[x] for x in ('func_150ADA20','D_800BE9E4','D_800C3EF0'))
CONSTANTS=(0x45FFFF00,0x43360B61,0x3B808081,0x477FFF00,
           0x3B808081,0x45FFFF00,0x43360B61,0x3B808081)
SCALES=tuple(stream.floating(x) for x in CONSTANTS)
INDICES=(0,1,254,255,256,511,0x7FFFFFFF,0x80000000,0xFFFFFFFF)
RANDOMS=(0,1,19,20,0x7FFFFFFF,0x80000000,0xFFFFFFFF)


def apply_finalizer_symbol_serialization(expected):
    groups=(
        (('D_80097D4C','.L1508E838_game_data'),
            ((0x80097D4C,0,16,0,65521),(0x1508E838,0,16,0,5))),
        (('D_800DDDA0','D_800A5F14'),
            ((0x800DDDA0,0,16,0,65521),(0x800A5F14,0,16,0,6))),
        (('D_80097D58','D_80082BC0'),
            ((0x80097D58,0,16,0,65521),(0x80082BC0,0,16,0,65521))))
    for names,definitions in groups:
        rows={name:(offset,fields,string) for offset,name,fields,string in symbol_rows(expected) if name in names}
        assert set(rows)==set(names)
        first=rows[names[0]]
        cursor=first[2]
        for index,(name,definition) in enumerate(zip(names,definitions)):
            offset,fields,string=rows[name]
            assert offset==first[0]+index*16 and fields[1:]==definition
            assert string==cursor and expected[string:string+len(name)+1]==name.encode()+b'\0'
            cursor+=len(name)+1
        base=first[2]-first[1][0]
        cursor=first[2]
        for index,name in enumerate(reversed(names)):
            fields=list(rows[name][1])
            fields[0]=cursor-base
            struct.pack_into('>IIIBBH',expected,first[0]+index*16,*fields)
            expected[cursor:cursor+len(name)+1]=name.encode()+b'\0'
            cursor+=len(name)+1


def sb(x):
    return (x&255)-256 if x&128 else x&255


def f32(x):
    return stream.floating(stream.bits(x))


def fixture(kind=0,pattern=0,first=1,second=2,timer=1):
    memory={STACK+i:165 for i in range(-0x400,0x100)}
    for base,length in ((ACTOR,0x240),(OUTPUT,64),(TIMER,4),(VALUE,2)):
        memory.update({base+i:165 for i in range(length)})
    fields=((4,kind,1),(0x1FE,(0,1,127,255)[pattern%4],1),
        (0x1FF,pattern%4,1),(0x200,(0,1,60,255)[pattern%4],1),
        (0x201,(0,1,127,255)[pattern%4],1),(0x202,(-128,-1,0,127)[pattern%4],1),
        (0x203,(-60,0,60,127)[pattern%4],1),
        (0x204,(-32768,-255,0,255,32767)[pattern%5],2),
        (0x206,pattern%4,1),(0x207,(0,1,60,255)[pattern%4],1),
        (0x208,(-128,-1,0,1,127)[pattern%5],1),(0x209,(-128,-60,0,60,127)[pattern%5],1))
    for offset,value,size in fields:
        stream.put(memory,ACTOR+offset,value,size)
    stream.put(memory,TIMER,timer)
    for i,bits in enumerate(CONSTANTS):
        stream.put(memory,CONSTANT_BASE+i*4,bits)
    return memory,(OUTPUT,ACTOR,first,second)


def mutate(memory,actor,mode,count):
    if mode==1:
        for offset,value,size in ((4,0x7C,1),(0x1FE,0,1),(0x206,3,1),(0x207,0,1)):
            stream.put(memory,actor+offset,value,size)
        stream.put(memory,TIMER,2)


def reference(memory,args,seed=0,mode=0):
    memory=memory.copy()
    output,actor,first,second=args
    calls=[]
    def get(off,size=1):
        return stream.read(memory,actor+off,size)
    def put(off,value,size=1):
        stream.put(memory,actor+off,value,size)
    def scale_constant(index):
        return stream.floating(stream.read(memory,CONSTANT_BASE+index*4))
    def rnd():
        calls.append((RANDOM,()))
        mutate(memory,actor,mode,len(calls))
        return (seed+(len(calls)-1)*0x9E3779B9)&0xFFFFFFFF
    def tag(index,bias,amount):
        nonlocal output
        stream.put(memory,output,index*6+bias,2)
        stream.put(memory,output+2,amount,2)
        output+=4
    kind=get(4)
    bias,extra=(4,0) if kind==0x7C else (0,2)
    noise=0 if kind in (0x69,0x7C,0x87) else 10
    if first&0xFFFFFFFF!=255:
        scale=scale_constant(0) if not get(0x201) else f32(get(0x201)*scale_constant(1))
        value=stream.signed16(math.trunc(f32(f32(get(0x1FE)*scale)*scale_constant(2))))
        if kind!=0x70:
            tag(first,bias,value)
        stream.put(memory,VALUE,value,2)
        product=sb(get(0x202))*get(0x1FE)
        divided=(abs(product)//255)*(-1 if product<0 else 1)
        value=stream.signed16(math.trunc(f32(f32(divided*scale_constant(3))*scale_constant(4))))
        if kind!=0x70:
            tag(first,extra,value)
        low,high=(80,120) if get(4)==0x42 else (40,60)
        state=get(0x1FF)
        if state==0:
            put(0x203,-high)
        elif state==2:
            put(0x203,high)
            put(0x202,0)
        elif not get(0x203) or get(0x1FE) in (0,255):
            sample=rnd()
            current=get(0x1FE)
            put(0x203,sample%(high-low)+low)
            if current==255:
                put(0x203,-sb(get(0x203)))
            elif current==0 and noise:
                put(0x202,rnd()%(2*noise)-noise)
        current=get(0x1FE)+sb(get(0x203))
        put(0x1FE,min(255,max(0,current)))
        if get(0x1FF)==3:
            timer=signed(stream.read(memory,TIMER))
            if get(0x200)>=timer:
                put(0x200,get(0x200)-timer)
            else:
                put(0x200,0)
                put(0x1FF,0)
    if second&0xFFFFFFFF!=255:
        scale=scale_constant(5) if not get(0x208) else f32(sb(get(0x208))*scale_constant(6))
        sign=-1 if scale<0 else 1
        amount=math.trunc(f32(f32(stream.signed16(get(0x204,2))*abs(scale))*scale_constant(7)))
        tag(second,bias,-amount)
        choose=reverse=False
        state=get(0x206)
        if state in (0,2):
            put(0x209,sign*(-60 if state==0 else 60))
        else:
            delta=sb(get(0x209))
            current=stream.signed16(get(0x204,2))
            if not delta:
                choose=True
            elif current*sign<0 and delta*sign<0:
                reverse=True
            elif not current and delta*sign<0:
                choose=True
            elif current==sign*255:
                choose=reverse=True
        if choose:
            put(0x209,rnd()%20+40)
            put(0x209,sb(get(0x209))*sign)
        if reverse:
            put(0x209,-sb(get(0x209)))
        delta=sb(get(0x209))
        current=stream.signed16(get(0x204,2)+delta)
        put(0x204,current,2)
        if current*sign<0 and delta*sign<0:
            put(0x204,0,2)
        elif current*sign>=256:
            put(0x204,sign*255,2)
        if get(0x206)==3:
            timer=signed(stream.read(memory,TIMER))
            if get(0x207)>=timer:
                put(0x207,get(0x207)-timer)
            else:
                put(0x207,0)
                put(0x206,0)
    return memory,output,calls


class FinalizerOracle(stream.StreamOracle):
    def __init__(self,words,memory,args,phase=0,seed=0,mode=0,entry=screen.ENTRY,connected=None):
        super().__init__(words,memory,phase=phase,entry=entry,connected=connected)
        self.r[4:8]=[x&0xFFFFFFFF for x in args]
        self.actor,self.seed,self.mode=args[1],seed,mode
        self.hi=0
    def execute(self,word):
        op,rs,rt,rd,fd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word>>6&31,word&63
        if op==0 and fn==27:
            assert self.r[rt]
            self.lo,self.hi=divmod(self.r[rs],self.r[rt])
        elif op==0 and fn==16:
            self.r[rd]=self.hi
        elif op==17 and rs==16 and fn==5:
            self.f[fd]=self.f[rd]&0x7FFFFFFF
        else:
            super().execute(word)
        self.r[0]=0
    def record_call(self,target):
        assert target==RANDOM
        self.calls.append((target,()))
        self.events.append(('CALL',target,()))
    def hook(self,target):
        assert target==RANDOM
        mutate(self.memory,self.actor,self.mode,len(self.calls))
        for register in (1,2,3,*range(4,16),24,25):
            self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.r[2]=(self.seed+(len(self.calls)-1)*0x9E3779B9)&0xFFFFFFFF


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x800<=a<STACK+0x100}


class GameActorCommandFinalizerRecoveryTests(unittest.TestCase):
    run_native=native.GameActorRendererInstallMatchTests.run_native

    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/'conker/build/game-actor-command-finalizer-test'
        cls.out.mkdir(exist_ok=True)
        cls.paths=dict(source=screen.SOURCE,elf='conker/build/conker.us.elf',
            guards='conker/retail_word_patches.us.csv',progress='conker/progress.csv',
            layout='conker/retail_layout.us.txt',makefile='conker/Makefile',
            rodata='conker/asm/data/23C630.rodata.s',caller='conker/src/game/generated_61490.c')
        manifest=cls.out/'baseline.json'
        if not manifest.exists():
            hashes={}
            for name,path in cls.paths.items():
                data=(cls.root/path).read_bytes()
                (cls.out/('before-'+name)).write_bytes(data)
                hashes[name]=hashlib.sha256(data).hexdigest()
            manifest.write_text(json.dumps(hashes,indent=2)+'\n')
        cls.before=(cls.out/'before-elf').read_bytes()
        cls.owner_before=(cls.out/'before-source').read_text()
        cls.owner_after=screen.recovered_owner(cls.owner_before)
        cls.meta,cls.words=screen.compile_candidate(cls.root,cls.out,'selected')
        cls.retail=list(struct.unpack_from('>405I',(cls.root/'conker/conker.us.bin').read_bytes(),screen.ROM))

    def receipt(self,name,**values):
        (self.out/(name+'.json')).write_text(json.dumps(values,indent=2)+'\n')

    def compare(self,memory,args,seed=0,mode=0,phase=0):
        expected,cursor,calls=reference(memory,args,seed,mode)
        pair=[FinalizerOracle(words,memory,args,phase,seed,mode).run() for words in (self.retail,self.words)]
        for model in pair:
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.r[2],cursor)
            self.assertEqual(model.calls,calls)
        writes=lambda m:[e for e in m.events if e[0]=='W' and not STACK-0x800<=e[1]<STACK+0x100]
        self.assertEqual(writes(pair[0]),writes(pair[1]))
        return pair

    def test_01_complete_body_no_guards_or_matching_credit(self):
        self.assertEqual((self.meta['body_words'],self.meta['frame'],self.meta['differences'],
            self.meta['pool_bytes'],self.meta['diagnostics']),(395,64,398,0,''))
        with (self.root/self.paths['guards']).open(newline='') as source:
            self.assertFalse([r for r in csv.DictReader(source) if r['function']==screen.FUNCTION])
        self.assertEqual(self.words[-2:],self.retail[-2:])
        self.assertNotEqual(self.words,self.retail)
        self.receipt('shape',words=395,retail_words=405,frame=64,retail_frame=72,
            differences=398,matching_credit=0,guards_added=0)

    def test_02_all_types_channels_field_boundaries_and_call_mutations(self):
        cases=0
        visits=set()
        for kind,pattern,gates,phase in itertools.product(range(256),range(4),range(4),(0,8)):
            memory,args=fixture(kind,pattern,255 if gates&1 else 1,255 if gates&2 else 2)
            pair=self.compare(memory,args,RANDOMS[pattern],pattern&1,phase)
            visits.update(pair[0].visits)
            cases+=1
        for field in (0x1FE,0x1FF,0x200,0x201,0x202,0x203,0x206,0x207,0x208,0x209):
            for value in range(256):
                memory,args=fixture(0x42,1)
                stream.put(memory,ACTOR+field,value,1)
                pair=self.compare(memory,args,0xFFFFFFFF)
                visits.update(pair[0].visits)
                cases+=1
        for current,delta,sign,state,timer in itertools.product(
                (-32768,-256,-255,-1,0,1,255,256,32767),(-128,-60,-1,0,1,60,127),
                (-1,0,1),(0,1,2,3),(-2147483648,-1,0,1,255,2147483647)):
            memory,args=fixture(0,1,255,0x80000000,timer)
            stream.put(memory,ACTOR+0x204,current,2)
            stream.put(memory,ACTOR+0x209,delta,1)
            stream.put(memory,ACTOR+0x208,sign,1)
            stream.put(memory,ACTOR+0x206,state,1)
            pair=self.compare(memory,args,0x80000000)
            visits.update(pair[0].visits)
            cases+=1
        self.receipt('guest',cases=cases,retail_words_visited=len(visits),provider='opaque full32 PRNG',
            public_write_order_exact=True,private_frame_match=False)

    def test_03_full_word_selectors_and_output_aliases(self):
        cases=0
        for first,second in itertools.product(INDICES,repeat=2):
            memory,args=fixture(0x7C,3,first,second)
            self.compare(memory,args,0xFFFFFFFF)
            cases+=1
        for kind,pattern,offset,phase in itertools.product((0x42,0x70,0x7C,0x87),range(4),
                (4,0x1FC,0x1FE,0x200,0x202,0x204,0x206,0x208),(0,8)):
            memory,args=fixture(kind,pattern)
            args=(ACTOR+offset,*args[1:])
            self.compare(memory,args,0xFFFFFFFF,pattern&1,phase)
            cases+=1
        # Float/global overlaps retain original pre-store reads and later reloads.
        for output in (VALUE,TIMER,0x80097D48,0x80097D5C):
            for kind,pattern in itertools.product((0x42,0x70,0x7C),range(4)):
                memory,args=fixture(kind,pattern)
                memory.update({output+i:165 for i in range(12)})
                for i,bits in enumerate(CONSTANTS):
                    stream.put(memory,0x80097D40+i*4,bits)
                args=(output,*args[1:])
                self.compare(memory,args,0x80000000)
                cases+=1
        self.receipt('aliases',cases=cases,full32_selectors=True,native_endian_alias_claim=False)

    def test_04_empty_channel_backing_and_private_frame_witness(self):
        memory,args=fixture(first=255,second=255)
        minimal={a:v for a,v in memory.items() if STACK-0x400<=a<STACK+0x100 or ACTOR+4==a}
        self.compare(minimal,args)
        pair=self.compare(memory,args)
        self.assertNotEqual(pair[0].memory,pair[1].memory)
        self.assertNotEqual(pair[0].events,pair[1].events)
        self.assertEqual(pair[0].before[29],pair[1].before[29])
        self.receipt('private',literal_frame_rejected=True,empty_reads_only_type=True,
            hardware_and_fault_prefix_parity=False)

    def native_source(self,body,count=4096):
        vectors=[]
        for i in range(count):
            kind=(0,0x42,0x69,0x70,0x7C,0x87,0x98)[i%7]
            pattern=i%20
            first,second=INDICES[(i//7)%9],INDICES[(i//63)%9]
            timer=(-2147483648,-1,0,1,255,2147483647)[i%6]
            seed=RANDOMS[i%7]
            mode=(i//441)%2
            memory,args=fixture(kind,pattern,first,second,timer)
            field=(0x1FE,0x1FF,0x200,0x201,0x202,0x203,0x206,0x207,0x208,0x209)[(i//2)%10]
            stream.put(memory,ACTOR+field,(i//3)&255,1)
            expected,cursor,calls=reference(memory,args,seed,mode)
            before=[memory[ACTOR+0x1FE+j] for j in range(12)]
            after=[expected[ACTOR+0x1FE+j] for j in range(12)]
            out=[stream.read(expected,OUTPUT+j*2,2) for j in range(6)]
            vectors.append('{%s,%s,%s,%s,%s,%s,%s,{%s},{%s},{%s},%s,%s,%s}'%(
                kind,expected[ACTOR+4],first&0xFFFFFFFF,second&0xFFFFFFFF,timer,seed,mode,
                ','.join(map(str,before)),','.join(map(str,after)),','.join(map(str,out)),
                stream.signed16(stream.read(expected,VALUE,2)),cursor-OUTPUT,len(calls)))
        floats='\n'.join('static f32 D_%08X = %sf;'%(0x80097D40+j*4,repr(x)) for j,x in enumerate(SCALES))
        return '''typedef unsigned char u8; typedef signed char s8; typedef short s16;
typedef unsigned short u16; typedef unsigned int u32; typedef int s32; typedef float f32;
static u8 actor[0x240] __attribute__((aligned(16))), output[64] __attribute__((aligned(16)));
static s32 D_800BE9E4; static s16 D_800C3EF0;
static u32 randomSeed; static int callCount,mutation;
static f32 fabsf(f32 x) { union {f32 f;u32 u;} v;v.f=x;v.u&=0x7FFFFFFF;return v.f;}
static s32 func_150ADA20(void) {
    u32 v=randomSeed+(u32)callCount*0x9E3779B9u;callCount++;
    if(mutation) {actor[4]=0x7C;actor[0x1FE]=0;actor[0x206]=3;actor[0x207]=0;D_800BE9E4=2;}
    return (s32)v;
}
''' + floats+'\n'+body+'''
struct Vector {u32 kind,afterKind,first,second;s32 timer;u32 seed,mode;
    u8 before[12],after[12];u16 out[6];s16 value;u32 advance,calls;};
static const struct Vector cases[]={'''+','.join(vectors)+'''};
static int test(void) {
    u32 i,j;u8 want[0x240];const struct Vector *v;s32 result;
    for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
        v=&cases[i];
        for(j=0;j<0x240;j++) actor[j]=want[j]=165;
        for(j=0;j<64;j++) output[j]=165;
        actor[4]=v->kind;want[4]=v->afterKind;
        for(j=0;j<12;j++) {actor[0x1FE + j]=v->before[j];want[0x1FE + j]=v->after[j];}
        *(u16 *)(actor+0x204)=((u16)v->before[6]<<8)|v->before[7];
        *(u16 *)(want+0x204)=((u16)v->after[6]<<8)|v->after[7];
        D_800BE9E4=v->timer;D_800C3EF0=(s16)0xA5A5;
        randomSeed=v->seed;callCount=0;mutation=v->mode;
        result=func_15034860(output,actor,(s32)v->first,(s32)v->second);
        if((u32)result!=(u32)output+v->advance || callCount!=(int)v->calls || D_800C3EF0!=v->value) return 1;
        for(j=0;j<0x240;j++) if(actor[j]!=want[j]) return 2;
        for(j=0;j<6;j++) if(((u16 *)output)[j]!=v->out[j]) return 3;
        for(j=12;j<64;j++) if(output[j]!=165) return 4;
    }
    return 0;
}
void _start(void) {int result=test();__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''

    def test_05_native32_actual_source_and_effective_negatives(self):
        for profile in ('-O2','-O0'):
            self.assertEqual(self.run_native('native-'+profile[1:],self.native_source(screen.SELECTED),profile)[0],0)
        negatives={
            'narrow-first':screen.SELECTED.replace('if (first != limit)','if ((u8)first != limit)'),
            'unsigned-delta':screen.SELECTED.replace('*(s8 *)(actor + 0x202) * actor[0x1FE]','actor[0x202] * actor[0x1FE]'),
            'wrong-suppression':screen.SELECTED.replace('type == 0x70','type == 0x71'),
            'wrong-second-sign':screen.SELECTED.replace('sign = -1;','sign = 1;'),
            'wrong-prng-width':screen.SELECTED.replace('(u32)func_150ADA20() %','func_150ADA20() %'),
        }
        for name,body in negatives.items():
            self.assertNotEqual(self.run_native(name,self.native_source(body))[0],0,name)
        self.receipt('native',cases=8192,profiles=['O2','O0'],effective_negatives=len(negatives),
            host_endian_halfwords_normalized=True,output_actor_aliases_guest_only=True)

    def test_06_full_owner_neighbors_pools_and_both_padders(self):
        objects=[screen.compile_owner(self.root,self.out,source,'owner-'+name)
            for name,source in (('before',self.owner_before),('after',self.owner_after))]
        self.assertEqual(objects[0][1],objects[1][1])
        old,new=(parse_object(obj) for obj,_ in objects)
        names=set(old[1])-set((screen.FUNCTION,))
        self.assertEqual(names,set(new[1])-set((screen.FUNCTION,)))
        for name in names:
            a,b=old[1][name],new[1][name]
            self.assertEqual(old[0][a['value']:a['value']+a['size']],
                new[0][b['value']:b['value']+b['size']],name)
            relative=lambda obj,meta:{off-meta['value']:items for off,items in obj[2].items()
                if meta['value']<=off<meta['value']+meta['size']}
            self.assertEqual(relative(old,a),relative(new,b),name)
        self.assertEqual(normalized_pools(objects[0][0]),normalized_pools(objects[1][0]))
        padded=[]
        for script in ('pad_c_object.py','pad_generated_object.py'):
            assembly=self.out/(script+'.s')
            args=[str(objects[1][0]),str(self.root/'conker/retail_layout.us.txt'),'generated_61D10',str(assembly)] if script=='pad_c_object.py' else [
                str(objects[1][0]),str(self.root/'conker/asm/61D10.s'),str(assembly),'--filename','generated_61D10']
            result=subprocess.run([sys.executable,str(self.root/'tools'/script),*args,'--word-patches',
                str(self.root/self.paths['guards'])],capture_output=True,text=True)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            obj=assembly.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-I',str(self.root/'conker'),
                '-o',str(obj),str(assembly)],check=True,capture_output=True)
            padded.append(parse_object(obj))
        self.assertEqual(padded[0],padded[1])
        self.padded_size=padded[0][1][screen.FUNCTION]['size']
        self.receipt('owner',neighbors=len(names),both_full_padders=True,pools_fixed=True,
            diagnostics_unchanged=True,padded_size=self.padded_size)

    def test_07_literal_image_protected_inputs_and_no_credit(self):
        current=(self.root/self.paths['elf']).read_bytes()
        source=(self.root/screen.SOURCE).read_text()
        installed=source==self.owner_after
        expected=bytearray(self.before)
        if installed:
            offset=elf_slot_offset(self.before,screen.ENTRY,1620)
            self.assertEqual(offset,elf_slot_offset(current,screen.ENTRY,1620))
            payload=struct.pack('>%dI'%len(self.words),*self.words)
            expected[offset:offset+1620]=payload+b'\0'*(1620-len(payload))
            with patch.multiple(descriptor.screen,FUNCTION=screen.FUNCTION,ENTRY=screen.ENTRY):
                size_offset=descriptor.size_field(self.before)
            size=json.loads((self.out/'owner.json').read_text())['padded_size']
            struct.pack_into('>I',expected,size_offset,size)
            before_metadata=bytes(expected)
            apply_finalizer_symbol_serialization(expected)
            self.assertEqual(sum(a!=b for a,b in zip(before_metadata,expected)),79)
            for name in ('D_80097D4C','D_800A5F14','D_80097D58'):
                corrupt=bytearray(before_metadata)
                record=next(offset for offset,n,_,_ in symbol_rows(corrupt) if n==name)
                corrupt[record+7]^=1
                with self.assertRaises(AssertionError):
                    apply_finalizer_symbol_serialization(corrupt)
        else:
            self.assertEqual(source,self.owner_before)
        self.assertEqual(current,bytes(expected))
        for name in set(self.paths)-{'source','elf'}:
            self.assertEqual((self.root/self.paths[name]).read_bytes(),(self.out/('before-'+name)).read_bytes(),name)
        data=audit_layout(self.root/self.paths['elf'],self.root/'conker')
        self.assertEqual((data['exact'],data['bytes'],data['owner_count'],data['different_bytes']),(True,189088,720,0))
        self.receipt('linked-audit',installed=installed,matching_credit=0,guard_rows_added=0,
            changed_bytes=sum(a!=b for a,b in zip(self.before,current)),data=data,
            closed_metadata_bytes=79 if installed else 0,metadata_corruption_controls=3 if installed else 0)

    def test_08_independent_original_links_and_carry_sensitive_rebases(self):
        original=(self.root/'conker/asm/61D10.s').read_text().split('glabel '+screen.FUNCTION+'\n',1)[1]
        assembly=self.out/'original.s'
        assembly.write_text('.include "'+str(self.root/'conker/include/asm_processor_prelude.inc')+
            '"\nglabel '+screen.FUNCTION+'\n'+original.split('endlabel '+screen.FUNCTION,1)[0]+
            'endlabel '+screen.FUNCTION+'\n')
        obj=assembly.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(assembly)],check=True,capture_output=True)
        cases=0
        layouts=((screen.ENTRY,0x80097D40,TIMER,VALUE,RANDOM),
            (0x15234860,0x80107FFC,0x80218004,0x80227FFC,0x15307FFC),
            (0x15434860,0x80318004,0x80417FFC,0x80428004,0x15518004))
        for index,(entry,constants,timer,value,random) in enumerate(layouts):
            symbols=dict(func_150ADA20=random,D_800BE9E4=timer,D_800C3EF0=value,
                **{'D_%08X'%(0x80097D40+i*4):constants+i*4 for i in range(8)})
            with patch.multiple(screen,ENTRY=entry,SYMBOLS=symbols):
                _,candidate=screen.compile_candidate(self.root,self.out,'rebase-'+str(index))
            script=self.out/('original-'+str(index)+'.ld')
            script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
            elf=script.with_suffix('.elf')
            subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',screen.FUNCTION,
                *['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(elf),str(obj)],check=True,capture_output=True)
            retail=list(struct.unpack_from('>405I',sections(elf)['.text'][1]))
            if index==0:
                self.assertEqual(retail,self.retail)
                self.assertEqual(candidate,self.words)
            self.assertNotEqual(retail,candidate)
            with patch.multiple(sys.modules[__name__],CONSTANT_BASE=constants,TIMER=timer,VALUE=value,RANDOM=random):
                for kind,pattern,gates,phase in itertools.product((0x42,0x70,0x7C,0x98),range(5),range(4),(0,8)):
                    memory,args=fixture(kind,pattern,255 if gates&1 else 1,255 if gates&2 else 2)
                    expected,cursor,calls=reference(memory,args,0xFFFFFFFF,1)
                    for words in (retail,candidate):
                        model=FinalizerOracle(words,memory,args,phase,0xFFFFFFFF,1,entry).run()
                        self.assertEqual((public(model.memory),model.r[2],model.calls),(public(expected),cursor,calls))
                    cases+=1
        self.receipt('rebases',independent_original_links=3,original_and_candidate_cases=cases,
            HI16_signed_LO16_carries=True,exact_matching_claim=False)

    def test_09_effective_compiled_second_channel_alias_negative(self):
        calculation='        delta = (s32)((f32)*(s16 *)(actor + 0x204) * magnitude * D_80097D5C);\n'
        tag='        *(s16 *)output = (u32)second * 6 + primaryBias;\n'
        negative=screen.SELECTED.replace(calculation,'',1).replace(tag,tag+calculation,1)
        _,words=screen.compile_candidate(self.root,self.out,'negative-late-second-read',negative)
        memory,args=fixture(0x7C,1,255,2)
        args=(ACTOR+0x204,*args[1:])
        expected,cursor,calls=reference(memory,args,0xFFFFFFFF)
        correct=FinalizerOracle(self.words,memory,args,seed=0xFFFFFFFF).run()
        bad=FinalizerOracle(words,memory,args,seed=0xFFFFFFFF).run()
        self.assertEqual((public(correct.memory),correct.r[2],correct.calls),(public(expected),cursor,calls))
        self.assertNotEqual(public(bad.memory),public(expected))
        self.receipt('alias-negative',fresh_compiled_control=True,pre_header_value_read_required=True)

    def test_10_actual_parent_calls_complete_finalizer(self):
        from tools.tests import test_game_actor_command_dispatch_match as parent
        rom=(self.root/'conker/conker.us.bin').read_bytes()
        caller=list(struct.unpack_from('>119I',rom,parent.screen.ROM))
        self.assertEqual(caller,list(struct.unpack_from('>119I',self.before,
            elf_slot_offset(self.before,parent.screen.ENTRY,476))))
        actor_base=parent.ACTORS
        class Connected(FinalizerOracle):
            def record_call(self,target):
                if target in (parent.LOOKUP,screen.ENTRY):
                    args=tuple(self.r[4:6 if target==parent.LOOKUP else 8])
                    self.calls.append((target,args))
                    self.events.append(('CALL',target,args))
                else:
                    super().record_call(target)
            def hook(self,target):
                if target==parent.LOOKUP:
                    result=self.channels[self.calls[-1][1][1]]
                else:
                    assert target==RANDOM
                    count=sum(call[0]==RANDOM for call in self.calls)
                    mutate(self.memory,self.actor,self.mode,count)
                    result=(self.seed+(count-1)*0x9E3779B9)&0xFFFFFFFF
                for register in (1,2,3,*range(4,16),24,25):
                    self.r[register]=0xA5000000+register
                self.f[:20]=[0xA5000000+i for i in range(20)]
                self.r[2]=result
        cases=0
        for kind,pattern,gates,phase in itertools.product((0,0x42,0x70,0x7C,0x87),range(5),range(4),(0,8)):
            first,second=(255 if gates&1 else 1),(255 if gates&2 else 2)
            memory,_=fixture(kind,pattern,first,second)
            memory={(actor_base+a-ACTOR if ACTOR<=a<ACTOR+0x240 else a):v for a,v in memory.items()}
            memory.update({parent.screen.TABLE+i:b for i,b in enumerate(rom[parent.screen.TABLE_ROM:parent.screen.TABLE_ROM+148])})
            stream.put(memory,actor_base,0)
            stream.put(memory,actor_base+0x1D4,1)
            expected,cursor,calls=reference(memory,(OUTPUT,actor_base,first,second),0xFFFFFFFF,1)
            stream.put(expected,cursor,0x1000,2)
            expected_calls=[(parent.LOOKUP,(kind,0)),(parent.LOOKUP,(kind,1)),
                (screen.ENTRY,(OUTPUT,actor_base,first,second)),*calls]
            for words in (self.retail,self.words):
                connected={screen.ENTRY+i*4:w for i,w in enumerate(words)}
                model=Connected(caller,memory,(OUTPUT,0,0,0),phase,0xFFFFFFFF,1,parent.screen.ENTRY,connected)
                model.actor,model.channels=actor_base,(first,second)
                model.run()
                self.assertEqual(public(model.memory),public(expected))
                self.assertEqual(model.calls,expected_calls)
            cases+=1
        self.receipt('connected',cases=cases,parent_words=119,retail_finalizer_words=405,
            candidate_finalizer_words=len(self.words),lookup_and_PRNG_providers_opaque=True,
            full_gameplay_claim=False)


if __name__=='__main__':
    unittest.main()
