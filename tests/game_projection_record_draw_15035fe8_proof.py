"""Independent prefix/inductive-loop relation for quiet mapped o32 execution.

Complete 112-byte private/incoming state is compared at calls and exits.
Only the packet is exposed; providers may retain/mutate it and all public
state, but cannot inspect implementation PCs or unpassed private homes.
The loop invariant carries the last loaded byte count and its cached limit.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
from collections import Counter
from copy import deepcopy
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind
e=g.e;OUT=source.OUT;ENTRY=0x15035FE8;BASE=0x800C3F08;COUNT=0x800C3F00;DRAW=0x1502CCFC

def byte_value(v):return e.tagged(v,'AND')and v[2]==255 or isinstance(v,int)and 0<=v<=255

def predicate(s,op,a,b):
    # Exact unsigned-byte identity: 0 <s x iff x != 0.
    if op=='SLT'and a==0 and byte_value(b):return e.negate(e.pred('EQ',b,0))
    if op=='ULT':
        const,terms=e.linear(a)
        if const==BASE and b==BASE+1 and len(terms)==1:
            count,k=next(iter(terms.items()))
            if k==12 and byte_value(count)and e.choices(s,e.pred('EQ',count,0))==(False,):
                assert BASE+12*255<=e.U32
                return False
    return e.pred(op,a,b)

def bound_lemma():
    # For every positive byte c, 12*c-1 is in [11,3059]. Consequently
    # B+12*c >= B+1 for every B whose complete record array does not wrap.
    differences=[12*c-1 for c in range(1,256)]
    assert min(differences)==11 and max(differences)==3059
    checks=0
    for base in(0,4,BASE,BASE+0x12348,e.U32-12*255):
        for count in range(1,256):
            assert base+12*count<=e.U32 and not(base+12*count<base+1);checks+=1
    assert BASE<BASE+1 # count0 is an effective rejected-domain witness
    assert ((0xfffffff0+3*12)&e.U32)<0xfffffff1 # wrap is an effective witness
    return dict(positive_byte_counts=255,general_difference_range=[11,3059],independent_checks=checks,
                zero_count_and_wrapping_controls_effective=True,dominating_positive_count_required=True)

class State(g.State):
    def __init__(self,side):
        super().__init__(side);self.mem={off:('PRIVATE_ENTRY',off)for off in range(-104,8)}
        self.r=[('INITIAL',i)for i in range(32)];self.r[0]=0;self.r[4:6]=[('COMMANDS',),('VIEW',)]
        self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
        self.f=[('INITIAL_FP',i)for i in range(32)]
        for i in range(20,32):self.f[i]=('ENTRY_FP',i)
        self.cache=None;self.fcsr=('ENTRY_FCSR',);self.exposed=False
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert off%size==0 and-104<=off and off+size<=8,('private read bounds',off,size)
            return g.join([self.mem[off+i]for i in range(size)])
        e.plain(address);self.read_set[self.epoch,address,size]+=1
        value=('LOAD',address,size,self.epoch)
        if address==COUNT:
            assert size==1;self.cache=e.bitop('AND',value,255)
        return value
    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            off=address[1];assert off%size==0 and-104<=off and off+size<=8,('private write bounds',off,size)
            for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
        else:
            e.plain(address);e.plain(value)
            self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)));self.epoch+=1
    def frame(self):return tuple(self.mem[off]for off in range(-104,8))

class Program(g.Program):
    def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
    def step(self,s,w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0 and fn in(42,43):
            s.r[rd]=e.boolean(predicate(s,'SLT'if fn==42 else'ULT',s.r[rs],s.r[rt]));s.r[0]=0
        else:super().step(s,w)
    def call(self,s,target):
        assert target==DRAW and s.r[29]==('STACK',-104),('draw target/frame',target,s.r[29])
        args=tuple(s.r[4:8])+tuple(s.load(('STACK',-88+4*i),4)for i in range(4))
        assert args[5]==('STACK',-20)and args[6:]==(0,1),('packet/mode/extra ABI',args)
        for i,a in enumerate(args):
            if i!=5:e.plain(a)
        ordinal=sum(s.calls.values());s.calls[target]+=1;s.exposed=True
        s.trace.append(('CALL',target,args,s.fcsr));s.trace.append(('PRIVATE_FRAME',s.frame()));s.epoch+=1
        for off in range(-20,-4):s.mem[off]=('PROVIDER_PACKET_BYTE',ordinal,off)
        for i in range(8):s.store(('STACK',-104+4*i),4,('CALL_HOME',ordinal,i))
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        s.r[2]=('CURSOR_RESULT',ordinal);s.r[31]=('CALL_RETURN',ordinal)
        s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal);s.fcsr=('CALL_FCSR',ordinal);s.condition=('CALL_FCC',ordinal)
    def paths(self,start,stops,initial):
        pending=[(start,initial)];answers={};work=0
        while pending:
            pc,s=pending.pop();work+=1;s.steps+=1;assert work<1000 and s.steps<250,('unbounded proof',pc,work)
            if s.steps>1 and pc in stops:
                key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key)
                answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;delay=lambda n:self.step(n,self.instruction(pc+4))
            if op in(4,5,6,7,20,21,22,23):
                p=predicate(s,'EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else predicate(s,'SLT',0,s.r[rs])
                if op in(5,21,6,22):p=e.negate(p)
                for take in e.choices(s,p):
                    n=deepcopy(s);e.assume(n,p,take)
                    if take or op<20:delay(n)
                    dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;pending.append((dest,n))
            elif op==3:
                s.r[31]=self.entry+pc+8;delay(s);self.call(s,((self.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));pending.append((pc+8,s))
            elif op==0 and w&63==8:
                assert s.r[rs]==('RETURN',),('saved RA restoration',s.r[rs]);delay(s);pending.append((-4,s))
            else:self.step(s,w);pending.append((pc+4,s))
        return answers

def initial(side,phase,p,index=('INDEX',),count=None):
    s=State(side)
    if phase=='prefix':return s
    for word in p.words[:10]:p.step(s,word)
    for i in(1,2,3,*range(4,16),24,25,31):s.r[i]=('DEAD_LOOP_GPR',side,i)
    count=e.bitop('AND',('CACHED_COUNT_BYTE',),255)if count is None else count;s.cache=count
    s.r[16]=e.add(BASE,e.scale(index,12));s.r[17]=('CURSOR',);s.r[18]=('STACK',-20);s.r[19]=('VIEW',)
    skip=e.bitop('AND',('SKIP_BYTE',),255)
    if side=='raw':s.r[3]=e.add(BASE,e.scale(count,12));s.r[11]=skip
    else:s.r[4]=count;s.r[9]=skip
    for off in range(-20,-4):s.mem[off]=('CARRY_PACKET_BYTE',off)
    s.exposed=True;s.trace=[];s.read_set=Counter();s.epoch=0;s.facts={};s.steps=0
    return s

def observation(s,end,side,phase,index):
    if end=='return':
        assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('SP/RA restoration',)
        assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30)),('saved GPR restoration',)
        roles=(s.r[2],)
    else:
        next_index=0 if phase=='prefix'else e.add(index,1)
        assert s.r[29]==('STACK',-104)and s.r[16]==e.add(BASE,e.scale(next_index,12)),('record recurrence',s.r[16],next_index)
        assert s.r[18]==('STACK',-20)and s.r[19]==('VIEW',),('live packet/view roles',)
        assert(s.r[3]==e.add(BASE,e.scale(s.cache,12)))if side=='raw'else(s.r[4]==s.cache),('cached count/limit recurrence',)
        for reg,off in((16,-68),(17,-64),(18,-60),(19,-56),(31,-52)):
            assert s.load(('STACK',off),4)==(('RETURN',)if reg==31 else('ENTRY',reg)),('saved GPR home',reg,off)
        roles=(s.r[16],s.r[17],s.r[18],s.r[19],s.cache,s.r[11 if side=='raw'else 9])
    assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)],('saved FPR restoration',)
    return(s.trace,s.read_set,s.fcsr,s.frame(),roles)

def prove(raw,retail):
    bound_lemma();terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];reports={}
    for phase in('prefix','loop'):
        outputs=[]
        for side,p in enumerate(programs):
            label='raw'if side==0 else'retail';cut=48*4 if side==0 else 40*4
            states=p.paths(0 if phase=='prefix'else cut,{cut:'loop',-4:'return'},initial(label,phase,p))
            outputs.append({key:observation(s,key[0],label,phase,('INDEX',))for key,s in states.items()})
        a,b=outputs
        if a.keys()!=b.keys():
            (OUT/'proof-mismatch.txt').write_text(repr(('keys',phase,a.keys()-b.keys(),b.keys()-a.keys())))
            raise AssertionError(('predicate paths',phase,len(a),len(b)))
        for key,value in a.items():
            if value!=b[key]:
                part=next(i for i,(x,y)in enumerate(zip(value,b[key]))if x!=y)
                (OUT/'proof-mismatch.txt').write_text(repr((phase,key,part,value[part],b[key][part])))
                raise AssertionError(('transfer',phase,part))
        reports[phase]=len(a)
    assert[len(p.seen)for p in programs]==[90,88],('coverage',[len(p.seen)for p in programs])
    return dict(paths=reports,visited_words=[len(p.seen)for p in programs],full_private_bytes=112,private_at_calls_and_exits=True,
                loop_count_limit_and_record_recurrence=True,quiet_public_read_multiplicity=True,ordered_public_stores=True,
                opaque_full_FCSR=True,arbitrary_o32_providers=True,retained_packet_mutable=True,matching_credit=0)


from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields

def negative_controls(raw,retail):
    raw=list(raw)
    changes={'geometry-mode':{18:raw[18]^1},'color-byte':{50:raw[50]+1},
             'skip-byte':{47:raw[47]-1,81:raw[81]-1},'skip-record-stride':{49:raw[49]+4},
             'call-record-stride':{78:raw[78]+4},'saved-return-home':{7:raw[7]-4},
             'packet-pointer':{46:raw[46]+4},'return-cursor':{82:0x00001025},
             'mode-argument':{65:raw[65]|(24<<16)}}
    rejected={}
    for name,updates in changes.items():
        changed=raw[:]
        for i,w in updates.items():assert changed[i]!=w;changed[i]=w
        try:prove(changed,retail)
        except AssertionError as error:
            message=str(error);assert not any(s in message for s in('unsupported','unbounded','escaped code')),message
            rejected[name]=message
        else:raise AssertionError('Ineffective control: '+name)
    alternate=[]
    for w in raw:
        changed=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in(8,9):changed=(changed&~(31<<shift))|((17-reg)<<shift)
        alternate.append(changed)
    assert alternate!=raw;positive=prove(alternate,retail)
    r=dict(effective_controls=len(rejected),rejected=rejected,positive_T0_T1_reallocation=True,
           positive_paths=positive['paths'],bound_lemma=bound_lemma(),matching_credit=0)
    (OUT/'proof-controls.json').write_text(json.dumps(r,indent=2)+'\n')
    return r
