"""Original mask caller plus connected owner/action providers and SDK gate."""
import itertools,struct
from dataclasses import replace
from tools.tests import game_record_subtype_150a25d4_oracle as g
from tools.experiments import game_record_subtype_150a25d4_match as source
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
LOWER_OWNER,LOWER_ACTION=0x151403A8,0x15200000

class ConnectedOracle(g.Oracle):
    def __init__(self,*args,**kwargs):
        self.payloads=[];super().__init__(*args,**kwargs)
    def record_call(self,target):
        if target not in(LOWER_OWNER,LOWER_ACTION):return super().record_call(target)
        args=tuple(map(g.u32,self.arguments(2)));self.physical_calls.append((target,args));self.calls.append((target,args));self.events.append(('CALL',target,args))
        if target==LOWER_OWNER:self.payloads.append(tuple(g.rd(self.memory,args[0]+j*4)for j in range(2)))
    def hook(self,target):
        if target not in(LOWER_OWNER,LOWER_ACTION):return super().hook(target)
        g.effect(self.memory,self.case,target,self.target_home)
        for i in range(4):self.put(self.r[29]+4*i,0xB5000000+i,4)
        for i in(1,2,3,*range(4,16),24,25):self.r[i]=0xA5000000+i
        self.f[:20]=[0xA5000000+i for i in range(20)];self.r[2]=0xDEADBEEF

def caller(rom,normal):
    count=0
    for c in[g.Case(kind=k,selector=s,high=h,low=l,padding=p,phase=phase)for k,s,h,l,p,phase in itertools.product((1,2,3,6,8,9,10),(0,3,255),(0,1,0xFFFFFFFF),(0,1),(0,0xABCD1234),(0,8))]:
        initial=g.fixture(c);home=g.STACK+c.phase
        g.wr(initial,home+0x80,c.high);g.wr(initial,home+0x84,c.low);g.wr(initial,home+0xC8,c.selector)
        entry,end=0x150A1C20,0x150A1CF8;window=struct.unpack_from('>10I',rom,0xCF0D0)
        code=dict(zip(range(source.ENTRY,source.ENTRY+440,4),normal));code[end]=struct.unpack_from('>I',rom,0xCF1A8)[0]
        m=g.Oracle(window,initial,c,entry=entry,connected=code);m.r[16]=0;m.r[3]=g.record(c);m.r[17]=g.actor(c);m.r[7]=c.padding
        expected=g.reference(initial,c);m.code=WindowCode(m.code,m);m.code.ends=(end,)
        try:m.run()
        except WindowBoundary:pass
        else:raise AssertionError('Caller did not reach its original common destination')
        physical=(g.record(c),g.actor(c),g.u32(c.selector),g.u32(c.padding),g.u32(c.high),g.u32(c.low))
        assert(g.observable(m.memory,c),m.calls)==(expected[0],[(source.ENTRY,physical)]+expected[1]),c
        assert m.r[29]==home
        assert m.physical_calls[0][1]==physical
        count+=1
    return dict(cases=count,window_words=10,mask_high_low_stack_words=True,A3_padding_ignored=True,selector_from_original_home=True,void_return_ignored=True)

def providers(rom,bodies):
    counts={};visits={};fault_cases=[]
    owner_code=dict(zip(range(g.OWNER,g.OWNER+56,4),struct.unpack_from('>14I',rom,0x1F5B24)))
    for null,mutation,phase in itertools.product((0,1),(0,1,2,4,8,16,31),(0,8)):
        c=g.Case(kind=8,null_actor=null,mutation=mutation,phase=phase);initial=g.fixture(c);home=g.STACK+phase;wanted=dict(initial);g.wr(wanted,home+8,c.selector);expected_calls=[(g.OWNER,(g.actor(c),g.record(c)))];payload=[]
        if not null:
            expected_calls.append((LOWER_OWNER,(home-48,0x20)));g.effect(wanted,c,LOWER_OWNER,home);payload=[(g.actor(c),g.record(c))]
        states=[]
        for i,body in enumerate(bodies):
            m=ConnectedOracle(body,initial,c,connected=owner_code);m.run();assert(g.observable(m.memory,c),m.calls,m.payloads)==(g.observable(wanted,c),expected_calls,payload),(c,i)
            visits.setdefault('owner',set()).update(m.visits)
            if i<2:states.append(g.state(m))
        assert states[0]==states[1];counts['owner']=counts.get('owner',0)+1
    action_code=dict(zip(range(g.ACTION,g.ACTION+72,4),struct.unpack_from('>18I',rom,0x18C720)))
    for index,present,mutation,phase in itertools.product((-1,0,11,12),(0,1),(0,3,8),(0,8)):
        c=g.Case(kind=9,mutation=mutation,phase=phase);initial=g.fixture(c);home=g.STACK+phase;g.wr(initial,g.RECORD+0x18,index)
        for j in range(12):g.wr(initial,0x8008B090+j*4,LOWER_ACTION if present else 0)
        wanted=dict(initial);g.wr(wanted,home+8,c.selector);expected_calls=[(g.ACTION,(g.actor(c),g.record(c)))]
        if 0<=index<12 and present:expected_calls.append((LOWER_ACTION,(g.actor(c),g.record(c))));g.effect(wanted,c,LOWER_ACTION,home)
        states=[]
        for i,body in enumerate(bodies):
            m=ConnectedOracle(body,initial,c,connected=action_code);m.run();assert(g.observable(m.memory,c),m.calls)==(g.observable(wanted,c),expected_calls),(c,index,present,i)
            visits.setdefault('action',set()).update(m.visits)
            if i<2:states.append(g.state(m))
        assert states[0]==states[1];counts['action']=counts.get('action',0)+1
    audio_code=dict(zip(range(g.AUDIO,g.AUDIO+532,4),struct.unpack_from('>133I',rom,0x10344)))
    for active,delta,value,phase in itertools.product((0,5),(-31,0,1,255),(240,241,1440,1441),(0,8)):
        c=g.Case(delta=delta,value=value,phase=phase);initial=g.fixture(c);g.wr(initial,g.ACTOR,active);expected=g.reference(initial,c);wanted=expected[2]
        for j in range(4):wanted[g.MARK+j]=initial[g.MARK+j]
        states=[]
        for i,body in enumerate(bodies):
            m=ConnectedOracle(body,initial,c,connected=audio_code);m.run();assert(g.observable(m.memory,c),m.calls)==(g.observable(wanted,c),expected[1]),(c,active,i)
            visits.setdefault('audio',set()).update(m.visits)
            if i<2:states.append(g.state(m))
        assert states[0]==states[1];counts['audio_inactive']=counts.get('audio_inactive',0)+1
    assert set(range(g.OWNER,g.OWNER+56,4))<=visits['owner']
    assert set(range(g.ACTION,g.ACTION+72,4))<=visits['action']
    return dict(cases=counts,owner_words_reached=14,action_words_reached=18,audio_words_reached=len({p for p in visits['audio']if g.AUDIO<=p<g.AUDIO+532}),audio_full_provider_not_claimed=True)
