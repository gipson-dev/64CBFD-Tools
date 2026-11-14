"""Allocation, floor query, mutable homes/constants and complete piece writes."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,os,struct
from tools.experiments import game_burst_piece_1517a644_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_randomized_burst_1517aa20_oracle as burst
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.check_game_data_layout import load_section
from tools.patch_generated_slice_ld import load_game_data_layout
u32,signed,half=burst.u32,burst.signed,burst.half
ALLOC,GROUND,RANDOM,OUTPUT,MARK=0x15167A68,0x1510E82C,0x150ADA20,0x50000,0x70000
C1,C2=0x800A7224,0x800A7228
@dataclass(frozen=True)
class Case:
    size:int=0x41420000
    kind:int=0x123400ff
    x:int=0x87658000
    y:int=0x12347fff
    z:int=0xa5a58001
    outcome:int=1
    floor:int=0xc0940000
    pattern:int=2
    seed:int=0
    mutation:int=0
    phase:int=0
def cases():
    sizes=tuple(map(bits,(-.75,0.,.75,1.,2.5,12.125,-3.25,255.875)))
    coords=((0,0,0),(0x87658000,0x12347fff,0xa5a58001),(32767,0xaaaa8000,0xffff7fff))
    for i,(size,xyz,outcome,pattern,mutation,phase) in enumerate(itertools.product(sizes,coords,(0,1),range(3),(0,1,3),(0,8))):
        yield Case(size,0x123400ff if i&1 else 0,*xyz,outcome,bits((-32768.75,0.,32766.5)[i%3]),pattern,i,mutation,phase)
    for high,low in itertools.product((0,0x12340000,0xa5a50000,0xffff0000),(0,32767,32768,65535)):
        yield Case(z=high|low,pattern=1,seed=low,mutation=0)
def constants(root):
    rom=(root/'conker/conker.us.bin').read_bytes();start,base,_,_=load_game_data_layout(root/'conker');address,data=load_section(root/'conker/build/conker.us.elf','.game_data');assert address==base
    result={a:read({a+i:b for i,b in enumerate(data[a-base:a-base+4])},a) for a in (C1,C2)}
    assert all(data[a-base:a-base+4]==rom[start+a-base:start+a-base+4] for a in result)
    return result
def fixture(c,values):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for i in range(184):m[OUTPUT+i]=(i*29+c.seed*11+0x5a)&255
    for i in range(16):m[MARK+i]=(i+c.seed)&255
    for a,v in values.items():put(m,a,v)
    return m
def sample(c,draw):return burst.sample(c,draw)
def effect(m,c,ordinal,target,home):
    put(m,MARK,u32(0x13579bdf^ordinal*0x10203))
    if c.mutation&1:
        put(m,C1,bits((ordinal+1)*.125));put(m,C2,bits((ordinal-2)*.25))
        if c.outcome:m[OUTPUT+0x50]^=(ordinal+1)&255
        if target==GROUND and c.outcome:m[OUTPUT+0xb2]^=0x55
    if c.mutation&2:
        for i,v in enumerate((bits(16.25+ordinal),0x12340000|((c.seed+ordinal*17)&255),0xa5a58000|((c.seed+ordinal*13)&32767),0xbad00000|((c.seed+ordinal*19)&65535),0x76540000|((0xfff0+ordinal*5)&65535))):put(m,home+4*i,v)
def record(m):return bytes(m[OUTPUT+i] for i in range(184))
def observe(m):return record(m),read(m,C1),read(m,C2)
def reference(initial,c,start_draw=0,start_ordinal=0):
    m=dict(initial);home=STACK+c.phase;calls=[];observations=[];draws=start_draw
    for i,v in enumerate((c.size,c.kind,c.x,c.y,c.z)):put(m,home+4*i,u32(v))
    divisor=math.trunc(floating(c.size))
    def call(t,args):
        nonlocal draws
        observations.append((t,observe(m)));calls.append((t,args));answer=0
        if t==ALLOC:
            answer=OUTPUT if c.outcome else 0
            if answer:m[OUTPUT+1]=0;m[OUTPUT+12]=255
        elif t==GROUND:put(m,args[2],c.floor)
        else:assert t==RANDOM;answer=sample(c,draws);draws+=1
        effect(m,c,start_ordinal+len(calls)-1,t,home);return answer
    if divisor and call(ALLOC,(9,0,184,1,255,1)):
        x,y,z=(half(read(m,home+at)) for at in (8,12,16));height=home-12
        call(GROUND,(0,0,height,0,0,0,bits(float(x)),bits(float(y)),bits(float(z)),bits(float(y)),0,0))
        ground=math.trunc(floating(bits(floating(read(m,height))+3.)))
        put(m,OUTPUT+0xb0,ground&65535,2);put(m,OUTPUT+0x92,ground&65535,2)
        put(m,OUTPUT+0x90,read(m,home+8)&65535,2);put(m,OUTPUT+0x94,read(m,home+16)&65535,2);put(m,OUTPUT+0x96,90,2)
        value=call(RANDOM,());put(m,OUTPUT+0x98,value%360,2)
        for at in (0x9a,0xa0,0xa4):put(m,OUTPUT+at,0,2)
        m[OUTPUT+0x9f]=read(m,home+4)&255
        value=call(RANDOM,());put(m,OUTPUT+0xa8,bits(float(value%80+100)*floating(read(m,C1))))
        speed=math.trunc(floating(bits(floating(read(m,home))*floating(read(m,C2)))))
        put(m,OUTPUT+0xa2,speed&65535,2)
        value=call(RANDOM,());half_size=math.trunc(floating(bits(floating(read(m,home))*.5)))
        m[OUTPUT+0x9c]=(value%u32(divisor)-half_size)&255
        for at in (0x9d,0x9e):value=call(RANDOM,());m[OUTPUT+at]=(value%u32(divisor)-half_size)&255
        put(m,OUTPUT+0xa6,0,2);m[OUTPUT+0xb3]=255
    return m,calls,observations
class Oracle(burst.Oracle):
    execute=burst.Oracle.execute
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None,arguments=None):
        self.draws=0;self.observed=[]
        FactoryOracle.__init__(self,words,initial,c,entry=entry,connected=connected,arguments=arguments or (0,u32(c.kind),u32(c.x),u32(c.y),u32(c.z)))
        self.f[12]=c.size;self.before_r=self.r[:];self.before_f=self.f[:]
    def record_call(self,t):
        assert t in (ALLOC,GROUND,RANDOM),hex(t)
        a=tuple(map(u32,self.arguments({ALLOC:6,GROUND:12,RANDOM:0}[t])))
        self.calls.append((t,a));self.events.append(('CALL',t,a));self.observed.append((t,observe(self.memory)))
    def hook(self,t):
        value=0;c=self.case
        if t==ALLOC:
            value=OUTPUT if c.outcome else 0
            if value:self.memory[OUTPUT+1]=0;self.memory[OUTPUT+12]=255
        elif t==GROUND:put(self.memory,self.calls[-1][1][2],c.floor)
        else:value=sample(c,self.draws);self.draws+=1
        effect(self.memory,c,len(self.calls)-1,t,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def verify(m,initial,c):
    expected,calls,obs=reference(initial,c);assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
    assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:] and m.r[29]==m.before_r[29]
def state(m):return m.r,m.f,m.memory,m.trace,m.calls,m.observed,m.hi,m.lo
def load():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;values=constants(root)
    programs=[bound_blob(*payload(out/f,source.NAME)) for f in ('retail.o','selected.o','guarded.o')]
    assert programs[0]==programs[2] and [i for i,(a,b) in enumerate(zip(programs[0],programs[1])) if a!=b]==[58]
    return root,out,values,programs
def main():
    root,out,values,programs=load();seen=set();count=0
    for c in cases():
        initial=fixture(c,values);states=[]
        for words in programs:
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);seen.update(m.visits);states.append(state(m))
        assert states[0]==states[2];count+=1
    unvisited=sorted((a-source.ENTRY)//4 for a in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen)
    assert unvisited==[100,110,122],unvisited
    c=Case(mutation=3,seed=41);initial=fixture(c,values);m=Oracle(programs[0],initial,c);m.run();prefixes=m.all_accesses
    for cut in range(prefixes):
        models=[]
        for words in programs:
            m=Oracle(words,initial,c);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError('Missing fired instruction-access boundary')
            models.append(m)
        assert state(models[0])==state(models[2])
        assert all((public(m.memory),m.calls,m.observed)==(public(models[0].memory),models[0].calls,models[0].observed) for m in models)
    changes={'wrong_category':(9,0x24040008),'wrong_allocation_size':(12,0x240600b4),'wrong_pitch':(49,0x240e005b),'wrong_angle_modulus':(62,0x24010167),'wrong_floor_offset':(46,0x3c014080),'wrong_timer':(123,0xa60100a6)}
    killed=[]
    for name,(at,word) in changes.items():
        changed=programs[0][:];assert changed[at]!=word;changed[at]=word;failed=False
        for pattern in range(3):
            c=Case(pattern=pattern,seed=59);initial=fixture(c,values)
            try:m=Oracle(changed,initial,c);m.run();verify(m,initial,c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,name;killed.append(name)
    report=dict(cases=count,observed_words=len(seen),unvisited_word_indices=unvisited,full_state_retail_guarded_prefixes=prefixes,public_state_raw_prefixes=prefixes,negative_controls=killed,callee_saves_preserved=True,helpers_modeled=True,raw_four_byte_argument_home_required=True,finite_conversion_domain=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
