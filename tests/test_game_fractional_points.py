"""Original deltas, sequential aliases, literal anchoring and bounded float32 ABI."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_fractional_points as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests import game_packet_rectangle_oracle as base
from tools.tests.test_game_projected_packet_draw import native_command

ARENA=0x30000
COEFFICIENTS=(0x3EAA7EFA,0x3F2AACDA)
PATTERNS=(
    (0,), (0x80000000,),
    (0x3F800000,0xC0000000,0x40400000,0x40A00000,0xC0E00000,0x41200000),
    (1,0x80000001,0x007FFFFF,0x807FFFFF,0x00800000,0x80800000),
    (0x71800000,0xF1800000,0x71000001,0xF0800000),
    (0x4B000001,0xCB000000,0x3F000001,0xBF7FFFFF),
    (0x3F800001,0x3F7FFFFF,0xBF800001,0xBF7FFFFF,0x40000001),
    (0x3EAAAAAB,0xBEAAAAAB,0x3F2AAAAB,0xBF2AAAAB,0x47800001))
LAYOUTS=tuple((a,b,c,d) for (a,b),(c,d) in itertools.product(
    ((0,3),(0,0),(1,0),(0,1),(2,1)),itertools.product(range(8),repeat=2)))


def fixture(seed=2,layout=(0,3,6,9),high=0,symbol=source.FIRST):
    arena=ARENA+(0x80000000 if high else 0)
    memory={base.STACK+i:0xA5 for i in range(-128,0x300)}
    memory.update({arena+i:0xA5 for i in range(-16,144)})
    pattern=PATTERNS[seed]
    for i in range(32):base.put(memory,arena+i*4,pattern[i%len(pattern)])
    for i,v in enumerate((*COEFFICIENTS,0,0)):base.put(memory,symbol+i*4,v)
    return memory,tuple(arena+i*4 for i in layout)


def reference(initial,args):
    memory=dict(initial);start,end,first,second=args
    deltas=[base.rounded(base.floating(base.read(memory,end+i*4))-
        base.floating(base.read(memory,start+i*4))) for i in range(3)]
    for output,fraction in ((first,base.floating(COEFFICIENTS[0])),(second,base.floating(COEFFICIENTS[1]))):
        for i,delta in enumerate(deltas):
            value=base.floating(base.read(memory,start+i*4))
            base.put(memory,output+i*4,base.bits(base.rounded(value+base.rounded(delta*fraction))))
    return memory


def controls():
    body=source.SELECTED
    cached=body.replace('    f32 dx = end[0] - start[0];',
        '    f32 sx = start[0], sy = start[1], sz = start[2];\n    f32 dx = end[0] - start[0];')
    for i,name in enumerate(('sx','sy','sz')):
        cached=cached.replace('= start[%d] +'%i,'= '+name+' +')
    live=body
    for i,name in enumerate(('dx','dy','dz')):
        live=live.replace('second[%d] = start[%d] + %s *'%(i,i,name),
            'second[%d] = start[%d] + (end[%d] - start[%d]) *'%(i,i,i,i))
    first,second=body.index('    first[0]'),body.index('    second[0]')
    reversed_body=body[:first]+body[second:body.rfind('}')]+body[first:second]+body[body.rfind('}'):]
    return {
        'exact-thirds':body.replace('0.333f','(1.0f / 3.0f)').replace('0.6667f','(2.0f / 3.0f)'),
        'cached-start':cached,
        'live-second-deltas':live,
        'reversed-stores':reversed_body,
        'reversed-deltas':body.replace('end[0] - start[0]','start[0] - end[0]').replace(
            'end[1] - start[1]','start[1] - end[1]').replace('end[2] - start[2]','start[2] - end[2]'),
    }


def native_harness():
    rows=',\n'.join('{'+','.join('0x%Xu'%p[i%len(p)] for i in range(32))+'}' for p in PATTERNS)
    layouts=',\n'.join('{'+','.join(str(i) for i in layout)+'}' for layout in LAYOUTS)
    return '#include <ultra64.h>\nstatic const u32 patterns[][32]={'+rows+'};\n'+\
        'static const u32 layouts[][4]={'+layouts+'};\n'+r'''
static f32 actual[32],expected[32];
static u32 word(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
static f32 floating(u32 u){union{f32 f;u32 u;}v;v.u=u;return v.f;}
static f32 rounded(f32 f){volatile f32 v=f;return v;}
void func_15107AE0(const f32*,const f32*,f32*,f32*);
static void reference(f32*s,f32*e,f32*a,f32*b){u32 i;f32 d[3];
 for(i=0;i<3;i++)d[i]=rounded(e[i]-s[i]);
 for(i=0;i<3;i++)a[i]=rounded(s[i]+rounded(d[i]*0.333f));
 for(i=0;i<3;i++)b[i]=rounded(s[i]+rounded(d[i]*0.6667f));}
static int run(void){u32 p,l,i;const u32*r;
 if(sizeof(void*)!=4||sizeof(f32)!=4)return 29;
 for(p=0;p<sizeof(patterns)/sizeof(patterns[0]);p++)for(l=0;l<sizeof(layouts)/sizeof(layouts[0]);l++){
 r=layouts[l];for(i=0;i<32;i++)actual[i]=expected[i]=floating(patterns[p][i]);
 reference(expected+r[0],expected+r[1],expected+r[2],expected+r[3]);
 func_15107AE0(actual+r[0],actual+r[1],actual+r[2],actual+r[3]);
 for(i=0;i<32;i++)if(word(actual[i])!=word(expected[i]))return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''


def rebased(root,out,label,symbol,entry):
    obj,diagnostics=source.compile_owner(root,out,'#include <ultra64.h>\n'+source.SELECTED,label)
    if diagnostics:raise AssertionError(diagnostics)
    source.checked_object(obj)
    script=out/(label+'.ld')
    script.write_text('SECTIONS { .text 0x%X : { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(entry,symbol))
    elf=script.with_suffix('.elf')
    subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',source.FUNCTION,'-o',str(elf),str(obj)],
        check=True,capture_output=True)
    sec=sections(elf)
    if sec['.rodata'][0]!=symbol:raise AssertionError('Unexpected literal anchor')
    return list(struct.unpack_from('>38I',sec['.text'][1]))


class FractionalPointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD
        cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):
            cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin')
        cls.truth=struct.unpack_from('>38I',cls.rom,source.ROM)

    def test_01_finite_partial_aliases_original_deltas_and_store_order(self):
        self.assertEqual(self.words,list(self.truth))
        count=0
        for seed,layout,high,phase in itertools.product(range(8),LAYOUTS,(0,1),(0,8)):
            memory,args=fixture(seed,layout,high)
            model=base.RectangleOracle(self.words,memory,args,phase=phase,entry=source.ENTRY).run()
            self.assertEqual(model.memory,reference(memory,args))
            self.assertFalse(model.calls);count+=1
        self.assertEqual(count,10240)

    def test_02_native32_O2_O0_UBSan_and_effective_controls(self):
        harness=self.out/'native-harness.c';harness.write_text(native_harness())
        for label,opt,body,valid in [('O2','-O2',source.SELECTED,True),('O0','-O0',source.SELECTED,True)]+[
                (n,'-O2',b,False) for n,b in controls().items()]:
            p=self.out/('native-'+label+'.c');p.write_text('#include <ultra64.h>\n'+body);exe=p.with_suffix('')
            result=subprocess.run([*native_command(opt,valid),'-mstackrealign',str(p),str(harness),'-o',str(exe)],
                cwd=self.root,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=30).returncode,0 if valid else 23,label)

    def test_03_effective_compiled_guest_memory_controls(self):
        with source.historical_view(self.root,self.out):
            for name,body in controls().items():
                obj,words,row=source.measure(self.root,self.out,'negative-'+name,body)
                self.assertEqual(row['diagnostics'].replace('negative-'+name+'.c','owner.c'),
                    self.row['diagnostics'].replace('qualified.c','owner.c'))
                address,pool=sections(obj.with_suffix('.elf'))['.rodata']
                for seed,layout in itertools.product((2,3,5,6),LAYOUTS):
                    memory,args=fixture(seed,layout)
                    memory.update({address+i:v for i,v in enumerate(pool)})
                    expected=reference(memory,args)
                    model=base.RectangleOracle(words,memory,args,entry=source.ENTRY).run()
                    if model.memory!=expected:break
                else:self.fail('Ineffective fractional control: '+name)

    def test_04_literal_pool_rebases_and_wrong_anchor_control(self):
        for i,(symbol,entry) in enumerate(((source.FIRST,source.ENTRY),(0x12347FFC,0x15004000),
                (0x800A7FFC,0x15107AE0))):
            words=rebased(self.root,self.out,'rebase-%d'%i,symbol,entry)
            for seed,layout in itertools.product((2,3,6),LAYOUTS[::17]):
                memory,args=fixture(seed,layout,symbol=symbol)
                model=base.RectangleOracle(words,memory,args,entry=entry).run()
                self.assertEqual(model.memory,reference(memory,args))
        with source.historical_view(self.root,self.out):
            script=self.out/'wrong-anchor.s'
            script.write_text(source.emit_padded_assembly(self.obj,self.root/'conker/asm/133190.s',filename=source.OWNER,
                word_patches_path=self.root/'conker/retail_word_patches.us.csv',rodata_symbol='D_800A2424'))
            obj=script.with_suffix('.o')
            subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(script)],check=True,capture_output=True)
            data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=struct.unpack_from('>38I',data,f['value'])
            memory,args=fixture(2)
            model=base.RectangleOracle(words,memory,args,entry=source.ENTRY).run()
            self.assertNotEqual(model.memory,reference(memory,args))

    def test_05_nonfinite_pairing_and_all_access_fault_prefixes(self):
        paired=0
        for value,layout in itertools.product((0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345),LAYOUTS[::17]):
            memory,args=fixture(2,layout)
            base.put(memory,args[0],value)
            a=base.RectangleOracle(self.words,memory,args,entry=source.ENTRY).run()
            b=base.RectangleOracle(self.truth,memory,args,entry=source.ENTRY).run()
            self.assertEqual((a.memory,a.f),(b.memory,b.f));paired+=1
        count=0;states=0
        for seed,layout,phase in itertools.product((0,2,3,6),LAYOUTS[::17],(0,8)):
            memory,args=fixture(seed,layout)
            complete=base.RectangleOracle(self.words,memory,args,phase=phase,entry=source.ENTRY).run()
            for fault in range(complete.accesses):
                pairs=[]
                for words in (self.words,self.truth):
                    model=base.RectangleOracle(words,memory,args,phase=phase,entry=source.ENTRY,fault=fault)
                    with self.assertRaises(base.base.edge.AccessFault):model.run()
                    pairs.append((model.memory,model.events,model.r,model.f,model.accesses))
                self.assertEqual(*pairs);count+=1
            states+=1
        (self.out/'fault-prefixes.json').write_text(json.dumps(dict(states=states,equal_prefixes=count,
            nonfinite_pairs=paired,not_a_hardware_FCSR_or_NaN_policy_emulator=True),indent=2)+'\n')

    def test_06_four_retail_caller_windows_and_vector_ABI(self):
        class Boundary(Exception):pass
        class Caller(base.RectangleOracle):
            entered=False
            def record_call(self,target):
                if target!=source.ENTRY:raise AssertionError(target)
                self.entered=True;self.entry_args=tuple(self.arguments(4));self.entry_memory=dict(self.memory)
            def execute(self,word):
                if self.entered and word==self.stop_word:raise Boundary
                super().execute(word)
        windows=((0x15107870,0x1510789C),(0x15107A00,0x15107A08),
            (0x15107DF0,0x15107E00),(0x15107F34,0x15107F3C))
        connected=dict(zip(range(source.ENTRY,source.ENTRY+152,4),self.words));count=0
        for (entry,end),seed,phase in itertools.product(windows,(2,3,6),(0,8)):
            caller=struct.unpack_from('>%dI'%((end-entry)//4+1),self.rom,entry-0x15000000+0x2D4B0)
            memory,args=fixture(seed)
            sp=base.STACK+phase
            for i in range(0,0x280,4):base.put(memory,sp+i,PATTERNS[seed][(i//4)%len(PATTERNS[seed])])
            base.put(memory,sp+0x28,ARENA+0x14);base.put(memory,sp+0x20,ARENA+0x14)
            model=Caller(caller,memory,(),phase=phase,entry=entry,connected=connected)
            model.stop_word=caller[-1]
            model.r[24]=sp+0x64;model.r[4]=sp+0xC0
            model.r[5],model.r[6],model.r[7]=ARENA+0x38,ARENA+0x20,ARENA+0x2C
            with self.assertRaises(Boundary):model.run()
            self.assertEqual(model.memory,reference(model.entry_memory,model.entry_args));count+=1
        self.assertEqual(count,24)

    def test_07_words_pool_bindings_inputs_and_actual_image(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION]
        raw,bindings=source.checked_object(self.obj)
        self.assertEqual(len(raw),152);self.assertEqual(len(bindings),4)
        for i in range(38):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        for i in bindings:
            bad=dict(rel);bad[f['value']+i]=[]
            with patch.object(source,'parse_object',return_value=(text,functions,bad)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'normalized_pools',return_value={'.rodata':(b'\0'*16,()),'.data':None}):
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
