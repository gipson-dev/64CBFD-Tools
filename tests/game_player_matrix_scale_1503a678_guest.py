"""Planar scale, retained translation, fresh phase byte and callback ABI."""
from pathlib import Path
from dataclasses import dataclass
import itertools,json,struct,sys
from tools.experiments import game_player_matrix_scale_1503a678_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
ENTRY,SIZE=0x1503A678,376
ACTORS,INDEX,PHASE,PAGES=0x800CC2D0,0x800C3E78,0x800C3FFA,0x80084404
MATRICES=0x50000
IDENT,SCALE,MULT,COPY=0x150A7BC0,0x150A7CB0,0x150A7A48,0x10023A10
SYMS=dict(D_800CC2D0=ACTORS,D_800C3E78=INDEX,D_800C3FFA=PHASE,D_80084404=PAGES,guMtxIdentF=IDENT,func_150A7CB0=SCALE,func_150A7A48=MULT,bcopy=COPY)
u32=lambda n:n&0xFFFFFFFF
bits=lambda x:struct.unpack('>I',struct.pack('>f',x))[0]
floating=lambda n:struct.unpack('>f',struct.pack('>I',n))[0]
f32=lambda x:floating(bits(x))

@dataclass(frozen=True)
class Case:
    index:int=0
    kind:int=0x22
    scale:int=64
    counter:int=0
    page:int=0
    mutation:int=0
    phase:int=0

def owner(c):return ACTORS+812*c.index
def data(m,p,n):return bytes(m[p+i]for i in range(n))
def public(m):return{a:b for a,b in m.items()if not STACK-2048<=a<STACK+256}
def fixture(c):
    assert not STACK-2048<=MATRICES<STACK+256
    m={STACK+i:(i*17+0xA5)&255 for i in range(-2048,256)}
    for base,n in((owner(c),812),(MATRICES,128),(PAGES,256),(INDEX,4),(PHASE,4)):
        m.update({base+i:(i*13+0x35)&255 for i in range(n)})
    m[INDEX]=c.index;m[PHASE]=c.counter
    for i in range(256):m[PAGES+i]=c.page
    m[owner(c)+4]=c.kind;m[owner(c)+0x20A]=c.scale;put(m,owner(c)+0x1D4,MATRICES)
    for page in range(2):
        for i in range(16):put(m,MATRICES+page*64+4*i,bits(((i*5+page*3)%19-9)*0.25))
    return m

def mutation(m,c,ordinal,matrix):
    if c.mutation&1 and ordinal==1:
        m[INDEX]=(c.index+1)&255;m[PHASE]=255;m[PAGES+c.counter]=1-c.page
        m[owner(c)+4]=0;m[owner(c)+0x20A]=0
    if c.mutation&2 and ordinal==2:
        for i in range(3):put(m,matrix+48+4*i,bits(10.0+i))

def helper(m,c,target,args,ordinal,matrix):
    if target==IDENT:
        for i in range(16):put(m,args[0]+4*i,0x3F800000 if i%5==0 else 0)
    elif target==SCALE:
        for i in range(16):put(m,args[0]+4*i,0)
        for i,value in zip((0,5,10),args[1:]):put(m,args[0]+4*i,value)
        put(m,args[0]+60,0x3F800000)
    elif target==MULT:
        left=[[floating(read(m,args[0]+4*(4*r+k)))for k in range(4)]for r in range(4)]
        right=[[floating(read(m,args[1]+4*(4*r+k)))for k in range(4)]for r in range(4)]
        for r in range(4):
            for col in range(4):
                products=[f32(left[r][k]*right[k][col])for k in range(4)]
                value=products[0]
                for product in products[1:]:value=f32(value+product)
                put(m,args[2]+4*(4*r+col),bits(value))
    else:
        assert target==COPY and args[2]==64
        saved=data(m,args[0],64)
        for i,value in enumerate(saved):m[args[1]+i]=value
    mutation(m,c,ordinal,matrix)

def reference(initial,c,home=None):
    m=dict(initial);home=STACK+c.phase if home is None else home;calls=[];observations=[]
    if m[owner(c)+4]!=0x22:return public(m),calls,observations
    factor=f32(f32(float(c.scale)*0.015625)+1.0)
    factor=factor if c.counter==0 else f32(1.0/factor)
    matrix=MATRICES+64*c.page;translation=[read(m,matrix+48+4*i)for i in range(3)]
    put(m,matrix+60,0x3F800000)
    for i in(3,7,11):put(m,matrix+4*i,0)
    scaling,result=home-216+0x7C,home-216+0x3C
    for target,args in((IDENT,(scaling,)),(SCALE,(scaling,bits(factor),0x3F800000,bits(factor))),(MULT,(matrix,scaling,result)),(COPY,(result,matrix,64))):
        calls.append((target,args))
        if target==MULT:observations.append((data(m,args[0],64),data(m,args[1],64)))
        helper(m,c,target,args,len(calls),matrix)
    for i,value in enumerate(translation):put(m,matrix+48+4*i,value)
    m[PHASE]=(m[PHASE]+1)&255
    return public(m),calls,observations

class Machine(FactoryOracle):
    def __init__(self,words,c,m,connected=None):
        self.c=c;self.observations=[]
        super().__init__(words,m,c,entry=ENTRY,s=SYMS,arguments=(),connected=connected)
    def record_call(self,t):
        count={IDENT:1,SCALE:4,MULT:3,COPY:3}[t]
        args=tuple(self.arguments(count));self.calls.append((t,args));self.events.append(('CALL',t,args))
        if t==MULT:self.observations.append((data(self.memory,args[0],64),data(self.memory,args[1],64)))
    def hook(self,t):
        a=self.calls[-1][1];ordinal=sum(target in(IDENT,SCALE,MULT,COPY)for target,_ in self.calls)
        helper(self.memory,self.c,t,a,ordinal,MATRICES+64*self.c.page)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for reg in(1,2,3,*range(4,16),24,25):self.r[reg]=0xA5000000+reg
        self.f[:20]=[0xA5000000+i for i in range(20)];self.hi,self.lo=0xA5000010,0xA5000011

def programs():
    paths=(out/'image-qualification/retail.o',out/'qualified-source/candidate.o',out/'image-qualification/qualified-owner/generated_64120.c.o')
    return[bound_blob(*payload(p,'func_1503A678'),SYMS)for p in paths]
def state(m):return(m.memory,m.r,m.f,m.hi,m.lo,m.condition,m.trace,m.calls,m.observations,m.current_pc,m.delay_of)
def corpus():
    for scale,counter in itertools.product(range(256),(0,1,255)):yield Case(scale=scale,counter=counter,page=scale&1)
    for index in range(256):yield Case(index=index,counter=index,page=index&1,scale=index)
    for kind,scale,counter,page,mutation_value,phase in itertools.product((0,0x22,255),(0,1,64,255),(0,1,2,255),(0,1),range(4),(0,8)):
        yield Case(kind=kind,scale=scale,counter=counter,page=page,mutation=mutation_value,phase=phase)
def compare(streams,c):
    initial=fixture(c);wanted=reference(initial,c);machines=[]
    for words in streams:
        m=Machine(words,c,dict(initial)).run()
        assert(public(m.memory),m.calls,m.observations)==wanted,('public model',c)
        assert m.r[29]==STACK+c.phase
        for reg in(*range(16,24),30):assert m.r[reg]==m.before[reg]
        machines.append(m)
    assert state(machines[0])==state(machines[2]),('normalized private',c)
    if c.kind==0x22:assert state(machines[0])==state(machines[1]),('active raw private',c)
    else:
        # Raw code legitimately clobbers different volatile GPRs on the void skip path.
        assert machines[0].memory==machines[1].memory and machines[0].trace==machines[1].trace
        assert machines[0].f==machines[1].f
        assert all(a==b for i,(a,b)in enumerate(zip(machines[0].r,machines[1].r))if i not in(2,3))
    return machines[0]

def run():
    streams=programs();assert streams[0]==streams[2]and streams[0]!=streams[1]
    coverage=set();count=0
    for c in corpus():
        m=compare(streams,c);coverage.update((p-ENTRY)//4 for p in m.visits if ENTRY<=p<ENTRY+SIZE);count+=1
    assert coverage==set(range(94))-{29,30,31},sorted(set(range(94))-coverage)
    faults=0
    for c in(Case(),Case(counter=255,mutation=3,page=1),Case(kind=0)):
        full=compare(streams,c)
        for cut in range(full.all_accesses):
            states=[]
            for words in(streams[0],streams[2]):
                m=Machine(words,c,fixture(c));m.cut=cut
                try:m.run();raise AssertionError('Missing access cut')
                except AccessBoundary:pass
                states.append(state(m))
            assert states[0]==states[1];faults+=1
    controls=[]
    for label,index,value,c in(('wrong-kind-gate',18,0x24010021,Case()),('wrong-phase-increment',87,0x258D0002,Case()),('wrong-unit-scale',23,0x3C014000,Case())):
        changed=list(streams[0]);changed[index]=value
        try:
            m=Machine(changed,c,fixture(c)).run();rejected=(public(m.memory),m.calls,m.observations)!=reference(fixture(c),c)
        except(AssertionError,KeyError):rejected=True
        assert rejected,label;controls.append(label)
    report=dict(cases_per_stream=count,streams=3,covered_words=len(coverage),unsigned_byte_conversion_unreachable_words=[29,30,31],complete_normalized_private_state_equal=True,raw_active_private_equal_under_helper_ABI_clobbers=True,raw_skip_volatile_GPRs_differ=[2,3],normalized_fault_prefixes=faults,effective_controls=controls,limits='Helpers use explicit matrix/byte-copy contracts with input snapshots, mutations and ABI clobbers. Raw skip V0/V1 differences are qualified through the real full-save callback separately.',source_installed=packet.installed(),matching_credit=0)
    (out/'guest-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
if __name__=='__main__':run()
