"""Independent symbolic transfer proof for the initializer scheduling proposal.

No register-color/schedule template is used by the proof engine. Instructions
drive every effect and branch, including annulled likely delays. Loop cuts are
inductive: arbitrary indices and matching 48-byte cursors are supplied, and all
successors must preserve the relation. Fresh symbolic public reads and opaque
ABI calls deliberately avoid assuming records, actors or mutable globals are
disjoint. The one allowed public commute is the fixed state/count pair.

Contract: mapped/aligned code, immutable implementation literals, valid private
stack, and no public alias of private stack/literal storage. Opaque providers
cannot inspect the caller's code, return PC, implementation literals or unpassed
locals. They preserve o32 saved registers; their mutable public effects, caller
registers and FCSR are otherwise arbitrary. Literal jump pointers may only feed JR. This is normal
execution equivalence, not raw fault-state or portable C undefined-input proof.
"""
from collections import Counter
from copy import deepcopy
import json,struct

U32=0xffffffff
def signed(n):return((n&U32)^0x80000000)-0x80000000
def linear(value):
    if isinstance(value,int):return value&U32,{}
    if value[0]=='LINEAR':return value[1],dict(value[2])
    return 0,{value:1}
def affine(const,terms):
    terms=tuple(sorted(((v,k&U32)for v,k in terms.items()if k&U32),key=repr));const&=U32
    if not terms:return const
    if const==0 and len(terms)==1 and terms[0][1]==1:return terms[0][0]
    return('LINEAR',const,terms)
def scale(value,k):
    assert not tagged(value,'STACK')
    c,t=linear(value);return affine(c*k,{v:n*k for v,n in t.items()})
def add(a,b):
    if tagged(a,'STACK')and isinstance(b,int):return('STACK',a[1]+signed(b))
    if tagged(b,'STACK')and isinstance(a,int):return add(b,a)
    assert not tagged(a,'STACK')and not tagged(b,'STACK'),('stack arithmetic',a,b)
    c,t=linear(a);d,u=linear(b)
    for v,k in u.items():t[v]=t.get(v,0)+k
    return affine(c+d,t)
def tagged(value,tag):return isinstance(value,tuple)and value[0]==tag
def has_tag(value,tag):
    return isinstance(value,tuple)and(tagged(value,tag)or any(has_tag(v,tag)for v in value))
def plain(value):
    assert not has_tag(value,'JT')and not has_tag(value,'STACK'),('escaped private/literal pointer',value)
    return value
def bitop(op,a,b):
    plain(a);plain(b)
    if isinstance(a,int)and isinstance(b,int):return(a&b if op=='AND'else a|b)&U32
    if a==b:return a
    if op=='AND'and(a==0 or b==0):return 0
    if op=='OR'and(a==0 or b==0):return b if a==0 else a
    if op=='AND'and(a==U32 or b==U32):return b if a==U32 else a
    if isinstance(a,int)and not isinstance(b,int):a,b=b,a
    if op=='AND'and isinstance(b,int)and tagged(a,'AND')and isinstance(a[2],int):return bitop(op,a[1],b&a[2])
    return(op,a,b)if isinstance(b,int)else(op,*sorted((a,b),key=repr))
def pred(op,a,b):
    plain(a);plain(b)
    if op=='EQ':
        if a==b:return True
        if tagged(a,'BOOL')and b in(0,1):return a[1]if b else negate(a[1])
        if tagged(b,'BOOL')and a in(0,1):return pred(op,b,a)
    if isinstance(a,int)and isinstance(b,int):
        return a==b if op=='EQ'else a<b if op=='ULT'else signed(a)<signed(b)
    if op=='EQ':return(op,*sorted((a,b),key=repr))
    return(op,a,b)
def negate(p):
    if isinstance(p,bool):return not p
    return p[1]if tagged(p,'NOT')else('NOT',p)
def boolean(p):return int(p)if isinstance(p,bool)else('BOOL',p)
def choices(s,p):
    if isinstance(p,bool):return(p,)
    if tagged(p,'NOT'):return tuple(not v for v in choices(s,p[1]))
    return(s.facts[p],)if p in s.facts else(False,True)
def assume(s,p,value):
    if isinstance(p,bool):assert p==value;return
    if tagged(p,'NOT'):assume(s,p[1],not value);return
    assert p not in s.facts or s.facts[p]==value
    s.facts[p]=value

class State:
    def __init__(self,side,phase):
        self.r=[('DEAD',side,phase,i)for i in range(32)];self.r[0]=0;self.r[29]=('STACK',-88)
        self.f=[('DEAD_FP',side,phase,i)for i in range(32)]
        for i in(16,17,18,19,20,21,22,23,28,30):self.r[i]=('ENTRY',i)
        for i in range(20,32):self.f[i]=('ENTRY_FP',i)
        self.r[16]=0x800d20fc;self.fcsr=('FCSR',phase);self.hi=('DEAD_HI',side);self.lo=('DEAD_LO',side)
        self.mem={-56:('ENTRY',16),-52:('RETURN',),0:('CATEGORY',)}
        self.reads=Counter();self.calls=Counter();self.trace=[];self.facts={};self.steps=0;self.side=side
    def private(self,address):
        assert tagged(address,'STACK')
        return address[1]
    def store(self,address,size,value):
        plain(value)
        value=bitop('AND',value,(1<<(8*size))-1)
        if tagged(address,'STACK'):
            assert size==4 and address[1]%4==0;self.mem[address[1]]=value
        else:self.trace.append(('WRITE',plain(address),size,value))
    def load(self,address,size,pool):
        if tagged(address,'STACK'):
            assert size==4 and address[1]%4==0
            return self.mem.get(address[1],('DEAD_HOME',self.side,address[1]))
        plain(address)
        base=0x80096760
        # Symbolic table indices must have the actual dominating range check.
        for offset,count,name in((0,38,'bank'),(0xa8,41,'resource')):
            indices=[p[1]for p,v in self.facts.items()if v and p[0]=='ULT'and p[2]==count]
            if isinstance(address,int)and base+offset<=address<base+offset+count*4:
                assert(address-base-offset)%4==0;indices.append((address-base-offset)//4)
            for index in indices:
                if size==4 and address==add(base+offset,scale(index,4)):
                    self.trace.append(('READ_TABLE',name,index))
                    return('JT',name,index)
        if isinstance(address,int)and base<=address<base+len(pool):
            assert size==4 and address in(base+0xa0,base+0xa4)
            value=struct.unpack_from('>I',pool,address-base)[0]
            self.trace.append(('READ_LITERAL',address,size,value));return value
        key=(address,size);epoch=self.reads[key];self.reads[key]+=1
        self.trace.append(('READ',address,size));return('LOAD',address,size,epoch)

class Program:
    def __init__(self,words,pool,entry):self.words,self.pool,self.entry=words,pool,entry
    def instruction(self,pc):
        assert pc%4==0 and 0<=pc<len(self.words)*4,('escaped code',hex(pc))
        return self.words[pc//4]
    def step(self,s,w):
        if w==0:return
        op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        imm=signed((w&65535)|(-65536 if w&32768 else 0));a,b=s.r[rs],s.r[rt]
        if op==0:
            if fn==0:plain(b);v=scale(b,1<<sa)
            elif fn in(2,3):
                plain(b)
                v=(signed(b)>>sa if fn==3 else b>>sa)&U32 if isinstance(b,int)else('ASR'if fn==3 else'LSR',b,sa)
            elif fn==4:
                plain(a);plain(b)
                v=scale(b,1<<(a&31))if isinstance(a,int)else('SHLV',b,bitop('AND',a,31))
            elif fn in(33,35):
                if fn==35:plain(a);plain(b)
                else:
                    assert not has_tag(a,'JT')and not has_tag(b,'JT')
                v=add(a,b if fn==33 else scale(b,-1))
            elif fn in(36,37):v=bitop('AND'if fn==36 else'OR',a,b)
            elif fn in(42,43):v=boolean(pred('SLT'if fn==42 else'ULT',a,b))
            elif fn in(16,18):v=s.hi if fn==16 else s.lo
            elif fn in(25,27):
                plain(a);plain(b)
                if fn==27:
                    assert isinstance(b,int)and b!=0,('unproven divisor',b)
                    s.lo=a//b if isinstance(a,int)else('UDIV',a,b)
                    s.hi=a%b if isinstance(a,int)else('UREM',a,b)
                elif isinstance(a,int)and isinstance(b,int):s.lo=(a*b)&U32;s.hi=(a*b)>>32
                else:
                    s.lo=scale(a,b)if isinstance(b,int)else scale(b,a)if isinstance(a,int)else('MUL',*sorted((a,b),key=repr))
                    s.hi=('MULHI',*sorted((a,b),key=repr))
                return
            else:raise AssertionError(('unsupported R op',hex(w)))
            s.r[rd]=v
        elif op==9:
            assert not has_tag(a,'JT');s.r[rt]=add(a,imm)
        elif op in(10,11):s.r[rt]=boolean(pred('SLT'if op==10 else'ULT',a,imm&U32))
        elif op in(12,13):s.r[rt]=bitop('AND'if op==12 else'OR',a,w&65535)
        elif op==15:s.r[rt]=(w&65535)<<16
        elif op in(32,33,35,36,37,40,41,43,49,57):
            assert not has_tag(a,'JT');address=add(a,imm)
            size={32:1,33:2,35:4,36:1,37:2,40:1,41:2,43:4,49:4,57:4}[op]
            if op in(40,41,43,57):s.store(address,size,s.f[rt]if op==57 else b)
            else:
                value=s.load(address,size,self.pool)
                if op in(32,33):value=((value^(1<<(size*8-1)))-(1<<(size*8-1)))&U32 if isinstance(value,int)else('SEXT',size*8,value)
                if op==49:s.f[rt]=value
                else:s.r[rt]=value
        elif op==17:
            if rs==0:s.r[rt]=s.f[rd]
            elif rs==16 and fn==13:
                value=plain(s.f[rd]);s.trace.append(('TRUNC_W_S',value,s.fcsr))
                s.f[sa]=('TRUNC',value,s.fcsr);s.fcsr=('TRUNC_STATUS',value,s.fcsr)
            else:raise AssertionError(('unsupported COP1',hex(w)))
        else:raise AssertionError(('unsupported op',hex(w)))
        s.r[0]=0
    def call(self,s,target):
        from tools.tests.game_record_initializer_150169a0_oracle import COUNTS
        assert target in COUNTS,('unknown helper',hex(target))
        n=COUNTS[target];args=s.r[4:4+min(n,4)]
        if n>4:args+=[s.load(add(s.r[29],16+4*i),4,self.pool)for i in range(n-4)]
        for a in args:plain(a)
        s.trace.append(('CALL',target,tuple(args),s.fcsr))
        ordinal=s.calls[target];s.calls[target]+=1
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',target,ordinal,i)
        s.r[2]=('RESULT',target,ordinal)
        for i in range(20):s.f[i]=('CALLER_FP',target,ordinal,i)
        s.hi=('CALLER_HI',target,ordinal);s.lo=('CALLER_LO',target,ordinal)
        s.fcsr=('CALLER_FCSR',target,ordinal)
        for i in range(0,32,4):s.mem[s.r[29][1]+i]=('CALL_HOME',target,ordinal,i)
    def paths(self,start,stops,initial):
        states=[(start,initial)];answers={};work=0
        def push(pc,s):states.append((pc,s))
        while states:
            pc,s=states.pop();work+=1;s.steps+=1
            assert work<200000 and s.steps<1500,('unbounded proof',start,len(answers),hex(pc))
            if s.steps>1 and pc in stops:
                key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)))
                assert key not in answers,('duplicate proof path',key)
                answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31
            delay=lambda state:self.step(state,self.instruction(pc+4))
            if op in(4,5,6,7,20,21,22,23):
                if op in(4,5,20,21):condition=pred('EQ',s.r[rs],s.r[rt])
                else:assert rt==0;condition=pred('SLT',0,s.r[rs])
                if op in(5,21,6,22):condition=negate(condition)
                for taken in choices(s,condition):
                    n=deepcopy(s);assume(n,condition,taken)
                    if taken or op<20:delay(n)
                    dest=pc+4+4*((w&65535)^32768)-4*32768 if taken else pc+8
                    push(dest,n)
            elif op==3:
                s.r[31]=self.entry+pc+8;delay(s)
                target=((self.entry+pc+4)&0xf0000000)|((w&0x3ffffff)<<2)
                self.call(s,target);push(pc+8,s)
            elif op==0 and w&63==8:
                target=s.r[rs];delay(s)
                if target==('RETURN',):push(-4,s)
                else:
                    assert tagged(target,'JT'),('unproven JR',target)
                    _,name,index=target;offset,count=(0,38)if name=='bank'else(0xa8,41)
                    for i in range(count):
                        condition=pred('EQ',index,i)
                        if True not in choices(s,condition):continue
                        n=deepcopy(s);assume(n,condition,True)
                        dest=struct.unpack_from('>I',self.pool,offset+4*i)[0]-self.entry
                        push(dest,n)
            else:self.step(s,w);push(pc+4,s)
        return answers

def initial(side,phase):
    s=State(side,phase)
    if phase=='prefix':
        s.r[29]=('STACK',0);s.mem={};s.r[16]=('ENTRY',16);s.r[31]=('RETURN',);s.r[4]=('CATEGORY',)
    elif phase=='player':
        s.r[6]=('PLAYER_INDEX',);s.r[3]=scale(s.r[6],48);s.r[8 if side=='raw'else 7]=1
    elif phase=='identity':
        s.r[4]=('IDENTITY_BOUND',);s.r[5]=('IDENTITY_INDEX',);s.r[3]=scale(s.r[5],48)
    elif phase=='finish':s.r[4]=('CATEGORY',)
    return s

def observable(s,phase,end,side):
    trace=s.trace[:]
    if phase=='header':
        read=('READ',0x8008fd8c,1);write=('WRITE',0x800d1548,4,0)
        assert len(trace)==2 and Counter(trace)==Counter((read,write)),('invalid commute',trace)
        # These actual fixed byte ranges are independent, even with other aliases.
        assert 0x8008fd8c+1<=0x800d1548
        trace=[write,read]
    saved=tuple(s.r[i]for i in(16,17,18,19,20,21,22,23,28,30))
    assert all(s.r[i]==('ENTRY',i)for i in(17,18,19,20,21,22,23,28,30))
    if phase=='finish':
        assert s.r[29]==('STACK',0)and s.r[16]==('ENTRY',16)and s.r[31]==('RETURN',)
        roles=()
    else:
        assert s.r[29]==('STACK',-88)and s.r[16]==0x800d20fc
        assert(s.mem[-56],s.mem[-52],s.mem[0])==(('ENTRY',16),('RETURN',),('CATEGORY',))
        roles=()
        if phase=='header'and end=='player':
            roles=(s.r[6],s.r[3],s.r[8 if side=='raw'else 7]);assert roles==(0,0,1)
        elif phase=='player':
            index=add(('PLAYER_INDEX',),1);roles=(s.r[6],s.r[3],s.r[8 if side=='raw'else 7])
            assert roles==(index,scale(index,48),1),('player induction',roles)
        elif phase=='cache'and end=='identity':roles=(s.r[4],s.r[5],s.r[3]);assert roles[1:]==(0,0)
        elif phase=='identity'and end=='identity':
            index=add(('IDENTITY_INDEX',),1);roles=(s.r[4],s.r[5],s.r[3])
            assert roles[1:]==(index,scale(index,48)),('identity induction',roles)
        elif phase in('cache','identity')and end=='finish':roles=(s.r[4],);assert roles==(('CATEGORY',),)
    assert tuple(s.f[20:])==tuple(('ENTRY_FP',i)for i in range(20,32))
    return(trace,saved,s.r[29],tuple(s.f[20:]),s.fcsr,roles)

def prove(raw,normal):
    assert len(raw[0])==481 and len(normal[0])==477 and len(raw[1])==len(normal[1])==336
    a,b=Program(*raw),Program(*normal);counts={}
    phases=(('prefix',0,0,{0x1a4:'header'},{0x1a4:'header'}),
            ('header',0x1a4,0x1a4,{0x1c4:'player',0x6dc:'cache'},{0x1c4:'player',0x6cc:'cache'}),
            ('player',0x1c4,0x1c4,{0x1c4:'player',0x6dc:'cache'},{0x1c4:'player',0x6cc:'cache'}),
            ('cache',0x6dc,0x6cc,{0x6fc:'identity',0x74c:'finish'},{0x6ec:'identity',0x73c:'finish'}),
            ('identity',0x6fc,0x6ec,{0x6fc:'identity',0x74c:'finish'},{0x6ec:'identity',0x73c:'finish'}),
            ('finish',0x74c,0x73c,{-4:'return'},{-4:'return'}))
    for phase,starta,startb,stopa,stopb in phases:
        left=a.paths(starta,stopa,initial('raw',phase));right=b.paths(startb,stopb,initial('normal',phase))
        assert left.keys()==right.keys(),('path predicates',phase,len(left),len(right),next(iter(left.keys()-right.keys()),None),next(iter(right.keys()-left.keys()),None))
        for key in left:
            x=observable(left[key],phase,key[0],'raw');y=observable(right[key],phase,key[0],'normal')
            if x!=y:
                mismatch=next((i for i,(c,d)in enumerate(zip(x[0],y[0]))if c!=d),None)
                raise AssertionError(('relational transfer',phase,key,'event',mismatch,x[0][mismatch]if mismatch is not None else x,y[0][mismatch]if mismatch is not None else y))
        counts[phase]=len(left)
    return dict(symbolic_paths=counts,arbitrary_public_aliases=True,opaque_o32_helpers=True,branch_likely_annul=True,inductive_loop_cursors=True,ordered_public_and_fp_effects=True,private_stack_nonalias_contract=True,raw_fault_state_claimed=False)

def main():
    from tools.experiments import game_record_initializer_150169a0_candidates as source
    from tools.experiments.game_record_initializer_150169a0_schedule import private_projection
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    retail,raw=source.programs();blob,refs=payload(source.OUT/'selected.o',source.NAME)
    normal,nrefs=private_projection(blob,refs)
    candidate=(bound_blob(normal,nrefs,source.symbols()),retail[1],retail[2])
    report=prove(raw,candidate)
    # A different valid allocation must pass: the checker is not a retail-word
    # or fixed color-template comparison. T0/T1 have no entry or ABI roles.
    def alternate(w):
        op,fn,fmt=w>>26,w&63,w>>21&31
        if op==0:
            fields=(16,11)if fn in(0,2,3)else(21,16,11)if fn in(4,33,35,36,37,42,43)else(11,)if fn in(16,18)else(21,16)if fn in(25,27)else(21,)if fn==8 else()
        elif op==17:fields=(16,)if fmt==0 else()
        elif op==3:fields=()
        elif op in(6,7,22,23,49,57):fields=(21,)
        elif op==15:fields=(16,)
        else:fields=(21,16)
        for shift in fields:
            reg=w>>shift&31
            if reg in(8,9):w=(w&~(31<<shift))|((17-reg)<<shift)
        return w
    reallocated=([alternate(w)for w in candidate[0]],*candidate[1:])
    assert reallocated[0]!=candidate[0];assert prove(raw,reallocated)==report
    report['independent_allocation_positive_control']=True
    controls=[]
    for name,pc,change in(('player-index',0x6b8,lambda w:(w&0xffff0000)|2),
                           ('identity-index',0x728,lambda w:(w&0xffff0000)|2),
                           ('active-marker',0x6ac,lambda w:w&~(31<<16)),
                           ('selector-field',0x1e8,lambda w:(w&0xffff0000)|2),
                           ('coordinate',0x638,lambda w:(w&0xffff0000)|0x18),
                           ('annulled-delay',0x5f0,lambda w:(w&0x03ffffff)|(5<<26)),
                           ('private-cursor-home',0x1ec,lambda w:(w&0xffff0000)|0x34)):
        words=candidate[0][:];assert change(words[pc//4])!=words[pc//4];words[pc//4]=change(words[pc//4])
        try:prove(raw,(words,*candidate[1:]))
        except AssertionError as error:
            reason=str(error)
            assert not any(text in reason for text in('unsupported','escaped code','unbounded proof')),('invalid control',name,reason)
            controls.append(dict(name=name,rejected=reason[:180]))
        else:raise AssertionError(('ineffective proof control',name,hex(pc)))
    report['effective_controls']=controls
    report['uninstalled']=True
    (source.OUT/'proof-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
