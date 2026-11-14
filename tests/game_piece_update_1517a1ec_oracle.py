"""Wrapped motion, random damping, lifetime/fade and retirement observations."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct
from tools.experiments import game_piece_update_1517a1ec_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests import game_randomized_burst_1517aa20_oracle as randoms
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
u32,signed,half=randoms.u32,randoms.signed,randoms.half
RANDOM,FREE,TICKS,RECORD,MARK,SLOT=0x150ADA20,0x1516972C,0x800BE9E4,0x50000,0x70000,0x71000
class DivisionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    timer:int=0
    mode:int=5
    damping:int=257
    ticks:int=1
    opacity:int=255
    packed:int=0
    seed:int=0
    pattern:int=2
    mutation:int=0
    phase:int=0
    layout:int=0
def cases():
    base=[]
    for i,(timer,mode,damping,ticks,mutation,phase) in enumerate(itertools.product((0,1,4,5,65534,65535),(0,5,65535),(1,2,65535),(0,1,2,-1,0x7fffffff,0x80000000,0x40000001,0xffff0000),(0,1),(0,8))):
        c=Case(timer,mode,damping,ticks,(0,1,4,127,255)[i%5],(0,0x11,0x12,0xff,0x10,1,0xf0)[i%7],i,i%3,mutation,phase);base.append(c);yield c
    for value in range(256):
        yield Case(timer=1,mode=0,ticks=0,opacity=1,packed=value,seed=value)
        yield Case(timer=0,mode=0,ticks=1,opacity=value,seed=value)
    for mutation,pattern,phase in itertools.product((0,1,2,4),range(3),(0,8)):yield Case(damping=0,mode=5,pattern=pattern,mutation=mutation,phase=phase)
    for c in base[::37]:
        for layout in range(1,6):yield replace(c,layout=layout)
def address(c):return (RECORD,TICKS-0x90,TICKS-0xa4,TICKS-0xa6,TICKS-0xac,TICKS-0xb0)[c.layout]
def fixture(c):
    record=address(c);m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-256,256)}
    m.update({record+i:(i*29+c.seed*11+0x5a)&255 for i in range(184)})
    m.update({MARK+i:(i+c.seed)&255 for i in range(16)});put(m,SLOT,0xabcdef01)
    values=(-32768,-32767,-1,0,1,32766,32767)
    for i,at in enumerate((0x90,0x92,0x94,0x96,0x98,0x9a,0xa0,0xa2,0xa4)):put(m,record+at,values[(c.seed+i)%7]&65535,2)
    for i in range(3):m[record+0x9c+i]=(-128,-1,0,1,127)[(c.seed+i)%5]&255
    for at,v in ((0xa6,c.timer),(0xac,c.mode),(0xae,c.damping)):put(m,record+at,v&65535,2)
    m[record+0xb2]=c.packed;m[record+0xb3]=c.opacity;put(m,TICKS,u32(c.ticks));return m
def sample(c,draw):return randoms.sample(c,draw)
def packet(m,record):return bytes(m[record+i] for i in range(184))
def observe(m,record):return packet(m,record),read(m,TICKS)
def effect(m,c,t,ordinal,record):
    put(m,MARK,u32(0x13579bdf^ordinal*0x10203))
    if t==FREE:
        for i in range(184):m[record+i]=0xdd
        return
    if c.mutation&1:
        put(m,record+0xa0,(-32768 if ordinal&1 else 32767)&65535,2);put(m,record+0xa4,(1234 if ordinal&1 else -1234)&65535,2)
        put(m,record+0xae,ordinal*3+2,2);put(m,record+0xa6,(read(m,record+0xa6,2)+1)&65535,2)
        m[record+0xb3]^=0x55;m[record+0xb2]=0x22 if ordinal&1 else 0x12;put(m,TICKS,read(m,TICKS)^0x10203)
    if c.mutation&2 and ordinal==1:put(m,record+0xae,0,2)
    if c.mutation&4 and ordinal==0:put(m,record+0xae,0,2)
def reference(initial,c):
    m=dict(initial);record=address(c);calls=[];obs=[];draws=0
    h=lambda at:half(read(m,record+at,2))
    s=lambda at,v:put(m,record+at,v&65535,2)
    def call(t,args):
        nonlocal draws
        calls.append((t,args));obs.append((t,observe(m,record)));value=0
        if t==RANDOM:value=sample(c,draws);draws+=1
        effect(m,c,t,len(calls)-1,record);return value
    x,y,z=h(0x90),h(0x92),h(0x94);vx,vy,vz=h(0xa0),h(0xa2),h(0xa4)
    s(0x90,x+vx);s(0x92,y-vy);s(0x94,z+vz)
    for i,at in enumerate((0x96,0x98,0x9a)):s(at,h(at)+((m[record+0x9c+i]^128)-128))
    if read(m,record+0xac,2)==5:s(0xa2,vy+1)
    if read(m,record+0xa6,2)<read(m,record+0xac,2):
        for at in (0xa0,0xa4):
            value=call(RANDOM,());divisor=read(m,record+0xae,2)
            if not divisor:return m,calls,obs,True
            velocity=h(at);s(at,velocity-(1 if velocity>=0 else -1)*(value%divisor))
    ticks=read(m,TICKS);remaining=signed(read(m,record+0xa6,2)-ticks)
    if remaining<0:
        remaining=0;opacity=signed(m[record+0xb3]-u32(ticks<<2));m[record+0xb3]=max(0,opacity)&255
    s(0xa6,remaining);packed=m[record+0xb2]
    if m[record+0xb3]==0 or packed and packed&15==packed>>4:call(FREE,(record,))
    return m,calls,obs,False
class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        self.draws=0;self.observed=[]
        super().__init__(words,initial,c,entry=entry,connected=connected,arguments=(address(c),));self.before_r=self.r[:];self.before_f=self.f[:]
    def execute(self,w):
        if w>>26==0 and w&63==27 and self.r[w>>16&31]==0:raise DivisionBoundary
        return super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:assert self.r[4]==address(self.case);return
        assert t in (RANDOM,FREE),hex(t);a=() if t==RANDOM else tuple(self.arguments(1))
        self.calls.append((t,a));self.events.append(('CALL',t,a));self.observed.append((t,observe(self.memory,address(self.case))))
    def hook(self,t):
        value=sample(self.case,self.draws) if t==RANDOM else 0x87654321
        if t==RANDOM:self.draws+=1
        effect(self.memory,self.case,t,len(self.calls)-1,address(self.case))
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def public(m):return {a:v for a,v in m.items() if not STACK-256<=a<STACK+256}
def verify(m,initial,c):
    expected,calls,obs,zero=reference(initial,c);assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
    if not zero:assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:] and m.r[29]==m.before_r[29]
def state(m):return m.r,m.f,m.memory,m.trace,m.calls,m.observed,m.hi,m.lo
def load():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
    programs=[bound_blob(*payload(out/f,source.NAME)) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2]
    return root,out,programs
def main():
    root,out,programs=load();seen=set();valid=zeroes=0
    for c in cases():
        initial=fixture(c);zero=reference(initial,c)[3];models=[]
        for words in programs:
            m=Oracle(words,initial,c)
            try:m.run();assert not zero
            except DivisionBoundary:assert zero
            verify(m,initial,c);models.append(m)
        seen.update(models[0].visits);assert state(models[0])==state(models[2])
        if zero:assert state(models[0])==state(models[1]);zeroes+=1
        else:valid+=1
    unvisited=sorted((a-source.ENTRY)//4 for a in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen);assert unvisited==[46,66],unvisited
    callers=0;rom=(root/'conker/conker.us.bin').read_bytes();pc,end=0x15167164,0x15167178;window=struct.unpack_from('>5I',rom,0x194614)
    for descriptor,timer,opacity,packed,mutation,phase in itertools.product((8,12,89),(0,5),(1,255),(0,0x11,0x12),(0,1),(0,8)):
        c=Case(timer=timer,opacity=opacity,packed=packed,seed=47,mutation=mutation,phase=phase);initial=fixture(c);table=0x8008b4a8+descriptor*0x34;pointer=struct.unpack_from('>I',rom,0x22ff68+descriptor*0x34)[0];assert pointer==source.ENTRY;put(initial,table,pointer);put(initial,SLOT,read(initial,address(c)+8))
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[16]=address(c);m.r[17]=SLOT;m.r[18]=table;m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing dispatcher continuation')
            verify(m,initial,c)
        callers+=1
    prefixes=0
    for c in (Case(seed=19,mutation=1),Case(timer=0,mode=0,opacity=1),Case(timer=5,mode=0,ticks=0,packed=0x12)):
        initial=fixture(c);m=Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            models=[]
            for words in (programs[0],programs[2]):
                machine=Oracle(words,initial,c);machine.cut=cut
                try:machine.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing fired memory boundary')
                models.append(machine)
            assert state(models[0])==state(models[1]);prefixes+=1
    # Source controls are additionally checked in native32. These instruction
    # controls exercise wrapped Y motion, gravity selection, fade and retirement.
    changes={'wrong_y_direction':(9,0x03234021),'wrong_gravity_mode':(20,0x24010004),'wrong_fade_rate':(83,0x00055040),'wrong_nibble_mask':(96,0x306c0007)};killed=[]
    for name,(at,word) in changes.items():
        changed=programs[0][:];assert changed[at]!=word;changed[at]=word;failed=False
        for c in (Case(seed=9),Case(timer=0,mode=0,opacity=255,packed=0x88),Case(timer=5,mode=0,ticks=0,packed=0x88)):
            initial=fixture(c)
            try:m=Oracle(changed,initial,c);m.run();verify(m,initial,c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,name;killed.append(name)
    report=dict(valid_cases=valid,predivision_zero_prefixes=zeroes,observed_words=len(seen),unvisited_word_indices=unvisited,dispatcher_cases=callers,descriptor_indices=[8,12,89],retail_guarded_full_state_prefixes=prefixes,negative_controls=killed,raw_access_reordering_explicit=True,aliased_global_guest_only=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
