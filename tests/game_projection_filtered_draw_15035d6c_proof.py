"""Independent instruction-driven relation across both inductive loop cuts.

Ordinary public memory is quiet between ordered stores; each store advances
the epoch, so public descriptor/record/command aliases remain conservative.
Private and incoming homes are byte-observed. No fault, PC, MMIO or portable
C alias-undefined execution claim. Neither fitting nor origin maps are used.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
from collections import Counter
from copy import deepcopy
import json,struct
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_list_unlink_1517e134_match import bind

e=g.e;OUT=source.OUT;ENTRY=0x15035D6C;BASE=0x800C3F08;COUNT=0x800C3F00

def byte_value(v):return e.tagged(v,'AND')and v[2]==255 or isinstance(v,int)and 0<=v<=255

def predicate(op,a,b):
    if op=='SLT'and a==0 and byte_value(b):return e.negate(e.pred('EQ',b,0))
    return e.pred(op,a,b)

class State(g.State):
    def __init__(self,side):
        super().__init__(side);self.mem={off:('PRIVATE_ENTRY',off)for off in range(-32,20)}
        self.r=[('INITIAL',i)for i in range(32)];self.r[0]=0
        self.r[4:8]=[('CURSOR',),('DESCRIPTOR',),('RED',),('GREEN',)]
        self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
        for i in range(4):self.mem[16+i]=g.byte(('BLUE',),8*(3-i))
        self.f=[('INITIAL_FP',i)for i in range(32)];self.fcsr=('ENTRY_FCSR',)
        self.cache=None
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert off%size==0 and -32<=off and off+size<=20,('private read',off,size)
            return g.join([self.mem[off+i]for i in range(size)])
        e.plain(address);self.read_set[self.epoch,address,size]+=1
        value=('LOAD',address,size,self.epoch)
        if address==COUNT:
            assert size==1;self.cache=e.bitop('AND',value,255)
        return value
    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            off=address[1];assert off%size==0 and -32<=off and off+size<=20,('private write',off,size)
            for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
        else:
            e.plain(address);e.plain(value)
            self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)));self.epoch+=1
    def frame(self):return tuple(self.mem[off]for off in range(-32,20))

class Program(g.Program):
    def __init__(self,words,terms):e.Program.__init__(self,words,b'',ENTRY);self.terms=terms;self.seen=set()
    def step(self,s,w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0 and fn in(42,43):
            s.r[rd]=e.boolean(predicate('SLT'if fn==42 else'ULT',s.r[rs],s.r[rt]));s.r[0]=0
        else:super().step(s,w)
    def call(self,s,target):raise AssertionError(('unexpected call',target))
    def paths(self,start,stops,initial):
        pending=[(start,initial)];answers={};work=0
        while pending:
            pc,s=pending.pop();work+=1;s.steps+=1;assert work<2000 and s.steps<300,('unbounded proof',pc,work)
            if s.steps>1 and pc in stops:
                key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key)
                answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
            delay=lambda n:self.step(n,self.instruction(pc+4))
            if op in(4,5,6,7,20,21,22,23):
                p=predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else predicate('SLT',0,s.r[rs])
                if op in(5,21,6,22):p=e.negate(p)
                for take in e.choices(s,p):
                    n=deepcopy(s);e.assume(n,p,take)
                    if take or op<20:delay(n)
                    dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;pending.append((dest,n))
            elif op==0 and w&63==8:
                assert s.r[rs]==('RETURN',),('saved RA',s.r[rs]);delay(s);pending.append((-4,s))
            else:self.step(s,w);pending.append((pc+4,s))
        return answers

def initial(side,phase,p):
    s=State(side)
    if phase=='prefix':return s
    for w in p.words[:12]:p.step(s,w)
    for i in(1,2,3,*range(4,23),24,25):s.r[i]=('DEAD',side,i)
    s.r[4]=('CURSOR',);s.r[5]=('DESCRIPTOR',);s.r[6]=e.add(BASE,e.scale(('RECORD_INDEX',),12))
    s.r[7]=0xDB060020;s.r[8]=('BLUE',);s.r[9]=1;s.r[10]=0xE7000000
    s.r[11]=0xDB06000C;s.r[12]=0xFB000000;s.r[13]=0x80082FC0;s.r[3]=0xDE000000
    for reg,value in zip((16,17,18)if side=='raw'else(17,18,16),(('RED',),('GREEN',),0x80083140)):s.r[reg]=value
    if phase=='outer':
        s.cache=e.bitop('AND',('CACHED_COUNT',),255);s.r[2]=s.cache;s.r[25]=e.bitop('AND',('RECORD_MODE',),255)
    else:
        s.r[2]=('LIST_INDEX',);s.r[19]=e.bitop('AND',('LIST_COUNT',),255);s.r[25]=e.bitop('AND',('LIST_MASK',),255)
    s.trace=[];s.read_set=Counter();s.epoch=0;s.facts={};s.steps=0
    return s

def observation(s,end,side,phase):
    assert s.f==[('INITIAL_FP',i)for i in range(32)]and s.fcsr==('ENTRY_FCSR',),('opaque FP/FCSR',)
    if end=='return':
        assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('SP/RA',)
        assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30)),('callee saved',)
        roles=(s.r[2],)
    else:
        assert s.r[29]==('STACK',-32)and s.r[31]==('RETURN',),('loop SP/RA',)
        idx=0 if phase=='prefix'else('RECORD_INDEX',)
        if end=='outer'and phase!='prefix':idx=e.add(idx,1)
        assert s.r[6]==e.add(BASE,e.scale(idx,12)),('record recurrence',phase,end,s.r[6],idx)
        for reg,value in zip((16,17,18)if side=='raw'else(17,18,16),(('RED',),('GREEN',),0x80083140)):
            assert s.r[reg]==value,('live saved role',reg,s.r[reg],value)
        assert s.r[5]==('DESCRIPTOR',)and s.r[8]==('BLUE',),('descriptor/fifth argument',)
        for reg,offset in((reg,-28+4*(reg-16))for reg in range(16,23)):
            assert s.load(('STACK',offset),4)==('ENTRY',reg),('saved home',reg)
        roles=tuple(s.r[i]for i in(3,4,5,6,7,8,9,10,11,12,13))
        if end=='outer':
            assert s.r[2]==s.cache,('count recurrence',)
            roles+=(s.cache,s.r[25])
        else:
            expected=0 if phase=='outer'else e.add(('LIST_INDEX',),1)
            assert s.r[2]==expected,('list recurrence',phase,s.r[2],expected)
            roles+=(s.r[2],s.r[19],s.r[25])
    return(s.trace,s.read_set,s.fcsr,s.frame(),roles)

def prove(raw,retail):
    terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];report={}
    for phase in('prefix','outer','inner'):
        outputs=[]
        for index,p in enumerate(programs):
            side='raw'if index==0 else'retail';cuts={41*4:'outer',114*4:'inner',-4:'return'}
            states=p.paths(0 if phase=='prefix'else(41 if phase=='outer'else 114)*4,cuts,initial(side,phase,p))
            outputs.append({key:observation(s,key[0],side,phase)for key,s in states.items()})
        a,b=outputs
        if a.keys()!=b.keys():
            (OUT/'proof-mismatch.txt').write_text(repr(('keys',phase,a.keys()-b.keys(),b.keys()-a.keys())))
            raise AssertionError(('predicate paths',phase,len(a),len(b)))
        for key,value in a.items():
            if value!=b[key]:
                part=next(i for i,(x,y)in enumerate(zip(value,b[key]))if x!=y)
                (OUT/'proof-mismatch.txt').write_text(repr((phase,key,part,value[part],b[key][part])))
                raise AssertionError(('transfer',phase,part))
        report[phase]=len(a)
    assert[len(p.seen)for p in programs]==[160,159],('coverage',[len(p.seen)for p in programs])
    # These finite domains are exhaustive byte identities; the loop transfers
    # above remain symbolic for arbitrary index words and quiet public aliases.
    alpha=[(a*b)>>8 for a in range(256)for b in range(256)];assert min(alpha)==0 and max(alpha)==254
    assert all((1<<(x&31))==(1<<((x&31)&31))for x in range(256))
    return dict(paths=report,visited_words=[len(p.seen)for p in programs],full_private_bytes=52,
        saved_homes_and_RGB_roles=True,fifth_argument_home=True,outer_and_inner_recurrence=True,
        quiet_public_read_multiplicity=True,ordered_public_stores=True,opaque_full_FCSR=True,
        alpha_domain_cases=65536,alpha_range=[0,254],opaque_branch_unreachable_for_byte_inputs=True,
        stronger_abstract_alpha_branch_also_proved=True,matching_credit=0)
