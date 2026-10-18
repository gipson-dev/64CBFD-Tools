"""Ordered releases, callback mutation, first-argument guards and linked scope."""
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_actor_owned_resource_cleanup as source
from tools.tests import game_packet_rectangle_oracle as base
from tools.tests.test_game_projected_packet_draw import native_command

ACTOR = 0x30000
OFFSETS = (0x138,0x13C,0x134,0x140,0x144)


def fixture(mask=31,mode=0,alias=0,high=0):
    memory = {base.STACK+i:(i*13+0xA5)&255 for i in range(-256,256)}
    memory.update({ACTOR+i:(i*7+0xA5)&255 for i in range(0x160)})
    for i,offset in enumerate(OFFSETS):
        base.put(memory,ACTOR+offset,((0x80000000 if high else 0)+0x50000+(0 if alias else i*32)) if mask&(1<<i) else 0)
    return memory,(ACTOR,)


def effect(memory,mode,number,target,arg):
    if target == source.RELEASE:
        if mode == 1 and number == 1:
            for offset in OFFSETS:
                base.put(memory,ACTOR+offset,0)
        elif mode == 2:
            for i,offset in enumerate(OFFSETS):
                base.put(memory,ACTOR+offset,0x80060000+(i+number)*32)
        elif mode == 3:
            for i,offset in enumerate(OFFSETS):
                base.put(memory,ACTOR+offset,0 if (i+number)&1 else 0x80070000+i*32)
    elif target == source.DESTROY:
        base.put(memory,ACTOR+0x50,0xD3570000|number)
    else:
        raise AssertionError(('unexpected cleanup provider',hex(target)))


def reference(initial,mode=0,base_only=False):
    memory,calls = dict(initial),[]
    if not base_only:
        for offset in OFFSETS:
            pointer = base.read(memory,ACTOR+offset)
            if pointer:
                calls.append((source.RELEASE,pointer))
                effect(memory,mode,len(calls),*calls[-1])
    calls.append((source.DESTROY,ACTOR))
    effect(memory,mode,len(calls),*calls[-1])
    return memory,calls


class CleanupOracle(base.RectangleOracle):
    def __init__(self,words,memory,args,mode=0,**kwargs):
        self.cleanup_mode,self.entered = mode,False
        super().__init__(words,memory,args,entry=kwargs.pop('entry',source.ENTRY),**kwargs)

    def record_call(self,target):
        if target == source.ENTRY:
            self.entered = self.r[4] == ACTOR
            return
        if target not in (source.RELEASE,source.DESTROY):
            raise AssertionError(('unconnected cleanup call',hex(target)))
        self.calls.append((target,self.r[4]))

    def hook(self,target):
        effect(self.memory,self.cleanup_mode,len(self.calls),target,self.r[4])
        for register in (*range(2,16),24,25):
            self.r[register] = (0xA5000000+len(self.calls)*256+register)&0xFFFFFFFF
        self.hi,self.lo = 0x12345678,0x89ABCDEF
        for register in range(20):
            self.f[register] = 0x3F800000+register


def controls():
    body = source.SELECTED
    return {
        'drop-first':body.replace('        func_1516979C(resource);','        (void)resource;',1),
        'wrong-order':body.replace('resource2C','saved24').replace('resource24','resource2C').replace('saved24','resource24'),
        'null-release':body.replace('    if (resource != NULL) {','    if (1) {',1),
        'wrong-final-owner':body.replace('    func_1513CAA0(actor);','    func_1513CAA0((struct210 *)((u8 *)actor + 0x110));'),
    }


def native_types():
    return '''#include <ultra64.h>
typedef struct { u8 bytes[0x160]; } struct210;
typedef struct { u32 tag; } struct102;
'''


def native_harness():
    return native_types()+r'''
static struct210 actor __attribute__((aligned(16)));
static struct102 resources[16];
static const u32 offsets[]={0x138,0x13C,0x134,0x140,0x144};
static u32 calls[8],expected[8],count,expected_count,mode,error;
void func_15101148(struct210 *actor);
static void put(u32 offset,u32 value){*(u32*)(actor.bytes+offset)=value;}
static u32 get(u32 offset){return *(u32*)(actor.bytes+offset);}
static void mutate(u32 n){u32 i;
 if(mode==1&&n==1)for(i=0;i<5;i++)put(offsets[i],0);
 if(mode==2)for(i=0;i<5;i++)put(offsets[i],(u32)&resources[(i+n)%16]);
 if(mode==3)for(i=0;i<5;i++)put(offsets[i],(i+n)&1?0:(u32)&resources[i]);}
void func_1516979C(struct102*p){if(!p||count>=7){error=21;return;}calls[count++]=(u32)p;mutate(count);}
void func_1513CAA0(struct210*p){if(p!=&actor||count>=7){error=22;return;}calls[count++]=0xFFFFFFFFu;}
static void setup(u32 mask,u32 alias){u32 i;for(i=0;i<0x160;i++)actor.bytes[i]=0;
 for(i=0;i<5;i++)put(offsets[i],mask&(1u<<i)?(u32)&resources[alias?0:i]:0);count=error=0;}
static int run(void){u32 mask,alias,i,p;
 if(sizeof(void*)!=4)return 29;
 for(mask=0;mask<32;mask++)for(mode=0;mode<4;mode++)for(alias=0;alias<2;alias++){
 setup(mask,alias);expected_count=0;
 for(i=0;i<5;i++){p=get(offsets[i]);if(p){expected[expected_count++]=p;mutate(expected_count);}}
 expected[expected_count++]=0xFFFFFFFFu;
 setup(mask,alias);func_15101148(&actor);
 if(error||count!=expected_count)return 23;
 for(i=0;i<count;i++)if(calls[i]!=expected[i])return 24;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


class ActorOwnedResourceCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2]
        cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>40I',cls.rom,source.ROM)

    def test_01_complete_order_mutation_alias_and_caller_saved_poison(self):
        count=0
        for mask,mode,alias,high,phase in itertools.product(range(32),range(4),range(2),range(2),(0,8)):
            memory,args=fixture(mask,mode,alias,high)
            expected,calls=reference(memory,mode)
            for words in (self.truth,self.words):
                model=CleanupOracle(words,memory,args,mode=mode,phase=phase).run()
                self.assertEqual(model.calls,calls)
                self.assertEqual(base.base.public(model.memory),base.base.public(expected))
            count+=1
        self.assertEqual(count,1024)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c'
        harness.write_text(native_harness())
        types=native_types()+source.DECLARATIONS.replace('#include "structs.h"\n','')
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in controls().items()]:
            path=self.out/('native-'+label+'.c')
            path.write_text(types+body)
            exe=self.out/('native-'+label)
            result=subprocess.run([*native_command(opt,valid),'-fno-strict-aliasing',str(path),str(harness),
                '-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            run=subprocess.run([str(exe)],timeout=30)
            self.assertIn(run.returncode,(0,) if valid else (21,22,23,24),label)

    def test_03_effective_compiled_guest_controls(self):
        with source.historical_view(self.root,self.out):
            for name,body in controls().items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertFalse(row['diagnostics'])
                for mask,mode in itertools.product(range(32),range(4)):
                    memory,args=fixture(mask,mode)
                    expected,calls=reference(memory,mode)
                    model=CleanupOracle(words,memory,args,mode=mode).run()
                    if model.calls!=calls or base.base.public(model.memory)!=base.base.public(expected):
                        break
                else:
                    self.fail('Ineffective compiled cleanup control: '+name)

    def test_04_first_binding_branches_and_guard_controls(self):
        self.assertEqual(source.first_call_proof(self.words,self.truth)['branches'],2)
        for index in range(40):
            bad=list(self.truth)
            bad[index]^=1
            with self.assertRaises(ValueError):
                source.first_call_proof(self.words,bad)
        raw,bindings=source.checked_object(self.obj)
        text,functions,rel=source.parse_object(self.obj)
        f=functions[source.FUNCTION]
        for i in range(40):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        self.assertEqual(len(bindings),6)

    def test_05_all_fault_prefixes_preserve_calls_and_memory(self):
        count=0
        for mask,mode,phase in itertools.product(range(32),(0,2),(0,8)):
            memory,args=fixture(mask,mode,high=1)
            complete=CleanupOracle(self.words,memory,args,mode=mode,phase=phase).run()
            for fault in range(complete.accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    model=CleanupOracle(words,memory,args,mode=mode,phase=phase,fault=fault)
                    with self.assertRaises(base.base.edge.AccessFault):model.run()
                    pairs.append((model.memory,model.events,model.calls,model.accesses))
                self.assertEqual(*pairs)
                count+=1
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=128,equal_prefixes=count,
            no_dead_caller_scratch_register_equality_claim=True),indent=2)+'\n')

    def test_06_real_callback_dispatcher_preserves_owner_argument(self):
        entry=0x1513CBA4
        caller=struct.unpack_from('>19I',self.rom,entry-0x15000000+0x2D4B0)
        count=0
        for selected,mask,phase in itertools.product((0,1),range(32),(0,8)):
            memory,args=fixture(mask,mode=2)
            base.put(memory,ACTOR+0x58,0x400000 if selected else 0)
            base.put(memory,ACTOR+0x19,1,1)
            base.put(memory,0x80089F2C,source.DESTROY)
            base.put(memory,0x80089F30,source.ENTRY)
            expected,calls=reference(memory,2,not selected)
            connected=dict(zip(range(source.ENTRY,source.ENTRY+160,4),self.truth))
            model=CleanupOracle(caller,memory,args,mode=2,entry=entry,phase=phase,connected=connected).run()
            self.assertEqual(model.calls,calls)
            self.assertEqual(model.entered,bool(selected))
            self.assertEqual(base.base.public(model.memory),base.base.public(expected))
            count+=1
        self.assertEqual(count,128)

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
        if self.stage=='after':
            self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':
    unittest.main()
