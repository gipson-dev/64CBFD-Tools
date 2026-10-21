"""Two-draw range selection, pointer lifetime, typed vectors and the retained RNG."""

from dataclasses import dataclass, replace
from pathlib import Path
import itertools
import json
import math
import struct
import subprocess
import unittest

from tools.experiments import game_two_range_position as source
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.game_frame_timing_oracle import TimingOracle
from tools.tests.test_game_random_selector_outputs_match import RandomOutputsOracle, next_seed, SEEDS
from tools.tests.game_animation_timeline_oracle import bits, floating
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_table_range_loader import STACK
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_point_random_burst import ReturnBoundaryCode, CallerBoundary
from tools.tests import test_game_actor_burst_consumer_match as faults

ROOT = Path(__file__).resolve().parents[2]
THRESHOLD, LEFT, RIGHT, RNG = 0x800A130C, 0x80088A3C, 0x80088A40, 0x150ADA68
ROWS, OUTPUT, DESCRIPTOR = (0x28000, 0x29000, 0x2A000), 0x30000, 0x34000
SEED, SCALE = 0x800885B0, 0x8009F740
WINDOW, JOIN, TABLE = 0x150E6988, 0x150E69CC, 0x80088A20
SYMBOLS = dict(D_800A130C=THRESHOLD, D_80088A3C=LEFT, D_80088A40=RIGHT, func_150ADA68=RNG)
PATTERNS = ((-10.,20.,-30.,-2.,4.,2.), (100.,-200.,300.,140.,-120.,380.),
            (1e20,1.,-1e20,-1e20,2.,1e20), (-0.,0.,-0.,0.,-0.,0.),
            (floating(1),-floating(1),0.,floating(3),floating(1),-floating(1)))


@dataclass(frozen=True)
class Case:
    first: int = bits(.25)
    second: int = bits(.75)
    threshold: int = 0x3F102F57
    mode: int = 0
    row: int = -1
    shift: int = 0
    pattern: int = 0
    home: bool = False


def corpus():
    for i in range(128):
        yield Case(bits((i % 65)/64), bits(((i*7) % 65)/64), mode=i % 4, pattern=i % 5)
    firsts = (0, 0x80000000, bits(.5), 0x3F102F56, 0x3F102F57, 0x3F102F58, bits(1.), 0x7FC12345)
    for first, second, mode in itertools.product(firsts, (-1.,0.,.25,.75,1.,2.), (0,3)):
        yield Case(first, bits(second), mode=mode)
    for row, shift, first, mode in itertools.product(range(3), range(-2,8), (.25,.75), (0,3)):
        yield Case(bits(first), bits(.75), mode=mode, row=row, shift=shift)
    for threshold, first, mode in itertools.product((0,0x80000000,bits(.5),0x7FC12345),
                                                   (0x80000000,bits(.5),0x7FC54321), (0,3)):
        yield Case(first, threshold=threshold, mode=mode)
    for first, mode in itertools.product((.25,.75), range(4)):
        yield Case(bits(first), mode=mode, home=True)


def symbols(values=None):
    return dict(values or SYMBOLS)


def output_pointer(case):
    return ROWS[case.row]+16+case.shift*4 if case.row >= 0 else OUTPUT+8


def fixture(case, anchors=None):
    s = symbols(anchors)
    m = {STACK+i: (i*17+0xA5)&255 for i in range(-0x1000,0x400)}
    for base, size in ((*((row,56) for row in ROWS), (OUTPUT,28), (DESCRIPTOR-16,64),
                       (TABLE,12), (SEED,8), (SCALE,4),
                       (s['D_800A130C']-16,36), (s['D_80088A3C']-16,40), (s['D_80088A40']-16,40))):
        for i in range(size):
            m.setdefault(base+i,(i*13+0xA5)&255)
    for r, base in enumerate(ROWS):
        for i in range(14):
            value = PATTERNS[(case.pattern+r)%len(PATTERNS)][i-4] if 4 <= i < 10 else -999.
            put(m,base+i*4,bits(value))
    for i in range(7):
        put(m,OUTPUT+i*4,bits(-999.))
    put(m,s['D_800A130C'],case.threshold)
    put(m,s['D_80088A3C'],ROWS[0]+16)
    put(m,s['D_80088A40'],ROWS[1]+16)
    put(m,SEED,0x123456789ABCDEF0,8)
    put(m,SCALE,0x37800080)
    return m


def public(memory):
    return {a:v for a,v in memory.items() if not STACK-0x1000 <= a < STACK+0x400}


def native_words(memory, case, anchors=None):
    s = symbols(anchors)
    return ([0xCA000000+i for i in range(4)] + [read(memory,s['D_800A130C'])] +
            [read(memory,row+i*4) for row in ROWS for i in range(14)] +
            [read(memory,OUTPUT+i*4) for i in range(7)] + [0xCB000000+i for i in range(4)])


def observe(memory, case, anchors):
    values = native_words(memory,case,anchors)
    digest = 2166136261
    for word in values:
        digest = ((digest ^ word)*16777619)&0xFFFFFFFF
    pointers = [read(memory,anchors[name]) for name in ('D_80088A3C','D_80088A40')]
    return (read(memory,anchors['D_800A130C']), *(ROWS.index(p-16) for p in pointers), digest)


def mutation(memory, case, stage, anchors):
    if not case.mode & stage:
        return
    if stage == 1:
        put(memory,anchors['D_800A130C'],bits(.875))
        pair = (2,0)
    else:
        pair = (1,2)
    for name, row in zip(('D_80088A3C','D_80088A40'),pair):
        put(memory,anchors[name],ROWS[row]+16)
    for row, base in enumerate(ROWS):
        for i in range(6):
            put(memory,base+16+i*4,bits((row+1)*100.+stage*10.+i*3.))


def reference(case, anchors=None, memory=None, output=None, seed=None):
    s = symbols(anchors);m = dict(fixture(case,s) if memory is None else memory)
    seen=[];samples=[]
    for stage in (1,2):
        seen.append(observe(m,case,s))
        if seed is None:
            sample = case.first if stage == 1 else case.second
            mutation(m,case,stage,s)
        else:
            value=next_seed(read(m,SEED,8));put(m,SEED,value,8)
            sample=bits(float(value&65535)*floating(read(m,SCALE)))
        samples.append(sample)
        if stage == 1:
            choice = 'D_80088A3C' if floating(sample) < floating(read(m,s['D_800A130C'])) else 'D_80088A40'
            selected = read(m,s[choice])
    target = OUTPUT+16 if case.home else output_pointer(case) if output is None else output
    for axis in range(3):
        base=read(m,selected+axis*4);end=read(m,selected+(axis+3)*4)
        delta=bits(floating(end)-floating(base))
        product=bits(floating(delta)*floating(samples[1]))
        put(m,target+axis*4,bits(floating(base)+floating(product)))
    return m,seen,selected


class RangeOracle(RandomOutputsOracle,TimingOracle):
    def __init__(self,words,case,phase=0,anchors=None,entry=source.ENTRY,connected=None,
                 memory=None,output=None,real=False,window=False):
        self.case,self.anchors,self.real=case,symbols(anchors),real
        self.seen,self.visits,self.number=[],set(),0
        self.entry_sp,self.boundary_hit=STACK+phase,None
        self.output=output_pointer(case) if output is None else output
        TimingOracle.__init__(self,words,fixture(case,self.anchors) if memory is None else memory,
            phase=phase,entry=entry,arguments=(self.output,),connected=connected)
        if window:
            self.r[29]-=0xA8;self.entry_sp=self.r[29]
            self.r[2]=DESCRIPTOR;self.r[6]=0xFFFFFFFF;self.f[2]=0
            self.code=ReturnBoundaryCode(self.code,JOIN,self)

    def execute(self,word):
        self.visits.add(self.current_pc)
        if word>>26==32:
            rs,rt=word>>21&31,word>>16&31
            imm=(word&65535)-(65536 if word&0x8000 else 0)
            value=self.get((self.r[rs]+imm)&0xFFFFFFFF,1)
            self.r[rt]=((value^128)-128)&0xFFFFFFFF;self.r[0]=0
        else:
            super().execute(word)

    def record_call(self,target):
        if target==source.ENTRY:
            self.entry_sp=self.r[29]
            assert self.r[4]==self.r[29]+0x8C
            args=(self.r[4],)
        else:
            assert target==self.anchors['func_150ADA68'],hex(target)
            args=();self.seen.append(observe(self.memory,self.case,self.anchors))
            self.number+=1
        self.calls.append((target,args));self.events.append(('CALL',target,args))

    def hook(self,target):
        assert target==self.anchors['func_150ADA68'] and self.number in (1,2)
        stage=self.number
        mutation(self.memory,self.case,stage,self.anchors)
        if stage==2 and self.case.home:
            put(self.memory,self.entry_sp,OUTPUT+16)
        for i in range(4):
            self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in (1,2,3,*range(4,16),24,25):
            self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)]
        self.hi,self.lo=0x87654321,0x12345678
        self.f[0]=self.case.first if stage==1 else self.case.second


def native_harness(body,cases):
    row=lambda values:'{'+','.join('0x%08Xu'%v for v in values)+'}'
    records=[]
    for case in cases:
        initial=fixture(case);final,seen,_=reference(case)
        pair=[ROWS.index(read(final,a)-16) for a in (LEFT,RIGHT)]
        records.append('{%s,%s,%s,%s,%s,%d,%d,%d}'%(
            row((case.first,case.second)),row(native_words(initial,case)),
            row(native_words(final,case)),row(sum((list(v) for v in seen),[])),
            row(pair),case.mode,case.row,case.shift))
    return r"""typedef unsigned int u32;typedef int s32;typedef float f32;typedef unsigned char u8;
typedef union{u32 word;f32 real;}Float;
typedef struct{u32 before[4];f32 threshold;f32 rows[3][14];f32 output[7];u32 after[4];}State;
typedef char Width[(sizeof(void*)==4&&sizeof(State)==232)?1:-1];
typedef struct{u32 samples[2],initial[58],expected[58],seen[8],pointers[2];u32 mode;s32 row,shift;}Case;
static const Case cases[]={""" + ',\n'.join(records) + r"""};
static State state;static const Case *item;static f32 *left,*right;static u32 calls,seen[8],error;
static f32 real(u32 w){Float f;f.word=w;return f.real;}
static u32 word(f32 v){Float f;f.real=v;return f.word;}
static u32 identity(f32 *p){u32 i;for(i=0;i<3;i++)if(p==state.rows[i]+4)return i;return 99;}
static u32 checksum(void){u32 i,j,w,h=2166136261u;u8 *p=(u8*)&state;
 for(i=0;i<58;i++){w=0;for(j=0;j<4;j++)w|=(u32)p[i*4+j]<<(8*j);h=(h^w)*16777619u;}return h;}
#define D_800A130C state.threshold
#define D_80088A3C left
#define D_80088A40 right
__attribute__((noinline)) f32 func_150ADA68(void){u32 n=calls++,r,i;
 if(n>=2){error=1;return 0;}
 seen[n*4]=word(state.threshold);seen[n*4+1]=identity(left);
 seen[n*4+2]=identity(right);seen[n*4+3]=checksum();
 if(item->mode&(n+1)){
  if(n==0){state.threshold=.875f;left=state.rows[2]+4;right=state.rows[0]+4;}
  else{left=state.rows[1]+4;right=state.rows[2]+4;}
  for(r=0;r<3;r++)for(i=0;i<6;i++)state.rows[r][4+i]=(r+1)*100.0f+(n+1)*10.0f+i*3.0f;
 }
 return real(item->samples[n]);}
""" + body + r"""
static int run(void){u32 n,i,j;u8 *p=(u8*)&state;f32 *out;
 for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++){item=&cases[n];calls=error=0;
  for(i=0;i<58;i++)for(j=0;j<4;j++)p[4*i+j]=(u8)(item->initial[i]>>(8*j));
  left=state.rows[0]+4;right=state.rows[1]+4;
  out=item->row<0?state.output+2:state.rows[item->row]+4+item->shift;
  func_150E6E34(out);
  if(calls!=2||error||identity(left)!=item->pointers[0]||identity(right)!=item->pointers[1])return 23;
  for(i=0;i<8;i++)if(seen[i]!=item->seen[i])return 23;
  for(i=0;i<58;i++)for(j=0;j<4;j++)if(p[4*i+j]!=(u8)(item->expected[i]>>(8*j)))return 23;
 }return 0;}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
"""


class TwoRangePositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=ROOT/source.BUILD
        cls.installed=source.digest((ROOT/source.SOURCE).read_bytes())!=source.INPUTS[source.SOURCE]
        if cls.installed:source.audit(ROOT,cls.output)
        else:
            source.freeze(ROOT,cls.output)
            if not (cls.output/'first-link.json').exists():
                source.qualify(ROOT,cls.output);source.make_shadow(ROOT,cls.output);source.predict(ROOT,cls.output)
        cls.values=source.snapshot(cls.output);cls.rom=cls.values['conker/conker.us.bin']
        cls.obj,diagnostics=source.compile_owner(ROOT,cls.output,'#include <ultra64.h>\n'+source.DECLARATIONS+source.SELECTED,'fresh-selected')
        if diagnostics:raise ValueError(diagnostics)
        data,fs=source.link_owner(ROOT,cls.output,cls.obj,source.OWNER)
        cls.words=list(struct.unpack_from('>41I',data,fs[source.FUNCTION]['value']))
        cls.truth=list(struct.unpack_from('>41I',cls.rom,source.ROM))
        cls.cases=list(corpus());cls.native_cases=[c for c in cls.cases if not c.home]
        cls.receipt=dict(installed=cls.installed,cases=len(cls.cases),native_cases=len(cls.native_cases))

    @classmethod
    def tearDownClass(cls):
        (cls.output/'test-receipt.json').write_text(json.dumps(cls.receipt,indent=2)+'\n')
        print('two-range position qualification:',cls.receipt)

    def compare(self,case,phase=0,anchors=None,images=None,entry=source.ENTRY,seed=None):
        memory=fixture(case,anchors);connected=None
        if seed is not None:
            put(memory,SEED,seed,8)
            code=struct.unpack_from('>25I',self.rom,0xDAF18)
            connected=dict(zip(range(RNG,RNG+100,4),code))
        expected,seen,_=reference(case,anchors,memory=memory,seed=seed)
        models=[]
        for code in images or (self.truth,self.words):
            model=RangeOracle(code,case,phase,anchors,entry,connected,memory=memory,real=seed is not None).run()
            self.assertEqual(public(model.memory),public(expected))
            self.assertEqual(model.seen,seen)
            self.assertEqual([c[0]for c in model.calls],[symbols(anchors)['func_150ADA68']]*2)
            self.assertEqual(model.r[29],STACK+phase);models.append(model)
        self.assertEqual(complete(models[0]),complete(models[1]))
        for reg in (*range(16,24),28,29,30,31):self.assertEqual(models[1].r[reg],models[1].before[reg])
        self.assertEqual(models[1].f[20:],models[1].saved_f)
        return models

    def test_01_direct_extent_bindings_actual_owner_and_old_stub(self):
        raw,bindings=source.payload(self.obj)
        self.assertEqual(self.words,self.truth);self.assertEqual((len(raw),self.words[0]),(164,0x27BDFFE0))
        self.assertEqual(source.digest(raw),source.RAW_SHA)
        self.assertEqual(bindings,{12:[('R_MIPS_26','func_150ADA68')],20:[('R_MIPS_HI16','D_800A130C')],
            24:[('R_MIPS_LO16','D_800A130C')],28:[('R_MIPS_HI16','D_80088A40')],
            48:[('R_MIPS_HI16','D_80088A3C')],56:[('R_MIPS_LO16','D_80088A3C')],
            60:[('R_MIPS_LO16','D_80088A40')],64:[('R_MIPS_26','func_150ADA68')]})
        self.assertEqual(source.payload(source.original(ROOT,self.output)),(raw,bindings))
        before=self.values['conker/build/conker.us.elf'];at=source.elf_slot_offset(before,source.ENTRY,164)
        old=list(struct.unpack_from('>41I',before,at))
        self.assertNotEqual(public(RangeOracle(old,Case()).run().memory),public(reference(Case())[0]))
        q=json.loads((self.output/'qualification.json').read_text())
        self.assertGreater(q['preserved_neighbors'],0);self.assertTrue(q['compiler_only'])
        self.assertEqual(json.loads((self.output/'make-shadow.json').read_text())['actual_Make_commands'],5)
        self.receipt.update(words=41,frame=32,bindings=8,guards=0,compiler_only=True,
            preserved_neighbors=q['preserved_neighbors'],actual_Make_commands=5,old_stub_effectively_rejected=True)

    def test_02_complete_semantics_boundaries_lifetimes_and_sequential_aliases(self):
        visits=set()
        for case,phase in itertools.product(self.cases,(0,8)):
            models=self.compare(case,phase);visits.update(models[0].visits)
        self.assertTrue(set(range(source.ENTRY,source.ENTRY+164,4))<=visits)
        self.receipt.update(modeled_phases=len(self.cases)*2,all41_target_words_visited=True,
            late_threshold_and_pointer_capture=True,late_range_reads=True,sequential_aliases=True,
            quiet_NaN_selection_not_FCSR_claim=True,guest_home_phases=sum(c.home for c in self.cases)*2)

    def native(self,body,label,opt='-O2'):
        path=self.output/(label+opt+'.c');exe=path.with_suffix('.elf')
        path.write_text(native_harness(body,self.native_cases))
        p=subprocess.run(['gcc','-m32','-std=c99',opt,'-fno-pie','-no-pie','-nostdlib','-fno-stack-protector',
            '-fno-builtin','-mstackrealign','-msse2','-mfpmath=sse','-ffp-contract=off',
            '-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Werror=implicit-function-declaration',
            '-Wl,-e,_start',str(path),'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return subprocess.run([str(exe)],capture_output=True).returncode

    def test_03_native32_typed_arrays_and_effective_semantic_controls(self):
        b=source.SELECTED
        for opt in ('-O0','-O2','-O3'):self.assertEqual(self.native(b,'native',opt),0)
        before='    fraction = func_150ADA68();'
        output='\n'.join(line for line in b.splitlines()if '    output['in line)
        snapshot=b.replace('    f32 fraction;','    f32 fraction;\n    f32 saved[6];\n    s32 i;')
        controls={
            'inclusive':b.replace('< D_800A130C','<= D_800A130C'),
            'wrong-range':b.replace('range = D_80088A3C','range = D_80088A40'),
            'early-threshold':b.replace('    f32 fraction;','    f32 fraction;\n    f32 limit = D_800A130C;').replace('< D_800A130C','< limit'),
            'early-pointers':b.replace('    f32 fraction;','    f32 fraction;\n    f32 *capturedLeft = D_80088A3C;\n    f32 *capturedRight = D_80088A40;').replace('range = D_80088A3C','range = capturedLeft').replace('range = D_80088A40','range = capturedRight'),
            'one-draw':b.replace('    f32 fraction;','    f32 fraction;\n    f32 first;').replace('if (func_150ADA68() <','if ((first = func_150ADA68()) <').replace(before,'    fraction = first;'),
            'clamped-fraction':b.replace(before,before+'\n    if (fraction < 0.0f) fraction = 0.0f;\n    if (fraction > 1.0f) fraction = 1.0f;'),
            'early-fields':snapshot.replace(before,'    for (i=0;i<6;i++) saved[i]=range[i];\n'+before).replace(output,output.replace('range[','saved[')),
            'snapshot-fields':snapshot.replace(before,before+'\n    for (i=0;i<6;i++) saved[i]=range[i];').replace(output,output.replace('range[','saved[')),
            'reverse-stores':b.replace(output,'\n'.join(output.splitlines()[::-1])),
            'wrong-end':b.replace('range[3] - range[0]','range[4] - range[0]'),
            'extra-draw':b.replace('output[2] =','fraction = func_150ADA68();\n    output[2] ='),
            'missing-store':b.replace(next(line for line in b.splitlines()if 'output[1]'in line),''),
        }
        for name,body in controls.items():
            self.assertNotEqual(body,b,name);self.assertEqual(self.native(body,name),23,name)
        self.receipt.update(native_optimizations=3,trap_UBSan=True,typed_fenced_float_arrays=True,
            compiled_semantic_negatives=len(controls),native_home_redirection_claimed=False)

    def test_04_actual_17_word_caller_window_signed_gate_and_void_result(self):
        self.assertEqual([i for i in range(0,len(self.rom),4)if self.rom[i:i+4]==struct.pack('>I',source.ENTRY)],[0x22D4E0])
        opcode=0x0C000000|(source.ENTRY>>2&0x3FFFFFF)
        self.assertFalse(any(self.rom[i:i+4]==struct.pack('>I',opcode)for i in range(0,len(self.rom),4)))
        window=list(struct.unpack_from('>17I',self.rom,0x113E38));count=joins=0
        for case,slot,phase in itertools.product(self.native_cases[::37],(0,255),(0,8)):
            memory=fixture(case);memory[DESCRIPTOR+4]=slot
            for i,word in enumerate(struct.unpack_from('>3I',self.rom,0x22D4E0)):put(memory,TABLE+i*4,word)
            output=STACK+phase-0xA8+0x8C
            if slot==0:expected,seen,_=reference(case,memory=memory,output=output)
            else:
                expected,seen=dict(memory),[]
                for i in range(3):put(expected,output+i*4,0)
            models=[]
            for code in (self.truth,self.words):
                connected=dict(zip(range(source.ENTRY,source.ENTRY+164,4),code))
                model=RangeOracle(window,case,phase,entry=WINDOW,connected=connected,memory=memory,window=True)
                with self.assertRaises(CallerBoundary):model.run()
                self.assertEqual(model.boundary_hit,JOIN);self.assertEqual(model.r[29],STACK+phase-0xA8)
                self.assertEqual(public(model.memory),public(expected));self.assertEqual(model.seen,seen)
                self.assertEqual(tuple(read(model.memory,output+i*4)for i in range(3)),
                                 tuple(read(expected,output+i*4)for i in range(3)))
                self.assertEqual(model.r[2],DESCRIPTOR)
                models.append(model);joins+=1
            self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(actual_caller_words=17,caller_phases=count,fired_join_boundaries=joins,
            signed_minus1_bypass=True,void_result_unused=True,full_parent_and_other_slots_not_claimed=True)

    def test_05_original_25_word_float_RNG_and_full_seed_steps(self):
        seeds=list(SEEDS)+[(i*0x123456789ABCDEF+0xFEDCBA9876543210)&0xFFFFFFFFFFFFFFFF for i in range(32)]
        visits=set();selected=set();count=0
        for seed,phase in itertools.product(seeds,(0,8)):
            case=Case()
            models=self.compare(case,phase,seed=seed);visits.update(models[0].visits)
            memory=fixture(case);put(memory,SEED,seed,8)
            selected.add(reference(case,memory=memory,seed=seed)[2]);count+=1
        self.assertTrue(set(range(RNG,RNG+100,4))<=visits)
        self.assertEqual(selected,{ROWS[0]+16,ROWS[1]+16})
        self.receipt.update(original_RNG_words=25,all25_RNG_words_visited=True,real_RNG_phases=count,
            full_seed64=True,exact_scale_word=0x37800080,RNG_left_handwritten=True,FCSR_or_hardware_claimed=False)

    def test_06_independent_GNU_relocations_and_signed_low_carries(self):
        from tools.experiments.alternative_source_draft_word_screen import emit_function
        original=source.original(ROOT,self.output);count=0
        for i in range(3):
            anchors=dict(D_800A130C=0x80107FFC+i*0x10000,D_80088A3C=0x80208000+i*0x10000,
                         D_80088A40=0x8030FFFC+i*0x10000,func_150ADA68=RNG+(i+1)*0x10000)
            entry=0x17007FFC+i*0x10000;images=[]
            for label,obj in (('original',original),('C',self.obj)):
                text,fs,rs=source.parse_object(obj)
                assembly,unknown=emit_function(text,fs[source.FUNCTION],rs,source.FUNCTION,anchors)
                self.assertEqual(unknown,[]);stem=self.output/('rebase-%d-%s'%(i,label))
                asm=stem.with_suffix('.s');out=stem.with_suffix('.o');ld=stem.with_suffix('.ld');elf=stem.with_suffix('.elf')
                asm.write_text(assembly);ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(out),str(asm)],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(ld),'-e',source.FUNCTION,
                    *['--defsym=%s=0x%X'%p for p in anchors.items()],'-o',str(elf),str(out)],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>41I',sections(elf)['.text'][1])))
            self.assertEqual(images[0],images[1])
            for case,phase in itertools.product(self.native_cases[::53],(0,8)):
                self.compare(case,phase,anchors,images,entry);count+=1
        self.receipt.update(independent_GNU_links=6,rebase_phases=count,all8_bindings_rebased=True)

    def test_07_fired_target_fault_prefixes(self):
        count=0
        for case,phase in itertools.product((Case(),Case(first=bits(.75),mode=3)),(0,8)):
            good=RangeOracle(self.truth,case,phase).run()
            for cut in range(good.root_accesses):
                models=[RangeOracle(code,case,phase)for code in (self.truth,self.words)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        self.receipt.update(target_fault_prefixes=count,guest_faults_not_portable_C_or_hardware_claims=True)

    def test_08_strict_image_and_all_frozen_installed_inputs(self):
        before=self.values['conker/build/conker.us.elf'];truth=self.rom[source.ROM:source.ROM+164]
        expected=source.predicted_image(before,truth)
        self.assertEqual(expected,(self.output/'first-linked.elf').read_bytes())
        at=source.elf_slot_offset(before,source.ENTRY,164)
        offsets=(0,at-1,at,at+160,at+164,len(before)-1)
        for offset in offsets:
            bad=bytearray(expected);bad[offset]^=1
            with self.assertRaises(ValueError):source.check_image(before,bytes(bad),truth)
        with self.assertRaises(ValueError):source.check_image(before,expected[:-1],truth)
        for name,wanted in source.INPUTS.items():
            old=(self.output/('before-'+name.replace('/','_'))).read_bytes()
            self.assertEqual(source.digest(old),wanted)
            current=source.recovered_owner(old.decode()).encode()if self.installed and name==source.SOURCE else expected if self.installed and name=='conker/build/conker.us.elf'else old
            self.assertEqual((ROOT/name).read_bytes(),current)
        self.assertEqual(source.digest((self.output/'before-padded.o').read_bytes()),source.BEFORE_OBJECT_SHA)
        self.receipt.update(strict_image_negatives=7,live_inputs=len(source.INPUTS),old_padded_object_pinned=True,
                            complete_guard_manifest_unchanged=True)


if __name__=='__main__':
    unittest.main()
