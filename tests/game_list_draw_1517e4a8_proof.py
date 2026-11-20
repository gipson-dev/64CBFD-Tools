"""Instruction-driven relation, independent of a word-normalization template.

Normal nontrapping IEEE operations with a common rounding mode at each call
epoch. Exception flags are sticky ORs; cause and FCC retain their last writer.
Quiet ordinary public reads can repeat between writes/calls. Opaque providers
may mutate public objects and the retained 20-byte packet, but cannot inspect
unpassed private homes, code PCs or non-argument registers. DIV zero/overflow
paths are explicitly excluded. This script is research, not matching credit.
"""
from copy import deepcopy
from collections import Counter
from pathlib import Path
import json,struct,sys,time
from tools.tests import game_growth_curve_151a1fb4_proof as g
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.experiments import game_list_draw_1517e4a8_recovery as source
from tools.tests import game_list_draw_1517e4a8_oracle as abi
e=g.e;OUT=source.OUT/'match-proof'
HOMES=set(range(-24,-20))|set(range(-8,-4))
def disjoint(a,n,b,m):
    """Prove nonoverlap only for equal affine bases (including two constants)."""
    ca,ta=e.linear(a);cb,tb=e.linear(b)
    if ta!=tb:return False
    delta=e.signed((cb-ca)&e.U32)
    return not(-m<delta<n)
class State(g.State):
    def __init__(self,side,group,intensity):
        super().__init__(side);self.group=group;self.exposed=False;self.public_writes=[];self.call_epoch=0
        self.mem={off:('PRIVATE_ENTRY',off)for off in range(-184,28)}
        self.r=[('INITIAL_GPR',i)for i in range(32)];self.r[0]=0
        self.r[4:8]=[('COMMANDS',),('RECORD',),group,('COUNT',)]
        self.r[29]=('STACK',0);self.r[31]=('RETURN',)
        for i in(*range(16,24),28,30):self.r[i]=('ENTRY',i)
        self.f=[('INITIAL_FP',i)for i in range(32)]
        for i in range(20,32):self.f[i]=('ENTRY_FP',i)
        for off,value in((16,('FALLOFF',)),(20,('STRENGTH',)),(24,('INTENSITY',)if intensity else 0)):
            for i in range(4):self.mem[off+i]=g.byte(value,8*(3-i))
        self.control=('ENTRY_CONTROL',);self.rounding=('ENTRY_ROUNDING',);self.flag_base=('ENTRY_FLAGS',);self.flags=set();self.cause=('ENTRY_CAUSE',);self.condition=('ENTRY_FCC',);self.fp_events=[]
    def load(self,address,size,pool=b''):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and-184<=off and off+size<=28,('private load bounds',off,size)
            return g.join([self.mem[off+i]for i in range(size)])
        e.plain(address)
        version=('MEMORY_VERSION',self.call_epoch,('WRITES',*((i,a,n)for i,(a,n)in enumerate(self.public_writes)if not disjoint(address,size,a,n))))
        self.read_set[version,address,size]+=1
        if isinstance(address,int)and abi.PALETTE<=address<abi.PALETTE+16:
            assert size==1;return abi.TABLE[address-abi.PALETTE]
        return('LOAD',address,size,version)
    def store(self,address,size,value):
        if e.tagged(address,'STACK'):
            off=address[1];assert size in(1,2,4)and off%size==0 and-184<=off and off+size<=28,('private store bounds',off,size)
            for i in range(size):self.mem[off+i]=g.byte(value,8*(size-i-1))
        else:
            e.plain(address);e.plain(value)
            self.trace.append(('WRITE',address,size,e.bitop('AND',value,(1<<(8*size))-1)));self.epoch+=1;self.public_writes.append((address,size))
    def frame(self):return tuple((off,self.mem[off])for off in range(-184,28)if off not in HOMES)
    def status(self):return(self.control,self.rounding,self.flag_base,frozenset(self.flags),self.cause,self.condition)

class Program(g.Program):
    def __init__(self,words,terms):e.Program.__init__(self,words,b'',abi.ENTRY);self.terms=terms;self.seen=set()
    def fp(self,s,fmt,fn,args):
        # Sticky exceptions commute and duplicate identical effects idempotently.
        # Cause and FCC remain separate last-writer state and are compared too.
        key=(fmt,fn,args,s.control,s.rounding)
        s.fp_events.append(key)
        flag=self.terms.term('FP_EXCEPTION_BITS',*key);s.flags.add(flag);s.cause=flag
        if fmt==16 and fn in(60,62):
            s.condition=self.terms.term('FCMP',fn,args);return None
        return self.terms.term('FP_RESULT',*key)
    def step(self,s,w):
        op,rs,rt,rd,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
        if op==17 and rs in(16,20):
            assert(fmt:=rs)==20 and fn==32 or fmt==16 and fn in(0,1,2,3,5,6,13,60,62),('unsupported FP',hex(w))
            if fmt==16 and fn==6:s.f[fd]=s.f[rd]
            else:
                args=(s.f[rd],s.f[rt])if fmt==16 and fn in(0,1,2,3,60,62)else(s.f[rd],)
                value=self.fp(s,fmt,fn,args)
                if value is not None:s.f[fd]=value
        else:super().step(s,w)
    def call(self,s,target):
        assert target in(abi.INIT,abi.SETUP,abi.DRAW),hex(target);assert s.r[29]==('STACK',-184)
        n={abi.INIT:1,abi.SETUP:10,abi.DRAW:4}[target]
        args=tuple(s.r[4:4+min(n,4)])+tuple(s.load(('STACK',-168+4*i),4)for i in range(max(0,n-4)))
        for i,arg in enumerate(args):
            if target==abi.DRAW and i==1:assert arg==('STACK',-60),('draw packet ABI',arg);s.exposed=True
            else:e.plain(arg)
        ordinal=sum(s.calls.values());s.calls[target]+=1
        s.trace.append(('FP_ORDER',tuple(s.fp_events)));s.trace.append(('CALL',target,args,s.status()));s.trace.append(('PRIVATE_FRAME',s.frame()));s.fp_events=[]
        s.epoch+=1;s.call_epoch+=1;s.public_writes=[]
        if s.exposed:
            for off in range(-60,-40):s.mem[off]=('PROVIDER_BYTE',ordinal,off)
        for i in range(max(4,n)):s.store(('STACK',-184+4*i),4,('CALL_HOME',ordinal,i))
        for i in(1,2,3,*range(4,16),24,25):s.r[i]=('CALLER',ordinal,i)
        for i in range(20):s.f[i]=('CALLER_FP',ordinal,i)
        s.r[2]=('RESULT',target,ordinal);s.r[31]=('CALL_RETURN',ordinal);s.hi=('CALL_HI',ordinal);s.lo=('CALL_LO',ordinal)
        s.control=('CALL_CONTROL',ordinal);s.rounding=('CALL_ROUNDING',ordinal);s.flag_base=('CALL_FLAGS',ordinal);s.flags=set();s.cause=('CALL_CAUSE',ordinal);s.condition=('CALL_FCC',ordinal)
    def paths(self,start,stops,initial):
        pending=[(start,initial)];answers={};work=0
        while pending:
            pc,s=pending.pop();work+=1;s.steps+=1;assert work<500000 and s.steps<1800,('unbounded proof',start,work,hex(pc))
            if s.steps>1 and pc in stops:
                key=(stops[pc],tuple(sorted(s.facts.items(),key=repr)));assert key not in answers,('duplicate path',key)
                answers[key]=s;continue
            w=self.instruction(pc);op,rs,rt=w>>26,w>>21&31,w>>16&31;delay=lambda n:self.step(n,self.instruction(pc+4))
            if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
                if op==1:
                    assert rt in(0,1,2,3);p=g.predicate('SLT',s.r[rs],0)
                    if rt&1:p=e.negate(p)
                    likely=bool(rt&2)
                elif op==17:
                    p=s.condition;assert p is not None
                    if not rt&1:p=e.negate(p)
                    likely=bool(rt&2)
                else:
                    p=g.predicate('EQ',s.r[rs],s.r[rt])if op in(4,5,20,21)else g.predicate('SLT',0,s.r[rs]);likely=op>=20
                    if op in(5,21,6,22):p=e.negate(p)
                for take in e.choices(s,p):
                    n=deepcopy(s);e.assume(n,p,take)
                    if take or not likely:delay(n)
                    dest=pc+4+4*(((w&65535)^32768)-32768)if take else pc+8;pending.append((dest,n))
            elif op==3:
                s.r[31]=self.entry+pc+8;delay(s);self.call(s,((self.entry+pc+4)&0xF0000000)|((w&0x3FFFFFF)<<2));pending.append((pc+8,s))
            elif op==0 and w&63==8:
                assert s.r[rs]==('RETURN',),('saved return restoration',s.r[rs]);delay(s);pending.append((-4,s))
            elif op==0 and w&63==13:raise AssertionError(('normal-domain BREAK',pc,s.facts))
            else:self.step(s,w);pending.append((pc+4,s))
        return answers

def initial(side,phase,p,group,intensity,index=0,count=1):
    s=State(side,group,intensity)
    if phase=='prefix':
        if intensity:e.assume(s,g.predicate('EQ',('INTENSITY',),0),False)
        return s
    for w in p.words[:22]:p.step(s,w)
    for i in(1,2,3,*range(4,21),24,25,31):s.r[i]=('DEAD_LOOP_GPR',side,i)
    for i in range(28):s.f[i]=('DEAD_LOOP_FPR',side,i)
    factor=e.scale(e.add(index,1),2)
    s.r[3]=index;s.r[16:21]=[factor,e.add(abi.PALETTE+group*7,index),('ALPHA',),('RECORD',),('CURSOR',)]
    s.f[6]=factor;s.f[20]=abi.bits(5.0);s.f[22]=abi.bits(255.0);s.f[24]=('CENTER_X',);s.f[26]=('CENTER_Y',)
    for i in range(4):s.mem[12+i]=g.byte(count,8*(3-i))
    for off in range(-60,-40):s.mem[off]=('CARRY_PACKET_BYTE',off)
    s.exposed=True;s.trace=[];s.read_set=Counter();s.epoch=0;s.facts={};s.steps=0
    return s

def observation(s,end):
    if end=='return':
        assert s.r[29]==('STACK',0)and s.r[31]==('RETURN',),('saved SP/return restoration',s.r[29],s.r[31])
        assert all(s.r[i]==('ENTRY',i)for i in(*range(16,24),28,30))
        assert s.f[20:]==[('ENTRY_FP',i)for i in range(20,32)]
        roles=(s.r[2],)
    else:
        assert s.r[29]==('STACK',-184)and s.r[19]==('RECORD',)
        roles=tuple(s.r[i]for i in(3,16,17,18,19,20))+(s.f[6],s.f[20],s.f[22],s.f[24],s.f[26])
        for i,off in((16,-104),(17,-100),(18,-96),(19,-92),(20,-88),(31,-84)):
            assert s.load(('STACK',off),4)==(('RETURN',)if i==31 else('ENTRY',i)),('saved GPR home',i,off)
        for i in range(20,28):assert s.load(('STACK',-136+4*(i-20)),4)==('ENTRY_FP',i)
    return(s.trace,s.read_set,s.divisors,s.status(),s.frame(),roles,tuple(s.fp_events))

def structural_dead(words):
    """Independent CFG, including delay execution and literal always branches."""
    pending=[0];seen=set()
    while pending:
        i=pending.pop()
        if i in seen:continue
        assert 0<=i<len(words);seen.add(i);w=words[i];op,rs,rt=w>>26,w>>21&31,w>>16&31
        if op in(1,4,5,6,7,20,21,22,23)or op==17 and rs==8:
            outcomes=(True,False)
            if op in(4,5,20,21)and rs==rt:outcomes=(op in(4,20),)
            likely=op>=20 if op!=17 else bool(rt&2)
            if True in outcomes or not likely:seen.add(i+1)
            if True in outcomes:pending.append(i+1+(((w&65535)^32768)-32768))
            if False in outcomes:pending.append(i+2)
        elif op==0 and w&63==8:seen.add(i+1)
        elif op==0 and w&63==13:pass
        elif op==3:seen.add(i+1);pending.append(i+2)
        else:pending.append(i+1)
    return sorted(set(range(len(words)))-seen)

def coverage(programs):
    reports=[]
    for side,p in enumerate(programs):
        w=p.words;dead=structural_dead(w);assert dead==([42,107,209]if side==0 else[102,107,209]),dead
        unseen=[i for i in range(len(w))if i*4 not in p.seen]
        breaks=[i for i in unseen if w[i]>>26==0 and w[i]&63==13]
        assert breaks==([77,83,179,185]if side==0 else[77,83,180,186])
        assert set(unseen)==set(dead)|set(breaks)|{81,82}
        # V1 is set to 120 at word54 and survives through the divide and BNE79.
        # AT is -1 at the branch; hence its overflow-test successor81 cannot run.
        assert w[54]==0x24030078 and list(w[78:81])==[0x2401FFFF,0x14610004,0x3C018000]
        def written(word):
            op,rs,rt,rd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
            if op==0:return rd if fn in(0,2,3,4,16,18,33,35,36,37,42,43)else None
            if op==17:return rt if rs==0 else None
            if op==3:return 31
            return rt if op in(8,9,10,11,12,13,14,15,32,33,35,36,37)else None
        assert all(written(word)!=3 for word in w[55:79])
        reports.append(dict(structurally_unreachable=dead,constant_divisor_overflow_test_unreachable=[81,82],normal_domain_BREAKs=breaks,unvisited_words_accounted_for=True))
    return reports

def prove(raw,retail,phases=('prefix','loop'),selected=None,verbose=True):
    terms=Terms();programs=[Program(raw,terms),Program(retail,terms)];report={}
    groups=((phase,group,kind,i,n)for phase in phases for group in(0,1)for kind in((False,True)if phase=='prefix'else(True,))
            for i,n in([(0,1)]if phase=='prefix'else[(('INDEX',),('COUNT',))]if phase=='symbolic-loop'else[(i,n)for n in range(1,8)for i in range(n)]))
    if selected is not None:groups=iter(selected)
    for phase,group,kind,index,count in groups:
        outputs=[]
        for side,p in enumerate(programs):
            states=p.paths(0 if phase=='prefix'else 295*4,{295*4:'loop',-4:'return'},initial('raw'if side==0 else'retail',phase,p,group,kind,index,count))
            for key,state in states.items():
                if key[0]=='loop':
                    next_index=0 if phase=='prefix'else e.add(index,1)
                    assert state.r[3]==next_index
                    assert state.r[16]==e.scale(e.add(next_index,1),2)
                    assert state.r[17]==e.add(abi.PALETTE+group*7,next_index)
                    assert state.f[6]==state.r[16]
                    assert state.f[20:24:2]==[abi.bits(5.0),abi.bits(255.0)]
            outputs.append({key:observation(s,key[0])for key,s in states.items()})
        a,b=outputs
        if a.keys()!=b.keys():
            if verbose:(OUT/'path-key-mismatch.txt').write_text('RAW ONLY:\n'+repr(next(iter(a.keys()-b.keys()),None))+'\nRETAIL ONLY:\n'+repr(next(iter(b.keys()-a.keys()),None)))
            raise AssertionError(('path keys',phase,group,kind,index,count,len(a),len(b),'see path-key-mismatch.txt'))
        for key,value in a.items():
            wanted=b[key]
            if value!=wanted:
                part=next(i for i,(x,y)in enumerate(zip(value,wanted))if x!=y)
                detail=(phase,group,kind,index,count,key,part,value[part],wanted[part])
                if verbose:(OUT/'transfer-mismatch.txt').write_text(repr(detail))
                reverse={v:k for k,v in terms.values.items()}
                def expand(x,depth=6):
                    if depth and isinstance(x,tuple):
                        if x in reverse:return expand(reverse[x],depth-1)
                        return tuple(expand(v,depth-1)for v in x)
                    return x
                if part==0 and verbose:
                    at=next((j for j,(x,y)in enumerate(zip(value[0],wanted[0]))if x!=y),None)
                    if at is not None:
                        x,y=value[0][at],wanted[0][at];print('EVENT',at,x[0],y[0],flush=True)
                        if x[0]==y[0]=='CALL':
                            print('ARGS',expand(x[2]),expand(y[2]),flush=True)
                            print('FLAG DIFF',x[3][3]-y[3][3],y[3][3]-x[3][3],flush=True)
                            print('CAUSE',expand(x[3][4],12),expand(y[3][4],12),flush=True)
                        elif x[0]==y[0]=='PRIVATE_FRAME':print('PRIVATE DIFF',[(a,b)for a,b in zip(x[1],y[1])if a!=b][:10],flush=True)
                        else:print(expand(x),expand(y),flush=True)
                raise AssertionError(('transfer',phase,group,kind,index,count,part,'see transfer-mismatch.txt'))
        label=f'{phase}/g{group}/k{int(kind)}/i{index}/n{count}';report[label]=len(a)
        if verbose:print(label,len(a),flush=True)
    r=dict(paths=report,visited_words=[len(p.seen)for p in programs],ordered_FP_operations=True,normal_sticky_FP_flags_cause_FCC=True,quiet_public_reads=True,public_read_multiplicity=True,
        unvisited_indices=[[i for i in range(len(p.words))if i*4 not in p.seen]for p in programs],
        arbitrary_o32_providers=True,private_212_bytes_modulo_counter_homes=True,matching_credit=0)
    if selected is None and'prefix'in phases and any(x in phases for x in('loop','symbolic-loop')):r['coverage_accounting']=coverage(programs)
    if selected is None:(OUT/'proof-report.json').write_text(json.dumps(r,indent=2)+'\n')
    return r


from tools.tests.game_list_draw_1517e4a8_normalizer import gpr_fields

def negative_controls(raw,retail):
    reports={};start=time.monotonic()
    prefix=[('prefix',0,False,0,1)]
    loop=[('symbolic-loop',0,True,('INDEX',),('COUNT',))]
    controls=[
        ('distance-cutoff',[(217,0x34210D40,0x34210D41)],prefix),
        ('brightness-numerator',[(174,0x358CDB00,0x358CDB01)],prefix),
        ('setup-stack-argument',[(263,0xAFAE0018,0xAFA00018)],prefix),
        ('saved-return-home',[(13,0xAFBF0064,0xAFBF0068)],prefix),
        ('packet-pointer',[(305,0x27A5007C,0x27A50078)],loop),
        ('packet-alpha-byte',[(301,0xA3B20086,0xA3B20087)],loop),
        ('loop-FP-multiply',[(303,0x4602C402,0x4602C403)],loop),
        ('counter-outside-allowed-homes',[(302,0xAFA300A0,0xAFA300A4),(338,0x8FA300A0,0x8FA300A4)],loop),
        ('pipe-sync-word',[(339,0x3C0BE700,0x3C0BE701)],loop),
    ]
    for label,changes,selected in controls:
        altered=list(raw)
        for i,old,new in changes:assert altered[i]==old,(label,i,hex(altered[i]));altered[i]=new
        try:prove(altered,retail,selected=selected,verbose=False)
        except AssertionError as error:
            reason=str(error)
            assert not any(s in reason for s in('unsupported','unbounded','code escape','instruction range','normal-domain BREAK')),reason
            reports[label]=reason[:500]
        else:raise AssertionError(('control accepted',label))
        print('REJECTED',label,reports[label][:140],flush=True)
    # A different scratch allocation must still be accepted. This checks that
    # the proof is not a literal register-color or normalizer-template test.
    alternate=[]
    for w in raw:
        changed=w
        for shift in gpr_fields(w):
            reg=w>>shift&31
            if reg in(8,9):changed=(changed&~(31<<shift))|((17-reg)<<shift)
        alternate.append(changed)
    assert alternate!=list(raw)
    positive=prove(alternate,retail,selected=prefix+[
        ('symbolic-loop',g,True,('INDEX',),('COUNT',))for g in(0,1)],verbose=False)
    # Test the one added memory reasoning rule independently, including overlap,
    # distinct unknown bases and 32-bit wrap. Unknown aliases stay conservative.
    checks=0
    for base in(0,0xFFFFFFFE,('BASE',)):
        for left in range(-6,7):
            for right in range(-6,7):
                for n in(1,2,4):
                    for m in(1,2,4):
                        expected=set(range(left,left+n)).isdisjoint(range(right,right+m))
                        assert disjoint(e.add(base,left),n,e.add(base,right),m)==expected
                        checks+=1
    assert not disjoint(('BASE_A',),4,('BASE_B',),4)
    assert not disjoint(('BASE',),4,0x800380A0,4)
    report=dict(effective_semantic_controls=len(reports),rejections=reports,positive_T0_T1_reallocation=positive['paths'],
                exact_affine_disjoint_checks=checks,unknown_aliases_conservative=True,elapsed_seconds=round(time.monotonic()-start,3),matching_credit=0)
    (OUT/'proof-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report
