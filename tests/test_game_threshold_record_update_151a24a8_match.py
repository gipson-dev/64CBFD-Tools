"""Threshold ramps, gated colour mode, wrapped growth and both original callers."""

from dataclasses import dataclass
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest

from tools.experiments import game_threshold_record_update_151a24a8_match as match
candidate = match
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_remaining_donor_candidates import compile_owner, link_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.tests import test_game_envelope_gates_match as base
from tools.tests.game_frame_timing_oracle import TimingOracle, STACK
from tools.tests.test_game_point_transform_match import put, read
from tools.tests.test_game_effect_position_payload import complete
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests import test_game_actor_burst_consumer_match as faults


ROOT, EFFECT, STEP = match.ROOT, 0x30000, 0x800BE9E4
TABLE, TABLE_ROM = 0x8008C9C8, 0x231488
WINDOWS = ((0x15167E80,0x15167EC4,0x195330,0x2F,0x38,0x20),
           (0x151689D4,0x15168A08,0x195E84,0xB2,0x98,0x18))
STEPS = (0,1,0xFFFFFFFF,0x80000000,0x7FFFFFFF,0x10000)
PRESETS = tuple(p[:6]+(0x1234,p[9],p[6],p[7],p[8],p[9],
    (0,1,-1,32767,-32768,-9999,-9998,127)[i],(-32768,32767,-1,0,1,127,-129,256)[i])
    for i,p in enumerate(base.PRESETS))


@dataclass(frozen=True)
class Case:
    time:int=0
    parameters:tuple=PRESETS[0]
    step:int=1
    layout:int=0
    alias:int=-1
    seed:int=0


def owner_at(c,phase=0,step=STEP):
    return step-c.alias if c.alias>=0 else (EFFECT,EFFECT+4,STACK+phase-0x50,STACK+phase-0x38)[c.layout]


def fixture(c,phase=0,step=STEP):
    owner=owner_at(c,phase,step)
    memory={STACK+phase+i:(i*17+0xA5)&255 for i in range(-512,512)}
    memory.update({owner+i:(i*13+c.seed+0x5A)&255 for i in range(-16,0xC0)})
    put(memory,owner+0x38,c.time,2)
    for i,value in enumerate(c.parameters):put(memory,owner+0x50+i*2,value,2)
    put(memory,step,c.step)
    return memory


def reference(initial,owner,step=STEP):
    memory=dict(initial);time=base.half(memory,owner+0x38)
    parameter=lambda i:base.half(memory,owner+0x50+i*2)
    if parameter(2)<time:put(memory,owner+0x3F,parameter(0)*(parameter(1)-time),1)
    if parameter(5)<time:
        value=parameter(3)*(parameter(4)-time)
        put(memory,owner+0x36,value,2);put(memory,owner+0x34,value,2)
    if time<parameter(8):put(memory,owner+0x3F,time*parameter(9),1)
    if time<parameter(10):
        increment=(parameter(11)*read(memory,step))&0xFFFFFFFF
        first,second=base.half(memory,owner+0x34),base.half(memory,owner+0x36)
        put(memory,owner+0x34,first+increment,2);put(memory,owner+0x36,second+increment,2)
        time=base.half(memory,owner+0x38)
    if time<parameter(6):
        flags=read(memory,owner+0x44,2);put(memory,owner+0x2F,0x13,1);put(memory,owner+0x44,flags|0x101,2)
        colour=time*parameter(7);put(memory,owner+0x14,0x00520003)
        for offset in (0x42,0x41,0x40):put(memory,owner+offset,colour,1)
    if time<parameter(12):
        put(memory,owner+0x32,parameter(13),2);put(memory,owner+0x68,-9999,2)
    return memory


class Oracle(base.EnvelopeOracle):
    def __init__(self,words,memory,c=Case(),phase=0,entry=match.ENTRY,step=STEP,connected=None,targets=(),observed=0x38):
        owner=owner_at(c,phase,step)
        TimingOracle.__init__(self,words,memory,phase=phase,entry=entry,arguments=(owner,),connected=connected)
        self.owner,self.targets,self.observed=owner,set(targets),observed
        self.hi,self.lo,self.condition=0x89ABCDEF,0x76543210,True
    def record_call(self,target):
        if target!=match.ENTRY and target not in self.targets:raise AssertionError(hex(target))
        args=self.arguments(1)
        if args!=(self.owner,):raise AssertionError(args)
        self.calls.append((target,args));self.events.append(('CALL',target,args))
    def hook(self,target):
        if target not in self.targets or target==match.ENTRY:raise AssertionError(hex(target))
        put(self.memory,self.owner+self.observed,0x1357,2)
        for reg in (1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.hi,self.lo=0x87654321,0x12345678


def corpus():
    for time,parameters,step,layout,phase in itertools.product(base.TIMES,PRESETS,STEPS,range(2),(0,8)):
        yield Case(time,parameters,step,layout),phase
    for time,mask,coefficient,phase in itertools.product((-32767,-1,0,1,32766),range(64),(1,-32768),(0,8)):
        p=(coefficient,123,time-1 if mask&1 else time,coefficient,-456,time-1 if mask&2 else time,
           time+1 if mask&16 else time,coefficient,time+1 if mask&4 else time,coefficient,
           time+1 if mask&8 else time,coefficient,time+1 if mask&32 else time,-123)
        yield Case(time,p,0xFFFFFFFF,seed=mask),phase
    for time,parameters,layout,phase in itertools.product(base.TIMES,PRESETS,(2,3),(0,8)):
        yield Case(time,parameters,0x80000000,layout),phase
    for time,parameters in itertools.product(range(-128,128),PRESETS):yield Case(time,parameters),0


def controls():
    b=candidate.SELECTED
    rows={
        'colour_inclusive':b.replace('time < parameters[6]','time <= parameters[6]'),
        'wrong_flags':b.replace('|= 0x101','|= 0x100'),
        'wrong_mode':b.replace('0x00520003','0x00520002'),
        'first_inclusive':b.replace('parameters[2] < time','parameters[2] <= time'),
        'second_inclusive':b.replace('parameters[5] < time','parameters[5] <= time'),
        'third_inclusive':b.replace('time < parameters[8]','time <= parameters[8]'),
        'growth_inclusive':b.replace('time < parameters[10]','time <= parameters[10]'),
        'switch_inclusive':b.replace('time < parameters[12]','time <= parameters[12]'),
        'wrong_remaining':b.replace('parameters[1] - time','time - parameters[1]'),
        'missing_pair':b.replace('*(s16 *)(effect + 0x34) = ', '',1),
        'wrong_growth_scale':b.replace('parameters[11] *','parameters[9] *'),
        'wrong_sentinel':b.replace('parameters[12] = -9999','parameters[12] = -9998'),
        'wrong_switch_value':b.replace('= parameters[13];','= parameters[11];'),
        'wrong_color':b.replace('parameters[7] * time','parameters[6] * time'),
        'missing_color_byte':b.replace('effect[0x40] = ',''),
        'first_ramp_wins':b.replace('if (time < parameters[8])','else if (time < parameters[8])'),
    }
    if any(body==b for body in rows.values()):raise ValueError('Ineffective effect growth control')
    return rows


def source_with(body):
    return match.source_states((ROOT/match.SOURCE).read_text())[1].replace(match.SELECTED,body,1)


def early_step_control():
    b=candidate.SELECTED.replace('    s32 time = *(s16 *)(effect + 0x38);',
        '    s32 time = *(s16 *)(effect + 0x38);\n    u32 earlyStep = (u32)D_800BE9E4;',1)
    return b.replace('parameters[11] * (u32)D_800BE9E4','parameters[11] * earlyStep',1)


def native_source(body):
    return r'''typedef unsigned char u8;
typedef signed short s16;
typedef unsigned short u16;
typedef signed int s32;
typedef unsigned int u32;
s32 D_800BE9E4;
typedef void (*Handler)(u8*);
static u32 actual[64],expected[64];
static Handler callbacks[22];
''' + body + r'''
static void wanted(u8*p){
 s16*q=(s16*)(void*)(p+0x50);s32 t=*(s16*)(void*)(p+0x38),v;u32 d;
 if(q[2]<t)p[0x3F]=(u8)(q[0]*(q[1]-t));
 if(q[5]<t){v=q[3]*(q[4]-t);*(s16*)(void*)(p+0x36)=(s16)v;*(s16*)(void*)(p+0x34)=(s16)v;}
 if(t<q[8])p[0x3F]=(u8)(q[9]*t);
 if(t<q[10]){d=(u32)(s32)q[11]*(u32)D_800BE9E4;
  *(s16*)(void*)(p+0x34)=(s16)((u32)*(s16*)(void*)(p+0x34)+d);
  *(s16*)(void*)(p+0x36)=(s16)((u32)*(s16*)(void*)(p+0x36)+d);}
 if(t<q[6]){u16 flags=*(u16*)(void*)(p+0x44);p[0x2F]=0x13;*(u16*)(void*)(p+0x44)=flags|0x101;
  v=t*q[7];*(u32*)(void*)(p+0x14)=0x00520003u;p[0x42]=(u8)v;p[0x41]=(u8)v;p[0x40]=(u8)v;}
 if(t<q[12]){*(s16*)(void*)(p+0x32)=q[13];q[12]=-9999;}
}
static s16 boundary(s32 value){return value>32767?32767:value< -32768?-32768:(s16)value;}
__attribute__((noinline)) static void invoke(Handler fn,u8*p){fn(p);}
static int one(u32 seed,u32 indirect){
 u32 i,state=seed*1664525u+1013904223u;u8*p=(u8*)(void*)(actual+(seed&1));
 u8*w=(u8*)(void*)(expected+(seed&1));s16*q=(s16*)(void*)(p+0x50),t=(s16)seed;
 static const u32 steps[]={0,1,0xFFFFFFFFu,0x80000000u,0x7FFFFFFFu,0x10000};
 for(i=0;i<sizeof(actual);i++)((u8*)(void*)actual)[i]=(u8)(i*13u+seed*7u+0x5A);
 *(s16*)(void*)(p+0x38)=t;
 for(i=0;i<14;i++){state=state*1664525u+1013904223u;q[i]=(s16)(state>>16);}
 q[2]=boundary((s32)t+((seed>>0)%3)-1);q[5]=boundary((s32)t+((seed>>2)%3)-1);
 q[8]=boundary((s32)t+((seed>>4)%3)-1);q[10]=boundary((s32)t+((seed>>6)%3)-1);
 q[6]=boundary((s32)t+((seed>>10)%3)-1);q[12]=boundary((s32)t+((seed>>8)%3)-1);D_800BE9E4=(s32)steps[seed%6];
 for(i=0;i<sizeof(actual);i++)((u8*)(void*)expected)[i]=((u8*)(void*)actual)[i];
 wanted(w);
 if(indirect){callbacks[18]=func_151A24A8;invoke(callbacks[18],p);}else func_151A24A8(p);
 for(i=0;i<sizeof(actual);i++)if(((u8*)(void*)actual)[i]!=((u8*)(void*)expected)[i])return 1;
 return 0;
}
static int run(void){u32 i,j;
 if(sizeof(void*)!=4||sizeof(s16)!=2||sizeof(s32)!=4)return 9;
 for(i=0;i<65536;i++)for(j=0;j<2;j++)if(one(i,j))return 1;
 return 0;
}
void _start(void){s32 code=run();__asm__ volatile("int $0x80"::"a"(1),"b"(code));__builtin_unreachable();}
'''


class ThresholdRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=ROOT/match.BUILD;cls.prepared=match.prepare(ROOT)
        cls.rom=(ROOT/'conker/conker.us.bin').read_bytes()
        cls.retail=list(struct.unpack_from('>78I',cls.rom,match.ROM))
        cls.table=struct.unpack_from('>22I',cls.rom,TABLE_ROM)
        text,functions,_=parse_object(cls.out/'qualified-owner.o');info=functions[match.FUNCTION]
        cls.raw_blob=text[info['value']:info['value']+312]
        cls.fitted_blob,_=match.normalize(cls.raw_blob,match.BINDINGS);cls.proof=match.certificate(cls.raw_blob,match.BINDINGS)
        linked,_=link_owner(ROOT,cls.out,cls.out/'qualified-owner.o',match.OWNER)
        cls.raw=list(struct.unpack_from('>78I',linked,info['value']))
        linked,functions=link_owner(ROOT,cls.out,cls.prepared['qualified_object'],match.OWNER)
        cls.fitted=list(struct.unpack_from('>78I',linked,functions[match.FUNCTION]['value']))

    def receipt(self,name,value):
        (self.out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')

    def compare(self,c,phase=0,images=None,entry=match.ENTRY,step=STEP,initial=None):
        memory=fixture(c,phase,step)if initial is None else initial
        expected=reference(memory,owner_at(c,phase,step),step)
        models=[Oracle(words,memory,c,phase,entry,step).run()for words in images or(self.retail,self.raw,self.fitted)]
        for model in models:self.assertEqual(model.memory,expected,c);self.assertFalse(model.calls)
        self.assertEqual(complete(models[0]),complete(models[2]))
        return models

    def test_01_derived_lifetimes_permutation_owner_and_literal_image(self):
        r=self.prepared['report'];p=self.proof
        self.assertEqual((r['words'],r['guards'],r['raw_neighbors'],r['padded_neighbors']),(78,33,38,38))
        self.assertEqual((p['temporary_lifetimes'],p['insertions'],p['omissions']),(15,0,0))
        self.assertEqual(r['changed_bodies'],[match.FUNCTION]);self.assertEqual(r['exclusions'],0)
        self.assertEqual(self.table[18],match.ENTRY)
        aligned=list(struct.unpack('>%dI'%(len(self.rom)//4),self.rom[:len(self.rom)&~3]))
        self.assertEqual([i*4 for i,w in enumerate(aligned)if match.ENTRY<=w<match.ENTRY+312],[0x2314D0])
        self.assertFalse([w for w in aligned if w>>26 in(2,3) and match.ENTRY<=(((w&0x3FFFFFF)<<2)|0x10000000)<match.ENTRY+312])
        for at in range(312):
            bad=bytearray(self.raw_blob);bad[at]^=1
            with self.assertRaises(ValueError):match.normalize(bytes(bad),match.BINDINGS)
        for bindings in ({},{104:match.BINDINGS[104]},{**match.BINDINGS,160:[('R_MIPS_LO16','D_800BE9A4')]}):
            with self.assertRaises(ValueError):match.normalize(self.raw_blob,bindings)
        import csv,io
        rows=list(csv.DictReader(io.StringIO((self.out/'qualified-guards.csv').read_text())))
        targets=[i for i,row in enumerate(rows)if row['function']==match.FUNCTION]
        self.assertEqual(len(targets),33)
        for ordinal in(0,16,32):
            changed=[dict(row)for row in rows];row=changed[targets[ordinal]]
            row['expected']='0x%08X'%(int(row['expected'],16)^1)
            path=self.out/('rejected-guard-%d.csv'%ordinal)
            with path.open('w',newline='')as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(changed)
            with self.assertRaises(ValueError):emit_padded_assembly(self.out/'qualified-owner.o',ROOT/'conker/asm/1CC440.s',word_patches_path=path,filename=match.OWNER)
        before,after=self.prepared['predecessor_elf'].read_bytes(),self.prepared['qualified_elf'].read_bytes()
        truth=self.rom[match.ROM:match.ROM+312]
        for at in (0x80,len(after)-1,match.elf_slot_offset(before,match.ENTRY,312)):
            bad=bytearray(after);bad[at]^=1
            with self.assertRaises(ValueError):match.strict_image(before,bytes(bad),truth)

    def test_02_signed_boundaries_gate_priority_wrapping_and_all_words(self):
        count=0;visits=set()
        for c,phase in corpus():
            models=self.compare(c,phase);visits.update(models[0].visits);count+=1
        self.assertEqual(visits,set(range(match.ENTRY,match.ENTRY+312,4)))
        self.receipt('guest-contract',{'cases_per_body':count,'retail_words_visited':78,
            'all_64_feasible_gate_masks':True,'signed_thresholds':True,'wrapped_32_bit_growth':True})

    def test_03_live_step_aliases_and_repeated_sentinel_updates(self):
        count=0
        for alias,time,preset,step,phase in itertools.product(range(0,0x70,4),(-32768,-1,0,1,32767),(1,6),(1,0xFFFFFFFF),(0,8)):
            self.compare(Case(time,PRESETS[preset],step,alias=alias),phase);count+=1
        repeated=0
        for time in (-32768,-10000,-9999,-9998,0,32767):
            c=Case(time,PRESETS[3]);initial=fixture(c)
            for _ in range(3):
                models=self.compare(c,initial=initial);initial=models[0].memory;repeated+=1
        self.receipt('aliases',{'cases_per_body':count,'word_aligned_step_layouts':28,
            'layouts_inside_0x6C_record':27,'boundary_layout':0x6C,'repeated_updates_per_body':repeated,
            'negative_ages_below_minus9999_not_clamped':True})

    def test_04_native32_all_timer_bits_and_typed_callback_controls(self):
        output=self.out/'native';output.mkdir(exist_ok=True)
        rows=[('positive-'+opt[1:],candidate.SELECTED,opt,0)for opt in('-O0','-O2','-O3')]
        rows.extend((label,body,'-O2',1)for label,body in controls().items())
        for label,body,opt,expected in rows:
            path=output/(label+'.c');binary=path.with_suffix('.elf');path.write_text(native_source(body))
            built=subprocess.run([*native_command(opt),'-fno-strict-aliasing','-mstackrealign',str(path),'-o',str(binary)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            self.assertEqual(subprocess.run([str(binary)],capture_output=True,timeout=60).returncode,expected,label)
        self.receipt('native-contract',{'profiles':['O0','O2','O3'],'direct_cases_per_profile':65536,
            'typed_callback_cases_per_profile':65536,'controls':sorted(controls()),'trap_UBSan':True,
            'typed_halfword_storage':True,'global_aliases_qualified_in_guest_only':True})

    def test_05_both_original_callback_windows_all_registry_slots(self):
        count=0;visits=[set(),set()]
        for which,index,time,layout,phase,dead in itertools.product(range(2),range(-1,22),(-1,0,127),range(2),(0,8),(0,1)):
            entry,end,rom,selector,observed,frame=WINDOWS[which]
            c=Case(time,PRESETS[(time+index)%8],0xFFFFFFFF,layout);owner=owner_at(c,phase)
            initial=fixture(c,phase);initial[owner+selector]=index&255
            for i,target in enumerate(self.table):put(initial,TABLE+4*i,target)
            target=self.table[index]if index!=-1 else 0
            expected=dict(initial)
            if target:
                put(expected,STACK+phase,owner)
                if which==0:put(expected,STACK+phase-5,dead,1)
                if target==match.ENTRY:expected=reference(expected,owner)
                else:put(expected,owner+observed,0x1357,2)
            original=list(struct.unpack_from('>%dI'%((end-entry)//4),self.rom,rom));models=[]
            for child in(self.retail,self.raw,self.fitted):
                connected={match.ENTRY+i*4:w for i,w in enumerate(child)}
                model=Oracle(original,initial,c,phase,entry,connected=connected,targets=self.table,observed=observed)
                model.r[29]=STACK+phase-frame;model.r[7]=dead;model.code=base.WindowCode(model.code,model,end)
                with self.assertRaises(base.WindowBoundary):model.run()
                self.assertEqual(model.memory,expected,(which,index,c));self.assertEqual(model.calls,[(target,(owner,))]if target else[])
                self.assertEqual(model.r[10 if which==0 else 24],base.half(expected,owner+observed)&0xFFFFFFFF)
                self.assertEqual(model.r[4],owner)
                if which==0:self.assertEqual(model.r[7],dead)
                visits[which].update(model.visits);models.append(model)
            self.assertEqual(complete(models[0]),complete(models[2]));count+=1
        for which,(entry,end,*_)in enumerate(WINDOWS):self.assertTrue(set(range(entry,end,4))<=visits[which])
        self.receipt('callers',{'cases_per_body':count,'original_window_words':[17,13],
            'all_22_slots_and_minus_one':True,'observed_reload_and_owner_homes':True,
            'other_providers_bounded':True,'full_parent_or_gameplay_claimed':False})

    def test_06_literal_private_fault_prefixes_and_inactive_global(self):
        count=0
        for time,preset,alias in itertools.product((-32768,-1,0,1,32767),(1,3,6),(-1,0x34)):
            c=Case(time,PRESETS[preset],0xFFFFFFFF,alias=alias);initial=fixture(c)
            baseline=Oracle(self.retail,initial,c).run()
            for cut in range(baseline.root_accesses):
                models=[Oracle(words,initial,c)for words in(self.retail,self.fitted)]
                for model in models:
                    model.root_fault=cut
                    with self.assertRaises(faults.AccessBoundary):model.run()
                self.assertEqual(complete(models[0]),complete(models[1]));count+=1
        c=Case();initial=fixture(c)
        for byte in range(4):initial.pop(STEP+byte)
        self.compare(c,initial=initial)
        self.receipt('fault-prefixes',{'fired_prefixes':count,'complete_fitted_private_state_equal':True,
            'raw_fault_PC_or_order_not_equated':True,'inactive_global_can_be_unmapped':True})

    def test_07_independent_GNU_links_and_step_carry_edges(self):
        from tools.tests.test_game_view_list_setup import ViewListSetupTests
        context=type('GrowthOriginal',(),dict(root=ROOT,out=self.out))
        original=ViewListSetupTests.original.__func__(context,'original-growth',(ROOT/'conker/asm/1CC440.s').read_text(),match.FUNCTION)
        objects=(original,self.out/'qualified-owner.o',self.prepared['qualified_object']);count=links=0
        for index,(entry,step)in enumerate(((match.ENTRY,STEP),(0x18017FFC,0x800A7FFC),(0x1A028000,0x800A8000))):
            images=[]
            for ordinal,obj in enumerate(objects):
                text,functions,relocations=parse_object(obj)
                assembly,unknown=emit_function(text,functions[match.FUNCTION],relocations,match.FUNCTION,{'D_800BE9E4':step})
                self.assertFalse(unknown);path=self.out/('rebase-%d-%d'%(index,ordinal))
                path.with_suffix('.s').write_text(assembly);path.with_suffix('.ld').write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(path.with_suffix('.o')),str(path.with_suffix('.s'))],capture_output=True,check=True)
                subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(path.with_suffix('.ld')),'-e',match.FUNCTION,
                    '--defsym=D_800BE9E4=0x%X'%step,'-o',str(path.with_suffix('.elf')),str(path.with_suffix('.o'))],capture_output=True,check=True)
                images.append(list(struct.unpack_from('>78I',sections(path.with_suffix('.elf'))['.text'][1])));links+=1
            self.assertEqual(images[0],images[2])
            for alias,time in itertools.product((-1,0x34,0x3C,0x68),(-32768,1,32767)):
                self.compare(Case(time,PRESETS[6],0xFFFFFFFF,alias=alias),images=images,entry=entry,step=step);count+=1
        self.receipt('rebases',{'GNU_links':links,'cases_per_body':count,'HI_LO_carry_edges':True})

    def test_08_compiled_early_step_and_semantic_controls(self):
        labels=('wrong_remaining','wrong_growth_scale','wrong_sentinel','missing_color_byte')
        cases=list(corpus());results={}
        for label in labels:
            obj,_=compile_owner(ROOT,self.out,source_with(controls()[label]),'control-'+label)
            text,functions=link_owner(ROOT,self.out,obj,match.OWNER);info=functions[match.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(info['size']//4),text,info['value']))
            found=False
            for c,phase in cases:
                actual=Oracle(words,fixture(c,phase),c,phase).run()
                if actual.memory!=reference(fixture(c,phase),owner_at(c,phase)):found=True;break
            self.assertTrue(found,label);results[label]={'guest_counterexample':True,'words':len(words)}
        obj,_=compile_owner(ROOT,self.out,source_with(early_step_control()),'control-early-step')
        text,functions=link_owner(ROOT,self.out,obj,match.OWNER);info=functions[match.FUNCTION]
        words=list(struct.unpack_from('>%dI'%(info['size']//4),text,info['value']))
        p=(1,9,32767,3,9,-1,0,1,0,1,32767,5,-32768,1)
        c=Case(1,p,2,alias=0x34);actual=Oracle(words,fixture(c),c).run()
        self.assertNotEqual(actual.memory,reference(fixture(c),owner_at(c)))
        c=Case();initial=fixture(c)
        for byte in range(4):initial.pop(STEP+byte)
        with self.assertRaisesRegex(AssertionError,'unmapped read'):Oracle(words,initial,c).run()
        results['early-step']={'alias_0x34_counterexample':True,'inactive_unmapped_global_fault':True,'words':len(words)}
        self.receipt('compiled-controls',results)


if __name__=='__main__':unittest.main()
