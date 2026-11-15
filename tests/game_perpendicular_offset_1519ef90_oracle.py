"""Ordered scalar reference, actual phase helpers and explicit alias fixtures.

Floating operations use the retained binary32/ordered-NaN model. This is not
hardware FCSR emulation. Public objects may overlap; unpassed private stack is
excluded from public equivalence and is audited separately before adoption.
"""
from dataclasses import dataclass,replace
from functools import lru_cache
import itertools,json,math
from tools.experiments import game_perpendicular_offset_1519ef90_recovery as s
from tools.tests.game_owner_float_payload_oracle import FactoryOracle,Case as BaseCase
from tools.tests.game_quaternion_matrix_1504a140_oracle import fp,is_nan
from tools.tests.game_animation_timeline_oracle import bits,floating,signed
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
RECORD,STATE,ACTOR,OUTPUT,ALT=0x30000,0x31000,0x32000,0x34000,0x35000
HEADING,SAMPLE=0x15143e08,0x151423d8

@lru_cache(None)
def helper_data():return s.helper_input()

@dataclass(frozen=True)
class Case:
    dx:int=0x40400000
    dz:int=0x40800000
    height:int=0xC6147000
    offset:int=0x40000000
    mode:int=6
    present:int=1
    heading:int=17
    alias:int=0
    effects:int=0
    phase:int=0
    rule:str='left'

def output(c):return (OUTPUT,ACTOR+0x14,ACTOR+0x18,ACTOR+0x118,RECORD+0x20,STATE+0x68,s.symbols()['D_800A8CE4'])[c.alias]

def fixture(c):
    m={STACK+c.phase+i:(i*17+0xA5)&255 for i in range(-256,512)}
    for p,n in ((RECORD,0x40),(STATE,0x80),(ACTOR,0x200),(OUTPUT,32),(ALT,0x300)):
        m.update({p+i:(i*13+0x53)&255 for i in range(n)})
    _,data,_=helper_data()
    for p,v in data.items():
        for i in range(-8,16):m.setdefault(p+i,0xA5)
        put(m,p,v)
    put(m,RECORD,STATE);put(m,STATE+0x18,ACTOR);put(m,ACTOR+0x1D4,c.present)
    put(m,ACTOR+0x14,c.dx);put(m,ACTOR+0x1C,c.dz);put(m,ACTOR+0x18,bits(12.5));put(m,ACTOR+0x118,c.height)
    put(m,ACTOR+0x7A,((c.heading-64)&255)<<8,2)
    put(m,RECORD+0x20,0);put(m,RECORD+0x24,0);put(m,STATE+0x68,c.offset)
    return m

def public(m,c):return {a:v for a,v in m.items() if not STACK+c.phase-256<=a<STACK+c.phase+512}
def public_trace(q,c):return [v for v in q.trace if not STACK+c.phase-256<=v[1]<STACK+c.phase+512]

def sqrt_word(value):
    if is_nan(value):return value|0x400000
    x=floating(value)
    return bits(math.sqrt(x)) if x>=0 else 0x7fc00000

def sample(m,angle):
    angle&=255;index=64-(angle&63) if angle&64 else angle&63
    value=read(m,s.symbols()['D_8009A220']+4*index)
    return value if angle&192 in (0,192) else value^0x80000000

def effect(m,c,ordinal):
    if c.effects&1:
        for offset,v in ((0x14,10.+ordinal),(0x18,20.+ordinal),(0x1C,-15.-ordinal),(0x118,-9600.+ordinal)):
            put(m,ACTOR+offset,bits(v))
        put(m,STATE+0x68,bits(3.+ordinal));put(m,RECORD,ALT);put(m,STATE+0x18,ALT+0x100)
    if c.effects&2:put(m,STACK+c.phase+4,0xAC000000|(7 if ordinal&1 else 6))

def answer(m,c,target,args,ordinal):
    if target==HEADING:value=((read(m,args[0]+0x7A,2)>>8)+64)&255
    else:value=(bits(.25 if ordinal==1 else -.75) if c.effects&4 else sample(m,args[0]))
    effect(m,c,ordinal);return value

def reference(initial,c):
    m=initial.copy();calls=[];mode=c.mode&255;actor=read(m,read(m,RECORD)+0x18);parameters=read(m,RECORD)+0x58;out=output(c)
    if not read(m,actor+0x1D4):return 0,m,calls
    op=lambda a,b,k:fp(a,b,k,c.rule)
    x=read(m,actor+0x14);dx=op(x,read(m,RECORD+0x20),'sub');dz=op(read(m,actor+0x1C),read(m,RECORD+0x24),'sub')
    threshold=floating(read(m,s.symbols()['D_800A8CE0']))
    if threshold<abs(floating(dx)) or threshold<abs(floating(dz)):
        inverse=op(bits(1.),sqrt_word(op(op(dx,dx,'mul'),op(dz,dz,'mul'),'add')),'div')
        tangent_x,tangent_z=op(dz,inverse,'mul'),op(dx,inverse,'mul')
    else:
        def call(target,args):
            ordinal=len(calls);calls.append((target,args));return answer(m,c,target,args,ordinal)
        heading=call(HEADING,(actor,))&255
        tangent_x=call(SAMPLE,(heading,));tangent_z=call(SAMPLE,((heading-64)&255,))
        x=read(m,actor+0x14)
        if c.effects&2:mode=read(m,STACK+c.phase+4)&255
    offset=read(m,parameters+0x10)
    if mode!=6:offset^=0x80000000
    put(m,out,op(x,op(offset,tangent_x,'mul'),'add'))
    put(m,out+8,op(read(m,actor+0x1C),op(offset,tangent_z,'mul'),'sub'))
    height=read(m,actor+0x118)
    put(m,out+4,read(m,actor+0x18) if floating(height)<floating(read(m,s.symbols()['D_800A8CE4'])) else height)
    return 1,m,calls

class Oracle(FactoryOracle):
    def __init__(self,words,m,c,connected=None):
        super().__init__(words,m,BaseCase(phase=c.phase),entry=s.ENTRY,s={},arguments=(RECORD,c.mode,output(c)),connected=connected)
        self.c=c;self.fp_ops=[]
    def execute(self,w):
        op,fmt,fn=w>>26,w>>21&31,w&63
        if op==0 and fn==3:
            self.r[w>>11&31]=signed(self.r[w>>16&31])>>(w>>6&31)&0xFFFFFFFF;return
        if op==17 and fmt==16 and fn in(0,1,2,3,4,5,7,60):
            fs,ft,fd=w>>11&31,w>>16&31,w>>6&31;a,b=self.f[fs],self.f[ft]
            if s.ENTRY<=self.current_pc<s.ENTRY+len(self.root_words)*4:self.fp_ops.append((fn,a,b) if fn in(0,1,2,3,60) else(fn,a))
            if fn in(0,1,2,3):self.f[fd]=fp(a,b,('add','sub','mul','div')[fn],self.c.rule)
            elif fn==4:self.f[fd]=sqrt_word(a)
            elif fn==5:self.f[fd]=a&0x7fffffff
            elif fn==7:self.f[fd]=a^0x80000000
            else:self.condition=floating(a)<floating(b)
            return
        return super().execute(w)
    def record_call(self,t):
        assert t in(HEADING,SAMPLE),hex(t);a=(self.r[4],);self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        ordinal=len(self.calls)-1;value=answer(self.memory,self.c,t,self.calls[-1][1],ordinal)
        for i in range(4):self.put(self.r[29]+i*4,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011
        if t==HEADING:self.r[2]=value
        else:self.f[0]=value

def run(ws,m,c,connected=None):
    q=Oracle(ws,m,c,connected);q.root_words=ws;return q.run()

def finite_cases():
    limit=helper_data()[1][s.symbols()['D_800A8CE0']]
    positions=((0,0),(limit,0),(limit-1,0),(limit+1,0),(bits(3.),bits(4.)),(bits(-3.),bits(4.)),(0,bits(-8.)),(0x80000000,0))
    for (dx,dz),mode,present,height,alias in itertools.product(positions,(0,6,7,0x106,0xFFFFFF06),(0,1),(bits(-9600.),bits(-9500.),bits(-9400.)),range(7)):
        yield Case(dx=dx,dz=dz,mode=mode,present=present,height=height,alias=alias)
    for effects,mode,alias in itertools.product(range(1,8),(6,7,0xFFFFFF06),range(7)):
        yield Case(dx=0,dz=0,effects=effects,mode=mode,alias=alias)

def reachable(words):
    work=[0];seen=set();dispatched=set()
    while work:
        pc=work.pop()
        if pc in seen:continue
        seen.add(pc);assert 0<=pc<len(words);dispatched.add(pc)
        w=words[pc];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op==17 and rs==8 or op in(4,5,20,21):
            fixed=(rs==rt) if op in(4,20) and rs==rt else False if op in(5,21) and rs==rt else None
            likely=(bool(rt&2) if op==17 else op>=20)
            if fixed is not False:
                dispatched.add(pc+1);work.append(pc+1+(((w&65535)^32768)-32768))
            if fixed is not True:
                if not likely:dispatched.add(pc+1)
                work.append(pc+2)
        elif op==3:dispatched.add(pc+1);work.append(pc+2)
        elif op==0 and w&63==8:dispatched.add(pc+1)
        else:work.append(pc+1)
    return dispatched

def controls(streams):
    baseline=streams['retail'];cases=[('gate',0x8cef01d4,4,Case(present=0)),('mode',0x24010006,1,Case()),
        ('sqrt',0x46000004,1,Case()),('output',0xe4c40000,4,Case()),
        ('heading-mask',0x304400ff,128,Case(dx=0,dz=0,heading=192)),('height',0x4608103c,(10<<11)|(10<<16),Case(height=bits(-9600.)))]
    rejected=[]
    for name,w,mask,c in cases:
        assert baseline.count(w)==1;changed=baseline[:];changed[changed.index(w)]^=mask
        m=fixture(c);want,expected,calls=reference(m,c)
        q=run(changed,m.copy(),c)
        assert(q.r[2],public(q.memory,c),q.calls)!=(want,public(expected,c),calls),('ineffective instruction control',name)
        rejected.append(name)
    return rejected

def main():
    streams=s.programs()
    if (s.OUT/'guarded.o').exists():
        from tools.experiments.game_paired_ground_constructor_match import payload
        from tools.experiments.game_path_heading_turn_roles import bound_blob
        streams['guarded']=bound_blob(*payload(s.OUT/'guarded.o',s.NAME),s.symbols())
    visited={n:set() for n in streams};count=0
    for c in finite_cases():
        m=fixture(c);want,expected,calls=reference(m,c);runs=[]
        for n,ws in streams.items():
            q=run(ws,m.copy(),c);assert(q.r[2],public(q.memory,c),q.calls)==(want,public(expected,c),calls),(n,c,'semantic')
            visited[n].update(q.visits);runs.append(q)
        assert public_trace(runs[0],c)==public_trace(runs[1],c),(c,'ordered access')
        assert runs[0].fp_ops==runs[1].fp_ops,(c,'ordered FP operations',runs[0].fp_ops,runs[1].fp_ops)
        count+=1
    connected_cases=0;code,_,helpers=helper_data()
    for heading,mode in itertools.product(range(256),(6,7)):
        c=Case(dx=0,dz=0,heading=heading,mode=mode);m=fixture(c);want,expected,calls=reference(m,c)
        for n,ws in streams.items():
            q=run(ws,m.copy(),c,code);assert(q.r[2],public(q.memory,c),q.calls)==(want,public(expected,c),calls),(n,c,'connected')
        connected_cases+=1
    for n,ws in streams.items():assert {s.ENTRY+4*i for i in reachable(ws)}=={pc for pc in visited[n] if s.ENTRY<=pc<s.ENTRY+len(ws)*4},(n,'reachable coverage')
    rejected=controls(streams)
    exceptional=0
    for word,field,mode,alias,rule in itertools.product((0x7f800000,0xff800000,0x7fc00001,0x7fc12345,0x80000000,1),('dx','dz','height'),(6,7),range(7),('left','right')):
        c=replace(Case(),**{field:word},mode=mode,alias=alias,rule=rule);m=fixture(c);want,expected,calls=reference(m,c);runs=[]
        for n,ws in streams.items():
            q=run(ws,m.copy(),c);assert(q.r[2],public(q.memory,c),q.calls)==(want,public(expected,c),calls),(n,c,'exceptional model');runs.append(q)
        assert all(public_trace(q,c)==public_trace(runs[0],c) and q.fp_ops==runs[0].fp_ops for q in runs[1:]);exceptional+=1
    report=dict(finite_cases_per_stream=count,streams=len(streams),connected_cases_per_stream=connected_cases,actual_helpers=helpers,
                ordered_public_accesses_equal=True,ordered_root_FP_operations_equal=True,hardware_FCSR_emulation=False,raw_private_bytes_equated=False,c_match_credit=0,
                exceptional_modeled_cases_per_stream=exceptional,effective_instruction_controls=rejected,all_reachable_words_visited=True,
                unreachable_words={n:sorted(set(range(len(ws)))-reachable(ws)) for n,ws in streams.items()},
                words_visited={n:sum(s.ENTRY+4*i in pcs for i in range(len(streams[n]))) for n,pcs in visited.items()})
    (s.OUT/'guest-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
