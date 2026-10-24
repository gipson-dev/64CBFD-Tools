"""Sequence script requests: signed selector, full commands and retained audio setters."""
from dataclasses import dataclass
from pathlib import Path
import csv
import io
import itertools
import json
import struct
import subprocess
import unittest

from tools.experiments import game_sequence_event_dispatch as source
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT=Path(__file__).resolve().parents[2]
PACKET,SELECTOR=0x20000,0x800D3840
START_SEQUENCE,LEVEL,STOP=0x1001263C,0x151F2D6C,0x151F2BA8
RESOURCE,PAN,ENVELOPE,ATTACH=0x1502B020,0x151F2DFC,0x151F2E4C,0x151F2960
STATE,VOLUME,FADE,IDENTITY=0x800E0E04,0x800E0E08,0x800E0E10,0x800427F4
TABLE,VM,VM_END=0x800884D4,0x150AE12C,0x150AE194
MASK=0x89ABCDEF
COUNTS=(0x80000000,0xFFFFFFFF,0,1,2,3,4,5,6,7,0x7FFFFFFF,0x12345678)
VALUES=(0x80000000,0xFFFFFFFF,0,1,3,4,32767,32768,0x7FFFFFFF)
SEQUENCES=(0,0xD2,0x123400D2,0xFFFFFFFF,0x80000000,0x7FFFFFFF)


def signed(value):return ((value&0xFFFFFFFF)^0x80000000)-0x80000000


@dataclass(frozen=True)
class Case:
    command:int=0
    count:int=3
    sequence:int=0xD2
    level:int=32768
    fade:int=11000
    alias:int=0
    mutate:bool=False
    resource:int=0x12345678
    size:int=0x4000
    poison:int=0xA5000002


def packet_address(case,phase=0):return (PACKET,SELECTOR-8,VOLUME-8,STACK+phase-32)[case.alias]


def fixture(case,phase=0):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-1024,1024)}
    for base,size in((PACKET,32),(SELECTOR-16,48),(STATE-16,64),(IDENTITY-8,20)):
        m.update({base+i:0xA5 for i in range(size)})
    put(m,SELECTOR,case.count);put(m,STATE,5);put(m,VOLUME,13);put(m,FADE,11010);put(m,IDENTITY,0x1357,2)
    p=packet_address(case,phase)
    for i,value in enumerate((case.sequence,case.command,case.level,case.fade)):put(m,p+4*i,value)
    return m


def effect(m,case,phase=0):
    if case.mutate:
        put(m,SELECTOR,9);p=packet_address(case,phase);put(m,p+8,0xFFFFFFB3);put(m,p+12,11010)


def reference(initial,case,phase=0,chain=False,symbols=None,mask_call=None):
    s=source.SYMBOLS if symbols is None else symbols;m=dict(initial);calls=[];p=packet_address(case,phase)
    command=case.command&0xFFFFFFFF;count=signed(read(m,s['D_800D3840']))if command in(0,1)else 0
    mutated=False
    def update():
        nonlocal mutated
        if not mutated:
            if case.mutate:
                put(m,s['D_800D3840'],9);put(m,p+8,0xFFFFFFB3);put(m,p+12,11010)
            mutated=True
    def volume(level,fade):
        calls.append((s['func_151F2D6C'],(level,fade)))
        if chain:
            calls.append((mask_call,(1,)));update();put(m,VOLUME,max(0,min(32767,signed(level))));put(m,FADE,fade);calls.append((mask_call,(MASK,)))
        else:update()
    if command==0:
        level=32767 if count<3 else read(m,p+8);calls.append((s['func_1001263C'],(case.sequence,level,64)))
        if chain:
            calls.append((RESOURCE,('size-out',2,22,case.sequence)));update();put(m,IDENTITY,case.sequence&65535,2)
            if case.resource and case.size:
                volume(level,0);calls.append((PAN,(64,1)))
                calls.append((ENVELOPE,(0,0)if case.sequence==0xD2 else(10,11000)));calls.append((ATTACH,(case.resource,case.size)))
        else:update()
    elif command==1:volume(read(m,p+8),read(m,p+12)if count==4 else 0)
    elif command==2:
        calls.append((s['func_151F2BA8'],()))
        if chain:
            calls.append((mask_call,(1,)));update();put(m,STATE,3);calls.append((mask_call,(MASK,)))
        else:update()
    return m,calls,int(command in(0,1,2))


def public(memory):return {a:b for a,b in memory.items()if not STACK-1024<=a<STACK+1024}


class SequenceOracle(TimingOracle):
    def __init__(self,words,memory,case=Case(),phase=0,entry=source.ENTRY,connected=None,symbols=None,mask_call=None,arguments=None):
        super().__init__(words,memory,phase=phase,entry=entry,connected=connected,
            arguments=arguments or(case.sequence,case.command,packet_address(case,phase)))
        self.case,self.phase,self.symbols,self.mask_call=case,phase,source.SYMBOLS if symbols is None else symbols,mask_call
        self.effect_done=False

    def record_call(self,target):
        counts={self.symbols['func_1001263C']:3,self.symbols['func_151F2D6C']:2,self.symbols['func_151F2BA8']:0,
                PAN:2,ENVELOPE:2,ATTACH:2,source.ENTRY:3,self.mask_call:1}
        if target==RESOURCE:
            args=self.arguments(4);self.size_out=args[0]
            assert self.size_out==self.r[29]+24,('Unexpected original size home',args)
            assert read(self.memory,self.size_out)==0,'Original start did not initialize output size'
            args=('size-out',*args[1:])
        else:
            assert target in counts,('Unbounded sequence service',hex(target))
            args=self.arguments(counts[target])
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        if not self.effect_done:
            if self.case.mutate:
                put(self.memory,self.symbols['D_800D3840'],9);p=packet_address(self.case,self.phase)
                put(self.memory,p+8,0xFFFFFFB3);put(self.memory,p+12,11010)
            self.effect_done=True
        if target==RESOURCE:self.put(self.size_out,self.case.size,4);value=self.case.resource
        elif target==self.mask_call:value=MASK
        else:value=self.case.poison
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0x87654321,0x12345678;self.r[2]=value


class WindowBoundary(Exception):pass


class WindowCode(faults.TrackedCode):
    def __getitem__(self,pc):
        if pc==self.end:raise WindowBoundary
        return super().__getitem__(pc)


def controls():
    b=source.SELECTED
    return dict(selected=b,
        unsigned_selector=b.replace('D_800D3840 >= 3','(u32)D_800D3840 >= 3'),
        wrong_threshold=b.replace('D_800D3840 >= 3','D_800D3840 > 3'),
        narrowed_command=b.replace('switch (command)','switch ((u8)command)'),
        wrong_fade_gate=b.replace('D_800D3840 == 4','D_800D3840 <= 4'),
        wrong_level_word=b.replace('packet[2]','packet[1]'),
        wrong_fade_word=b.replace('packet[3]','packet[2]'),
        wrong_pan=b.replace('level, 0x40','level, 0'),
        swapped_fields=b.replace('packet[2], packet[3]','packet[3], packet[2]'),
        missing_stop=b.replace('            func_151F2BA8();','            (void)sequence;'),
        wrong_return=b.replace('return 1;','return sequence != 0;'),
        wrong_default=b.replace('    return 0;','    return 1;'))


def native_harness(values):
    text=source.HEADERS+source.DECLARATIONS.replace('extern s32 D_800D3840;\n','')+r'''
static s32 selectorWords[4],audioWords[8],ordinary[4],*packet;
#define D_800D3840 selectorWords[2]
#define D_800E0E04 audioWords[1]
#define D_800E0E08 audioWords[2]
#define D_800E0E10 audioWords[4]
static s16 D_800427F4;
static u32 mutation,mutated,resource,sizeValue,error,used,expectedUsed;
typedef struct {u32 target,a,b,c;} Call;
static Call actual[16],expected[16];
static void effect(void){if(!mutated++){if(mutation){D_800D3840=9;packet[2]=-77;packet[3]=11010;}}}
static void record(u32 target,u32 a,u32 b,u32 c){if(used>=16){error=1;return;}actual[used++]=(Call){target,a,b,c};}
static void want(u32 target,u32 a,u32 b,u32 c){expected[expectedUsed++]=(Call){target,a,b,c};}
u32 func_1502B020(u32 *out,u32 depth,...){
 __builtin_va_list ap;s32 kind,seq;__builtin_va_start(ap,depth);kind=__builtin_va_arg(ap,s32);seq=__builtin_va_arg(ap,s32);__builtin_va_end(ap);
 if(*out)error=1;record(0x1502B020,depth,(u32)kind,(u32)seq);*out=sizeValue;effect();return resource;
}
u32 osSetIntMask(u32 mask){record(MASK_CALL,mask,0,0);effect();return 0x89ABCDEF;}
void func_151F2DFC(s32 a,s32 b){record(0x151F2DFC,(u32)a,(u32)b,0);effect();}
void func_151F2E4C(s32 a,s32 b){record(0x151F2E4C,(u32)a,(u32)b,0);effect();}
void func_151F2960(s32 a,s32 b){record(0x151F2960,(u32)a,(u32)b,0);effect();}
'''
    for path,name,new in(('conker/src/init_12560.c','func_1001263C','real_start'),
        ('conker/src/libultra/audio/game_21FC90.c','func_151F2D6C','real_level'),
        ('conker/src/libultra/audio/game_21FC90.c','func_151F2BA8','real_stop')):
        body=values[path].decode();body=body[slice(*source.function_span(body,name))]
        body=body.replace('func_151F2D6C_retail','func_151F2D6C').replace('func_151F2E4C_retail','func_151F2E4C')
        text+=body.replace('void '+name+'(','static void '+new+'(')+'\n'
    text+=r'''
__attribute__((noinline,noclone)) void func_1001263C(s32 a,s32 b,s32 c){record(0x1001263C,(u32)a,(u32)b,(u32)c);real_start(a,b,c);}
__attribute__((noinline,noclone)) void func_151F2D6C(s32 a,s32 b){record(0x151F2D6C,(u32)a,(u32)b,0);real_level(a,b);}
__attribute__((noinline,noclone)) void func_151F2BA8(void){record(0x151F2BA8,0,0,0);real_stop();}
'''
    for name,body in controls().items():
        if name!='selected'and body==source.SELECTED:raise ValueError('Ineffective sequence control '+name)
        text+=body.replace(source.FUNCTION,source.FUNCTION+'_'+name)+'\n'
    text+=r'''
typedef s32(*Dispatch)(s32,s32,s32*);
static u32 sequences[]={SEQUENCES},counts[]={COUNTS},levels[]={LEVELS};
static void expectedMask(void){want(MASK_CALL,1,0,0);want(MASK_CALL,0x89ABCDEF,0,0);}
static int one(Dispatch fn,u32 command,u32 ci,u32 vi,u32 alias,u32 mutate){
 s32 sel,lev,fade,seq=(s32)sequences[vi%6];s32 beforeSelector[4],beforeAudio[8],beforePacket[4];u32 i; s16 id=0x1357;
 for(i=0;i<4;i++){selectorWords[i]=(s32)0xA5A5A5A5;ordinary[i]=(s32)0xA5A5A5A5;}
 for(i=0;i<8;i++)audioWords[i]=(s32)0xA5A5A5A5;
 D_800D3840=(s32)counts[ci];D_800E0E04=5;D_800E0E08=13;D_800E0E10=11010;D_800427F4=id;
 packet=alias==1?selectorWords:alias==2?audioWords:ordinary;
 packet[0]=seq;packet[1]=(s32)command;packet[2]=(s32)levels[vi];packet[3]=(s32)levels[(vi+4)%9];
 sel=D_800D3840;lev=command==0&&sel<3?32767:packet[2];fade=sel==4?packet[3]:0;
 for(i=0;i<4;i++){beforeSelector[i]=selectorWords[i];beforePacket[i]=packet[i];}for(i=0;i<8;i++)beforeAudio[i]=audioWords[i];
 mutation=mutate;mutated=error=used=expectedUsed=0;resource=(ci+vi)%3?0x80000000:0;sizeValue=(ci+vi)%4?0x4000:0;
 if(command<=2){
  if(mutate){beforeSelector[2]=9;beforePacket[2]=-77;beforePacket[3]=11010;}
  if(alias==1){if(mutate){beforeSelector[2]=-77;beforeSelector[3]=11010;}for(i=0;i<4;i++)beforePacket[i]=beforeSelector[i];}
  if(alias==2){if(mutate){beforeAudio[2]=-77;beforeAudio[3]=11010;}for(i=0;i<4;i++)beforePacket[i]=beforeAudio[i];}
  if(command==0){
   want(0x1001263C,(u32)seq,(u32)lev,64);want(0x1502B020,2,22,(u32)seq);id=(s16)seq;
   if(resource&&sizeValue){
    want(0x151F2D6C,(u32)lev,0,0);expectedMask();beforeAudio[2]=lev<0?0:lev>=32768?32767:lev;beforeAudio[4]=0;
    want(0x151F2DFC,64,1,0);want(0x151F2E4C,seq==0xD2?0:10,seq==0xD2?0:11000,0);want(0x151F2960,resource,sizeValue,0);
   }
  }else if(command==1){want(0x151F2D6C,(u32)lev,(u32)fade,0);expectedMask();beforeAudio[2]=lev<0?0:lev>=32768?32767:lev;beforeAudio[4]=fade;}
  else{want(0x151F2BA8,0,0,0);expectedMask();beforeAudio[1]=3;}
 }
 if(alias==1)for(i=0;i<4;i++)beforePacket[i]=beforeSelector[i];
 if(alias==2)for(i=0;i<4;i++)beforePacket[i]=beforeAudio[i];
 if(fn(seq,(s32)command,packet)!=(command<=2?1:0)||error||used!=expectedUsed||D_800427F4!=id)return 23;
 for(i=0;i<used;i++)if(actual[i].target!=expected[i].target||actual[i].a!=expected[i].a||actual[i].b!=expected[i].b||actual[i].c!=expected[i].c)return 23;
 for(i=0;i<4;i++)if(selectorWords[i]!=beforeSelector[i]||packet[i]!=beforePacket[i])return 23;
 for(i=0;i<8;i++)if(audioWords[i]!=beforeAudio[i])return 23;
 return 0;
}
static int variant(Dispatch fn,u32 full){
 u32 c,ci,vi,a,m;for(c=0;c<(full?512u:4u);c++)for(ci=0;ci<12;ci++)for(vi=0;vi<9;vi++)for(a=0;a<3;a++)for(m=0;m<2;m++)
  if(one(fn,full?c:(u32[]){0,1,2,256}[c],ci,vi,a,m))return 23;return 0;
}
int run(void){u32 i,c;
'''.replace('SEQUENCES',','.join('0x%Xu'%v for v in SEQUENCES)).replace('COUNTS',','.join('0x%Xu'%v for v in COUNTS)).replace('LEVELS',','.join('0x%Xu'%v for v in VALUES))
    for i,name in enumerate(controls()):text+='if(variant(%s_%s,%d)!=%d)return %d;\n'%(source.FUNCTION,name,int(name=='selected'),0 if name=='selected'else 23,11 if name=='selected'else 40+i)
    text+=r'''
for(c=0;c<6;c++)for(i=0;i<12;i++)if(one(func_1509E640_selected,(u32[]){0xFFFFFFFF,0x80000000,0x10000000,0xABCD0000,0xABCD0001,0xABCD0002}[c],i,8,0,1))return 70;
mutation=0;used=0;D_800D3840=-1;if(func_1509E640_selected(0,0,0)!=1)return 71;
for(c=3;c<256;c++)if(func_1509E640_selected(0,(s32)c,0))return 72;
return 0;}
'''
    return text+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')


class SequenceEventDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/source.BUILD;cls.values=source.snapshot(cls.out);cls.rom=cls.values['conker/conker.us.bin']
        cls.installed=(ROOT/source.SOURCE).read_bytes()!=cls.values[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'qualified-padded.o',source.OWNER);at=fs[source.FUNCTION]['value'];cls.words=list(struct.unpack_from('>44I',data,at))
        data,fs=source.link_owner(ROOT,cls.out,cls.out/'after-owner.o',source.OWNER);at=fs[source.FUNCTION]['value'];cls.raw=list(struct.unpack_from('>44I',data,at))
        cls.truth=list(struct.unpack_from('>44I',cls.rom,source.ROM));cls.receipt={}
        syms={name:fields[1]for _,name,fields,_ in source.symbol_rows(cls.values['conker/build/conker.us.elf'])}
        cls.mask_call=syms['osSetIntMask'];cls.helpers={entry:list(struct.unpack_from('>%dI'%n,cls.rom,entry-0x10000000 if entry==START_SEQUENCE else entry-0x15000000+0x2D4B0))for entry,n in((START_SEQUENCE,43),(LEVEL,36),(STOP,16))}
        cls.connected={at:word for entry,words in cls.helpers.items()for at,word in zip(range(entry,entry+4*len(words),4),words)}
        for alias,canonical in(('func_151F2D6C_retail','func_151F2D6C'),('func_151F2E4C_retail','func_151F2E4C')):assert syms[alias]==syms[canonical]

    def compare(self,case,phase=0,chain=False,images=None,entry=None,symbols=None,raw=False):
        memory=fixture(case,phase)
        if symbols is not None:
            put(memory,symbols['D_800D3840'],read(memory,SELECTOR))
        expected,calls,result=reference(memory,case,phase,chain,symbols,self.mask_call)
        models=[SequenceOracle(w,memory,case,phase,source.ENTRY if entry is None else entry,self.connected if chain else None,symbols,self.mask_call).run()for w in(images or(self.truth,self.words))]
        for m in models:self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result)
        for m in models[1:]:self.assertEqual(complete(models[0]),complete(m))
        if raw:
            m=SequenceOracle(self.raw,memory,case,phase,mask_call=self.mask_call).run();self.assertEqual(public(m.memory),public(expected));self.assertEqual(m.calls,calls);self.assertEqual(m.r[2],result)
        return models[0]

    def test_01_derived_permutation_all_guards_and_Make(self):
        raw,bindings=source.payload(self.out/'after-owner.o');self.assertEqual(source.normalized(raw,bindings),source.payload(source.original(ROOT,self.out)))
        for at in range(0,176,4):
            bad=bytearray(raw);bad[at]^=1
            with self.assertRaises(ValueError):source.normalized(bytes(bad),bindings)
        for at in bindings:
            bad=dict(bindings);bad.pop(at)
            with self.assertRaises(ValueError):source.normalized(raw,bad)
        old=self.values['conker/retail_word_patches.us.csv'];new=source.guard_bytes(old,raw,bindings);self.assertTrue(new.startswith(old))
        rows=[r for r in csv.DictReader(io.StringIO(new.decode()))if r['filename']==source.OWNER];fields=list(rows[0]);owned=[r for r in rows if r['function']==source.FUNCTION];self.assertEqual(len(owned),27);checks=0
        for target in owned:
            for kind in('word','binding'):
                changed=[dict(r)for r in rows];row=next(r for r in changed if r['function']==source.FUNCTION and r['offset']==target['offset'])
                if kind=='word':row['expected']='0x%08X'%(int(row['expected'],0)^1)
                else:row['expected_relocations']='R_MIPS_26:func_151F2BA8'
                stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(changed)
                path=self.out/'bad-guard.csv';path.write_text(stream.getvalue())
                with self.assertRaisesRegex(ValueError,'stale'):source.emit_padded_assembly(self.out/'after-owner.o',ROOT/source.ASM,word_patches_path=path,filename=source.OWNER)
                checks+=1
        with self.assertRaises(ValueError):source.guard_bytes(new,raw,bindings)
        self.assertEqual(self.words,self.truth);self.assertEqual(json.loads((self.out/'qualification.json').read_text())['preserved_neighbors'],3)
        self.assertTrue(json.loads((self.out/'make-shadow.json').read_text())['complete_padded_object_equal'])
        self.receipt.update(body_words=44,new_guards=27,bindings=8,preserved_neighbors=3,actual_guard_corruptions=checks,compiler_only=False)

    def test_02_guest_full_word_commands_selector_and_aliases(self):
        phases=0;visits=set()
        for command,count,level,alias,mutate,phase in itertools.product(range(3),COUNTS,VALUES,range(4),(False,True),(0,8)):
            case=Case(command,count,SEQUENCES[VALUES.index(level)%6],level,VALUES[(VALUES.index(level)+4)%9],alias,mutate)
            m=self.compare(case,phase,raw=True);visits.update(m.visits);phases+=1
        for command,phase in itertools.product(range(3,512),(0,8)):
            m=self.compare(Case(command,0xFFFFFFFF),phase);visits.update(m.visits);phases+=1
        for command in(0xFFFFFFFF,0x80000000,0x10000000,0xABCD0000,0xABCD0001,0xABCD0002):
            m=self.compare(Case(command,4));visits.update(m.visits);phases+=1
        self.assertEqual(set(range(source.ENTRY,source.ENTRY+176,4))-visits,{source.ENTRY+124})
        self.assertEqual(self.truth[31],self.truth[25]);self.assertEqual(self.truth[31],self.truth[26])
        for command,count,ptr in((0,2,0),(2,4,0),(0x100,4,0),(1,3,PACKET)):
            case=Case(command,count);m=fixture(case)
            for at in range(PACKET+12,PACKET+16):m.pop(at)
            models=[SequenceOracle(w,m,case,arguments=(case.sequence,command,ptr)).run()for w in(self.truth,self.words)]
            self.assertEqual(complete(models[0]),complete(models[1]))
        self.receipt.update(guest_phases=phases,all_43_reachable_root_words_visited=True,unreachable_duplicate_load_words=1,raw_C_public_semantics=True,guest_private_aliases_not_portable_C_claim=True)

    def test_03_native_actual_helpers_and_eleven_defined_controls(self):
        c=self.out/'native.c';c.write_text(native_harness(self.values).replace('MASK_CALL','0x%Xu'%self.mask_call))
        for opt in('-O0','-O2','-O3'):
            exe=self.out/('native-'+opt[1:]);p=subprocess.run(native_command(opt)+[str(c),'-o',str(exe)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),p.stdout+p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,text=True);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''),opt)
        self.receipt.update(native_selected_cases_per_optimization=512*12*9*3*2,native_optimizations=3,defined_wrong_C_controls=11,trap_UBSan=True,actual_three_helper_C_bodies=True,allocated_or_complete_typed_backing=True)

    def test_04_registration_and_original_handwritten_VM_window(self):
        ptr=struct.pack('>I',source.ENTRY);jal=struct.pack('>I',0x0C000000|(source.ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==ptr],[0x22CFA8]);self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        old=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(old,TABLE,60);self.assertEqual(old[at:at+60],self.rom[0x22CF94:0x22CFD0])
        code=list(struct.unpack_from('>26I',self.rom,VM-0x15000000+0x2D4B0));phases=0
        for nibble,sequence,command,count,phase in itertools.product((0,6),SEQUENCES,(0,1,2,0x100,0xFFFFFFFF),(2,4),(0,8)):
            sequence&=0xFFFF0FFF;case=Case(command,count,sequence);memory=fixture(case,phase);p=packet_address(case,phase);put(memory,p,sequence|(nibble<<12))
            for i in range(15):put(memory,TABLE+4*i,int.from_bytes(old[at+4*i:at+4*i+4],'big'))
            models=[]
            for words in(self.truth,self.words):
                m=SequenceOracle(code,memory,case,phase,VM,dict(zip(range(source.ENTRY,source.ENTRY+176,4),words)),mask_call=self.mask_call,arguments=(p,))
                m.r[31]=VM_END;m.code[VM_END]=0;m.code=WindowCode(m.code,m);m.code.end=VM_END
                with self.assertRaises(WindowBoundary):m.run()
                self.assertEqual([a for t,a in m.calls if t==source.ENTRY],[(sequence,command,p)]if nibble else[])
                self.assertEqual((m.r[2],m.r[23],m.r[31],m.r[29]),(int(command in(0,1,2))if nibble else 0,VM_END,VM_END,STACK+phase));models.append(m)
            self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.receipt.update(registered_table_slot=5,original_VM_window_words=26,VM_window_phases=phases,custom_S7_return_contract=True,complete_C_parent_claimed=False)

    def test_05_retained_original_and_live_helper_chain(self):
        old=self.values['conker/build/conker.us.elf'];visits=set();phases=0
        for entry,words in self.helpers.items():
            at=source.elf_slot_offset(old,entry,4*len(words));self.assertEqual(list(struct.unpack_from('>%dI'%len(words),old,at)),words)
        for command,count,sequence,level,alias,mutate,resource,size,phase in itertools.product(range(3),(2,4),SEQUENCES,(0x80000000,32767,32768),range(3),(False,True),(0,0x80000000),(0,0x4000),(0,8)):
            m=self.compare(Case(command,count,sequence,level,0x80000000,alias,mutate,resource,size),phase,True);visits.update(m.visits);phases+=1
        visited={entry:sorted(set(range(entry,entry+4*len(words),4))&visits)for entry,words in self.helpers.items()}
        self.receipt.update(retained_helper_literal_words=95,helper_phases=phases,helper_visited_words={hex(k):len(v)for k,v in visited.items()},resource_interrupt_pan_envelope_and_attach_backends_bounded=True)

    def linked(self,obj,entry,symbols,label):
        text,functions,bindings=source.parse_object(obj);asm,unknown=emit_function(text,functions[source.FUNCTION],bindings,source.FUNCTION,symbols);self.assertFalse(unknown)
        p=self.out/label;p.with_suffix('.s').write_text(asm);p.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
        subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(p.with_suffix('.o')),str(p.with_suffix('.s'))],capture_output=True,check=True)
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(p.with_suffix('.ld')),'-e',source.FUNCTION,*['--defsym=%s=0x%X'%x for x in symbols.items()],'-o',str(p.with_suffix('.elf')),str(p.with_suffix('.o'))],capture_output=True,check=True)
        return list(struct.unpack_from('>44I',sections(p.with_suffix('.elf'))['.text'][1]))

    def test_06_GNU_carries_and_fired_root_fault_prefixes(self):
        links=phases=cuts=0
        rebases=((source.ENTRY,source.SYMBOLS),(0x18017FFC,dict(zip(source.SYMBOLS,(0x81017FFC,0x18208000,0x1830FFFC,0x18408000)))),(0x1A028000,dict(zip(source.SYMBOLS,(0x82018000,0x1B04FFFC,0x1B058000,0x1B06FFFC)))))
        for i,(entry,symbols)in enumerate(rebases):
            objects=(source.original(ROOT,self.out),self.out/'qualified-padded.o',self.out/'make-shadow/src/game/generated_CBAF0.c.o')
            images=[self.linked(obj,entry,symbols,'rebase-%d-%d'%(i,j))for j,obj in enumerate(objects)];links+=3;self.assertEqual(images[0],images[1]);self.assertEqual(images[0],images[2])
            for command,count,phase in itertools.product((0,1,2,0x100),COUNTS,(0,8)):
                self.compare(Case(command,count,level=0x80000000),phase,images=images,entry=entry,symbols=symbols);phases+=1
        for command,count,alias,phase in itertools.product((0,1,2,0x100),(2,3,4),range(4),(0,8)):
            case=Case(command,count,alias=alias);memory=fixture(case,phase);done=SequenceOracle(self.truth,memory,case,phase,mask_call=self.mask_call).run()
            for cut in range(done.root_accesses):
                models=[SequenceOracle(w,memory,case,phase,mask_call=self.mask_call)for w in(self.truth,self.words)]
                for m in models:
                    m.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):m.run()
                self.assertEqual(complete(models[0]),complete(models[1]));self.assertEqual((models[0].current_pc,models[0].delay_of),(models[1].current_pc,models[1].delay_of));cuts+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,fired_root_fault_prefixes=cuts,portable_C_fault_claimed=False)

    def test_07_strict_image_body_and_metadata_corruptions(self):
        old=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+176];wanted=source.predicted_image(old,truth)
        positions=[0,len(wanted)-1,source.elf_slot_offset(old,source.ENTRY,176),source.elf_slot_offset(old,LEVEL,4),source.elf_slot_offset(old,TABLE+20,4),source.elf_slot_offset(old,0x80082B20,4)]
        positions.extend(at+8 for at,name,_,_ in source.symbol_rows(old)if name==source.FUNCTION)
        for pos in positions:
            wrong=bytearray(wanted);wrong[pos]^=1
            with self.assertRaises(ValueError):source.check_image(old,bytes(wrong),truth)
        with self.assertRaises(ValueError):source.check_image(old,wanted[:-1],truth)
        with self.assertRaises(ValueError):source.predicted_image(old,bytes(176))
        self.receipt.update(strict_image_negatives=len(positions)+2,metadata_exclusions=0)

    def test_08_frozen_inputs_guard_history_and_installation(self):
        source.check_inputs(ROOT,self.out,self.installed)
        old=self.values['conker/retail_word_patches.us.csv'];raw,bindings=source.payload(self.out/'after-owner.o')
        self.assertEqual((ROOT/'conker/retail_word_patches.us.csv').read_bytes(),source.guard_bytes(old,raw,bindings)if self.installed else old)
        self.receipt.update(focused_inputs=33,guard_prefix_byte_identical=True,installed=self.installed)


if __name__=='__main__':unittest.main()
