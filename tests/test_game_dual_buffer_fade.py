"""Public fade semantics and actual variadic-payload counterexample; no install credit."""
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_dual_buffer_fade as source
from tools.tests import game_view_point_projection_oracle as point
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function

STACK=point.STACK
RECORD,COUNTDOWN,ALT_COUNTDOWN,CLOCK,COLOR,TEXT,SUBMIT=0x20000,0x30000,0x30100,0x800BE9E4,0x1504332C,0x15042D94,0x15042ECC
CALLER,TABLE,CURSOR=0x150D0034,0x800888A0,0x76543210


def signed_byte(value):return (value&127)-(value&128)
def public(memory):return {a:v for a,v in memory.items() if not STACK-0x400<=a<STACK+0x100}


def fixture(count=8,flags=0,clock=1,index=0,alias=0,symbols=None):
    clock_address=(symbols or {}).get('D_800BE9E4',CLOCK)
    memory={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x100)}
    for base,size in ((RECORD-16,0x480),(COUNTDOWN-16,64),(ALT_COUNTDOWN-16,64),(clock_address-8,20),(0x800CBD50,64)):
        memory.update({base+i:(i*13+0x57)&255 for i in range(size)})
    for i in range(256):put(memory,RECORD+0x40+i*4,0x12000000+i*0x10203)
    put(memory,RECORD+0x48,COUNTDOWN);put(memory,RECORD+0x30,flags,1)
    put(memory,RECORD+0x3D,index,1);put(memory,clock_address,clock)
    address=(COUNTDOWN,RECORD+0x30,RECORD+0x3D,RECORD+0x40,RECORD+0x43,RECORD+0x48,
        RECORD+0x4B,clock_address,clock_address+3)[alias]
    put(memory,RECORD+0x48,address)
    # Pointer-field aliases begin with their actual pointer representation.
    if alias not in (5,6):put(memory,address,count,1)
    return memory,(RECORD,)


def effects(memory,target,record,ordinal,mode):
    if mode==1 and target==COLOR:
        index=(read(memory,record+0x3D,1)+1)&255
        put(memory,record+0x3D,index,1);put(memory,record+0x40+index*4,0xFACE0000+ordinal)
    elif mode==2 and target==TEXT:
        put(memory,record+0x3D,read(memory,record+0x3D,1)^1,1)
    elif mode==3 and target==COLOR and ordinal==1:
        put(memory,record+0x48,ALT_COUNTDOWN);put(memory,ALT_COUNTDOWN,99,1)
        put(memory,record+0x3D,1,1)


def reference(initial,args,mode=0,symbols=None):
    symbols=symbols or {};clock_address=symbols.get('D_800BE9E4',CLOCK)
    color,text=symbols.get('func_1504332C',COLOR),symbols.get('func_15042D94',TEXT)
    memory=dict(initial);record=args[0];calls=[];ordinals={COLOR:0,TEXT:0}
    countdown=read(memory,record+0x48)
    if read(memory,record+0x30,1)&1:put(memory,countdown,8,1)
    count=signed_byte(read(memory,countdown,1));old=0;alpha=255
    if count>0:
        old=(count*31)&255;alpha=255-old
        put(memory,countdown,(count-read(memory,clock_address))&255,1)
    for weight,other in ((alpha,False),(old,True)):
        if weight:
            calls.append((color,(206,196,97,weight)));ordinals[COLOR]+=1
            effects(memory,COLOR,record,ordinals[COLOR],mode)
            index=read(memory,record+0x3D,1)^(1 if other else 0)
            value=read(memory,record+0x40+index*4)
            calls.append((text,(146,190,129,value)));ordinals[TEXT]+=1
            effects(memory,TEXT,record,ordinals[TEXT],mode)
    return public(memory),calls


def cases():
    for count,flags,clock,index,mode,phase in itertools.product((0,1,2,7,8,9,33,127,128,255),(0,1,2,255),
            (0,1,3,8,127,255,0xFFFFFFFF,0x80000000),(0,1,255),range(4),(0,8)):
        yield *fixture(count,flags,clock,index),mode,phase
    for alias,count,flags,clock,mode,phase in itertools.product(range(1,9),(2,8,128,255),(0,1),
            (0,1,0xFFFFFFFF),range(4),(0,8)):
        yield *fixture(count,flags,clock,1,alias),mode,phase


class Oracle(point.PointProjectionOracle):
    def __init__(self,words,memory,args,mode=0,phase=0,symbols=None,entry=source.ENTRY,connected=None):
        self.providers=symbols or {};self.fade_mode=mode;self.record=args[0]
        self.ordinal={COLOR:0,TEXT:0};self.payloads=[]
        super().__init__(words,memory,args,[],phase,entry,connected)

    def execute(self,word):
        if word>>26==32:
            super().execute(word|0x10000000)
            rt=(word>>16)&31
            if rt:self.r[rt]=((self.r[rt]^128)-128)&0xFFFFFFFF
            self.dispatched_word=word
        else:super().execute(word)

    def record_call(self,target):
        color=self.providers.get('func_1504332C',COLOR);text=self.providers.get('func_15042D94',TEXT)
        if target in (color,text):self.calls.append((target,self.arguments(4)))
        elif target==SUBMIT:
            pointer=self.arguments(2)[1]
            self.payloads.append(tuple(self.get(pointer+i*4,4) for i in range(16)))
        elif target==source.ENTRY:self.calls.append((target,self.arguments(1)))
        else:raise AssertionError('Unexpected fade provider: '+hex(target))

    def hook(self,target):
        color=self.providers.get('func_1504332C',COLOR);text=self.providers.get('func_15042D94',TEXT)
        if target==SUBMIT:return
        kind=COLOR if target==color else TEXT if target==text else None
        if kind is None:raise AssertionError('Unexpected fade hook')
        self.ordinal[kind]+=1;effects(self.memory,kind,self.record,self.ordinal[kind],self.fade_mode)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for register in (1,2,3,*range(4,16),24,25):self.r[register]=0xA5000000+register
        self.f[:20]=[0xA5000000+i for i in range(20)]


class DualBufferFadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.obj,cls.padded,cls.images,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=(cls.out/'before-retail_rom').read_bytes()
        cls.truth=list(struct.unpack_from('>69I',cls.rom,source.ROM))
        context=type('OriginalContext',(),dict(root=cls.root,out=cls.out))
        cls.original=assembly.ViewListSetupTests.original.__func__(context,'original-fade',
            (cls.out/'before-tile_original').read_text(),source.FUNCTION)

    def receipt(self,name,**data):
        (self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def test_01_complete_candidate_identity_and_non_installable_lifetimes(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['unchanged_raw_padded_neighbors']),(65,48,24))
        self.assertEqual(self.images[0],self.images[1]);source.checked_parts(*source.parts(self.obj))
        self.assertEqual(self.images[0][2],0x00808025)
        self.assertEqual(self.images[0][31],0xAFA90024)
        self.assertEqual(self.truth[3:5],[0xAFA40030,0x8FAE0030])
        with self.assertRaisesRegex(ValueError,'extent/lifetimes'):source.require_installable(self.images[0])
        with self.assertRaisesRegex(ValueError,'unqualified'):source.require_installable(self.truth)
        raw,bindings=source.parts(self.obj)
        for i in range(65):
            wrong=bytearray(raw);wrong[i*4]^=1
            with self.assertRaises(ValueError):source.checked_parts(bytes(wrong),bindings)
        for at in bindings:
            wrong=dict(bindings);wrong[at]=[(bindings[at][0][0],'D_800BE9E8')]
            with self.assertRaises(ValueError):source.checked_parts(raw,wrong)
        self.receipt('emission',**self.row,raw_word_controls=65,binding_controls=6)

    def test_02_ordered_public_reference_aliases_and_callback_mutations(self):
        count=0;seen=set()
        for memory,args,mode,phase in cases():
            expected,calls=reference(memory,args,mode)
            for words in (self.truth,*self.images):
                machine=Oracle(words,memory,args,mode,phase).run()
                self.assertEqual((public(machine.memory),machine.calls,machine.r[2]),(expected,calls,1))
                if words is self.truth:seen.update(machine.visits)
            count+=1
        self.assertEqual({pc-source.ENTRY for pc in seen},set(range(0,276,4)))
        self.receipt('guest',three_way_public_cases=count,retail_words_executed=69,callback_modes=4,
            alias_placements=9,phases=2,private_state_and_fault_parity_not_claimed=True)

    def test_03_actual_color_and_variadic_wrapper_expose_private_gap(self):
        connected={}
        for entry,words in ((COLOR,22),(TEXT,42)):
            at=entry-0x15000000+0x2D4B0
            connected.update({entry+i*4:w for i,w in enumerate(struct.unpack_from('>%dI'%words,self.rom,at))})
        differences=[];count=0
        for initial in (0,1,8,127,128,255):
            memory,args=fixture(initial)
            machines=[Oracle(words,memory,args,connected=connected).run() for words in (self.truth,*self.images)]
            for m in machines:self.assertEqual(m.calls,machines[0].calls);self.assertEqual(m.r[2],1)
            self.assertEqual(machines[1].payloads,machines[2].payloads)
            differing=[(call,index,a,b) for call,(left,right) in enumerate(zip(machines[0].payloads,machines[1].payloads))
                for index,(a,b) in enumerate(zip(left,right)) if a!=b]
            self.assertTrue(differing,'Missing effective actual-helper private-lifetime counterexample')
            differences.append(dict(countdown=initial,words=differing));count+=1
        self.receipt('private-counterexample',actual_color_words=22,actual_text_words=42,cases=count,
            copied_words_per_text_call=16,positively_observed_differences=differences,installation_rejected=True,
            real_text_consumer_or_presentation_not_executed=True)

    def test_04_independent_original_raw_padded_relocations(self):
        count=0
        for index,(entry,clock,color,text) in enumerate(((source.ENTRY,CLOCK,COLOR,TEXT),
                (0x18018000,0x80347FFC,0x1814332C,0x18142D94),(0x1A027FFC,0x80418010,0x1B04332C,0x1B042D94))):
            symbols=dict(D_800BE9E4=clock,func_1504332C=color,func_15042D94=text);images=[]
            for label,obj in (('original',self.original),('raw',self.obj),('padded',self.padded)):
                data,fs,rs=source.parse_object(obj);f=fs[source.FUNCTION]
                text_asm,unresolved=emit_function(data,f,rs,source.FUNCTION,symbols);self.assertEqual(unresolved,[])
                stem=self.out/('rebase-%d-%s'%(index,label));asm=stem.with_suffix('.s');asm.write_text(text_asm)
                compiled=stem.with_suffix('.o');script=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(compiled),str(asm)],capture_output=True,check=True)
                script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%item for item in symbols.items()],'-o',str(elf),str(compiled)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>%dI'%(f['size']//4),source.projection.sections(elf)['.text'][1])))
            self.assertEqual(images[1],images[2])
            for byte,mode,alias in itertools.product((0,1,8,128),range(4),(0,2,7)):
                memory,args=fixture(byte,alias=alias,symbols=symbols);expected,calls=reference(memory,args,mode,symbols)
                for words in images:
                    machine=Oracle(words,memory,args,mode,symbols=symbols,entry=entry).run()
                    self.assertEqual((public(machine.memory),machine.calls,machine.r[2]),(expected,calls,1))
                count+=1
        self.receipt('rebases',independent_links=9,symbol_sets=3,three_way_public_cases=count,
            all_six_bindings=True,signed_low_carries=True,not_private_lifetime_or_actual_wrapper_rebases=True)

    def test_05_native_complete_body_separate_typed_caller_and_controls(self):
        declarations='#include <ultra64.h>\nextern s32 D_800BE9E4;\n'+source.PROTOTYPES
        driver=r'''#include <ultra64.h>
s32 D_800BE9E4;s32 func_150D01A0(u8 *);
typedef struct {u8 pad[0x30];u8 flags;u8 pad31[12];u8 index;u8 pad3E[2];s32 buffers[2];s8 *count;} Record;
static Record r;static s8 countdown;static u32 calls,error;static u8 alphas[2];static s32 values[2];
void func_1504332C(u8 a,u8 b,u8 c,u8 d){if(a!=206||b!=196||c!=97||calls>=4||calls&1)error=20;alphas[calls/2]=d;calls++;}
void func_15042D94(s32 a,s32 b,u8 c,s32 d,...){if(a!=146||b!=190||c!=129||calls>=4||!(calls&1))error=21;values[calls/2]=d;calls++;}
static int run(void){u32 byte,flag,clock,index,n,expectedCalls;u32 clocks[]={0,1,8,255,0xFFFFFFFFu,0x80000000u};
if(sizeof(void*)!=4||__builtin_offsetof(Record,count)!=72||__builtin_offsetof(Record,index)!=61)return 23;
for(byte=0;byte<256;byte++)for(flag=0;flag<2;flag++)for(clock=0;clock<6;clock++)for(index=0;index<2;index++){
s32 count;u32 old=0,alpha=255;u8 final;
r.flags=(u8)flag;r.index=(u8)index;r.buffers[0]=0x12345678;r.buffers[1]=(s32)0xABCDEF01u;r.count=&countdown;
countdown=(s8)byte;D_800BE9E4=(s32)clocks[clock];calls=0;error=0;
count=flag?8:(s8)byte;final=(u8)count;
if(count>0){old=((u32)count*31)&255;alpha=255-old;final=(u8)((u32)count-clocks[clock]);}
expectedCalls=(alpha?2:0)+(old?2:0);n=0;
if(func_150D01A0((u8 *)&r)!=1||error||calls!=expectedCalls||(u8)countdown!=final)return 22;
if(alpha){if(alphas[n]!=alpha||values[n]!=r.buffers[index])return 22;n++;}
if(old){if(alphas[n]!=old||values[n]!=r.buffers[index^1])return 22;}}
return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
        path=self.out/'native-driver.c';path.write_text(driver)
        controls={'unsigned-count':source.SELECTED.replace('count = *countdown;','count = *(u8 *)countdown;'),
            'wrong-factor':source.SELECTED.replace('count * 31','count * 32'),
            'wrong-buffer':source.SELECTED.replace('(state[0x15] ^ 1)','state[0x15]')}
        for opt in ('-O2','-O0'):
            for label,body in (('selected',source.SELECTED),*controls.items()):
                self.assertNotEqual(body,source.SELECTED) if label!='selected' else None
                c=self.out/('native-'+label+'.c');c.write_text(declarations+body+'\n');exe=self.out/('native-'+label+opt)
                subprocess.run(native_command(opt)+['-mstackrealign','-fno-builtin',str(c.relative_to(self.root)),
                    str(path.relative_to(self.root)),'-o',str(exe)],cwd=self.root,capture_output=True,check=True)
                result=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual(result.returncode,0 if label=='selected' else 22,(opt,label,result.stderr))
        self.receipt('native',cases_per_profile=6144,profiles=['O2','O0'],effective_controls=6,
            separate_typed_caller_UBSan=True,variadic_stub_reads_no_missing_arguments=True,
            guest_not_native_qualifies_aliases_full_byte_indices_and_actual_variadic_reads=True)

    def test_06_every_protected_live_and_frozen_input(self):
        source.freeze(self.root,self.out);real=hashlib.sha256;cache={}
        for key,path in source.PATHS.items():
            for p in (self.root/path,self.out/('before-'+key)):cache[p]=p.read_bytes()
        @lru_cache(None)
        def digest(data):return real(data)
        count=0
        for key,path in source.PATHS.items():
            for target,message in ((self.root/path,'Changed dual-buffer live'),(self.out/('before-'+key),'Changed dual-buffer frozen')):
                wrong=bytearray(cache[target]);wrong[len(wrong)//2]^=1;wrong=bytes(wrong)
                def read_bytes(path):return wrong if path==target else cache[path]
                with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'exists',lambda p:p in cache),\
                        patch.object(source.hashlib,'sha256',side_effect=digest):
                    with self.assertRaisesRegex(ValueError,message):source.freeze(self.root,self.out)
                count+=1
        self.receipt('inputs',protected_entries=len(source.PATHS),distinct_paths=len(set(source.PATHS.values())),fired_controls=count)

    def test_07_reproducible_profile_and_advisory_discriminators(self):
        rows=source.profiles(self.root,self.out)
        self.assertEqual({r['label']:(r['words'],r['frame']) for r in rows},
            {'normal':(65,48),'nodebug':(64,48),'o1':(74,48),'branch-weights':(64,48),'register-branch':(64,48),'staged-weight':(63,48)})
        self.assertEqual(rows[0]['sha256'],source.RAW_SHA)
        self.assertEqual(rows[3]['sha256'],rows[4]['sha256'])
        for row in rows:self.assertFalse(row['installable'])
        self.receipt('screens',reproduced_profiles=6,advisory_staged_weight_suggestion_falsified=True,
            no_original_volatile_qualifier_or_alternate_profile_claimed=True)

    def test_08_full_actual_callback_caller_uses_success_return(self):
        caller=list(struct.unpack_from('>35I',self.rom,CALLER-0x15000000+0x2D4B0));count=0
        self.assertEqual(struct.unpack_from('>I',self.rom,0x22D360)[0],source.ENTRY)
        for byte,flags,kind,mode,phase in itertools.product((0,8,33,128),(0,1,128,255),(0,255),range(4),(0,8)):
            memory,args=fixture(byte,flags);put(memory,RECORD+0x4C,kind,1);put(memory,TABLE,source.ENTRY)
            expected,calls=reference(memory,args,mode) if kind==0 else (public(memory),[])
            expected=dict(expected);put(expected,RECORD+0x30,read(expected,RECORD+0x30,1)&254,1)
            for words in (self.truth,*self.images):
                machine=Oracle(caller,memory,(CURSOR,RECORD,0xABCDEF00),mode,phase,entry=CALLER,
                    connected={source.ENTRY+i*4:w for i,w in enumerate(words)})
                machine.record=RECORD;machine.run()
                self.assertEqual((public(machine.memory),[c for c in machine.calls if c[0]!=source.ENTRY],machine.r[2]),
                    (expected,calls,CURSOR))
            count+=1
        self.receipt('caller',full_actual_caller_words=35,three_way_public_cases=count,
            table_slot=0,success_return_retains_cursor_and_clears_flag=True,not_private_caller_payload_parity=True)


if __name__=='__main__':unittest.main()
