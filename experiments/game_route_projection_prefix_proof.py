"""Cutpoint proof of the route prefix; no word rewriting or installation."""
from dataclasses import dataclass
import json
from pathlib import Path
import struct

from tools.experiments import game_route_projection_call_lifetime_fit as source


@dataclass(frozen=True)
class Symbol:
    index:int


class Expressions:
    # Share store-history terms when symbolic branches fork.
    def __init__(self):self.table={};self.nodes=[]

    def node(self,*key):
        if key not in self.table:
            self.table[key]=Symbol(len(self.nodes));self.nodes.append(key)
        return self.table[key]

    def order(self,value):return (1,value.index) if isinstance(value,Symbol) else (0,value)

    def add(self,a,b):
        terms=[];constant=0
        for value in (a,b):
            parts=self.nodes[value.index][1:] if isinstance(value,Symbol) and self.nodes[value.index][0]=='add' else (value,)
            for part in parts:
                if isinstance(part,int):constant+=part
                else:terms.append(part)
        constant&=0xFFFFFFFF;terms.sort(key=self.order)
        if constant:terms.append(constant)
        return 0 if not terms else terms[0] if len(terms)==1 else self.node('add',*terms)

    def mask(self,value,bits):
        if isinstance(value,int):return value&bits
        if bits==0xFFFFFFFF:return value
        key=self.nodes[value.index]
        if key[0]=='read' and key[3]==1 and not key[4] and bits==255:return value
        if key[0]=='and' and key[2]==bits:return value
        return self.node('and',value,bits)

    def shift(self,value,bits):
        if not bits:return value
        return (value<<bits)&0xFFFFFFFF if isinstance(value,int) else self.node('shift',value,bits)

    def signed_lt(self,a,b):
        if isinstance(a,int) and isinstance(b,int):return int(((a^0x80000000)-0x80000000)<((b^0x80000000)-0x80000000))
        return self.node('signed-lt',a,b)

    def equal(self,a,b):
        if a==b:return True
        if isinstance(a,int) and isinstance(b,int):return False
        return self.node('equal',*sorted((a,b),key=self.order))


class Prefix:
    def __init__(self,words,arena,retail=False,anchors=None):
        self.words=words;self.a=arena;self.retail=retail
        self.anchors=anchors or dict(flags=0x8008FDBC,count=0x80087290,table=0x800D2350,mode=0x800D23A8)
        self.cycle=150 if retail else 164;self.common=199 if retail else 213
        self.exit=13+(((words[12]&65535)^32768)-32768)
        self.cuts={39:'loop',self.cycle:'cycle',self.common:'common',self.exit:'exit'}
        if self.exit!=(313 if retail else 327) or words[39]>>26!=0 or words[self.cycle]!=0x9253004B or words[self.common]>>26!=15:
            raise ValueError('Unknown route-prefix cutpoints')
        self.paths={}

    def initial(self,loop=False):
        a=self.a;regs=[0,*(a.node('input',i) for i in range(1,32))]
        regs[4]=a.node('record');regs[5]=a.node('actor');regs[29]=a.node('entry-sp')
        if loop:
            for i in (1,*range(2,16),24,25,26,27):regs[i]=a.node('unrelated-scratch',self.retail,i)
            regs[29]=a.add(regs[29],-120);regs[16]=self.anchors['table'];regs[18]=a.node('record');regs[21]=a.node('actor')
            regs[13]=a.node('cached-table');regs[17]=a.node('old-anchor')
            if self.retail:
                assignments={2:a.node('index'),3:a.node('count'),6:255,7:self.anchors['mode'],8:3,9:5,10:2,11:self.anchors['count']}
            else:
                assignments={6:a.node('index'),2:a.node('count'),8:255,9:self.anchors['mode'],7:3,10:5,11:2,12:self.anchors['count']}
            for key,value in assignments.items():regs[key]=value
        return regs

    def execute(self,word,regs,memory,events):
        a=self.a;op,rs,rt,rd=word>>26,word>>21&31,word>>16&31,word>>11&31
        imm=((word&65535)^32768)-32768;fn=word&63
        address=a.add(regs[rs],imm)
        if op==0:
            if fn==0:regs[rd]=a.shift(regs[rt],word>>6&31)
            elif fn==33:regs[rd]=a.add(regs[rs],regs[rt])
            elif fn==37:
                x,y=regs[rs],regs[rt]
                regs[rd]=x if y==0 else y if x==0 else x|y if isinstance(x,int) and isinstance(y,int) else a.node('or',*sorted((x,y),key=a.order))
            elif fn==42:regs[rd]=a.signed_lt(regs[rs],regs[rt])
            else:raise ValueError('Unsupported prefix R instruction: %08X'%word)
        elif op==9:regs[rt]=address
        elif op==12:regs[rt]=a.mask(regs[rs],word&65535)
        elif op==15:regs[rt]=(word&65535)<<16
        elif op in (32,33,35,36,37):
            size={32:1,33:2,35:4,36:1,37:2}[op];signed=op in (32,33)
            value=a.node('read',memory,address,size,signed);regs[rt]=value;events.append(('R',address,size,signed,value))
        elif op in (40,41,43):
            size={40:1,41:2,43:4}[op];value=a.mask(regs[rt],(1<<(size*8))-1)
            events.append(('W',address,size,value));memory=a.node('store',memory,address,size,value)
        else:raise ValueError('Unsupported prefix instruction: %08X'%word)
        regs[0]=0;return memory

    def projection(self,name,regs,memory,events):
        saved=tuple(regs[i] for i in (*range(16,24),28,29,30,31))
        loop=()
        if name=='loop':
            loop=(regs[2],regs[3],regs[13]) if self.retail else (regs[6],regs[2],regs[13])
            constants=tuple(regs[i] for i in ((16,7,11,9,10,6,8) if self.retail else (16,9,12,10,11,8,7)))
            if constants!=(self.anchors['table'],self.anchors['mode'],self.anchors['count'],5,2,255,3):
                raise ValueError('Prefix cutpoint does not establish loop constants')
        return name,saved,loop,memory,tuple(events)

    def walk(self,pc,regs,memory,events,conditions,steps=0):
        regs=list(regs);events=list(events);a=self.a
        while True:
            if steps and pc in self.cuts:
                key=tuple(sorted(conditions.items(),key=lambda x:x[0].index))
                result=self.projection(self.cuts[pc],regs,memory,events)
                if key in self.paths:raise ValueError('Ambiguous prefix symbolic path')
                self.paths[key]=result;return
            if not 0<=pc<self.cycle or steps>400:raise ValueError('Unbounded or escaped prefix CFG')
            steps+=1;word=self.words[pc];op,rs,rt=word>>26,word>>21&31,word>>16&31
            if op in (4,5,20,21,6,7):
                if op in (6,7):
                    value=regs[rs]
                    condition=(((value^0x80000000)-0x80000000)<=0) if isinstance(value,int) else a.node('signed-le-zero',value)
                    equal=op==6
                else:condition=a.equal(regs[rs],regs[rt]);equal=op in (4,20)
                outcomes=(condition,) if isinstance(condition,bool) else (conditions[condition],) if condition in conditions else (False,True)
                for outcome in outcomes:
                    taken=outcome==equal;next_regs=list(regs);next_events=list(events);next_memory=memory
                    next_conditions=dict(conditions)
                    if not isinstance(condition,bool):next_conditions[condition]=outcome
                    if taken or op<20:next_memory=self.execute(self.words[pc+1],next_regs,next_memory,next_events)
                    target=pc+1+(((word&65535)^32768)-32768) if taken else pc+2
                    self.walk(target,next_regs,next_memory,next_events,next_conditions,steps)
                return
            memory=self.execute(word,regs,memory,events);pc+=1

    def run(self,loop=False):
        self.walk(39 if loop else 0,self.initial(loop),self.a.node('initial-memory'),[],{})
        return self.paths


def gp_liveins(words):
    """Delay-slot-aware whole-body GP liveness checks the prefix's cut interface."""
    preserved=set((*range(16,24),28,29,30,31));scratch=set((*range(1,16),24,25))
    graph={('exit',):(preserved,set(),())}
    def uses_defs(word):
        op,rs,rt,rd,fn=word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
        if op==0:
            if fn in (0,2,3):u,d={rt},{rd}
            elif fn in (4,6,7,32,33,34,35,36,37,38,39,42,43):u,d={rs,rt},{rd}
            elif fn in (16,18):u,d=set(),{rd}
            elif fn in (24,25,26,27):u,d={rs,rt},set()
            elif fn in (8,9):u,d={rs},{rd} if fn==9 else set()
            else:raise ValueError('Unsupported GP liveness R instruction')
        elif op in (1,6,7,22,23):u,d={rs},set()
        elif op in (4,5,20,21):u,d={rs,rt},set()
        elif op in (8,9,10,11,12,13,14,32,33,35,36,37):u,d={rs},{rt}
        elif op==15:u,d=set(),{rt}
        elif op in (40,41,43):u,d={rs,rt},set()
        elif op in (49,57):u,d={rs},set()
        elif op==17:
            if rs in (4,6):u,d={rt},set()
            elif rs in (0,2):u,d=set(),{rt}
            elif rs in (8,16,17,20,21):u,d=set(),set()
            else:raise ValueError('Unsupported GP liveness COP1 instruction')
        elif op in (2,3):u,d=set(),{31} if op==3 else set()
        else:raise ValueError('Unsupported GP liveness instruction')
        return u-{0},d-{0}
    def normal(pc):return ('pc',pc) if 0<=pc<len(words) else ('exit',)
    for pc,word in enumerate(words):
        key=normal(pc);op,rs,rt,fn=word>>26,word>>21&31,word>>16&31,word&63
        u,d=uses_defs(word)
        conditional=op in (1,4,5,6,7,20,21,22,23) or op==17 and rs==8
        if conditional:
            likely=op in (20,21,22,23) or op==17 and bool(rt&2)
            target=pc+1+(((word&65535)^32768)-32768)
            successors=[]
            for taken in (True,False):
                destination=normal(target if taken else pc+2)
                if taken or not likely:
                    delay=('delay',pc,taken);du,dd=uses_defs(words[pc+1]);graph[delay]=(du,dd,(destination,))
                    successors.append(delay)
                else:successors.append(destination)
            graph[key]=(u,d,tuple(successors))
        elif op in (2,3) or op==0 and fn==8:
            delay=('delay',pc,True);du,dd=uses_defs(words[pc+1])
            if op==3:
                target=((word&0x3FFFFFF)<<2)|((source.source.ENTRY+pc*4+4)&0xF0000000)
                if target not in (0x1508907C,0x1512D560):raise ValueError('Unknown projection liveness call')
                call=('call',pc);arguments=set(range(4,8 if target==0x1508907C else 7))
                graph[call]=(arguments|preserved,scratch,(normal(pc+2),));destination=call
            else:destination=('exit',) if op==0 else normal((((word&0x3FFFFFF)<<2)|0x10000000)-source.source.ENTRY>>2)
            graph[delay]=(du,dd,(destination,));graph[key]=(u,d,(delay,))
        else:graph[key]=(u,d,(normal(pc+1),))
    live={key:set() for key in graph}
    changed=True
    while changed:
        changed=False
        for key,(uses,defs,targets) in graph.items():
            value=uses|(set().union(*(live[t] for t in targets))-defs)
            if value!=live[key]:live[key]=value;changed=True
    return {pc:live[('pc',pc)] for pc in range(len(words))}


def prove(words,truth,anchors=None):
    result={};a=Expressions()
    for loop in (False,True):
        left=Prefix(words,a,anchors=anchors).run(loop);right=Prefix(truth,a,True,anchors).run(loop)
        key='iteration' if loop else 'entry'
        if left!=right:
            missing=set(left)-set(right);extra=set(right)-set(left)
            shared=set(left)&set(right);different=[k for k in shared if left[k]!=right[k]]
            raise ValueError('Prefix %s disagreement: raw=%d retail=%d missing=%d extra=%d different=%d'%
                (key,len(left),len(right),len(missing),len(extra),len(different)))
        result[key+'_paths']=len(left)
    lives=[gp_liveins(w) for w in (words,truth)];interfaces=[]
    allowed=set((*range(16,24),28,29,30,31))
    for body,live in zip((Prefix(words,a,anchors=anchors),Prefix(truth,a,True,anchors)),lives):
        constants={2,3,6,7,8,9,10,11,13} if body.retail else {2,6,7,8,9,10,11,12,13}
        if not live[39]<=allowed|constants:raise ValueError('Unrelated GP live-in at loop cut')
        rows={name:sorted(live[pc]) for pc,name in body.cuts.items() if name!='loop'}
        if any(not set(values)<=allowed for values in rows.values()):raise ValueError('Unproved caller-scratch live-in at prefix cut')
        interfaces.append(rows)
    result.update(expression_nodes=len(a.nodes),ordered_memory_and_cutpoint_ABI_equal=True,
        loop_state_relation_equal=True,delay_aware_suffix_liveins=interfaces,
        unrelated_scratch_inputs_per_side=True,no_FPU_or_full_function_normalization_claim=True)
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/source.BUILD
    obj,words,row=source.measure(root,out,'prefix-proof-body',source.SELECTED);source.checked(obj)
    truth=list(struct.unpack_from('>321I',(root/'conker/conker.us.bin').read_bytes(),source.source.ROM))
    result=prove(words,truth);(out/'prefix-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
