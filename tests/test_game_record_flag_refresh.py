"""Byte gates, live global aliases, native32, symbol rebases and caller ABI."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_record_flag_refresh as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_packet_rectangle_oracle as base
from tools.tests.game_animation_timeline_oracle import signed
from tools.tests.test_game_projected_packet_draw import native_command

RECORDS=0x30000


def fixture(count=1,flags=0,qualifier=0,attached=0,high=0,symbols=None):
    c,b=symbols or (source.COUNT,source.BASE)
    table=RECORDS+(0x80000000 if high else 0)
    memory={base.STACK+i:0xA5 for i in range(-128,128)}
    for i in range(max(count,1)*0xA0):memory[table+i]=(i*13+0xA5)&255
    for i in range(max(count,1)):
        base.put(memory,table+i*0xA0+0x6F,flags,1)
        base.put(memory,table+i*0xA0+0x70,qualifier,1)
        base.put(memory,table+i*0xA0+0x38,attached)
    base.put(memory,c,count);base.put(memory,b,table)
    return memory


def reference(initial,symbols=None):
    c,b=symbols or (source.COUNT,source.BASE)
    memory=dict(initial);index=offset=0
    while index<signed(base.read(memory,c)):
        record=(base.read(memory,b)+offset)&0xFFFFFFFF
        base.put(memory,record+0x6F,base.read(memory,record+0x6F,1)&~0x40,1)
        record=(base.read(memory,b)+offset)&0xFFFFFFFF
        flags=base.read(memory,record+0x6F,1)
        if (flags&15 or base.read(memory,record+0x70,1)&4) and base.read(memory,record+0x38):
            base.put(memory,record+0x6F,flags|0x40,1)
        index+=1;offset=(offset+0xA0)&0xFFFFFFFF
        if index>128:raise AssertionError('Unbounded reference fixture')
    return memory,index


def alias_fixture(kind,symbols=None):
    c,b=symbols or (source.COUNT,source.BASE)
    center=min(c,b)
    memory={center+i:0 for i in range(-0x200,0x3000)}
    memory.update({base.STACK+i:0xA5 for i in range(-128,128)})
    if kind=='count':
        record=c+3-0x6F
        for i in range(65):base.put(memory,record+i*0xA0+0x6F,0x40,1)
        base.put(memory,c,65);base.put(memory,b,record)
    elif kind=='base':
        record=b+3-0x6F
        base.put(memory,c,2);base.put(memory,b,record)
        base.put(memory,record+0x38,1)
        for delta in (-64,0,64):
            base.put(memory,record+delta+0xA0+0x6F,0x40,1)
    else:raise AssertionError(kind)
    return memory


def controls():
    body=source.SELECTED
    return {
        'cache-count':body.replace('D_800DBEF0','count').replace('    s32 index = 0;',
            '    s32 count = D_800DBEF0;\n    s32 index = 0;'),
        'cache-base':body.replace('D_800DBEF4','table').replace('    s32 index = 0;',
            '    u8 *table = D_800DBEF4;\n    s32 index = 0;'),
        'low-nibble-only':body.replace(' || (record[0x70] & 4) == 4',''),
        'missing-object-gate':body.replace(' &&\n                *(s32 *)(record + 0x38) != 0',''),
        'wrong-stride':body.replace('offset += 0xA0','offset += 0xA4'),
        'missing-clear':body.replace('            record[0x6F] &= ~0x40;','            (void)record;'),
    }


TYPES='''#include <ultra64.h>
extern u8 arena[0x4000];
#define D_800DBEF0 (*(s32 *)(arena + 0x240))
#define D_800DBEF4 (*(u8 **)(arena + 0x244))
'''


def native_harness():
    return TYPES+r'''
u8 arena[0x4000] __attribute__((aligned(256)));
static u8 expected[0x4000];
void func_15113180(void);
static void put(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(i*8));}
static u32 get(u8*p){return (u32)p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void clear(void){u32 i;for(i=0;i<sizeof(arena);i++)arena[i]=0;}
static void setup(u32 kind){u32 i;u8*p;clear();
 if(kind==0){p=arena+0x240-0x6F;for(i=0;i<64;i++)p[i*0xA0+0x6F]=0x40;
 D_800DBEF4=p;D_800DBEF0=64;}
 else{p=arena+0x244-0x6F;D_800DBEF0=2;D_800DBEF4=p;put(p+0x38,1);
 p[0xA0+0x6F]=0x40;p[-64+0xA0+0x6F]=0x40;p[64+0xA0+0x6F]=0x40;}}
static void reference(void){s32 i=0;u32 off=0;u8*p;u32 flags;
 while(i<D_800DBEF0){p=D_800DBEF4+off;p[0x6F]&=~0x40;
 p=D_800DBEF4+off;flags=p[0x6F];
 if((flags&15||(p[0x70]&4)==4)&&get(p+0x38))p[0x6F]=flags|0x40;
 i++;off+=0xA0;}}
static int run(void){u32 f,q,a,want,i,kind;u8*p=arena+0x1000;
 if(sizeof(void*)!=4)return 29;
 clear();
 for(f=0;f<256;f++)for(q=0;q<256;q++)for(a=0;a<2;a++){
 D_800DBEF0=1;D_800DBEF4=p;p[0x6F]=(u8)f;p[0x70]=(u8)q;put(p+0x38,a);
 want=(f&~0x40u)|(((f&15)||(q&4))&&a?0x40u:0);
 func_15113180();
 if(p[0x6F]!=want||p[0x70]!=q||get(p+0x38)!=a||D_800DBEF0!=1||D_800DBEF4!=p)return 23;
 }
 for(kind=0;kind<2;kind++){
 setup(kind);reference();for(i=0;i<sizeof(arena);i++)expected[i]=arena[i];
 setup(kind);func_15113180();for(i=0;i<sizeof(arena);i++)if(expected[i]!=arena[i])return 24;
 }
 for(kind=0;kind<3;kind++){D_800DBEF0=kind==0?0:kind==1?-1:(s32)0x80000000u;D_800DBEF4=0;
 func_15113180();if(D_800DBEF4)return 25;}
 return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


def rebased(root,out,label,symbols,entry):
    obj,diagnostics=source.compile_owner(root,out,
        '#include <ultra64.h>\nextern s32 D_800DBEF0;\nextern u8 *D_800DBEF4;\n'+source.SELECTED,label)
    if diagnostics:raise AssertionError(diagnostics)
    source.checked_object(obj)
    script=out/(label+'.ld');script.write_text('SECTIONS { .text 0x%X : { *(.text) } }\n'%entry)
    elf=script.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,
        '--defsym=D_800DBEF0=0x%X'%symbols[0],'--defsym=D_800DBEF4=0x%X'%symbols[1],
        '-o',str(elf),str(obj)],check=True,capture_output=True)
    data=sections(elf)['.text'][1]
    return list(struct.unpack_from('>38I',data))


class RecordFlagRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>38I',cls.rom,source.ROM)

    def check_case(self,memory,words=None,symbols=None,phase=0,entry=source.ENTRY):
        expected,index=reference(memory,symbols)
        model=base.RectangleOracle(self.words if words is None else words,memory,(),phase=phase,entry=entry).run()
        self.assertEqual(model.memory,expected)
        self.assertEqual(model.r[2],index)
        self.assertFalse(model.calls)
        return model

    def test_01_flags_widths_null_gate_and_signed_count(self):
        count=0
        for flags,qualifier,attached,high in itertools.product(range(256),(0,1,4,5,128,132,255),
                (0,1,0x80000000,0xFFFFFFFF),(0,1)):
            self.check_case(fixture(1,flags,qualifier,attached,high));count+=1
        for n in (-0x80000000,-1,0,1,2,7):
            memory=fixture(n,0xFF,4,1)
            if n<=0:memory.pop(source.BASE)
            self.check_case(memory)
        self.assertEqual(count,14336)

    def test_02_native32_exhaustive_O2_O0_UBSan_and_controls(self):
        harness=self.out/'native-harness.c';harness.write_text(native_harness())
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (name,'-O2',body,False) for name,body in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text(TYPES+body);exe=p.with_suffix('')
            result=subprocess.run([*native_command(opt,valid),'-mstackrealign','-fno-strict-aliasing',
                str(p),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(subprocess.run([str(exe)],timeout=30).returncode,(0,) if valid else (23,24,25),label)

    def test_03_effective_compiled_guest_controls(self):
        cases=[fixture(n,f,q,a) for n,f,q,a in itertools.product((1,2),(0,1,64,255),(0,4),(0,1))]
        cases+=[alias_fixture('count'),alias_fixture('base')]
        with source.historical_view(self.root,self.out):
            for name,body in controls().items():
                _,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertFalse(row['diagnostics'])
                for memory in cases:
                    expected,index=reference(memory)
                    model=base.RectangleOracle(words,memory,()).run()
                    if model.memory!=expected:break
                else:self.fail('Ineffective guest flag control: '+name)

    def test_04_count_base_aliases_and_independent_symbol_rebases(self):
        specs=[((source.COUNT,source.BASE),source.ENTRY),
            ((0x800DBF30,0x800DBF34),0x15004000),((0x12348000,0x12348004),0x15113180)]
        for i,(symbols,entry) in enumerate(specs):
            words=rebased(self.root,self.out,'rebase-%d'%i,symbols,entry)
            for kind in ('count','base'):
                memory=alias_fixture(kind,symbols)
                for phase in (0,8):self.check_case(memory,words,symbols,phase,entry)
            self.check_case(fixture(7,0xFF,4,0xFFFFFFFF,symbols=symbols),words,symbols,entry=entry)

    def test_05_all_target_fault_prefixes_with_aliases(self):
        cases=[fixture(1,f,q,a) for f,q,a in itertools.product((0,1,15,64,128,255),(0,4),(0,1))]
        cases+=[alias_fixture('count'),alias_fixture('base')]
        count=0
        for memory,phase in itertools.product(cases,(0,8)):
            complete=base.RectangleOracle(self.words,memory,(),phase=phase).run()
            for fault in range(complete.accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    model=base.RectangleOracle(words,memory,(),phase=phase,fault=fault)
                    with self.assertRaises(base.base.edge.AccessFault):model.run()
                    pairs.append((model.memory,model.events,model.accesses,model.r[2]))
                self.assertEqual(*pairs);count+=1
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=len(cases)*2,
            equal_prefixes=count),indent=2)+'\n')

    def test_06_actual_caller_discards_loop_index(self):
        caller=struct.unpack_from('>3I',self.rom,0x46630)
        self.assertEqual(caller,(0x0D444C60,0,0x3C02800C))
        class CallerBoundary(Exception):pass
        class Caller(base.RectangleOracle):
            def record_call(self,target):
                if target!=source.ENTRY:raise AssertionError(target)
            def execute(self,word):
                if word==caller[2]:raise CallerBoundary
                super().execute(word)
        connected=dict(zip(range(source.ENTRY,source.ENTRY+152,4),self.words))
        for n,phase in itertools.product((-1,0,1,7),(0,8)):
            memory=fixture(n,0xFF,4,1);expected,index=reference(memory)
            model=Caller(caller,memory,(),entry=0x15019180,phase=phase,connected=connected)
            with self.assertRaises(CallerBoundary):model.run()
            self.assertEqual(model.r[2],index);self.assertEqual(model.memory,expected)
            for reg in (*range(16,24),28,29,30):self.assertEqual(model.r[reg],model.before[reg])
            base.RectangleOracle.execute(model,caller[2]);self.assertEqual(model.r[2],0x800C0000)

    def test_07_words_bindings_inputs_views_and_actual_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        self.assertEqual(len(raw),152);self.assertEqual(len(bindings),4)
        for i in range(38):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[('R_MIPS_LO16','D_800DBEF0')]
            if bad[f['value']+i]==rel[f['value']+i]:bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with source.historical_view(self.root,self.out):
            read=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:read(x)+b'\n' if x==path else read(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)


if __name__=='__main__':unittest.main()
