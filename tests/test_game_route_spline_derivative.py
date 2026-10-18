"""Derivative publication, real aliases, F20 FR=0 pair and closed identity routing."""
import copy
import csv
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_spline_derivative as source
from tools.tests import test_game_route_cubic_spline as cubic
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_projected_packet_draw import native_command

put,read,STACK=base.put,base.read,base.STACK
POINTS,OUTPUT=cubic.POINTS,0x30000
FRACTIONS,INDICES,POINT_SETS=cubic.FRACTIONS,cubic.INDICES,cubic.POINT_SETS
SAVED_PAIRS=((0,0xFFFFFFFF),(0x3F800000,0x40000000),(0x7FC12345,0xFF800000),
    (0x80000000,1),(0x89ABCDEF,0x01234567))


def fixture(values=POINT_SETS[1],fraction=0x3F000000,index=0,phase=0,alias=0,point_alias=0):
    m,args=cubic.fixture(values,fraction,index,phase)
    m.update({OUTPUT+i:0xA5 for i in range(32)})
    at=POINTS if not point_alias else STACK+phase+(-24 if point_alias==1 else -16 if point_alias==2 else 8)
    for i,v in enumerate(values):put(m,at+i*4,v)
    out=OUTPUT
    if 1<=alias<=4:out=at+(alias-1)*4
    elif alias>=5:out=STACK+phase+(-24,-20,-16,-8,8)[alias-5]
    return m,((at-((index&0xFFFFFFFF)<<2))&0xFFFFFFFF,index&0xFFFFFFFF,fraction,out)


def derivative(values,fraction):
    c,q,l=cubic.coefficients(values)
    return base.add(base.mul(base.add(base.mul(base.mul(c,base.bits(3.)),fraction),base.add(q,q)),fraction),l)


def reference(initial,args,pair,phase=0):
    m=dict(initial);put(m,STACK+phase-24,(pair[1]<<32)|pair[0],8)
    at=(args[0]+(args[1]<<2))&0xFFFFFFFF;values=[read(m,at+i*4) for i in range(4)]
    c,q,l=cubic.coefficients(values);value=cubic.evaluate(values,args[2]);slope=derivative(values,args[2])
    put(m,STACK+phase-16,c);put(m,STACK+phase-8,l);put(m,args[3],slope)
    return m,value,slope,(read(m,STACK+phase-20),read(m,STACK+phase-24))


class DerivativeOracle(cubic.CubicOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY):
        self.entry_sp,self.output=STACK+phase,args[3]
        super().__init__(words,memory,args,phase,entry)

    def put(self,at,value,n):
        super().put(at,value,n)
        # A forged guest output may overwrite one word of the saved FR=0 pair.
        if self.own_instruction and n==4 and at==self.output:
            if at==self.entry_sp-24:self.saved_f[1]=value&0xFFFFFFFF
            elif at==self.entry_sp-20:self.saved_f[0]=value&0xFFFFFFFF

    def run(self):
        original=list(self.saved_f);self.saved_f[:2]=self.f[20:22]
        try:return super().run()
        finally:self.saved_f=original


def controls():
    b=source.SELECTED
    value='    value = ((cubic * fraction + quadratic) * fraction + linear) * fraction + points[index + 1];\n'
    slope='    *slope = (cubic * 3.0f * fraction + (quadratic + quadratic)) * fraction + linear;\n'
    if b.count(value+slope)!=1:raise ValueError('Unknown derivative output order')
    return {
        'wrong-window':b.replace('points[index + 3]','points[index + 4]'),
        'wrong-half':b.replace('-0.5f * points[index]','-0.25f * points[index]'),
        'wrong-basis':b.replace('1.5f * points','1.25f * points'),
        'wrong-quadratic':b.replace('-2.5f * points','-2.0f * points'),
        'missing-value-fraction':b.replace('+ linear) * fraction + points','+ linear) + points'),
        'wrong-slope-factor':b.replace('cubic * 3.0f','cubic * 2.0f'),
        'wrong-output-stride':b.replace('    *slope =','    slope[1] ='),
        'missing-store':b.replace(slope,''),
        'late-value':b.replace(value+slope,slope+value),
        'reassociated':b.replace('((half + 1.5f * points[index + 1]) + -1.5f * points[index + 2])',
            '(half + (1.5f * points[index + 1] + -1.5f * points[index + 2]))'),
    }


def native_case(values,fraction,index,alias=0):
    return '{{'+','.join('0x%Xu'%v for v in values)+'},0x%Xu,%d,%d,0x%Xu,0x%Xu}'%(
        fraction,index,alias,cubic.evaluate(values,fraction),derivative(values,fraction))


NATIVE=r'''#include <ultra64.h>
struct Case{u32 values[4],fraction;s32 index;u32 alias,value,slope;};
static const struct Case cases[]={ROWS};static f32 points[32],before[32],out[4];
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
f32 func_150498A4(f32*,s32,f32,f32*);
static int run(void){u32 i,j,result,expected;f32*tgt,t;
 if(sizeof(void*)!=4)return 29;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 for(j=0;j<32;j++)points[j]=real(0xA5A5A5A5u);for(j=0;j<4;j++){points[8+j]=real(cases[i].values[j]);out[j]=real(0xA5A5A5A5u);}
 for(j=0;j<32;j++)before[j]=points[j];tgt=cases[i].alias?points+7+cases[i].alias:out;
 result=word(func_150498A4(points+8-cases[i].index,cases[i].index,real(cases[i].fraction),tgt));
 if(!same(result,cases[i].value)||!same(word(*tgt),cases[i].slope))return 23;
 for(j=0;j<32;j++){expected=cases[i].alias&&j==7+cases[i].alias?cases[i].slope:word(before[j]);
 if(j==7+cases[i].alias&&cases[i].alias){if(!same(word(points[j]),expected))return 23;}
 else if(word(points[j])!=expected)return 23;}
 for(j=0;j<4;j++){expected=!cases[i].alias&&j==0?cases[i].slope:0xA5A5A5A5u;if(!same(word(out[j]),expected))return 23;}
 }
 points[0]=0.f;points[1]=1.f;points[2]=2.f;points[3]=3.f;
 for(i=0;i<65536;i++){t=(f32)((s32)i-32768)/32768.f;
 result=word(func_150498A4(points,0,t,out));if(result!=word(1.f+t)||word(out[0])!=word(1.f))return 23;}
 return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class RouteSplineDerivativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=list(struct.unpack_from('>62I',cls.rom,source.ROM))
        data,functions=source.link_owner(cls.root,cls.out,cls.padded,source.OWNER);f=functions[source.FUNCTION]
        cls.fixed=list(struct.unpack_from('>62I',data,f['value']))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,pair=None,bodies=None,entry=source.ENTRY):
        models=[]
        for words in bodies or (self.words,self.fixed,self.truth):
            m=DerivativeOracle(words,memory,args,phase,entry)
            if pair is not None:m.f[20:22]=pair
            expected,value,slope,restored=reference(memory,args,tuple(m.f[20:22]),phase)
            m.run();self.assertTrue(cubic.same(m.f[0],value));self.assertTrue(cubic.same(read(m.memory,args[3]),slope))
            actual=dict(m.memory)
            for at in (STACK+phase-16,STACK+phase-8,args[3]):
                if cubic.nan(read(expected,at)):
                    self.assertTrue(cubic.nan(read(actual,at)));put(actual,at,read(expected,at))
            self.assertEqual(actual,expected);self.assertFalse(m.calls);self.assertEqual(m.f[22:],m.saved_f[2:])
            for value,wanted in zip(m.f[20:22],restored):self.assertTrue(cubic.same(value,wanted))
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual(base.state(models[1]),base.state(models[2]));self.assertEqual(models[1].trace,models[2].trace)
        return models

    def test_01_complete_guest_aliases_frame_and_identity_lineage(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(62,32,45,1))
        self.assertEqual(self.fixed,self.truth);seen=set();count=0
        for values,fraction,index,phase in itertools.product(POINT_SETS,FRACTIONS,INDICES,(0,8)):
            memory,args=fixture(values,fraction,index,phase);models=self.compare(memory,args,phase);seen.update(models[0].visits);count+=1
        for alias,values,fraction,index,phase in itertools.product(range(1,10),POINT_SETS[:7],FRACTIONS[5:11],(-1,0),(0,8)):
            memory,args=fixture(values,fraction,index,phase,alias);self.compare(memory,args,phase);count+=1
        for point_alias,alias,fraction,index,phase in itertools.product(range(1,4),range(10),(0,0x3F000000,0x3F800000,0xBF000000),(-1,0),(0,8)):
            memory,args=fixture(phase=phase,alias=alias,point_alias=point_alias,index=index,fraction=fraction)
            self.compare(memory,args,phase);count+=1
        for pair,alias,point_alias,phase in itertools.product(SAVED_PAIRS,range(10),range(4),(0,8)):
            memory,args=fixture(phase=phase,alias=alias,point_alias=point_alias);self.compare(memory,args,phase,pair);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+248,4)))
        source.cubic.checked_object(self.obj)
        self.receipt('guest',three_way_cases=count,all62_words_executed=True,all_private_and_public_bytes=True,
            saved_FR0_high_odd_low_even_order=True,saved_pair_patterns=len(SAVED_PAIRS),guest_output_aliases=9,
            saved_pair_output_alias_may_intentionally_corrupt_F20=True,raw_NaN_class_not_payload=True,
            normalized_retail_full_state=True,cubic_raw_neighbor_unchanged=True)

    def test_02_native32_O2_O0_UBSan_all_fraction_steps_and_controls(self):
        rows=[native_case(v,f,i) for v,f,i in itertools.product(POINT_SETS,FRACTIONS,(-4,-1,0,1,4))]
        rows.extend(native_case(v,f,0,alias) for v,f,alias in itertools.product(POINT_SETS,FRACTIONS[5:9],range(1,5)))
        harness=self.out/'native-driver.c';harness.write_text(NATIVE.replace('ROWS',','.join(rows)));exits={}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            self.assertIn('return value;',body)
            unit=self.out/('native-'+name+'.c');unit.write_text('#include <ultra64.h>\n'+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr);exits[name]=subprocess.run([str(exe)],capture_output=True,timeout=120).returncode
            self.assertEqual(exits[name],status,name)
        self.receipt('native',cases_per_profile=len(rows)+65536,all65536_fraction_steps=True,UBSan=True,
            valid_input_output_float_aliases=4,all_input_output_canaries=True,private_stack_aliases_excluded=True,
            NaN_class_not_payload=True,controls=len(controls()),exits=exits)

    def test_03_effective_guest_controls_change_return_or_publication(self):
        witnesses={}
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,'#include <ultra64.h>\n'+body,'negative-'+name)
            self.assertFalse(diagnostics);data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            for case,(values,fraction,alias) in enumerate(itertools.product(POINT_SETS,FRACTIONS,range(5))):
                memory,args=fixture(values,fraction,alias=alias);m=DerivativeOracle(words,memory,args)
                expected,value,slope,_=reference(memory,args,tuple(m.f[20:22]));m.run()
                if not cubic.same(m.f[0],value) or not cubic.same(read(m.memory,args[3]),slope):witnesses[name]=case;break
            else:self.fail('Ineffective derivative control: '+name)
        self.receipt('controls',observable_value_or_slope_witnesses=witnesses,controls=len(witnesses),not_private_offsets_or_crashes=True)

    def test_04_independent_original_raw_padded_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-derivative',source.raw_text(self.root/'conker/asm/76C90.s'),source.FUNCTION)
        count=0
        for placement,entry in enumerate((source.ENTRY,0x16218004,0x18FFF000)):
            bodies=[]
            for label,obj in (('original',original),('raw',self.obj),('padded',self.padded)):
                if label!='original':
                    text,functions,rel=source.parse_object(obj);f=functions[source.FUNCTION]
                    emitted,missing=emit_function(text,f,rel,source.FUNCTION,{});self.assertFalse(missing)
                    path=self.out/('rebase-%s-%d.s'%(label,placement));path.write_text(emitted);obj=path.with_suffix('.o')
                    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(obj),str(path)],check=True,capture_output=True)
                ld=self.out/('rebase-%s-%d.ld'%(label,placement));elf=ld.with_suffix('.elf')
                ld.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry)
                subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',source.FUNCTION,'-o',str(elf),str(obj)],check=True,capture_output=True)
                bodies.append(list(struct.unpack_from('>62I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);source.normalization_proof(bodies[1],bodies[0])
            for alias,fraction,index,phase in itertools.product(range(10),(0,0x3F000000,0x3F800000),(-1,0),(0,8)):
                memory,args=fixture(fraction=fraction,index=index,phase=phase,alias=alias)
                self.compare(memory,args,phase,bodies=(bodies[1],bodies[2],bodies[0]),entry=entry);count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,zero_bindings=True,actual_padded_slot_exact=True)

    def test_05_fault_prefixes_and_pair_restore_order(self):
        count=0
        for alias,point_alias,phase in itertools.product(range(10),range(4),(0,8)):
            memory,args=fixture(alias=alias,point_alias=point_alias,phase=phase)
            models=self.compare(memory,args,phase,pair=(0x3F800000,0x40000000))
            for fault in range(models[2].all_accesses):
                halted=[]
                for words in (self.words,self.fixed,self.truth):
                    m=DerivativeOracle(words,memory,args,phase);m.f[20:22]=(0x3F800000,0x40000000);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    halted.append(m)
                self.assertEqual(halted[0].memory,halted[2].memory)
                self.assertEqual(base.state(halted[1]),base.state(halted[2]));self.assertEqual(halted[1].trace,halted[2].trace);count+=1
        self.receipt('faults',prefixes=count,fixtures=80,raw_finite_memory_prefixes=True,
            raw_read_schedule_and_fault_register_state_not_claimed=True,normalized_retail_full_fault_state=True,
            aligned_atomic_pair_word_model_not_hardware_MMU=True)

    def test_06_complete_live_C_caller_with_real_derivative(self):
        from tools.tests import test_game_actor_route_snap as parent
        helpers={}
        for entry,count in parent.HELPERS.items():helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,self.rom,entry-0x14FD2B50)))
        parent_words=struct.unpack_from('>118I',self.rom,parent.source.ROM);count=0
        for actor,steps,mode,angle,alias,phase in itertools.product((0,3),(0,2),(0,128),(0,0x8000,0xFFFF),(0,1),(0,8)):
            p=(actor,steps,-1,mode,angle,0x43360B61,0);memory,args=parent.fixture(p,alias);expected,calls=parent.reference(memory,args,angle);models=[]
            for derivative_words in (self.words,self.fixed,self.truth):
                connected=dict(helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+248,4),derivative_words))
                m=parent.RouteOracle(parent_words,memory,args,angle,connected,phase).run()
                self.assertEqual((parent.public(m.memory),m.calls),(parent.public(expected),calls));self.assertEqual(m.f[20:],m.saved_f)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                models.append(m)
            self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
        self.receipt('caller',three_way_complete_parent_cases=count,parent_words=118,connected_helper_words=555,
            sole_bounded_provider='u16 atan',caller_source_and_prototypes_unchanged=True,production_vector_still_stub=True,gameplay_not_claimed=True)

    def test_07_words_guards_inputs_and_alias_identity_gates_fail_closed(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,_=source.checked_object(self.obj)
        for i in range(62):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'parse_object',return_value=(text,functions,{f['value']:[('R_MIPS_HI16','unexpected')]})):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        for replacement in (0x4480A000,0xD7B60008):
            bad=list(self.truth);bad[57]=replacement
            memory,args=fixture();m=DerivativeOracle(bad,memory,args);m.f[20:22]=(0x40000000,0x40400000)
            with self.assertRaises(AssertionError):m.run()
        early=list(self.truth);early[53],early[57]=early[57],early[53]
        memory,args=fixture(alias=6);m=DerivativeOracle(early,memory,args);m.f[20:22]=(0x40000000,0x40400000)
        with self.assertRaises(AssertionError):m.run()
        reassociated=list(self.truth);reassociated[21]=0x46000000|(6<<16)|(8<<11)|(10<<6)
        reassociated[22]=0x46000000|(10<<16)|(14<<11)|(8<<6)
        with self.assertRaises(ValueError):source.normalization_proof(reassociated,self.truth)
        original=source.lineage(self.truth)
        positions={kind:[i for i,x in enumerate(original['events']) if predicate(x)] for kind,predicate in {
            'save':lambda x:x[0]=='save-pair','restore':lambda x:x[0]=='restore-pair',
            'read':lambda x:x[0]=='read' and x[1][0]!='stack',
            'private':lambda x:x[0]=='store-float' and x[1][0]=='stack',
            'public':lambda x:x[0]=='store-float' and x[1][0]!='stack'}.items()}
        for a,b in ((positions['save'][0],positions['read'][0]),(positions['read'][-1],positions['private'][0]),
                (positions['private'][-1],positions['public'][0]),(positions['public'][0],positions['restore'][0])):
            crossed=copy.deepcopy(original);events=crossed['events'];events[a],events[b]=events[b],events[a]
            with patch.object(source,'lineage',side_effect=[crossed,original]):
                with self.assertRaisesRegex(ValueError,'potentially aliased'):source.normalization_proof(self.words,self.truth)
        missing=copy.deepcopy(original);missing['identity'].pop()
        with patch.object(source,'lineage',side_effect=[missing,original]):
            with self.assertRaisesRegex(ValueError,'copy/NOP'):source.normalization_proof(self.words,self.truth)
        reader=csv.DictReader(io.StringIO(source.raw_read(self.out/'qualified-guards.csv').decode()));rows=list(reader)
        for guard in source.owner_guards(raw,self.truth):
            bad=[dict(r,expected='0x%08X'%(int(r['expected'],16)^1)) if
                (r['filename'],r['function'],r['offset'])==(guard['filename'],guard['function'],guard['offset']) else r for r in rows]
            path=self.out/'bad-guard.csv'
            with path.open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=reader.fieldnames);writer.writeheader();writer.writerows(bad)
            with self.assertRaisesRegex(ValueError,source.FUNCTION):source.emit_padded_assembly(self.obj,self.root/'conker/asm/76C90.s',filename=source.OWNER,word_patches_path=path)
        with source.historical_view(self.root,self.out):
            reader=Path.read_bytes
            for index,p in enumerate(source.INPUTS):
                for path in (self.root/p,self.out/('before-%02d'%index)):
                    with patch.object(Path,'read_bytes',lambda x:reader(x)+b'\n' if x==path else reader(x)):
                        with self.assertRaises(ValueError):source.freeze(self.root,self.out)
            with self.assertRaisesRegex(RuntimeError,'cannot nest'):
                with source.historical_view(self.root,self.out):pass
        self.assertEqual(source.verify(self.root,self.out),self.stage)
        if self.stage=='after':self.assertEqual(source.audit(self.root,self.out)['functions'],6057)
        self.receipt('fail-closed',raw_words=62,guards=45,unexpected_binding=True,reassociation=True,
            actual_F20_ABI_mutants=3,alias_ordering_mutations=4,identity_budget_mutations=1,live_and_snapshot_inputs=28,stage=self.stage)


if __name__=='__main__':unittest.main()
