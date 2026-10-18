"""Rounded cubic DAG, closed schedule, private homes, native ABI and live caller."""
import csv
import copy
import io
import itertools
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch

from tools.experiments import game_route_cubic_spline as source
from tools.tests import game_view_point_projection_oracle as base
from tools.tests import test_game_view_list_setup as assembly
from tools.tests.test_game_projected_packet_draw import native_command
from tools.experiments.alternative_source_draft_word_screen import emit_function
from tools.experiments.game_actor_classifier_candidates import sections

put,read,STACK=base.put,base.read,base.STACK
POINTS=0x20000
FRACTIONS=(0,0x80000000,1,0x80000001,0x00800000,0x3E800000,0x3F000000,0x3F800000,
    0xBF000000,0x40000000,0xC0200000,0x7F7FFFFF,0xFF7FFFFF,0x7F800000,0xFF800000,0x7FC12345)
INDICES=(-4,-1,0,1,7,0x40000001,-0x40000000,0x7FFFFFFF)
POINT_SETS=[tuple(map(base.bits,p)) for p in ((0.,0.,0.,0.),(1.,2.,3.,4.),(-2.,16777216.,16777216.,0.),
    (-32768.,32767.,0.,-1.),(1e20,-1e20,1e-20,-1e-20),(-0.,0.,-0.,0.),(.25,-2.5,7.75,-13.125))]
POINT_SETS.extend(tuple(v if j==axis else base.bits(float(j+1)) for j in range(4))
    for axis,v in itertools.product(range(4),FRACTIONS))


def nan(v):return v&0x7FFFFFFF>0x7F800000
def same(a,b):return a==b or nan(a) and nan(b)


def fixture(values=POINT_SETS[1],fraction=0x3F000000,index=0,phase=0,alias=0):
    m={STACK+i:(i*17+0xA5)&255 for i in range(-0x400,0x400)}
    m.update({POINTS+i:0xA5 for i in range(-32,96)})
    at=POINTS if not alias else STACK+phase+(8 if alias==1 else -12)
    for i,v in enumerate(values):put(m,at+i*4,v)
    return m,((at-((index&0xFFFFFFFF)<<2))&0xFFFFFFFF,index&0xFFFFFFFF,fraction)


def coefficients(values):
    p0,p1,p2,p3=values;b=base.bits;half=base.mul(b(-.5),p0)
    cubic=base.add(base.mul(p3,b(.5)),base.add(base.add(half,base.mul(b(1.5),p1)),base.mul(b(-1.5),p2)))
    quadratic=base.add(base.mul(p3,b(-.5)),base.add(base.add(p0,base.mul(b(-2.5),p1)),base.add(p2,p2)))
    linear=base.add(base.mul(p2,b(.5)),half)
    return cubic,quadratic,linear


def evaluate(values,fraction):
    cubic,quadratic,linear=coefficients(values)
    return base.add(base.mul(base.add(base.mul(base.add(base.mul(cubic,fraction),quadratic),fraction),linear),fraction),values[1])


def reference(initial,args,phase=0):
    m=dict(initial);put(m,STACK+phase+8,args[2])
    at=(args[0]+(args[1]<<2))&0xFFFFFFFF;values=[read(m,at+i*4) for i in range(4)]
    _,quadratic,linear=coefficients(values)
    put(m,STACK+phase-12,quadratic);put(m,STACK+phase-8,linear)
    return m,evaluate(values,args[2])


class CubicOracle(base.PointProjectionOracle):
    def __init__(self,words,memory,args,phase=0,entry=source.ENTRY):
        self.trace=[]
        super().__init__(words,memory,args,[],phase,entry)

    def get(self,at,n):
        value=super().get(at,n)
        if self.own_instruction:self.trace.append(('R',at,n,value))
        return value

    def put(self,at,value,n):
        super().put(at,value,n)
        if self.own_instruction:self.trace.append(('W',at,n,value&((1<<(8*n))-1)))

    def record_call(self,target):raise AssertionError('Cubic spline may not call a provider')
    def hook(self,target):raise AssertionError('Cubic spline has no opaque helpers')


def controls():
    b=source.SELECTED
    return {
        'wrong-window':b.replace('points[index + 3]','points[index + 4]'),
        'wrong-half':b.replace('-0.5f * points[index]','-0.25f * points[index]'),
        'wrong-basis':b.replace('1.5f * points','1.25f * points'),
        'wrong-quadratic':b.replace('-2.5f * points','-2.0f * points'),
        'wrong-linear':b.replace('linear = points[index + 2] * 0.5f','linear = points[index + 2] * 0.25f'),
        'wrong-final-point':b.replace('* fraction + points[index + 1];','* fraction + points[index];'),
        'missing-last-fraction':b.replace('+ linear) * fraction +','+ linear) +'),
        'reassociated':b.replace('((half + 1.5f * points[index + 1]) + -1.5f * points[index + 2])',
            '(half + (1.5f * points[index + 1] + -1.5f * points[index + 2]))'),
    }


def native_case(values,fraction,index):
    return '{{'+','.join('0x%Xu'%v for v in values)+'},0x%Xu,%d,0x%Xu}'%(fraction,index,evaluate(values,fraction))


NATIVE=r'''#include <ultra64.h>
struct Case{u32 values[4],fraction;s32 index;u32 expected;};
static const struct Case cases[]={ROWS};static f32 points[32],before[32];
static f32 real(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
static u32 word(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static int same(u32 a,u32 b){return a==b||((a&0x7FFFFFFFu)>0x7F800000u&&(b&0x7FFFFFFFu)>0x7F800000u);}
f32 func_150497E0(f32*,s32,f32);
static int run(void){u32 i,j,result;f32 t;
 if(sizeof(void*)!=4)return 29;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
 for(j=0;j<32;j++)points[j]=real(0xA5A5A5A5u);for(j=0;j<4;j++)points[8+j]=real(cases[i].values[j]);
 for(j=0;j<32;j++)before[j]=points[j];
 result=word(func_150497E0(points+8-cases[i].index,cases[i].index,real(cases[i].fraction)));
 if(!same(result,cases[i].expected))return 23;
 for(j=0;j<32;j++)if(word(points[j])!=word(before[j]))return 23;
 }
 points[0]=0.f;points[1]=1.f;points[2]=2.f;points[3]=3.f;
 for(i=0;i<65536;i++){t=(f32)((s32)i-32768)/32768.f;
 if(word(func_150497E0(points,0,t))!=word(1.f+t))return 23;}
 return 0;}
void _start(void){int r=run();__asm__ volatile("int $0x80"::"a"(1),"b"(r));__builtin_unreachable();}
'''


class RouteCubicSplineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(__file__).resolve().parents[2];cls.out=cls.root/source.BUILD;cls.stage=source.verify(cls.root,cls.out)
        with source.historical_view(cls.root,cls.out):cls.obj,cls.padded,cls.words,cls.row=source.qualify(cls.root,cls.out)
        cls.rom=source.raw_read(cls.root/'conker/conker.us.bin');cls.truth=list(struct.unpack_from('>49I',cls.rom,source.ROM))
        data,functions=source.link_owner(cls.root,cls.out,cls.padded,source.OWNER);f=functions[source.FUNCTION]
        cls.fixed=list(struct.unpack_from('>49I',data,f['value']))

    def receipt(self,name,**data):(self.out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')

    def compare(self,memory,args,phase=0,bodies=None,entry=source.ENTRY):
        expected,value=reference(memory,args,phase);models=[]
        for words in bodies or (self.words,self.fixed,self.truth):
            m=CubicOracle(words,memory,args,phase,entry).run();self.assertTrue(same(m.f[0],value))
            actual=dict(m.memory)
            for at in (STACK+phase-12,STACK+phase-8):
                if nan(read(expected,at)):
                    self.assertTrue(nan(read(actual,at)));put(actual,at,read(expected,at))
            self.assertEqual(actual,expected);self.assertFalse(m.calls);self.assertEqual(m.f[20:],m.saved_f)
            for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
            models.append(m)
        self.assertEqual(base.state(models[1]),base.state(models[2]));self.assertEqual(models[1].trace,models[2].trace)
        return models

    def test_01_guest_complete_slot_private_homes_and_closed_lineage(self):
        self.assertEqual((self.row['words'],self.row['frame'],self.row['differences'],self.row['neighbors']),(49,16,34,1))
        self.assertEqual(self.fixed,self.truth);seen=set();count=0
        for values,fraction,index,phase in itertools.product(POINT_SETS,FRACTIONS,INDICES,(0,8)):
            memory,args=fixture(values,fraction,index,phase);models=self.compare(memory,args,phase)
            seen.update(models[0].visits);count+=1
        for alias,fraction,index,phase in itertools.product((1,2),(0,0x3F000000,0x3F800000),(-1,0,0x40000001),(0,8)):
            memory,args=fixture(POINT_SETS[1],fraction,index,phase,alias);self.compare(memory,args,phase);count+=1
        self.assertEqual(seen,set(range(source.ENTRY,source.ENTRY+196,4)))
        self.assertEqual(sorted(self.row['proof']['operation_bijection']),list(range(49)))
        self.receipt('guest',three_way_cases=count,all49_words_executed=True,all_private_homes_checked=True,
            guest_index_wrap_and_argument_coefficient_aliases=True,raw_NaN_class_not_payload=True,
            normalized_retail_full_state=True,closed_49_operation_bijection=True,no_FP_reassociation=True)

    def test_02_native32_O2_O0_UBSan_all_fraction_steps_and_controls(self):
        rows=[native_case(v,f,i) for v,f,i in itertools.product(POINT_SETS,FRACTIONS,(-4,-1,0,1,4))]
        harness=self.out/'native-driver.c';harness.write_text(NATIVE.replace('ROWS',','.join(rows)));exits={}
        for name,opt,body,status in [('O2','-O2',source.SELECTED,0),('O0','-O0',source.SELECTED,0)]+[
                (n,'-O2',b,23) for n,b in controls().items()]:
            self.assertTrue('return value;' in body)
            unit=self.out/('native-'+name+'.c');unit.write_text('#include <ultra64.h>\n'+body);exe=unit.with_suffix('')
            c=subprocess.run([*native_command(opt),'-mstackrealign',str(unit),str(harness),'-o',str(exe)],cwd=self.root,capture_output=True,text=True)
            self.assertEqual(c.returncode,0,c.stderr);exits[name]=subprocess.run([str(exe)],capture_output=True,timeout=120).returncode
            self.assertEqual(exits[name],status,name)
        self.receipt('native',cases_per_profile=len(rows)+65536,all65536_fraction_steps=True,UBSan=True,
            complete_input_canaries=True,valid_native_indices_only=True,NaN_class_not_payload=True,controls=len(controls()),exits=exits)

    def test_03_guest_controls_change_real_return_value(self):
        witnesses={}
        for name,body in controls().items():
            obj,diagnostics=source.compile_owner(self.root,self.out,'#include <ultra64.h>\n'+body,'negative-'+name)
            self.assertFalse(diagnostics);data,functions=source.link_owner(self.root,self.out,obj,source.OWNER);f=functions[source.FUNCTION]
            words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
            for case,(values,fraction) in enumerate(itertools.product(POINT_SETS,FRACTIONS)):
                memory,args=fixture(values,fraction);_,expected=reference(memory,args)
                m=CubicOracle(words,memory,args).run()
                if not same(m.f[0],expected):witnesses[name]=case;break
            else:self.fail('Ineffective cubic control: '+name)
        self.receipt('controls',observable_return_witnesses=witnesses,controls=len(witnesses),not_instruction_offset_or_crash=True)

    def test_04_independent_original_raw_padded_links(self):
        context=type('OriginalContext',(),dict(root=self.root,out=self.out))
        original=assembly.ViewListSetupTests.original.__func__(context,'original-cubic',source.raw_text(self.root/'conker/asm/76C90.s'),source.FUNCTION)
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
                bodies.append(list(struct.unpack_from('>49I',sections(elf)['.text'][1])))
            self.assertEqual(bodies[0],bodies[2]);source.normalization_proof(bodies[1],bodies[0])
            for values,fraction,index,phase in itertools.product(POINT_SETS[:4],(0,0x3F000000,0x3F800000),(-4,0,0x40000001),(0,8)):
                memory,args=fixture(values,fraction,index,phase);self.compare(memory,args,phase,(bodies[1],bodies[2],bodies[0]),entry);count+=1
        self.receipt('rebases',independent_links=9,three_way_cases=count,zero_bindings=True,actual_padded_slot_exact=True)

    def test_05_fault_prefixes_and_explicit_raw_read_permutation(self):
        count=0
        for alias,phase in itertools.product((0,1,2),(0,8)):
            memory,args=fixture(POINT_SETS[1],phase=phase,alias=alias)
            models=self.compare(memory,args,phase)
            if not alias:
                traces=[[at-POINTS for kind,at,n,v in m.trace if kind=='R' and POINTS<=at<POINTS+16] for m in models]
                self.assertEqual(traces,[[0,8,4,12],[0,4,8,12],[0,4,8,12]])
            for fault in range(models[2].all_accesses):
                halted=[]
                for words in (self.words,self.fixed,self.truth):
                    m=CubicOracle(words,memory,args,phase);m.access_fault=fault
                    with self.assertRaises(base.faults.AccessBoundary):m.run()
                    halted.append(m)
                self.assertEqual(halted[0].memory,halted[2].memory)
                self.assertEqual(base.state(halted[1]),base.state(halted[2]));self.assertEqual(halted[1].trace,halted[2].trace);count+=1
        self.receipt('faults',prefixes=count,raw_memory_prefixes_finite=True,raw_read_order_and_fault_register_state_not_claimed=True,
            normalized_retail_complete_fault_state=True,hardware_FCSR_not_claimed=True)

    def test_06_live_C_parent_with_actual_cubic_body(self):
        from tools.tests import test_game_actor_route_snap as parent
        helpers={}
        for entry,count in parent.HELPERS.items():helpers.update(zip(range(entry,entry+count*4,4),struct.unpack_from('>%dI'%count,self.rom,entry-0x14FD2B50)))
        parent_words=struct.unpack_from('>118I',self.rom,parent.source.ROM);count=0
        for actor,steps,mode,angle,alias,phase in itertools.product((0,3),(0,2),(0,128),(0,0x8000,0xFFFF),(0,1),(0,8)):
            p=(actor,steps,-1,mode,angle,0x43360B61,0);memory,args=parent.fixture(p,alias);expected,calls=parent.reference(memory,args,angle)
            models=[]
            for cubic in (self.words,self.fixed,self.truth):
                connected=dict(helpers);connected.update(zip(range(source.ENTRY,source.ENTRY+196,4),cubic))
                m=parent.RouteOracle(parent_words,memory,args,angle,connected,phase).run()
                self.assertEqual((parent.public(m.memory),m.calls),(parent.public(expected),calls))
                self.assertEqual(m.f[20:],m.saved_f)
                for r in (*range(16,24),28,29,30,31):self.assertEqual(m.r[r],m.before[r])
                models.append(m)
            self.assertEqual(base.state(models[1]),base.state(models[2]));count+=1
        self.receipt('caller',three_way_complete_parent_cases=count,parent_words=118,connected_helper_words=555,
            sole_bounded_provider='u16 atan',caller_source_and_prototype_unchanged=True,
            production_vectors_and_derivative_still_stubs=True,gameplay_not_claimed=True)

    def test_07_words_guards_bindings_inputs_and_lineage_fail_closed(self):
        text,functions,rel=source.parse_object(self.obj);f=functions[source.FUNCTION];raw,_=source.checked_object(self.obj)
        for i in range(49):
            bad=bytearray(text);bad[f['value']+i*4]^=1
            with patch.object(source,'parse_object',return_value=(bytes(bad),functions,rel)):
                with self.assertRaises(ValueError):source.checked_object(self.obj)
        with patch.object(source,'parse_object',return_value=(text,functions,{f['value']:[('R_MIPS_HI16','unexpected')]})):
            with self.assertRaises(ValueError):source.checked_object(self.obj)
        reassociated=list(self.truth)
        reassociated[20]=0x46000000|(6<<16)|(8<<11)|(10<<6)
        reassociated[21]=0x46000000|(10<<16)|(14<<11)|(8<<6)
        with self.assertRaises(ValueError):source.normalization_proof(reassociated,self.truth)
        original=source.lineage(self.truth)
        for kind in ('store-word','store-float'):
            crossed=copy.deepcopy(original);events=crossed['events']
            public=[i for i,e in enumerate(events) if e[0]=='read' and e[1][0]!='stack']
            store=next(i for i,e in enumerate(events) if e[0]==kind)
            load=public[-1] if kind=='store-float' else public[0]
            events[load],events[store]=events[store],events[load]
            with patch.object(source,'lineage',side_effect=[crossed,original]):
                with self.assertRaisesRegex(ValueError,'crosses'):source.normalization_proof(self.words,self.truth)
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
        self.receipt('fail-closed',raw_words=49,expected_word_guards=34,unexpected_binding=True,
            reassociation_rejected=True,live_and_snapshot_inputs=28,stage=self.stage)


if __name__=='__main__':unittest.main()
