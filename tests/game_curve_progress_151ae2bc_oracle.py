"""Curve progress, caller homes, live table reloads and bounded IEEE-single checks.

Numerical cases use nontrapping single round-to-nearest, not hardware FCSR or
legacy NaN payload rules. Exact retail/normalized words establish scheduling.
Raw C is checked for public memory effects, without literal register/fault claims.
"""
from dataclasses import dataclass,replace
import itertools,json,math,struct,subprocess
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_view_fov_transfer import fp
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY,RESOURCE,KNOTS,ALTERNATE,OUTPUT,ACTOR,OWNER=0x151AE2BC,0x50000,0x70000,0x80000,0x90000,0xA0000,0xB0000
u32=lambda n:n&0xFFFFFFFF
@dataclass(frozen=True)
class Case:
    count:int=5
    height:int=bits(15.)
    pattern:int=0
    alias:int=0
    home_alias:int=0
    mutation:int=0
    phase:int=0
    x:int=bits(-7.)
    z:int=bits(11.)
def resource(c):return STACK+c.phase-64 if c.home_alias==1 else RESOURCE
def knots(c):return STACK+c.phase+4 if c.home_alias==2 else KNOTS
def output(c):return(OUTPUT,resource(c)+0x38,resource(c)+0x40,knots(c)+4,knots(c)+28,STACK+c.phase)[c.alias]
def levels(c):
    if c.pattern==0:return[bits(float(i*10))for i in range(256)]
    if c.pattern==1:return[bits(20.)for _ in range(256)]
    if c.pattern==2:return[bits(float(-i*10))for i in range(256)]
    if c.pattern==3:return[bits(float((i%3)*10))for i in range(256)]
    if c.pattern==4:return[0,0x80000000,0x7F800000,0xFF800000,0x7FC12345][0:]+[bits(float(i))for i in range(251)]
    return[0x7FC12345]*256
def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-256,256)}
    capacity=256 if c.home_alias==1 else max(c.count,3)
    for base,n in((resource(c),72),(knots(c),24*capacity),(ALTERNATE,24*capacity if c.mutation else 0),(OUTPUT-16,48)):
        for i in range(n):m[u32(base+i)]=(i*29+0x59)&255
    for i,v in enumerate(levels(c)[:capacity]):put(m,u32(knots(c)+24*i+4),v)
    if c.mutation:
        for i in range(capacity):put(m,ALTERNATE+24*i+4,bits(12. if c.mutation==1 else 10. if i%2 else 20.))
    put(m,resource(c)+0x38,knots(c));m[resource(c)+0x42]=c.count
    put(m,STACK+c.phase+0x10,c.z)
    return m
def reference(initial,c,home=None,out=None,res=None,x=None,height=None):
    m=dict(initial);home=STACK+c.phase if home is None else home
    out=output(c)if out is None else out;res=resource(c)if res is None else res
    x=c.x if x is None else x;height=c.height if height is None else height
    put(m,home,out);put(m,home+8,x)
    count=m[res+0x42];index=0;limit=count-1
    if limit>0:
        table=read(m,res+0x38)
        while index<limit:
            if floating(height)<=floating(read(m,u32(table+index*24+4))):break
            index+=1
    if index>=count-2:result=bits(1.)
    elif index==0:result=0
    else:
        if c.mutation:put(m,res+0x38,ALTERNATE)
        table=read(m,res+0x38);previous=read(m,u32(table+(index-1)*24+4));current=read(m,u32(table+index*24+4))
        fraction=fp(current,previous,'sub')
        if floating(fraction)!=0.:fraction=fp(fp(height,previous,'sub'),fraction,'div')
        else:fraction=0
        result=fp(fp(bits(float(index-1)),bits(float(count-3)),'div'),fp(fraction,bits(float(limit)),'div'),'add')
    put(m,out,result);return m
def cases():
    rows=[Case(n,bits(v))for n,v in itertools.product(range(256),(-1.,0.,10.,15.,9999.))]
    for n,p,y in itertools.product((0,1,2,3,4,5,7,255),range(6),(0,0x80000000,bits(-20.),bits(10.),bits(15.),bits(20.),0x7F800000,0xFF800000,0x7FC12345)):
        rows.append(Case(n,y,p))
    for alias,home,phase,mut in itertools.product(range(6),range(3),(0,8),range(3)):
        # Keep the artificial home/table overlap within a small scan. Caller
        # homes can alter the first knot or count before the first load.
        rows.append(Case(5,bits(15.),0,alias,home,mut,phase,x=bits(5.)))
    for n in(4,5,255):
        for y in(0x3F800001,bits(10.)-1,bits(10.)+1,bits(10000.)):
            rows.append(Case(n,y,x=0x7FC12345,z=0x80000000))
    return tuple(dict.fromkeys(rows))
class Oracle(FactoryOracle):
    def __init__(self,words,memory,c,entry=ENTRY,connected=None,arguments=None):
        self.reloads=0;self.curve=resource(c);self.c=c
        super().__init__(words,memory,c,entry=entry,s={},arguments=arguments or(output(c),resource(c),c.x,c.height,c.z),connected=connected)
        self.before=self.r[:];self.before_f=self.f[:]
    def get(self,p,n):
        if getattr(self,'own_instruction',False)and p==self.curve+0x38 and n==4:
            self.reloads+=1
            if self.reloads==2 and self.c.mutation:put(self.memory,p,ALTERNATE)
        return super().get(p,n)
    def execute(self,w):
        op,fmt,rt,fs,fd,fn=w>>26,(w>>21)&31,(w>>16)&31,(w>>11)&31,(w>>6)&31,w&63
        if op!=17 or fmt==8:return super().execute(w)
        if fmt==0:self.r[rt]=self.f[fs]
        elif fmt==4:self.f[fs]=self.r[rt]
        elif fmt==20 and fn==32:self.f[fd]=bits(float(signed(self.f[fs])))
        elif fmt==16:
            a,b=self.f[fs],self.f[rt]
            if fn in(0,1,2,3):self.f[fd]=fp(a,b,('add','sub','mul','div')[fn])
            elif fn==6:self.f[fd]=a
            elif fn==50:self.condition=floating(a)==floating(b)
            elif fn==62:self.condition=floating(a)<=floating(b)
            else:raise AssertionError(('foreign curve FP op',hex(w)))
        else:raise AssertionError(('foreign curve COP1',hex(w)))
        self.r[0]=0
    def record_call(self,t):
        assert t==ENTRY,hex(t);a=tuple(self.arguments(5));self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):raise AssertionError(('Unexpected curve helper',hex(t)))
def state(m):return(m.r,m.f,m.memory,m.hi,m.lo,m.condition,m.calls,m.events,m.trace,m.current_pc,m.delay_of,m.all_accesses,m.reloads)
def programs(core,q):
    truth=list(struct.unpack('>59I',(core.ROOT/'conker/conker.us.bin').read_bytes()[core.ROM:core.ROM+236]))
    normal=list(struct.unpack('>59I',q['normal']));raw=list(struct.unpack('>59I',q['raw']));assert normal==truth
    return truth,normal,raw
def guest(core,q):
    ps=programs(core,q);visited=set();count=0;mutated=0
    for c in cases():
        initial=fixture(c);wanted=reference(initial,c);ms=[]
        for k,p in enumerate(ps):
            m=Oracle(p,initial,c);m.run();assert m.memory==wanted,c
            assert m.r[16:24]==m.before[16:24]and m.r[28:31]==m.before[28:31]and m.f[20:]==m.before_f[20:],c
            if k<2:ms.append(m)
        assert state(ms[0])==state(ms[1]),c
        visited.update(ms[0].visits);count+=1;mutated+=bool(c.mutation and ms[0].reloads>1)
    missing=set(range(ENTRY,ENTRY+236,4))-visited;assert missing=={0x151AE380},list(map(hex,missing))
    prefixes=0
    for c in(Case(0),Case(2),Case(5,bits(-1.)),Case(),Case(5,bits(9999.)),Case(mutation=1),Case(mutation=2),Case(home_alias=1),Case(home_alias=2),Case(alias=5)):
        initial=fixture(c);full=Oracle(ps[0],initial,c);full.run()
        for cut in range(full.all_accesses):
            ms=[]
            for p in ps[:2]:
                m=Oracle(p,initial,c);m.cut=cut
                try:m.run()
                except AccessBoundary:pass
                else:raise AssertionError(('Missing curve fault cut',c,cut))
                ms.append(m)
            assert state(ms[0])==state(ms[1]);prefixes+=1
    return dict(cases=count,reachable_words=58,unreachable_words=['0x151AE380'],executed_fault_cuts=prefixes,
      live_table_mutation_cases=mutated,all_count_bytes=True,output_alias_layouts=6,home_alias_layouts=3,
      raw_C_public_memory_equal=True,normalized_literal_states_equal=True,raw_literal_fault_order_not_claimed=True,
      FP_model='bounded nontrapping IEEE single round-to-nearest; not hardware FCSR or legacy NaNs')
class PoisonCode(WindowCode):
    def __getitem__(self,pc):
        if pc==0x151AE154:
            self.owner.r[2]=self.owner.poison;self.owner.f[0]=self.owner.poison;self.owner.poison_hits+=1
        return super().__getitem__(pc)
def connected(core,q):
    rom=(core.ROOT/'conker/conker.us.bin').read_bytes();va=0x151AE134
    body=struct.unpack_from('>17I',rom,0x1DB5E4);assert body[6]==0x0D46B8AF and body[7]==0xE7A40010
    count=0;seen=set()
    for n,y,phase,poison in itertools.product((0,1,3,5,255),(bits(-1.),bits(15.),bits(9999.)),(0,8),(0,0xFFFFFFFF)):
        c=Case(n,y,phase=phase);initial=fixture(c)
        initial.update({ACTOR+i:(i*29+0x59)&255 for i in range(0x340)})
        initial.update({OWNER+i:(i*29+0x59)&255 for i in range(0xC0)})
        put(initial,ACTOR+0x31C,OWNER);put(initial,ACTOR+0x14,c.x);put(initial,ACTOR+0x18,c.height);put(initial,ACTOR+0x1C,c.z)
        put(initial,resource(c)+0x3C,bits(140.));put(initial,STACK+phase+0x34,resource(c));put(initial,STACK+phase+0x10,c.z)
        expected=reference(initial,c,out=OWNER+0xA0)
        for p in programs(core,q):
            code=dict(zip(range(ENTRY,ENTRY+236,4),p));m=Oracle(body,initial,c,va,code)
            m.r[16]=ACTOR;m.r[5]=resource(c);m.before=m.r[:];m.poison=poison;m.poison_hits=0;m.code=PoisonCode(m.code,m);m.code.ends=(va+68,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing curve caller boundary')
            assert m.memory==expected and m.calls==[(ENTRY,(OWNER+0xA0,resource(c),c.x,c.height,c.z))],c
            assert m.f[6]==read(expected,OWNER+0xA0)and m.r[5]==resource(c)
            assert m.poison_hits==1 and m.r[2]==poison and m.f[0]==poison
            seen.update(m.visits)
        count+=1
    assert all(va+4*i in seen for i in range(17))
    return dict(cases=count,body_variants=3,original_window_words=17,all_window_words_executed=True,
      stack_Z_delay_store=True,A2_X_home_preserved=True,output_reloaded_by_caller=True,integer_and_FP_return_poison_ignored=True,complete_parent_not_claimed=True)
def native(core,out):
    declarations,body=core.SELECTED.split('/* Locate',1);body='/* Locate'+body
    controls=dict(stub='void func_151AE2BC(f32 *output, CurveProgress1D92F0 *curve, f32 x, f32 height, f32 z){(void)output;(void)curve;(void)x;(void)height;(void)z;}',
      signed_count=body.replace('count = curve->count','count = (s8)curve->count'),
      strict_comparison=body.replace('height <= knot->value','height < knot->value'),
      wrong_stride=body.replace('knot++;','knot = (CurveKnot1D92F0 *)((u8 *)knot + 20);'),
      wrong_last=body.replace('index >= count - 2','index >= count - 1'),
      wrong_first=body.replace('*output = 0.0f','*output = 0.5f'),
      wrong_previous=body.replace('knot[-1]','knot[0]'),
      wrong_index_divisor=body.replace('(f32)(count - 3)','(f32)(count - 2)'),
      wrong_fraction_divisor=body.replace('fraction / (f32)(count - 1)','fraction / (f32)(count - 2)'),
      wrong_axis=body.replace('height <= knot->value','x <= knot->value'))
    assert all(v!=body for v in controls.values());rows=[]
    for c in cases():
        if c.alias or c.home_alias or c.mutation or c.phase or c.pattern>=4 or math.isnan(floating(c.height)):continue
        initial=fixture(c);result=read(reference(initial,c),output(c))
        if math.isnan(floating(result)):continue
        rows.append('{%du,%du,0x%Xu,0x%Xu,0x%Xu,0x%Xu}'%(c.count,c.pattern,c.height,c.x,c.z,result))
    code='#include <ultra64.h>\n'+declarations+'\n'
    code+='_Static_assert(sizeof(void*)==4,"native32");\n_Static_assert(sizeof(CurveKnot1D92F0)==24,"knot24");\n_Static_assert(__builtin_offsetof(CurveProgress1D92F0,count)==0x42,"count42");\n'
    for j,(_,b)in enumerate(dict(selected=body,**controls).items()):code+=b.replace('func_151AE2BC(','candidate_%d('%j)+'\n'
    code+='typedef struct{u32 count,pattern,height,x,z,result;}Case;\nstatic const Case cases[]={'+',\n'.join(rows)+'};\n'
    code+='static void(*candidates[])(f32*,CurveProgress1D92F0*,f32,f32,f32)={'+','.join('candidate_%d'%j for j in range(len(controls)+1))+'};\n'
    code+='''static CurveProgress1D92F0 curve;static CurveKnot1D92F0 knots[256];static u8 savedCurve[sizeof(curve)],savedKnots[sizeof(knots)];
    static union{u32 u[3];f32 f[3];}output;
    static f32 asFloat(u32 u){union{u32 u;f32 f;}v;v.u=u;return v.f;}
    static int run(void){u32 n,j,k,killed=0,bad;for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(j=0;j<sizeof(candidates)/sizeof(candidates[0]);j++){
    for(k=0;k<sizeof(curve);k++)((u8*)&curve)[k]=(u8)(k*29+0x59);for(k=0;k<sizeof(knots);k++)((u8*)knots)[k]=(u8)(k*29+0x59);
    for(k=0;k<256;k++)knots[k].value=cases[n].pattern==0?(f32)(k*10):cases[n].pattern==1?20.0f:cases[n].pattern==2?-(f32)(k*10):(f32)((k%3)*10);
    curve.knots=knots;curve.count=cases[n].count;for(k=0;k<sizeof(curve);k++)savedCurve[k]=((u8*)&curve)[k];for(k=0;k<sizeof(knots);k++)savedKnots[k]=((u8*)knots)[k];
    output.u[0]=0x12345678u;output.u[1]=0x87654321u;output.u[2]=0xCDEF0123u;
    candidates[j](output.f+1,&curve,asFloat(cases[n].x),asFloat(cases[n].height),asFloat(cases[n].z));bad=output.u[1]!=cases[n].result||output.u[0]!=0x12345678u||output.u[2]!=0xCDEF0123u;
    for(k=0;k<sizeof(curve);k++)if(savedCurve[k]!=((u8*)&curve)[k])bad=1;for(k=0;k<sizeof(knots);k++)if(savedKnots[k]!=((u8*)knots)[k])bad=1;
    if(!j&&bad)return 2;if(j&&bad)killed|=1u<<(j-1);}
    return killed==MASK?0:3;}
    '''.replace('MASK',str((1<<len(controls))-1)+'u')
    code+=START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
    p=out/'curve-native.c';p.write_text(code)
    for opt in('-O0','-O2','-O3'):
        exe=out/('curve-native-'+opt[1:]);build=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=core.ROOT,capture_output=True,text=True)
        assert build.returncode==0 and not build.stdout and not build.stderr,build.stdout+build.stderr
        run=subprocess.run([str(exe)],capture_output=True);assert run.returncode==0,(opt,run.returncode,run.stderr)
    return dict(cases_per_executable=len(rows),profiles=['-O0','-O2','-O3'],trapping_UBSan=True,
      exact_knot_and_count_layout=True,all_resource_table_bytes_and_output_canaries=True,effective_controls=list(controls),guest_mutations_and_aliases_separate=True)
