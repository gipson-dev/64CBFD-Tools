"""Direct quadratic position callback: signed bounds, aliases and original dispatch."""
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_parabolic_position as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
NAME = 'func_1517B7F8'
ENTRY, ROM, SIZE = 0x1517B7F8, 0x1A8CA8, 164
INPUT, OUTPUT, COUNTER = 0x28020, 0x30020, 0x38020
WINDOW, KEEP, SKIP = 0x1517C658, 0x1517C730, 0x1517C864
COUNTS = (-0x80000000,-1,0,0xFF,0x100,0x101,0x1FF,0x200,0x201,0x600,0xA00,0xA01,0xCFF,0xD00,0xD01,0x7FFFFFFF)


def signed(value, bits=32):
    return ((value & ((1 << bits)-1)) ^ (1 << (bits-1))) - (1 << (bits-1))


def fixture(value=0x600, point=(-32768,32767,-1)):
    m = {STACK+i:(i*17+0xA5)&255 for i in range(-0x200,0x200)}
    for base in (INPUT,OUTPUT,COUNTER):
        m.update({base+i:(i*13+0xA5)&255 for i in range(-32,96)})
    for i,x in enumerate(point):put(m,INPUT+i*2,x,2)
    put(m,COUNTER,value)
    return m


def reference(memory, arguments, sp):
    m = dict(memory);a,b,c,unused = arguments
    put(m,sp+12,unused)
    value = signed(read(m,c))
    if value >= 0xD00:return m,1
    if value >= 0x100:
        offset = 0x190000-(value-0x600)**2
        quotient = (abs(offset)//0x1E00)*(-1 if offset<0 else 1)
        put(m,b+2,signed(read(m,a+2,2),16)+quotient,2)
        value = signed(read(m,c))
        if value >= 0x200:put(m,c,value-0x800 if value>=0xA01 else 0x200)
    else:put(m,b+2,read(m,a+2,2),2)
    put(m,b,read(m,a,2),2);put(m,b+4,read(m,a+4,2),2)
    return m,0


class PositionOracle(TimingOracle):
    def __init__(self, words, memory, arguments, phase=0, entry=ENTRY, connected=None):
        self.trace = []
        super().__init__(words,memory,phase=phase,entry=entry,arguments=arguments,connected=connected)

    def get(self,address,size):
        value = super().get(address,size)
        if self.own_instruction:self.trace.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        if self.recording and self.own_instruction:
            assert all(address+i in self.memory for i in range(size)),('unmapped store',address,size)
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.trace.append(('W',address,size,value&((1<<(size*8))-1)))

    def execute(self,word):
        if word>>26 == 32:
            rs,rt,imm=word>>21&31,word>>16&31,signed(word&65535,16)
            self.r[rt]=signed(self.get((self.r[rs]+imm)&0xFFFFFFFF,1),8)&0xFFFFFFFF
            self.r[0]=0
        else:super().execute(word)

    def record_call(self,target):
        assert target == ENTRY
        args = tuple(self.r[4:8])
        self.calls.append((target,args));self.events.append(('CALL',target,args))
        self.callback_memory = dict(self.memory);self.callback_arguments = args

    def hook(self,target):
        raise AssertionError(('Unexpected external provider',target))


def native_harness(body):
    return """typedef short s16;typedef int s32;typedef unsigned int u32;typedef unsigned char u8;
typedef long long s64;
typedef struct{u32 pre[4];s16 points[12];s32 count;u32 post[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(s16)==2&&sizeof(s32)==4)?1:-1];
""" + body + """
static s32 truth(s16 *in,s16 *out,s32 *count){
 s32 v=*count,numerator; s64 d;
 if(v>=0xD00)return 1;
 if(v>=0x100){
  d=(s64)v-0x600;
  numerator=(s32)(0x190000-d*d);
  out[1]=(s16)(in[1]+numerator/0x1E00);
  v=*count;
  if(v>=0x200)*count=v>=0xA01?v-0x800:0x200;
 }else out[1]=in[1];
 out[0]=in[0];out[2]=in[2];return 0;
}
static int run(void){
 const s32 extra[]={(-2147483647-1),-1,0x7FFFFFFF};
 const s16 points[]={-32768,-32767,-1,0,1,32766,32767};
 const u32 offsets[]={0,1,2,3,6};
 State a,b;u8 *p=(u8*)&a,*q=(u8*)&b;u32 n,k,j,z; s32 value,x,y;
 for(n=0;n<0xD05;n++)for(k=0;k<7;k++)for(z=0;z<5;z++){
  for(j=0;j<sizeof(a);j++)p[j]=(u8)(j*13+0xA5);
  value=n<0xD02?(s32)n:extra[n-0xD02];
  a.count=value;a.points[2]=points[k];a.points[3]=points[(k+2)%7];a.points[4]=points[(k+4)%7];
  b=a;
  x=truth(b.points+2,b.points+offsets[z],&b.count);
  y=func_1517B7F8(a.points+2,a.points+offsets[z],&a.count,(s32)0xABCD1234u);
  if(x!=y)return 23;
  for(j=0;j<sizeof(a);j++)if(p[j]!=q[j])return 23;
 }
 value=0xD00;if(func_1517B7F8((void*)0,(void*)0,&value,0)!=1)return 23;
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class ParabolicPositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = ROOT/source.BUILD
        cls.installed = source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.out)
        else:
            source.qualify(ROOT,cls.out);source.make_shadow(ROOT,cls.out);source.predict(ROOT,cls.out)
        cls.values = source.snapshot(cls.out);cls.rom = cls.values['conker/conker.us.bin']
        cls.obj,diagnostics = source.compile_owner(ROOT,cls.out,'#include <ultra64.h>\n'+source.SELECTED[NAME],'fresh-selected')
        if diagnostics:raise ValueError(diagnostics)
        cls.words = list(struct.unpack('>41I',source.payload(cls.obj,NAME)[0]))
        cls.truth = list(struct.unpack_from('>41I',cls.rom,ROM))
        cls.receipt = dict(installed=cls.installed)

    @classmethod
    def tearDownClass(cls):
        (cls.out/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('parabolic position qualification:',cls.receipt)

    def compare(self,memory,args,phase=0,images=None,entry=ENTRY):
        expected,result = reference(memory,args,STACK+phase)
        models = [PositionOracle(code,memory,args,phase,entry).run()for code in images or (self.truth,self.words)]
        for m in models:
            self.assertEqual(m.memory,expected)
            self.assertEqual(m.r[2],result)
            self.assertFalse(m.calls)
        self.assertEqual(complete(models[0]),complete(models[1]))
        self.assertEqual(models[0].trace,models[1].trace)
        return models

    def test_01_direct_body_original_GNU_owner_Make_and_old_stub(self):
        self.assertEqual(self.words,self.truth)
        self.assertEqual(source.payload(source.original(ROOT,self.out,NAME),NAME),(struct.pack('>41I',*self.truth),{}))
        self.assertFalse(any(w>>26==9 and w>>21&31==29 and w>>16&31==29 for w in self.words))
        q = json.loads((self.out/'qualification.json').read_text())
        self.assertEqual((q['total_words'],q['preserved_neighbors'],q['new_guards']),(41,13,0))
        self.assertEqual(json.loads((self.out/'make-shadow.json').read_text())['actual_Make_commands'],3)
        before = self.values['conker/build/conker.us.elf'];at = source.elf_slot_offset(before,ENTRY,SIZE)
        old = list(struct.unpack_from('>41I',before,at));m=fixture()
        observed = PositionOracle(old,m,(INPUT,OUTPUT,COUNTER,0)).run()
        self.assertNotEqual(observed.memory,reference(m,(INPUT,OUTPUT,COUNTER,0),STACK)[0])
        self.receipt.update(body_words=41,frame=0,bindings=0,new_guards=0,neighbors=13,
                            actual_Make_commands=3,old_stub_effectively_rejected=True)

    def test_02_every_bounded_counter_signed_extremes_and_branch_likely(self):
        visits=set();count=0
        for value,phase in itertools.product((*range(0xD02),*COUNTS),(0,8)):
            point=(-32768,signed(value*79,16),32767)
            m=fixture(value,point);args=(INPUT,OUTPUT,COUNTER,0xABCD1234)
            if signed(value)>=0xD00:args=(0,0,COUNTER,0xABCD1234)
            models=self.compare(m,args,phase);visits.update(models[0].visits);count+=1
            self.assertEqual(models[0].trace[0],('W',STACK+phase+12,4,0xABCD1234))
            if signed(value)>=0xD00:self.assertEqual(len(models[0].trace),2)
        self.assertEqual(set(range(ENTRY,ENTRY+SIZE,4))-visits,{ENTRY+28})
        self.receipt.update(guest_counter_phases=count,reachable_words=40,
                            unreachable_duplicate_comparison_statically_exact=1,early_return_does_not_touch_positions=True)

    def test_03_guest_position_counter_home_aliases_and_effective_late_read_control(self):
        count=0
        for value,shift,where,phase in itertools.product((0xFF,0x100,0x200,0x600,0xA00,0xA01,0xCFF),
                (-4,-2,0,2,4,8),(COUNTER,INPUT,INPUT+4,OUTPUT,OUTPUT+4,STACK+12),(0,8)):
            a,b=INPUT,INPUT+shift
            c=STACK+phase+12 if where==STACK+12 else where
            m=fixture(value);put(m,c,value);args=(a,b,c,value if where==STACK+12 else 0xDEADBEEF)
            self.compare(m,args,phase);count+=1
        for phase in (0,8):
            m=fixture();args=(STACK+phase+10,OUTPUT,COUNTER,0x12345678)
            self.compare(m,args,phase);count+=1
        bad = source.SELECTED[NAME].replace('    s32 offset;','    s32 offset;\n    s32 cached = *counter;')
        bad = bad.replace('if (*counter >= 0x200)','if (cached >= 0x200)').replace('if (*counter >= 0xA01)','if (cached >= 0xA01)').replace('*counter -= 0x800','*counter = cached - 0x800')
        obj,diag=source.compile_owner(ROOT,self.out,'#include <ultra64.h>\n'+bad,'wrong-cached-counter')
        raw=source.payload(obj,NAME)[0];code=list(struct.unpack('>%dI'%(len(raw)//4),raw))
        distinguished=0
        for value,shift in itertools.product((0x100,0x200,0x600,0xA00,0xA01,0xCFF),(-2,0,2)):
            m=fixture(value);put(m,INPUT,value);args=(INPUT,INPUT+shift,INPUT,0)
            want,result=reference(m,args,STACK)
            wrong=PositionOracle(code,m,args).run()
            distinguished+=wrong.memory!=want or wrong.r[2]!=result
        self.assertGreater(distinguished,0)
        self.receipt.update(guest_alias_phases=count,full_unused_word_home=True,
                            compiled_cached_counter_control_distinguished=distinguished,
                            cross_type_and_stack_aliases_not_native_C_claim=True)

    def native(self,body,label,opt='-O2'):
        path=self.out/(label+opt+'.c');exe=path.with_suffix('.elf');path.write_text(native_harness(body))
        p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fno-builtin','-fsanitize=undefined','-fsanitize-undefined-trap-on-error',
            '-Werror=implicit-function-declaration','-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_04_native32_typed_overlap_fences_signed_math_and_wrong_C(self):
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(source.SELECTED[NAME],'native',opt),0)
        controls=[('cutoff','>= 0xD00','>= 0xD01'),('lower','>= 0x100','>= 0x110'),
            ('square','0x190000 - offset * offset','0x190000 + offset * offset'),
            ('numerator','0x190000','0x180000'),('divisor','/ 0x1E00','/ 0x1D00'),
            ('fold','>= 0xA01','>= 0x9FF'),('step','-= 0x800','-= 0x801'),
            ('copy-Z','output[2] = input[2]','output[2] = input[0]')]
        for label,old,new in controls:
            bad=source.SELECTED[NAME].replace(old,new);self.assertNotEqual(bad,source.SELECTED[NAME])
            self.assertEqual(self.native(bad,'wrong-'+label),23,label)
        self.receipt.update(native_cases_per_optimization=0xD05*7*5+1,native_optimizations=3,
                            trap_UBSan=True,typed_same_array_overlap=True,all_fences_checked=True,effective_wrong_C_controls=8)

    def test_05_original_dispatch_window_four_arguments_and_skip_join(self):
        parent=list(struct.unpack_from('>54I',self.rom,0x1A9B08))
        before=self.values['conker/build/conker.us.elf']
        # The large current parent remains a placeholder, so do not call this a current-parent execution.
        original_table=self.rom[0x23197C:0x2319C0]
        self.assertEqual(struct.unpack_from('>I',original_table,60)[0],ENTRY)
        results=set();visits=set();phases=0
        for value,null,phase,alpha_end in itertools.product(COUNTS,(False,True),(0,8),(30,0x400,0)):
            models=[]
            for code in (self.truth,self.words):
                m=fixture(value);sp=STACK+phase
                for i,b in enumerate(original_table):m[0x8008CEBC+i]=b
                put(m,0x60000,INPUT);put(m,sp+0xBC,value);put(m,sp+0xD4,0xABCDEF01);put(m,sp+0xE4,alpha_end)
                m[INPUT+0xA]=0;m[INPUT+0xC]=0x80;m[0x800DDC80]=0
                put(m,0x8008CF00,0 if null else 5,2)
                connected=dict(zip(range(ENTRY,ENTRY+len(code)*4,4),code))
                model=PositionOracle(parent,m,(0,0,0,0),phase,WINDOW,connected)
                model.r[17]=OUTPUT;model.r[19]=0;model.r[20]=0;model.r[22]=10;model.r[23]=0x60000
                expected_boundary=KEEP if null or signed(value)<0xD00 else SKIP
                with self.assertRaises(KeyError)as stop:model.run()
                self.assertEqual(stop.exception.args,(expected_boundary,))
                if null:
                    self.assertFalse(model.calls)
                    self.assertEqual(tuple(read(model.memory,OUTPUT+i*2,2)for i in range(3)),tuple(read(m,INPUT+i*2,2)for i in range(3)))
                else:
                    self.assertEqual(model.calls,[(ENTRY,(INPUT,OUTPUT,sp+0xBC,OUTPUT+15))])
                    expected,result=reference(model.callback_memory,model.callback_arguments,sp)
                    self.assertEqual(model.memory,expected);self.assertEqual(model.r[2],result);results.add(result)
                self.assertEqual(read(model.memory,OUTPUT+0x26,2),0xFF80)
                self.assertEqual(model.memory[OUTPUT+15],min(((alpha_end-10)&0xFFFFFFFF)>>1,255))
                models.append(model);visits.update(model.visits)
            self.assertEqual(complete(models[0]),complete(models[1]));phases+=1
        self.assertEqual(results,{0,1})
        self.assertEqual(set(range(WINDOW,KEEP,4))-visits,{0x1517C708})
        pointer=struct.pack('>I',ENTRY);jal=struct.pack('>I',0x0C000000|(ENTRY>>2&0x3FFFFFF))
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==pointer],[0x2319B8])
        self.assertFalse(any(self.rom[i:i+4]==jal for i in range(0,len(self.rom),4)))
        self.receipt.update(original_caller_window_words=54,caller_reachable_words=53,caller_phases=phases,
                            NULL_slot_copy=True,Boolean_result_selects_keep_or_skip=True,
                            parent_still_placeholder=True,full_parent_or_gameplay_claimed=False)

    def test_06_independent_GNU_rebases(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.out,NAME);links=phases=0
        for i in range(3):
            entry=0x17007FFC+i*0x10000;images=[]
            for label,obj in (('original',original),('C',self.obj)):
                text,fs,rs=source.parse_object(obj);assembly,unknown=emit_function(text,fs[NAME],rs,NAME,{})
                self.assertEqual(unknown,[])
                stem=self.out/('rebase-%d-%s'%(i,label));asm=stem.with_suffix('.s');obj=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',NAME,'-o',str(elf),str(obj)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])));links+=1
            self.assertEqual(images[0],images[1])
            for value,phase in itertools.product(COUNTS,(0,8)):
                self.compare(fixture(value),(INPUT,OUTPUT,COUNTER,0xDEADBEEF),phase,images,entry);phases+=1
        self.receipt.update(independent_GNU_links=links,rebase_phases=phases,relocation_free=True)

    def test_07_fired_fault_prefixes(self):
        count=0
        for value,phase in itertools.product(COUNTS,(0,8)):
            m=fixture(value);args=(INPUT,OUTPUT,COUNTER,0xDEADBEEF)
            good=PositionOracle(self.truth,m,args,phase).run()
            for cut in range(good.root_accesses):
                models=[PositionOracle(code,m,args,phase)for code in (self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]))
                self.assertEqual((models[0].trace,models[0].current_pc,models[0].delay_of),(models[1].trace,models[1].current_pc,models[1].delay_of));count+=1
        self.assertGreater(count,100)
        self.receipt.update(fired_root_fault_prefixes=count,portable_fault_or_hardware_claimed=False)

    def test_08_strict_image_22_inputs_and_corruptions(self):
        before=self.values['conker/build/conker.us.elf'];expected=source.predicted_image(before,self.rom)
        self.assertEqual(expected,(self.out/'first-linked.elf').read_bytes())
        at=source.elf_slot_offset(before,ENTRY,SIZE)
        sym=next(at for at,n,fields,_ in source.symbol_rows(before)if n==NAME and fields[1:3]==(ENTRY,12))
        offsets=[0,len(expected)-1,at,at+SIZE-1,sym+8]
        for at in offsets:
            bad=bytearray(expected);bad[at]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),self.rom)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],self.rom)
        for name,old in self.values.items():
            self.assertEqual(source.digest(old),source.INPUTS[name])
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.out/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_corruptions_rejected=6,live_and_historical_inputs=22,
                            complete_guard_manifest_unchanged=True,metadata_exclusions=0)


if __name__ == '__main__':
    unittest.main()
