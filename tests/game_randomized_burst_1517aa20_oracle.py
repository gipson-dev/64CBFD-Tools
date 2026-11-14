"""Finite-size burst model, authentic caller window and volatile clobbers."""
from pathlib import Path
from dataclasses import dataclass,replace
import itertools,json,math,os,struct
from tools.experiments import game_randomized_burst_1517aa20_match as source
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_float_payload_oracle import FactoryOracle
from tools.tests.game_animation_timeline_oracle import bits,floating
from tools.tests.game_view_render_pass_oracle import STACK
from tools.tests.test_game_point_transform_match import put,read
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
u32=lambda n:n&0xffffffff
signed=lambda n:((n&0xffffffff)^0x80000000)-0x80000000
half=lambda n:((n&65535)^32768)-32768
RANDOM,EMIT,MARK,RECORD=0x150ADA20,0x1517A644,0x70000,0x30000
@dataclass(frozen=True)
class Case:
    size:int=0x41400000
    x:int=32767
    y:int=0x12348000
    z:int=0x7fffffff
    count:int=3
    pattern:int=0
    seed:int=0
    mutation:int=0
    phase:int=0
def cases():
    sizes=(bits(-0.),bits(11.999999),bits(12.),bits(12.125),bits(31.875),bits(255.75),bits(1048576.),bits(268435440.))
    coords=((0,0,0),(32767,0x12348000,0x7fffffff),(0x80000000,0x76547fff,0x80000000))
    for i,(size,count,pattern,xyz,phase) in enumerate(itertools.product(sizes,(-1,0,1,3),range(4),coords,(0,8))):
        yield Case(size,*xyz,count,pattern,i, i&1,phase)
    for low in range(64):yield Case(pattern=3,seed=low,count=1,mutation=low&1)
def sample(c,draw):
    if c.pattern==0:return 0
    if c.pattern==1:return 0xffffffff
    if c.pattern==2:return u32((c.seed+draw)*1664525+1013904223)
    return u32(c.seed+draw*31)
def fixture(c):
    m={STACK+i:(i*17+c.seed*13+0xa5)&255 for i in range(-512,512)}
    for i in range(16):m[MARK+i]=(i*29+c.seed)&255
    return m
def effect(m,c,ordinal,home):
    put(m,MARK,u32(0x13579bdf^ordinal*0x10203))
    if c.mutation:
        for i in range(5):put(m,home+4*i,0xbad00000+i+ordinal)
def reference(initial,c):
    m=dict(initial);calls=[];ordinal=0
    if floating(c.size)<12.:return m,calls
    modulus=math.trunc(floating(bits(floating(c.size)*8.)))
    assert 96<=modulus<0x80000000
    reduced=floating(bits(floating(c.size)*.5))
    for i in range(max(0,c.count)):
        values=[]
        for draw in range(4):
            calls.append((RANDOM,()));values.append(sample(c,i*4+draw));effect(m,c,ordinal,STACK+c.phase);ordinal+=1
        dx=(values[0]&63)-32;dz=(values[1]&63)-32
        piece=bits(floating(bits(float((values[2]%modulus)>>4)))+reduced)
        calls.append((EMIT,(piece,values[3]&1,u32(half(c.x+dx)),u32(half(c.y)),u32(c.z+dz))))
        effect(m,c,ordinal,STACK+c.phase);ordinal+=1
    return m,calls
class Oracle(FactoryOracle):
    def __init__(self,words,initial,c,entry=source.ENTRY,connected=None):
        self.draws=0
        super().__init__(words,initial,c,entry=entry,arguments=(0,u32(c.x),u32(c.y),u32(c.z),u32(c.count)),connected=connected)
        self.f[12]=c.size;self.before_r=self.r[:];self.before_f=self.f[:]
    def execute(self,w):
        op,fmt,ft,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and fmt==16 and fn in (0,2,6):
            if fn==6:self.f[fd]=self.f[fs]
            else:
                a,b=floating(self.f[fs]),floating(self.f[ft]);self.f[fd]=bits(a+b if fn==0 else a*b)
            self.r[0]=0
        else:super().execute(w)
    def record_call(self,t):
        if t==source.ENTRY:
            assert self.f[12]==self.case.size
            assert tuple(map(u32,self.arguments(5)[1:]))==tuple(map(u32,(self.case.x,self.case.y,self.case.z,self.case.count)))
            return
        assert t in (RANDOM,EMIT),hex(t)
        a=() if t==RANDOM else (self.f[12],*map(u32,self.arguments(5)[1:]))
        self.calls.append((t,a));self.events.append(('CALL',t,a))
    def hook(self,t):
        value=sample(self.case,self.draws) if t==RANDOM else 0x87654321
        if t==RANDOM:self.draws+=1
        effect(self.memory,self.case,len(self.calls)-1,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xb5000000+i,4)
        for i in (1,2,3,*range(4,16),24,25):self.r[i]=0xa5000000+i
        self.f[:20]=[0xa5000000+i for i in range(20)];self.hi,self.lo=0xa5000010,0xa5000011;self.r[2]=u32(value)
def public(m):return {a:v for a,v in m.items() if not STACK-512<=a<STACK+512}
def verify(m,initial,c):
    memory,calls=reference(initial,c);assert m.calls==calls,(c,m.calls,calls)
    assert public(m.memory)==public(memory),c
    assert m.r[16:24]==m.before_r[16:24] and m.f[20:]==m.before_f[20:]
    assert m.r[29]==m.before_r[29]
def state(m):return m.r,m.f,m.memory,m.trace,m.calls,m.hi,m.lo
def load():
    root=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();out=root/source.BUILD
    programs=[bound_blob(*payload(out/f,source.NAME)) for f in ('retail.o','selected.o','guarded.o')]
    assert programs[0]==programs[1]==programs[2]
    return root,out,programs
def main():
    root,out,programs=load();seen=set();total_cases=0
    for c in cases():
        initial=fixture(c);states=[]
        for words in programs:
            m=Oracle(words,initial,c);m.run();verify(m,initial,c);seen.update(m.visits);states.append(state(m))
        assert states[0]==states[1]==states[2];total_cases+=1
    # Four instructions are unreachable in this finite, valid conversion domain:
    # divide-by-zero break and the unsigned-float sign-correction block.
    unvisited=sorted((set(range(source.ENTRY,source.ENTRY+source.SIZE,4))-seen))
    expected=[source.ENTRY+4*i for i in (49,53,54,55)]
    assert unvisited==expected,unvisited
    callers=0;rom=(root/'conker/conker.us.bin').read_bytes();pc,end=0x1518384c,0x15183884
    window=struct.unpack_from('>14I',rom,0x1b0cfc)
    for size,count,pattern,phase in itertools.product((11.,12.,123.125),(-1,1,3),(0,1),(0,8)):
        c=Case(bits(size),32767,-32768,65535,count,pattern,phase=phase);initial=fixture(c)
        initial.update({RECORD+i:0xa5 for i in range(128)})
        for at,v in ((0x14,32767.),(0x18,-32768.),(0x1c,65535.),(0x3c,size)):put(initial,RECORD+at,bits(v))
        put(initial,STACK+phase+0x74,u32(count))
        for words in programs:
            code=dict(zip(range(source.ENTRY,source.ENTRY+source.SIZE,4),words));code[end]=0
            m=Oracle(window,initial,c,entry=pc,connected=code);m.r[4]=RECORD;m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing real caller continuation')
            verify(m,initial,c)
        callers+=1
    c=Case(pattern=2,seed=19,mutation=1,count=2);initial=fixture(c);m=Oracle(programs[0],initial,c);m.run();prefixes=m.all_accesses
    for cut in range(prefixes):
        states=[]
        for words in programs:
            m=Oracle(words,initial,c);m.cut=cut
            try:m.run()
            except AccessBoundary:pass
            else:raise AssertionError('Missing fired instruction-access boundary')
            states.append(state(m))
        assert states[0]==states[1]==states[2]
    changes={'wrong_offset_mask':(37,0x3050001f),'wrong_size_half':(23,0x3c013f80),'wrong_variant_bit':(63,0x30a80002),'unsigned_x':(67,0x00093402),'early_loop_exit':(72,0x1235ffda)}
    killed=[]
    for name,(at,word) in changes.items():
        candidate=programs[0][:];assert candidate[at]!=word;candidate[at]=word;failed=False
        for pattern in (0,1,2,3):
            c=Case(pattern=pattern,x=0x80000000,count=3,seed=47)
            try:m=Oracle(candidate,fixture(c),c);m.run();verify(m,fixture(c),c)
            except (AssertionError,KeyError):failed=True;break
        assert failed,name;killed.append(name)
    report=dict(cases=total_cases,caller_windows=1,caller_cases=callers,observed_words=len(seen),unvisited_word_indices=[(a-source.ENTRY)//4 for a in unvisited],full_state_access_prefixes=prefixes,negative_controls=killed,callee_saves_preserved=True,random_and_emitter_modeled=True,finite_conversion_domain=True)
    (out/'behavior.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
