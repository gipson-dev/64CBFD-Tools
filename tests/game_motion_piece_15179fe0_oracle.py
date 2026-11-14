"""Eleven-word ABI, six random draws, captured ranges and record initialization."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,os,struct
from tools.experiments import game_motion_piece_15179fe0_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests import game_randomized_burst_1517aa20_oracle as randoms
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.check_game_data_layout import load_section
from tools.patch_generated_slice_ld import load_game_data_layout
u32,signed,half=randoms.u32,randoms.signed,randoms.half
byte=lambda x:((x&255)^128)-128
ALLOC,RANDOM,OUTPUT,MARK,FACTOR=0x15167A68,0x150ADA20,0x50000,0x70000,0x800A7220
class DivisionBoundary(Exception):pass
@dataclass(frozen=True)
class Case:
    variant:int=0x123400ff
    x:int=0x87658000
    y:int=0x12347fff
    z:int=0xa5a58001
    vertical:int=0x87650080
    lifetime:int=1
    mode:int=5
    movement:int=10
    spin:int=30
    damping:int=3
    category:int=8
    outcome:int=1
    pattern:int=2
    seed:int=0
    mutation:int=0
    phase:int=0
def args(c):return tuple(map(u32,(c.variant,c.x,c.y,c.z,c.vertical,c.lifetime,c.mode,c.movement,c.spin,c.damping,c.category)))
def cases():
    xyz=((0,0,0),(0x87658000,0x12347fff,0xa5a58001),(32767,0xaaaa8000,0xffff7fff))
    for i,(movement,spin,mode,lifetime,outcome,mutation,phase) in enumerate(itertools.product((1,2,10,255),(1,2,30,255),(0,5,37,65535),(0,1,1200,65535),(0,1),(0,1,3),(0,8))):
        yield Case((0,1,0x123400ff)[i%3],*xyz[i%3],0x87650000|((-128,-1,0,7,127)[i%5]&255),0x12340000|lifetime,0xabcd0000|mode,0x12340000|movement,0x87650000|spin,0xa5a50000|((0,3,255)[i%3]),(8,12,0xffffffff,0x80000000)[i%4],outcome,i%3,i,mutation,phase)
    for movement,spin,outcome,mutation,pattern,phase in itertools.product((0,7),(0,30),(0,1),(0,1,3),range(3),(0,8)):
        if movement and spin:continue
        yield Case(movement=movement,spin=spin,outcome=outcome,mutation=mutation,pattern=pattern,phase=phase)
    for value in range(256):
        yield Case(movement=value,seed=value)
        yield Case(spin=value,seed=value)
def factor(root):
    rom=(root/'conker/conker.us.bin').read_bytes();start,base,_,_=load_game_data_layout(root/'conker');address,data=load_section(root/'conker/build/conker.us.elf','.game_data');at=FACTOR-base;assert address==base and data[at:at+4]==rom[start+at:start+at+4];return struct.unpack_from('>I',data,at)[0]
def fixture(c,value):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    m.update({OUTPUT+i:(i*29+c.seed*11+0x5a)&255 for i in range(184)});m.update({MARK+i:(i+c.seed)&255 for i in range(16)});put(m,FACTOR,value);return m
def packet(m):return bytes(m[OUTPUT+i] for i in range(184))
def observe(m):return packet(m),read(m,FACTOR)
def sample(c,draw):return randoms.sample(c,draw)
def effect(m,c,t,ordinal,home):
    put(m,MARK,u32(0x13579bdf^ordinal*0x10203))
    if c.mutation&1:
        put(m,FACTOR,bits((ordinal+1)*.125))
        if c.outcome:
            m[OUTPUT+0x50]^=(ordinal+1)&255
            if t==RANDOM:
                for at,v in ((0x90,half(read(m,OUTPUT+0x90,2))+1),(0x92,half(read(m,OUTPUT+0x92,2))-1),(0x94,half(read(m,OUTPUT+0x94,2))+2),(0xa0,32767-ordinal),(0xa2,-3 if ordinal&1 else 5),(0xa4,-1234+ordinal)):put(m,OUTPUT+at,v&65535,2)
                m[OUTPUT+0x9c]=0x80|ordinal
    if c.mutation&2:
        values=(0x12340000|((c.seed+ordinal*17)&255),0xa5a58000|((c.seed+ordinal*13)&32767),0xbad00000|((c.seed+ordinal*19)&65535),0x76540000|((0xfff0+ordinal*5)&65535),0x12340000|((-128+ordinal*7)&255),0xabcd0000|((ordinal*23+2)&65535),0x12340000|(5 if ordinal in (0,2,6) else 37),0x87650000|(ordinal*3+1),0x76540000|(ordinal*5+1),0xa5a50000|((ordinal*7+3)&255),0x80000001)
        for i,v in enumerate(values):put(m,home+4*i,v)
def reference(initial,c):
    m=dict(initial);home=STACK+c.phase;calls=[];obs=[];draws=0
    for i,v in enumerate(args(c)):put(m,home+4*i,v)
    def call(t,arguments):
        nonlocal draws
        calls.append((t,arguments));obs.append((t,observe(m)));answer=0
        if t==ALLOC:
            answer=OUTPUT if c.outcome else 0
            if answer:m[OUTPUT+1]=0;m[OUTPUT+12]=255
        else:answer=sample(c,draws);draws+=1
        effect(m,c,t,len(calls)-1,home);return answer
    if call(ALLOC,(read(m,home+40),0,184,1,255,1)):
        for at,arg in ((0x90,1),(0x92,2),(0x94,3)):put(m,OUTPUT+at,read(m,home+arg*4)&65535,2)
        put(m,OUTPUT+0xa2,byte(read(m,home+16))&65535,2)
        value=call(RANDOM,());movement=read(m,home+28)&255;half_movement=movement>>1
        if not movement:return m,calls,obs,'movement'
        put(m,OUTPUT+0xa0,(value%movement-half_movement)&65535,2)
        value=call(RANDOM,());put(m,OUTPUT+0xa4,(value%movement-half_movement)&65535,2)
        if read(m,home+24)&65535==5:
            for pos,speed,sign in ((0x90,0xa0,1),(0x92,0xa2,-1),(0x94,0xa4,1)):put(m,OUTPUT+pos,(half(read(m,OUTPUT+pos,2))+sign*half(read(m,OUTPUT+speed,2))*4)&65535,2)
        for at in (0x96,0x98,0x9a):put(m,OUTPUT+at,0,2)
        value=call(RANDOM,());spin=read(m,home+32)&255;half_spin=spin>>1
        if not spin:return m,calls,obs,'spin'
        m[OUTPUT+0x9c]=(value%spin-half_spin)&255
        for at in (0x9d,0x9e):value=call(RANDOM,());m[OUTPUT+at]=(value%spin-half_spin)&255
        value=call(RANDOM,());put(m,OUTPUT+0xa8,bits(float((value&127)+140)*floating(read(m,FACTOR))))
        put(m,OUTPUT+0xa6,read(m,home+20)&65535,2);m[OUTPUT+0x9f]=read(m,home)&255;put(m,OUTPUT+0xac,read(m,home+24)&65535,2)
        m[OUTPUT+0xb2]=0;m[OUTPUT+0xb3]=255;put(m,OUTPUT+0xae,read(m,home+36)&255,2)
    return m,calls,obs,None
class Oracle(randoms.Oracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        self.draws=0;self.observed=[]
        FactoryOracle.__init__(self,words,initial,c,entry=entry,connected=connected,arguments=args(c));self.before_r=self.r[:];self.before_f=self.f[:]
    def execute(self,w):
        if w>>26==0 and w&63==27 and self.r[w>>16&31]==0:raise DivisionBoundary
        return super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:assert tuple(map(u32,self.arguments(11)))==args(self.case);return
        assert t in (ALLOC,RANDOM),hex(t);a=tuple(map(u32,self.arguments(6))) if t==ALLOC else ()
        self.calls.append((t,a));self.events.append(('CALL',t,a));self.observed.append((t,observe(self.memory)))
    def hook(self,t):
        c=self.case;value=sample(c,self.draws) if t==RANDOM else OUTPUT if c.outcome else 0
        if t==RANDOM:self.draws+=1
        elif value:self.memory[OUTPUT+1]=0;self.memory[OUTPUT+12]=255
        effect(self.memory,c,t,len(self.calls)-1,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def verify(m,initial,c):
    expected,calls,obs,zero=reference(initial,c);assert (public(m.memory),m.calls,m.observed)==(public(expected),calls,obs),c
    if zero is None:assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:] and m.r[29]==m.before_r[29]
def state(m):return m.r,m.f,m.memory,m.trace,m.calls,m.observed,m.hi,m.lo
def load():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD;value=factor(root);programs=[bound_blob(*payload(out/f,source.NAME)) for f in ('retail.o','selected.o','guarded.o')];assert programs[0]==programs[2];return root,out,value,programs
def main():
    root,out,value,programs=load();seen=set();valid=zeroes=0
    for c in cases():
        initial=fixture(c,value);zero=reference(initial,c)[3];models=[]
        for words in programs:
            m=Oracle(words,initial,c)
            try:m.run();assert zero is None
            except DivisionBoundary:assert zero is not None
            verify(m,initial,c);models.append(m)
        seen.update(models[0].visits);assert state(models[0])==state(models[2])
        if zero is None:valid+=1
        else:zeroes+=1
    unvisited=sorted((a-source.ENTRY)//4 for a in set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen);assert unvisited==[36,50,81,92,103],unvisited
    rom=(root/'conker/conker.us.bin').read_bytes();pc,end=0x150c7c0c,0x150c7c7c;window=struct.unpack_from('>28I',rom,0xf50bc);callers=0
    for x,z,integer,outcome,mutation,phase in itertools.product((-32768,32767),(-32768,32767),(0.,65534.,131070.),(0,1),(0,1),(0,8)):
        c=Case(variant=int(integer/65536),x=x,y=1583,z=z,vertical=7,lifetime=1200,mode=37,movement=10,spin=30,damping=3,category=8,outcome=outcome,mutation=mutation,phase=phase,seed=47);initial=fixture(c,value)
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words));code[end]=0;m=Oracle(window,initial,c,entry=pc,connected=code);m.r[5]=u32(x<<16);m.r[16]=u32(x);m.r[17]=u32(z);m.f[8]=bits(integer);m.before_r=m.r[:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing caller continuation')
            verify(m,initial,c)
        callers+=1
    prefixes=0
    for c in (Case(mutation=3,seed=19),Case(outcome=0)):
        initial=fixture(c,value);m=Oracle(programs[0],initial,c);m.run()
        for cut in range(m.all_accesses):
            models=[]
            for words in (programs[0],programs[2]):
                machine=Oracle(words,initial,c);machine.cut=cut
                try:machine.run()
                except AccessBoundary:pass
                else:raise AssertionError('Missing fired instruction-access boundary')
                models.append(machine)
            assert state(models[0])==state(models[1]);prefixes+=1
    changes={'wrong_allocation_size':(13,0x240600b4),'wrong_mode':(42,0x24010004),'wrong_initial_step':(59,0x0018c840),'wrong_scale_mask':(107,0x3059003f),'wrong_spin_field':(93,0xa20c009c)};killed=[]
    for name,(at,word) in changes.items():
        changed=programs[0][:];assert changed[at]!=word;changed[at]=word;failed=False
        for c in (Case(seed=19),Case(pattern=1),Case(mode=0,pattern=2)):
            initial=fixture(c,value)
            try:m=Oracle(changed,initial,c);m.run();verify(m,initial,c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,name;killed.append(name)
    report=dict(valid_cases=valid,predivision_zero_prefixes=zeroes,observed_words=len(seen),unvisited_word_indices=unvisited,caller_cases=callers,retail_guarded_full_state_prefixes=prefixes,negative_controls=killed,raw_private_spill_layout_explicit=True,incoming_home_mutations_guest_only=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
