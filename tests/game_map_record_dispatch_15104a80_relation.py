"""Effect-boundary bisimulation for the 113/110-word map-record dispatcher.

The abstract domain retains modular affine equalities among both streams' GPRs,
HI/LO, immutable entry-register ghosts and one caller-owned saved-RA cell. Pure
instructions may stutter. Memory operations and conditional decisions synchronize
in order; branch-likely annulment and pending delay-slot transfers are explicit.
Incoming relations meet by intersection and every final edge is rechecked.

This is emitted-instruction/source-ABI evidence, not literal GPR/PC fault-state
identity or a proof of arbitrary callees. The helper receives equal A0/A1/SP and
memory, may apply the same public effects and arbitrary synchronized volatile
outputs, and preserves the caller's owned frame above its argument homes. Its
physical continuation addresses and private RA spills are deliberately distinct.
The existing connected-wrapper, native and access-prefix tests remain separate.
No guards, padding, installation or matching credit follow from this module alone.
"""
from collections import deque, Counter
from dataclasses import dataclass

MASK = 0xffffffff
ENTRY = 0x15104A80
SAVED = (*range(16,24),28,29,30,31)
SAVED_SP = 34 + SAVED.index(29)
RA_CELL = 34 + len(SAVED)
N = RA_CELL + 1

def signed(n): return (n ^ 0x80000000) - 0x80000000
def C(n): return ('C', n & MASK)

def expr(op, *xs):
    if op == 'add':
        terms=[];constant=0
        for x in xs:
            for a in x[1:] if x[0]=='add' else (x,):
                if a[0]=='C': constant+=a[1]
                else: terms.append(a)
        constant &= MASK
        if constant: terms.append(C(constant))
        terms=sorted(terms,key=repr)
        return C(0) if not terms else terms[0] if len(terms)==1 else ('add',*terms)
    if op in ('and','or','eq'): xs=tuple(sorted(xs,key=repr))
    if op=='sub':
        if xs[0]==xs[1]: return C(0)
        if xs[1][0]=='C': return expr('add',xs[0],C(-xs[1][1]))
    if op in ('and','or'):
        a,b=xs
        if a==b: return a
        if C(0) in xs: return C(0) if op=='and' else b if a==C(0) else a
        if C(MASK) in xs: return C(MASK) if op=='or' else b if a==C(MASK) else a
    if op=='eq' and xs[0]==xs[1]: return C(1)
    if op=='shl' and (xs[0]==C(0) or xs[1]==C(0)): return xs[0]
    if all(x[0]=='C' for x in xs):
        vs=[x[1] for x in xs];a=vs[0];b=vs[1]
        if op=='sub': return C(a-b)
        if op=='and': return C(a&b)
        if op=='or': return C(a|b)
        if op=='eq': return C(a==b)
        if op=='shl': return C(a<<(b&31))
        if op=='slt': return C(signed(a)<signed(b))
        if op in ('div','rem'):
            a,b=signed(a),signed(b)
            assert b and not(a==-(1<<31) and b==-1)
            q=(abs(a)//abs(b))*(-1 if (a<0)!=(b<0) else 1)
            return C(q if op=='div' else a-q*b)
    return (op,*xs)

def split(a):
    if a[0]=='C':return C(0),a[1]
    if a[0]!='add':return a,0
    constants=[x[1] for x in a[1:] if x[0]=='C']
    terms=[x for x in a[1:] if x[0]!='C']
    return (terms[0] if len(terms)==1 else ('add',*terms)),sum(constants)&MASK

def abstract(regs):
    # Equal bases imply value_i == value_j + delta (mod 2**32). Retaining
    # offsets, rather than equality alone, preserves SP's relation to entry SP.
    values=regs[0]+regs[1]
    parts=[split(a) for a in values]
    return (frozenset((i,j,(a[1]-parts[j][1])&MASK) for i,a in enumerate(parts) for j in range(i+1,len(parts)) if a[0]==parts[j][0]),
            frozenset((i,a[1]) for i,a in enumerate(values) if a[0]=='C'))

def materialize(inv):
    # A fresh free variable per affine class represents all concrete states
    # admitted by the invariant. No previous-path expression is assumed here.
    pairs,constants=inv;parents=list(range(2*N))
    def find(i):
        while parents[i]!=i:i=parents[i]
        return i
    offsets={(i,j):d for i,j,d in pairs}
    for i,j,d in sorted(pairs):
        a,b=find(i),find(j);parents[max(a,b)]=min(a,b)
    known=dict(constants)
    values=[C(known[i]) if i in known else expr('add',('V',find(i)),C(-offsets[(find(i),i)])) if find(i)!=i else ('V',i) for i in range(2*N)]
    return [values[:N],values[N:]]

@dataclass
class Event:
    kind: str
    value: tuple
    loc: tuple
    regs: list
    reg: int = -1
    choices: tuple = ()

class Relation:
    def __init__(self,left,right):
        self.words=(left,right);assert (len(left),len(right))==(113,110)
        r=[C(0)]+[('INITIAL',i) for i in range(1,34)]
        r += [r[i] for i in SAVED]
        r += [('INITIAL-RA-CELL',)]
        self.incoming={((0,None),(0,None)):abstract([r,r])}
        self.visits=[set(),set()];self.edges=set();self.effects={};self.iterations=0

    def next_event(self,side,loc,r):
        ws=self.words[side];steps=0
        while True:
            pc,jump=loc;steps+=1
            assert steps<1000,('pure cycle',side,loc)
            if pc=='call':return Event('call',(jump[0],r[29],r[4],r[5]),(jump[1],None),r)
            if pc=='return':return Event('return',(jump,),loc,r)
            assert 0<=pc<len(ws),('pc bounds',side,loc)
            self.visits[side].add(pc)
            w=ws[pc];op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
            imm=((w&65535)^32768)-32768
            after=(pc+1,None) if jump is None else jump
            def assign(index,value):
                assert index!=0,('write-zero',side,pc)
                r[index]=value
            if op in (4,5,20,21):
                assert jump is None,('branch delay branch',side,pc)
                predicate=expr('eq',r[rs],r[rt]);target=pc+1+imm
                choices=[]
                for equal in (False,True):
                    take=equal if op in (4,20) else not equal
                    dest=target if take else pc+2
                    choices.append((dest,None) if op in(20,21) and not take else (pc+1,(dest,None)))
                if predicate[0]=='C':loc=choices[bool(predicate[1])];continue
                return Event('branch',(predicate,),loc,r,choices=tuple(choices))
            if op==3:
                assert jump is None
                assign(31,C(ENTRY+(pc+2)*4))
                loc=(pc+1,('call',(((ENTRY+(pc+1)*4)&0xf0000000)|((w&0x3ffffff)<<2),pc+2)));continue
            if op==0 and fn==8:
                assert jump is None and rt==rd==sa==0
                loc=(pc+1,('return',r[rs]));continue
            if op in (35,36):return Event('read',(4 if op==35 else 1,expr('add',r[rs],C(imm))),after,r,rt)
            if op in (40,43):
                width=4 if op==43 else 1
                return Event('write',(width,expr('add',r[rs],C(imm)),r[rt] if width==4 else expr('and',r[rt],C(255))),after,r)
            if not w:pass
            elif op==15:
                assert rs==0;assign(rt,C((w&65535)<<16))
            elif op==9:assign(rt,expr('add',r[rs],C(imm)))
            elif op==10:assign(rt,expr('slt',r[rs],C(imm)))
            elif op==0:
                if fn==0:
                    assert rs==0;assign(rd,expr('shl',r[rt],C(sa)))
                elif fn==4:assign(rd,expr('shl',r[rt],expr('and',r[rs],C(31))))
                elif fn in (33,35,36,37):assign(rd,expr({33:'add',35:'sub',36:'and',37:'or'}[fn],r[rs],r[rt]))
                elif fn==26:
                    assert rd==sa==0 and r[rt]==C(160),('division divisor',side,pc,r[rt])
                    r[32]=expr('rem',r[rs],r[rt]);r[33]=expr('div',r[rs],r[rt])
                elif fn==18:
                    assert rs==rt==sa==0;assign(rd,r[33])
                else:raise AssertionError(('SPECIAL',side,pc,hex(w)))
            else:raise AssertionError(('opcode',side,pc,hex(w)))
            loc=after

    def step(self,key,inv):
        regs=materialize(inv)
        reconstructed=abstract(regs)
        assert inv[0]<=reconstructed[0] and inv[1]<=reconstructed[1],('invalid materialization',key)
        events=[self.next_event(i,key[i],regs[i]) for i in range(2)]
        a,b=events
        assert (a.kind,a.value)==(b.kind,b.value),('effect mismatch',key,(a.kind,a.value),(b.kind,b.value))
        kind=a.kind;self.effects[key]=kind
        if kind=='return':
            for i,reg in enumerate(SAVED):
                assert a.regs[reg]==a.regs[34+i] and b.regs[reg]==b.regs[34+i],('ABI',key,reg)
            return []
        if kind=='branch':return [(tuple(e.choices[choice] for e in events),abstract(regs)) for choice in (0,1)]
        if kind=='read':
            assert a.reg and b.reg
            for e in events:
                saved_address=expr('add',e.regs[SAVED_SP],C(-84))
                e.regs[e.reg]=e.regs[RA_CELL] if e.value==(4,saved_address) else ('READ',)
        if kind=='write':
            for e in events:
                width,address,value=e.value
                saved_address=expr('add',e.regs[SAVED_SP],C(-84))
                if width==4 and address==saved_address:e.regs[RA_CELL]=value
                else:
                    a_base,a_offset=split(address);s_base,s_offset=split(saved_address)
                    disjoint=a_base==s_base and not({(a_offset+i)&MASK for i in range(width)}&{(s_offset+i)&MASK for i in range(4)})
                    # Any potential alias destroys the saved-value fact. This
                    # deliberately rejects a return proof after unknown damage.
                    if not disjoint:e.regs[RA_CELL]=('UNKNOWN-WRITE',)
        if kind=='call':
            assert a.value[0]==0x151494E0,('callee',a.value)
            for e in events:assert expr('add',e.regs[SAVED_SP],C(-84))==expr('add',e.regs[29],C(20))
            # Source ABI abstraction: same helper actions from same memory and
            # explicit arguments, plus synchronized arbitrary volatile results.
            # RA is NOT equated: physical continuation addresses differ. Callee
            # private stack/RA-spill effects are outside this abstraction.
            for reg in (1,2,3,*range(4,16),24,25,32,33):
                a.regs[reg]=b.regs[reg]=('CALL-OUTPUT',reg)
        return [((a.loc,b.loc),abstract(regs))]

    def run(self):
        todo=deque(self.incoming)
        while todo:
            key=todo.popleft();self.iterations+=1
            for dest,inv in self.step(key,self.incoming[key]):
                self.edges.add((key,dest));previous=self.incoming.get(dest)
                joined=inv if previous is None else (previous[0]&inv[0],previous[1]&inv[1])
                if joined!=previous:self.incoming[dest]=joined;todo.append(dest)
            assert self.iterations<20000
        for key,inv in self.incoming.items():
            for dest,after in self.step(key,inv):
                assert self.incoming[dest][0]<=after[0] and self.incoming[dest][1]<=after[1]
        return dict(CFG_nodes=len(self.incoming),CFG_edges=len(self.edges),worklist_steps=self.iterations,
                    visited_words=[len(v) for v in self.visits],unvisited_words=[sorted(set(range(len(w)))-v) for w,v in zip(self.words,self.visits)],
                    effect_boundaries=dict(Counter(self.effects.values())),loop_fixed_point_checked=True,
                    ordered_memory_and_explicit_call_arguments_equal=True,source_ABI_helper_abstraction=True,
                    arbitrary_synchronized_entry_registers_and_memory_reads=True,
                    caller_owned_RA_cell_preserved=True,void_return_value_unconstrained=True,
                    literal_GPR_PC_and_callee_private_RA_stack_identity=False,source_installed=False,matching_credit=0,
                    invariants=[dict(locations=key,affine_equalities=sorted(inv[0]),constants=sorted(inv[1])) for key,inv in sorted(self.incoming.items(),key=lambda row:repr(row[0]))],
                    edges=sorted(self.edges,key=repr))

def qualify(prepared):
    """Check the qualified raw object, complete CFG, and effective mutations."""
    left,right=prepared['truth'],prepared['words']
    report=Relation(left,right).run()
    rejected=[];accepted=[]
    # These target changes skip only redundant/dead pure setup. The successful
    # relation proves them under exactly the same abstraction as the baseline;
    # accepting them is intentional, rather than calling an inert control bad.
    benign={(0,0x98),(0,0xB4),(0,0x104),(0,0x10C),(0,0x150),(0,0x19C),
            (1,0x98),(1,0xB4),(1,0xBC),(1,0xD4),(1,0x108),(1,0x190)}
    for side,words in enumerate((left,right)):
        for i,w in enumerate(words):
            op=w>>26;changes=[]
            if op in(35,36,40,43):changes.append(('memory-offset',4 if op in(35,43)else 1))
            if op in(4,5,20,21):changes.append(('branch-target',1))
            if op==3:changes.append(('callee-target',1))
            if op==10:changes.append(('scan-limit',1))
            if op==9 and w>>21&31==0:changes.append(('immediate-value',1))
            for kind,mask in changes:
                wrong=[left[:],right[:]];wrong[side][i]^=mask
                item=dict(stream=side,offset=i*4,kind=kind)
                try:Relation(*wrong).run()
                except(AssertionError,KeyError,IndexError):
                    assert(side,i*4)not in benign,('benign control unexpectedly rejected',item)
                    rejected.append(item)
                else:
                    assert(side,i*4)in benign,('ineffective negative control',item)
                    accepted.append(item)
    for side in (0,1):
        wrong=[left[:],right[:]]
        # Turning BEQL into ordinary BEQ wrongly executes the packet-actor
        # store on its untaken path. Both streams must expose that extra write.
        assert wrong[side][0xAC//4]>>26==20
        wrong[side][0xAC//4]^=1<<30
        try:Relation(*wrong).run()
        except(AssertionError,KeyError,IndexError):
            rejected.append(dict(stream=side,offset=0xAC,kind='memory-delay-annulment'))
        else:raise AssertionError(('ineffective delay-annulment control',side))
    assert len(rejected)==131 and len(accepted)==12
    report['effective_instruction_controls']=rejected
    report['equivalent_pure_or_dead_setup_controls']=accepted
    return report
