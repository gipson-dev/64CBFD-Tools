"""Independent prefix/one-iteration proof, with ordinary nonfaulting ABI providers.

Private frame is disjoint from public objects. Public reads are stable between
writes/calls. Providers can mutate public memory and the retained passed depth
word; they cannot inspect implementation PCs, unpassed locals or non-argument
registers. Palette indices are zero/one, the enabled point selector is one,
and the 32-byte readonly block has its verified retail values. This is not a
raw fault-register, hardware, timing or C undefined-input equivalence claim.
"""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_list_render_1517e28c_recovery as source
from tools.tests import game_list_render_1517e28c_oracle as abi
e=g.e
READONLY=struct.pack('>3f5I',-73.,80.,-95.,0,0x8008CFF0,0x00010000,0x07030000,0x011E0000)

class State(g.State):
    def __init__(self,side,kind):
        super().__init__(side);self.kind=kind;self.exposed=False
        self.mem={off:('PRIVATE_ENTRY',off)for off in range(-120,24)}
        self.r=[('INITIAL_GPR',i)for i in range(32)];self.r[0]=0
        self.r[4:6]=[('COMMANDS',),('UNUSED_CATEGORY',)]
        self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        for r in(*range(16,24),28,30):self.r[r]=('ENTRY',r)
        self.f=[('INITIAL_FP',i)for i in range(32)]
        for r in range(20,32):self.f[r]=('ENTRY_FP',r)
        self.fcsr=('ENTRY_FCSR',)
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and-120<=off and off+size<=24,('private read bounds',off,size)
            return g.join([self.mem[off+i]for i in range(size)])
        e.plain(address);self.read_set[self.epoch,address,size]+=1
        if isinstance(address,int)and 0x8008CFF0<=address and address+size<=0x8008D010:
            at=address-0x8008CFF0;return int.from_bytes(READONLY[at:at+size],'big')
        if size==1 and address==e.add(self.r[16],0x2F):return self.kind
        # The only non-null entry in the verified two-pointer table is index one.
        context=('LOAD',abi.CONTEXT,4,self.epoch)
        if size==1 and address==e.add(context,16):return 1
        return('LOAD',address,size,self.epoch)
    def store(self,address,size,value):
        if not e.tagged(address,'STACK'):return super().store(address,size,value)
        off=address[1];assert size in(1,2,4)and off%size==0 and-120<=off and off+size<=24,('private write bounds',off,size)
        for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
    def frame(self):return tuple(self.mem[off]for off in range(-120,24))

class Program(g.Program):
    def __init__(self,words,terms):
        e.Program.__init__(self,words,b'',abi.ENTRY);self.terms=terms;self.seen=set()
    def call(self,s,target):
        assert target in(abi.POINT,abi.DEPTH,abi.DRAW),hex(target)
        assert s.r[29]==('STACK',-120)
        if target==abi.POINT:args=(s.f[12],s.f[14],s.r[6],s.r[7],s.load(('STACK',-104),4))
        else:
            n=2 if target==abi.DEPTH else 7
            args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-104+4*i),4)for i in range(max(0,n-4)))
        if target==abi.DEPTH:
            assert args==(s.r[16],('STACK',-12)),('exposed output ABI',args)
            s.exposed=True
        for i,arg in enumerate(args):
            if target!=abi.DEPTH or i!=1:e.plain(arg)
        ordinal=sum(s.calls.values());s.calls[target]+=1
        s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()))
        s.epoch+=1
        if s.exposed:
            for off in range(-12,-8):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        for i in range(4):s.store(('STACK',-120+4*i),4,('CALL_HOME',ordinal,i))
        for r in(1,2,3,*range(4,16),24,25):s.r[r]=('CALLER',ordinal,r)
        for r in range(20):s.f[r]=('CALLER_FP',ordinal,r)
        s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal)
        s.lo,s.hi,s.fcsr=('CALL_LO',ordinal),('CALL_HI',ordinal),('CALL_FCSR',ordinal)
        s.condition=('CALL_CONDITION',ordinal)

def initial(side,kind,phase,p):
    state=State(side,kind)
    if phase=='prefix':return state
    for i,w in enumerate(p.words[:38]):
        if i==33:continue
        p.step(state,w)
    state.r[16]=('NODE',);state.r[17]=('CARRY_SKIP',);state.r[18]=('CARRY_STRENGTH',);state.r[20]=('CURSOR',)
    for i in range(4):state.mem[-12+i]=('CARRY_DEPTH_BYTE',i)
    state.exposed=True;state.epoch=0
    state.r[14]=e.bitop('AND',state.load(e.add(state.r[16],0x30),1),255)
    state.trace=[];state.read_set=Counter();state.facts={};state.steps=0
    e.assume(state,e.pred('EQ',state.r[16],0),False)
    return state

def observation(state,ending):
    if ending=='return':
        assert state.r[29]==('STACK',0)and state.r[31]==('RETURN',)
        assert all(state.r[r]==('ENTRY',r)for r in(*range(16,24),28,30))
        assert state.f[20:]==[('ENTRY_FP',r)for r in range(20,32)]
        roles=(state.r[2],)
    else:
        assert state.r[29]==('STACK',-120)
        assert state.r[19]==1 and state.r[21:24]==[('STACK',-24),('STACK',-28),('STACK',-32)]
        assert state.r[30]==abi.GATE
        for r,off in [(r,-80+4*(r-16))for r in range(16,24)]+[(30,-48)]:
            assert state.load(('STACK',off),4)==('ENTRY',r),('saved register home',r,off)
        assert state.load(('STACK',-44),4)==('RETURN',)
        roles=(state.r[16],state.r[18],state.r[20],state.r[14])
    return(state.trace,state.read_set,state.fcsr,state.frame(),roles)

def prove(raw,retail):
    assert len(raw)==132 and len(retail)==135
    assert raw[0]==retail[0]==0x27BDFF88
    terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];counts={}
    for phase in('prefix','loop'):
        for kind in(0,1):
            answers=[]
            for side,p in enumerate(programs):
                paths=p.paths(0 if phase=='prefix'else 0x98,{0x98:'loop',-4:'return'},initial('raw'if side==0 else'retail',kind,phase,p))
                answers.append({key:observation(state,key[0])for key,state in paths.items()})
            a,b=answers
            assert a.keys()==b.keys(),('path predicates',phase,kind,len(a),len(b),repr(next(iter(a.keys()-b.keys()),None))[:500],repr(next(iter(b.keys()-a.keys()),None))[:500])
            for key,value in a.items():
                wanted=b[key]
                if value!=wanted:
                    part=next(i for i,(x,y)in enumerate(zip(value,wanted))if x!=y)
                    if part==0:
                        at=next((i for i,(x,y)in enumerate(zip(value[0],wanted[0]))if x!=y),None)
                        raise AssertionError(('trace',phase,kind,at,repr(value[0][at]if at is not None else value[0])[:2000],repr(wanted[0][at]if at is not None else wanted[0])[:2000]))
                    raise AssertionError(('transfer',phase,kind,part,repr(value[part])[:2000],repr(wanted[part])[:2000]))
            counts[phase+'-kind'+str(kind)]=len(a)
    visited=[len(p.seen)for p in programs]
    assert visited==[132,134],visited
    assert set(range(0,135*4,4))-programs[1].seen=={91*4}
    return dict(paths=counts,visited_words=visited,prefix_and_inductive_iteration_equal=True,full_144_private_and_incoming_bytes=True,
        ordered_public_writes_ABI_calls_and_FCSR=True,complete_private_frame_at_each_call=True,
        arbitrary_public_and_retained_output_mutations=True,valid_palette_indices=[0,1],valid_point_selector=1,
        raw_fault_register_or_hardware_claim=False)

def negative_controls(raw,retail):
    controls={}
    def reject(name,words):
        try:prove(words,retail)
        except(AssertionError,ValueError,KeyError)as error:
            assert not any(w in str(error).lower()for w in('unsupported','unbounded','out of range')),(name,error)
            controls[name]=repr(error.args)[:300]
        else:raise AssertionError(('Ineffective proof control',name))
    def one(name,predicate,change):
        hits=[i for i,w in enumerate(raw)if predicate(w)];assert len(hits)==1,(name,hits)
        bad=list(raw);at=hits[0];bad[at]=change(bad[at]);assert bad[at]!=raw[at];reject(name,bad)
    one('wrong-output-home',lambda w:w==0x27A5006C,lambda w:w+4)
    one('inclusive-depth',lambda w:w>>26==10 and w&65535==30,lambda w:w+1)
    one('wrong-depth-arithmetic',lambda w:w==0x018F7023,lambda w:w^2)
    one('wrong-point-route-mask',lambda w:w==0x30590001,lambda w:w^5)
    one('wrong-sample-sentinel',lambda w:w==0x3401FFFC,lambda w:w^4)
    one('wrong-intensity-clear',lambda w:w==0xA0600000,lambda w:0)
    one('wrong-saved-return-home',lambda w:w==0xAFBF004C,lambda w:w-4)
    bad=[(w&0xFFFF0000)|0x28 if w>>26==35 and w>>21&31==16 and w>>16&31==16 and w&65535==0x24 else w for w in raw]
    assert bad!=list(raw);reject('wrong-next-link',bad)
    return dict(effective_semantic_controls=len(controls),controls=controls)
