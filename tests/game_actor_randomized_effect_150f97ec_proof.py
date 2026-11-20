"""Instruction-driven normal relation, with all private bytes and ordered FP.

Mapped quiet public memory, no public/private alias, valid o32 stack and normal
implemented nontrapping FP instructions. Providers preserve saved registers and
may mutate public state, exposed pointer homes and retained point/scale buffers;
they cannot inspect PCs, unused registers or unpassed private homes. Void return
is qualified by the known caller's ignored V0. No fault/interrupt claim.
"""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as source
e=g.e;OUT=source.OUT;ROOT=source.ROOT;ENTRY=0x150F97EC
TRANSFORM,REAL,INTEGER,SUBMIT=0x15145EA4,0x150ADA68,0x150ADA20,0x15102B38
class State(g.State):
    def __init__(self,side):
        super().__init__(side);self.exposed=False;self.exposed_scale=False
        self.r=[('INITIAL',i)for i in range(32)];self.r[0]=0;self.r[4:7]=[('ACTOR',),('PRIORITY',),('PARAMETER',)];self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
        self.f=[('INITIAL_FP',i)for i in range(32)]
        for i in range(20,32):self.f[i]=('ENTRY_FP',i)
        self.mem={off:('PRIVATE_ENTRY',off)for off in range(-112,12)};self.fcsr=('ENTRY_FCSR',)
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert off%size==0 and-112<=off and off+size<=12,('private read',off,size)
            return g.join([self.mem[off+i]for i in range(size)])
        e.plain(address);self.read_set[self.epoch,address,size]+=1
        return('LOAD',address,size,self.epoch)
    def store(self,address,size,value):
        assert e.tagged(address,'STACK'),('unexpected root public store',address)
        off=address[1];assert off%size==0 and-112<=off and off+size<=12,('private store',off,size)
        for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
    def frame(self):return tuple(self.mem[off]for off in range(-112,12))
class Program(g.Program):
    def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
    def call(self,s,target):
        assert target in(TRANSFORM,REAL,INTEGER,SUBMIT),hex(target);assert s.r[29]==('STACK',-112)
        n={TRANSFORM:4,REAL:0,INTEGER:0,SUBMIT:14}[target]
        args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-96+4*i),4)for i in range(max(0,n-4)))
        for i,arg in enumerate(args):
            if target==TRANSFORM and i in(0,1):
                assert arg==('STACK',-28 if i==0 else-32),('matrix pointer-home ABI',i,arg)
            elif target==SUBMIT and i in(4,8):
                assert arg==('STACK',-24 if i==4 else-12),('effect buffer ABI',i,arg)
            else:e.plain(arg)
        if target==TRANSFORM:
            assert s.load(('STACK',-28),4)==0x800A1C48
            assert s.load(('STACK',-32),4)==('STACK',-12)
            assert args[3]==1;s.exposed=True
        if target==SUBMIT:s.exposed_scale=True
        ordinal=sum(s.calls.values());s.calls[target]+=1
        s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()));s.epoch+=1
        if s.exposed:
            for off in(*range(-32,-24),*range(-12,0)):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        if s.exposed_scale:
            for off in range(-24,-16):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        for i in range(max(4,n)):s.store(('STACK',-112+i*4),4,('CALL_HOME',ordinal,i))
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        s.r[2]=('RESULT',target,ordinal)
        if target==REAL:s.f[0]=('REAL_RESULT',ordinal)
        s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_FCC',ordinal)
def observation(s):
    assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('SP/RA restoration',s.r[29],s.r[31])
    assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30)),('saved GPR',)
    assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('saved FPR',)
    return(s.trace,s.read_set,s.divisors,s.fcsr,s.frame())
def prove(raw,retail):
    terms=Terms();programs=[Program(words,terms)for words in(raw,retail)];results=[]
    for side,p in enumerate(programs):
        states=p.paths(0,{-4:'return'},State(side));results.append({k:observation(s)for k,s in states.items()})
    a,b=results;assert a.keys()==b.keys(),('predicates',a.keys()-b.keys(),b.keys()-a.keys())
    for key,value in a.items():
        want=b[key]
        if value!=want:
            part=next(i for i,(x,y)in enumerate(zip(value,want))if x!=y)
            (OUT/'proof-mismatch.txt').write_text(repr((key,part,value[part],want[part])))
            raise AssertionError(('transfer',part,'see proof-mismatch.txt'))
    assert[len(p.seen)for p in programs]==[len(raw),len(retail)],('coverage',[len(p.seen)for p in programs])
    return dict(paths=len(a),visited_words=[len(p.seen)for p in programs],ordered_FP_and_FCSR=True,
        public_read_multiplicity=True,private_bytes=124,private_frame_at_all_calls=True,private_frame_at_return=True,
        arbitrary_o32_providers=True,mutable_retained_pointer_homes_point_scale=True,void_return_ignored_by_caller=True,matching_credit=0)

from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields

def negative_controls(raw,retail):
    changes={'actor-field':{8:raw[8]+4},'matrix-count':{19:0x24070002},'unit-factor':{24:0x3C014000},
             'unsigned-modulo-divisor':{45:0x24010004},'point-buffer':{67:raw[67]+4},
             'final-parameter-home':{83:raw[83]-4},'saved-return-home':{1:raw[1]-4},'FP-operation':{28:raw[28]^1}}
    rejected={}
    for name,updates in changes.items():
        other=list(raw)
        for i,w in updates.items():assert other[i]!=w,(name,i);other[i]=w
        try:prove(other,retail)
        except AssertionError as error:
            text=str(error);assert not any(s in text for s in('unsupported','unbounded','escaped code')),text
            rejected[name]=text[:400]
        else:raise AssertionError(('control accepted',name))
    alternate=[]
    for w in raw:
        changed=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in(8,9):changed=(changed&~(31<<shift))|((17-reg)<<shift)
        alternate.append(changed)
    assert alternate!=list(raw);positive=prove(alternate,retail)
    report=dict(effective_controls=len(rejected),rejected=rejected,positive_T0_T1_reallocation=True,positive_paths=positive['paths'],matching_credit=0)
    (OUT/'proof-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report
