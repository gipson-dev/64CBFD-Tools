"""Unsigned handle retirement, live callback reloads, guards and linked scope."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_resource_retirement as source
from tools.tests import game_packet_rectangle_oracle as base
from tools.tests.test_game_projected_packet_draw import native_command

ACTOR=0x30000
OFFSETS=(0x138,0x13C,0x134,0x140,0x144)
HANDLES=(0,1,0x7FFF,0x8000,0xFFFF)
WRONG=0x1516979C


def fixture(mask=31,handle=1,alias=0,high=0):
    memory={base.STACK+i:(i*13+0xA5)&255 for i in range(-256,256)}
    memory.update({ACTOR+i:(i*7+0xA5)&255 for i in range(0x1B0)})
    for i,offset in enumerate(OFFSETS):
        base.put(memory,ACTOR+offset,((0x80000000 if high else 0)+0x50000+
            (0 if alias else i*32)) if mask&(1<<i) else 0)
    base.put(memory,ACTOR+0x1A0,handle,2)
    base.put(memory,ACTOR+0x1A2,0xA55A,2)
    return memory,(ACTOR,)


def effect(memory,mode,number,target,arg):
    if target in (source.HANDLE,source.RETIRE,WRONG):
        if target==source.HANDLE:
            base.put(memory,ACTOR+0x1A0,0x8001,2)
        if mode==1 and number==1:
            for offset in OFFSETS:base.put(memory,ACTOR+offset,0)
        elif mode==2:
            for i,offset in enumerate(OFFSETS):
                base.put(memory,ACTOR+offset,0x80060000+(i+number)*32)
        elif mode==3:
            for i,offset in enumerate(OFFSETS):
                base.put(memory,ACTOR+offset,0 if (i+number)&1 else 0x80070000+i*32)
    elif target==source.FINISH:
        base.put(memory,ACTOR+0x50,0xF1A10000|number)
    else:
        raise AssertionError(('unknown retirement provider',hex(target)))


def reference(initial,mode=0,base_only=False):
    memory,calls=dict(initial),[]
    if not base_only:
        handle=base.read(memory,ACTOR+0x1A0,2)
        if handle:
            calls.append((source.HANDLE,handle))
            effect(memory,mode,len(calls),*calls[-1])
        for offset in OFFSETS:
            pointer=base.read(memory,ACTOR+offset)
            if pointer:
                calls.append((source.RETIRE,pointer))
                effect(memory,mode,len(calls),*calls[-1])
    calls.append((source.FINISH,ACTOR))
    effect(memory,mode,len(calls),*calls[-1])
    return memory,calls


class RetirementOracle(base.RectangleOracle):
    def __init__(self,words,memory,args,mode=0,**kwargs):
        self.retirement_mode,self.entered=mode,False
        super().__init__(words,memory,args,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def record_call(self,target):
        if target==source.ENTRY:
            self.entered=self.r[4]==ACTOR
            return
        if target not in (source.HANDLE,source.RETIRE,source.FINISH,WRONG):
            raise AssertionError(('unconnected retirement call',hex(target)))
        self.calls.append((target,self.r[4]))

    def hook(self,target):
        effect(self.memory,self.retirement_mode,len(self.calls),target,self.r[4])
        for register in (*range(2,16),24,25):
            self.r[register]=(0xA5000000+len(self.calls)*256+register)&0xFFFFFFFF
        self.hi,self.lo=0x12345678,0x89ABCDEF
        for register in range(20):self.f[register]=0x3F800000+register


def controls():
    body=source.SELECTED
    cached=body.replace('    u16 handle;','    u16 handle;\n    struct102 *first;')
    cached=cached.replace('    handle = actor->handle1A0;',
        '    first = actor->resources.resource28;\n    handle = actor->handle1A0;')
    cached=cached.replace('resources->resource28','first')
    return {
        'signed-positive':body.replace('handle != 0','(s16)handle > 0'),
        'wrong-halfword':body.replace('handle = actor->handle1A0;',
            'handle = *(u16 *)((u8 *)actor + 0x1A2);'),
        'drop-handle':body.replace('        func_100111C8(handle);','        (void)handle;'),
        'wrong-order':body.replace('resource2C','saved24').replace('resource24','resource2C').replace('saved24','resource24'),
        'cache-before-handle':cached,
        'wrong-final-owner':body.replace('(struct210 *)actor);','(struct210 *)((u8 *)actor + 0x110));'),
        'immediate-free':body.replace('func_1516972C','func_1516979C'),
    }


def native_types():
    return '''#include <ultra64.h>
#include <stddef.h>
typedef struct { u8 bytes[0x160]; } struct210;
typedef struct { u32 tag; } struct102;
'''+source.previous.DECLARATIONS.replace('#include "structs.h"\n','')+source.DECLARATIONS


def native_harness():
    return native_types()+r'''
static ActorResourceOwner101090 actor __attribute__((aligned(16)));
static struct102 resources[16];
static const u32 offsets[]={0x138,0x13C,0x134,0x140,0x144};
static const u16 handles[]={0,1,0x7FFF,0x8000,0xFFFF};
static u32 calls[8][2],expected[8][2],count,expected_count,mode,error;
static u8 expected_actor[sizeof(actor)];
void func_15101090(ActorResourceOwner101090 *actor);
static void put(u32 offset,u32 value){*(u32*)((u8*)&actor+offset)=value;}
static u32 get(u32 offset){return *(u32*)((u8*)&actor+offset);}
static void mutate(u32 n){u32 i;
 if(mode==1&&n==1)for(i=0;i<5;i++)put(offsets[i],0);
 if(mode==2)for(i=0;i<5;i++)put(offsets[i],(u32)&resources[(i+n)%16]);
 if(mode==3)for(i=0;i<5;i++)put(offsets[i],(i+n)&1?0:(u32)&resources[i]);}
static void record(u32 kind,u32 value){if(count>=8){error=21;return;}
 calls[count][0]=kind;calls[count++][1]=value;}
void func_100111C8(u16 h){if(!h)error=22;record(0,h);actor.handle1A0=0x8001;mutate(count);}
void func_1516972C(struct102*p){if(!p)error=22;record(1,(u32)p);mutate(count);}
void func_1516979C(struct102*p){record(3,(u32)p);mutate(count);}
void func_1513CA6C(struct210*p){if(p!=(struct210*)&actor)error=22;
 record(2,(u32)p);put(0x50,0xF1A10000|count);}
static void setup(u32 mask,u32 h,u32 alias){u32 i;
 for(i=0;i<sizeof(actor);i++)((u8*)&actor)[i]=(i*7+0xA5)&255;
 for(i=0;i<5;i++)put(offsets[i],mask&(1u<<i)?(u32)&resources[alias?0:i]:0);
 actor.handle1A0=handles[h];*(u16*)((u8*)&actor+0x1A2)=0xA55A;count=error=0;}
static void expect(u32 kind,u32 value){expected[expected_count][0]=kind;
 expected[expected_count++][1]=value;}
static int run(void){u32 mask,h,alias,i,p;
 if(sizeof(void*)!=4||sizeof(actor)!=0x1A4||offsetof(ActorResourceOwner101090,handle1A0)!=0x1A0||
 offsetof(ActorResourceOwner101090,resources)!=0x110)return 29;
 for(mask=0;mask<32;mask++)for(h=0;h<5;h++)for(mode=0;mode<4;mode++)for(alias=0;alias<2;alias++){
 setup(mask,h,alias);expected_count=0;
 if(handles[h]){expect(0,handles[h]);actor.handle1A0=0x8001;mutate(expected_count);}
 for(i=0;i<5;i++){p=get(offsets[i]);if(p){expect(1,p);mutate(expected_count);}}
 expect(2,(u32)&actor);put(0x50,0xF1A10000|expected_count);
 for(i=0;i<sizeof(actor);i++)expected_actor[i]=((u8*)&actor)[i];
 setup(mask,h,alias);func_15101090(&actor);
 if(error||count!=expected_count)return 23;
 for(i=0;i<count;i++)if(calls[i][0]!=expected[i][0]||calls[i][1]!=expected[i][1])return 24;
 for(i=0;i<sizeof(actor);i++)if(((u8*)&actor)[i]!=expected_actor[i])return 25;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ActorResourceRetirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>46I',cls.rom,source.ROM)

    def test_01_unsigned_handle_order_mutation_alias_and_ABI(self):
        count=0
        for mask,handle,mode,alias,high,phase in itertools.product(range(32),HANDLES,range(4),range(2),range(2),(0,8)):
            memory,args=fixture(mask,handle,alias,high)
            expected,calls=reference(memory,mode)
            for words in (self.truth,self.words):
                model=RetirementOracle(words,memory,args,mode=mode,phase=phase).run()
                self.assertEqual(model.calls,calls)
                self.assertEqual(base.base.public(model.memory),base.base.public(expected))
            count+=1
        self.assertEqual(count,5120)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in controls().items()]:
            path=self.out/('native-'+label+'.c');path.write_text(native_types()+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),'-fno-strict-aliasing',str(path),str(harness),
                '-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],timeout=30)
            self.assertIn(run.returncode,(0,) if valid else (21,22,23,24,25),label)

    def test_03_effective_compiled_guest_controls(self):
        with source.historical_view(self.root,self.out):
            for name,body in controls().items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertFalse(row['diagnostics'])
                for mask,handle,mode in itertools.product(range(32),HANDLES,range(4)):
                    memory,args=fixture(mask,handle)
                    expected,calls=reference(memory,mode)
                    model=RetirementOracle(words,memory,args,mode=mode).run()
                    if model.calls!=calls or base.base.public(model.memory)!=base.base.public(expected):break
                else:self.fail('Ineffective compiled retirement control: '+name)

    def test_04_handle_guard_and_all_word_and_binding_controls(self):
        self.assertTrue(source.handle_binding_proof(self.words,self.truth)['zero_extension'])
        for index in range(46):
            bad=list(self.truth);bad[index]^=1
            with self.assertRaises(ValueError):source.handle_binding_proof(self.words,bad)
        raw,bindings=source.checked_object(self.obj)
        text,functions,rel=source.parse_object(self.obj)
        f=functions[source.FUNCTION]
        for i in range(46):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for offset in bindings:
            bad=dict(rel);bad[f['value']+offset]=[('R_MIPS_26','func_1516979C')]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        self.assertEqual(len(raw),184)
        self.assertEqual(len(bindings),7)

    def test_05_all_target_memory_fault_prefixes(self):
        count=0
        for mask,handle,mode,phase in itertools.product(range(32),(0,0xFFFF),(0,2),(0,8)):
            memory,args=fixture(mask,handle,high=1)
            complete=RetirementOracle(self.words,memory,args,mode=mode,phase=phase).run()
            for fault in range(complete.accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    model=RetirementOracle(words,memory,args,mode=mode,phase=phase,fault=fault)
                    with self.assertRaises(base.base.edge.AccessFault):model.run()
                    pairs.append((model.memory,model.events,model.calls,model.accesses))
                self.assertEqual(*pairs);count+=1
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=256,equal_prefixes=count,
            provider_faults_not_modeled=True,no_dead_caller_scratch_equality_claim=True),indent=2)+'\n')

    def test_06_real_callback_dispatcher_preserves_owner(self):
        entry=0x1513CB58
        caller=struct.unpack_from('>19I',self.rom,entry-0x15000000+0x2D4B0)
        count=0
        for selected,mask,handle,phase in itertools.product((0,1),range(32),(0,0xFFFF),(0,8)):
            memory,args=fixture(mask,handle)
            base.put(memory,ACTOR+0x58,0x400000 if selected else 0)
            base.put(memory,ACTOR+0x19,1,1)
            base.put(memory,0x80089EF8,source.FINISH)
            base.put(memory,0x80089EFC,source.ENTRY)
            expected,calls=reference(memory,2,not selected)
            connected=dict(zip(range(source.ENTRY,source.ENTRY+184,4),self.truth))
            model=RetirementOracle(caller,memory,args,mode=2,entry=entry,phase=phase,connected=connected).run()
            self.assertEqual(model.calls,calls)
            self.assertEqual(model.entered,bool(selected))
            self.assertEqual(base.base.public(model.memory),base.base.public(expected));count+=1
        self.assertEqual(count,256)

    def test_07_frozen_inputs_views_and_actual_installed_image(self):
        with source.historical_view(self.root,self.out):
            read=Path.read_bytes
            for index,relative in enumerate(source.INPUTS):
                for path in (self.root/relative,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda p:read(p)+b'\n' if p==path else read(p)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
