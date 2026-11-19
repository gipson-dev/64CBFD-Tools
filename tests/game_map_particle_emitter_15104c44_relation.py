"""Private normal-execution ABI relation with strictly ordered FP transitions.

Frame cells follow the recovered typed layout. Private accesses may stutter;
public accesses, FP operations, decisions and calls synchronize. Every data cell
is compared BEFORE every helper, so arbitrary paired helper writes cannot hide
an earlier discrepancy. Physical raw fault-PC/private-prefix identity is outside
this source-ABI relation. Hardware FP transition functions remain uninterpreted.
"""
from collections import deque,Counter
from pathlib import Path
import json
from tools.tests.game_map_record_dispatch_15104a80_relation import C,expr,split,signed
F=lambda i:32+i
HI,LO,CC,CSR=64,65,66,67
SAVED=(*range(16,24),28,29,30,31,*range(F(20),F(32)))
GHOST_SP=68+SAVED.index(29)
CELLS=[(i,4)for i in range(0,0x8C,4)]+[(0x8C,2),(0x8E,1),(0x8F,1)]+[(i,4)for i in range(0x90,0xC0,4)]+[(i,1)for i in range(0xC0,0xC4)]+[(i,4)for i in range(0xC4,0xD0,4)]+[(0xD0,2),(0xD2,2)]+[(i,1)for i in range(0xD4,0xDC)]+[(0xDC,4)]
MEM=68+len(SAVED);N=MEM+len(CELLS)
INDEX={key:MEM+i for i,key in enumerate(CELLS)}
assert sorted(at+j for at,n in CELLS for j in range(n))==list(range(224))
def abstract(regs):
    values=regs[0]+regs[1];parts=[split(a)for a in values]
    return(frozenset((i,j,(a[1]-parts[j][1])&0xffffffff)for i,a in enumerate(parts)for j in range(i+1,len(parts))if a[0]==parts[j][0]),frozenset((i,a[1])for i,a in enumerate(values)if a[0]=='C'))
def materialize(inv):
    pairs,constants=inv;parents=list(range(2*N));offsets={(i,j):d for i,j,d in pairs};known=dict(constants)
    def find(i):
        while parents[i]!=i:i=parents[i]
        return i
    for i,j,d in sorted(pairs):a,b=find(i),find(j);parents[max(a,b)]=min(a,b)
    values=[C(known[i])if i in known else expr('add',('V',find(i)),C(-offsets[find(i),i]))if find(i)!=i else('V',i)for i in range(2*N)]
    return[values[:N],values[N:]]
def ex(op,*xs):
    if op=='sx16':
        x=xs[0]
        return C(((x[1]&65535)^32768)-32768)if x[0]=='C'else('sx16',x)
    if op in('sra','urem','udiv')and all(x[0]=='C'for x in xs):
        a,b=(x[1]for x in xs)
        return C(signed(a)>>(b&31))if op=='sra'else C(a%b)if op=='urem'else C(a//b)
    if op in('sra','urem','udiv'):return(op,*xs)
    return expr(op,*xs)
class Relation:
    def __init__(self,left,right):
        assert len(left)==len(right)==237;self.words=(left,right);self.visits=[set(),set()];self.effects={};self.edges=set();self.iterations=0
        r=[C(0)]+[('ENTRY',i)for i in range(1,68)];r +=[r[i]for i in SAVED];r +=[('INITIAL-FRAME',o,n)for o,n in CELLS]
        assert len(r)==N;self.incoming={((0,None),(0,None)):abstract([r,r])}
    def cell(self,address,width,r):
        base,offset=split(address);sp,shift=split(r[GHOST_SP])
        if base!=sp:return None
        delta=signed((offset-shift)&0xffffffff)+224
        if not 0<=delta<224:return None
        assert(delta,width)in INDEX,('private type/span mismatch',delta,width)
        return INDEX[delta,width]
    def next(self,side,loc,r):
        steps=0
        while True:
            pc,jump=loc;steps+=1;assert steps<1000
            if pc=='call':
                target,continuation=jump
                count={0x1000FD38:3,0x151464B8:1,0x150ADA68:0,0x150ADA20:0,0x15143874:4,0x15046C80:4,0x15105CE0:4}[target]
                return('CALL',(target,r[29],r[CSR],*r[4:4+count]),(continuation,None),r,())
            if pc=='return':return('RETURN',(jump,),loc,r,())
            assert 0<=pc<237,(side,loc);self.visits[side].add(pc);w=self.words[side][pc]
            op,rs,rt,rd,sa,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63;imm=((w&65535)^32768)-32768
            after=(pc+1,None)if jump is None else jump
            if op in(1,4,5,20,21)or(op==17 and rs==8):
                assert jump is None
                if op==1:
                    assert rt in(0,1,2,3);pred=ex('slt',r[rs],C(0));takes=(rt in(0,2));likely=rt in(2,3)
                elif op==17:pred=r[CC];takes=bool(rt&1);likely=bool(rt&2)
                else:pred=ex('eq',r[rs],r[rt]);takes=op in(4,20);likely=op in(20,21)
                choices=[]
                for truth in(False,True):
                    taken=truth==takes;dest=pc+1+imm if taken else pc+2
                    choices.append((dest,None)if likely and not taken else(pc+1,(dest,None)))
                if pred[0]=='C':loc=choices[bool(pred[1])];continue
                return('BRANCH',(pred,),loc,r,tuple(choices))
            if op==3:
                assert jump is None;r[31]=C(0x15104C44+(pc+2)*4);loc=(pc+1,('call',(((0x15104C44+(pc+1)*4)&0xf0000000)|((w&0x3ffffff)<<2),pc+2)));continue
            if op==0 and fn==8:
                assert jump is None and rs==31 and rt==rd==sa==0;loc=(pc+1,('return',r[rs]));continue
            if op in(33,35,36,49,53,40,41,43,57,61):
                address=ex('add',r[rs],C(imm));width=8 if op in(53,61)else 4 if op in(35,49,43,57)else 2 if op in(33,41)else 1
                write=op in(40,41,43,57,61);floating=op in(49,53,57,61);reg=F(rt)if floating else rt
                if width==8:assert rt%2==0 and rt<=30
                if not write and not floating:assert reg!=0
                cell=self.cell(address,4 if width==8 else width,r)
                if cell is not None:
                    count=2 if width==8 else 1
                    for i in range(count):
                        current=self.cell(ex('add',address,C(4*i)),4 if width==8 else width,r)
                        if write:r[current]=r[reg+i]if width>=4 else ex('and',r[reg],C((1<<(8*width))-1))
                        else:r[reg+i]=ex('sx16',r[current])if op==33 else r[current]
                    loc=after;continue
                assert width<=4,('public wide FP access',side,pc)
                if write:return('WRITE',(width,address,r[reg]if width==4 else ex('and',r[reg],C((1<<(8*width))-1))),after,r,())
                return('READ',(width,address),after,r,(reg,op))
            if op==17:
                if rs==0:r[rt]=r[F(rd)]
                elif rs==4:r[F(rd)]=r[rt]
                else:
                    assert rs==16 and fn in(0,1,2,60),(side,pc,hex(w))
                    if fn==60:assert sa==0
                    return('FP',(fn,r[F(rd)],r[F(rt)],r[CSR]),after,r,(F(sa),fn))
            elif w==0:pass
            elif op==15:r[rt]=C((w&65535)<<16)
            elif op in(9,12):r[rt]=ex('add'if op==9 else'and',r[rs],C(imm if op==9 else w&65535))
            elif op==0:
                if fn in(0,3):r[rd]=ex('shl'if fn==0 else'sra',r[rt],C(sa))
                elif fn in(33,35,37):r[rd]=ex({33:'add',35:'sub',37:'or'}[fn],r[rs],r[rt])
                elif fn==27:
                    assert r[rt][0]=='C'and r[rt][1]in(3,13,156)
                    r[HI]=ex('urem',r[rs],r[rt]);r[LO]=ex('udiv',r[rs],r[rt])
                elif fn==16:r[rd]=r[HI]
                else:raise AssertionError(('SPECIAL',side,pc,hex(w)))
            else:raise AssertionError(('opcode',side,pc,hex(w)))
            assert r[0]==C(0),('architectural zero modified',side,pc)
            loc=after
    def step(self,key,inv):
        regs=materialize(inv);reconstructed=abstract(regs);assert inv[0]<=reconstructed[0]and inv[1]<=reconstructed[1]
        a,b=(self.next(i,key[i],regs[i])for i in range(2));assert a[:2]==b[:2],('effect mismatch',key,a[:2],b[:2]);kind=a[0];self.effects[key]=kind
        if kind=='RETURN':
            for r in regs:
                for i,index in enumerate(SAVED):assert r[index]==r[68+i],('ABI return',key,index)
            return[]
        if kind=='BRANCH':return[(tuple(e[4][choice]for e in(a,b)),abstract(regs))for choice in(0,1)]
        if kind=='READ':
            for event,r in zip((a,b),regs):reg,op=event[4];r[reg]=ex('sx16',('READ',))if op==33 else('READ',)
        if kind=='FP':
            for event,r in zip((a,b),regs):
                dest,fn=event[4];r[CC if fn==60 else dest]=('FP-CC',)if fn==60 else('FP-VALUE',);r[CSR]=('FP-CSR',)
        if kind=='CALL':
            # Compare all descriptor/vector input cells BEFORE allowing arbitrary
            # coupled writes. A helper that preserves them is included; unequal
            # inputs are never repaired by replacing them with equal outputs.
            for i,(offset,width)in enumerate(CELLS):
                if offset>=0x70:assert regs[0][MEM+i]==regs[1][MEM+i],('call private data',key,offset,width,regs[0][MEM+i],regs[1][MEM+i])
            for side,r in enumerate(regs):
                for index in(1,2,3,*range(4,16),24,25,*range(F(0),F(20)),HI,LO,CC,CSR):r[index]=('CALL-OUTPUT',index)
                for i,(offset,width)in enumerate(CELLS):
                    if offset<16:r[MEM+i]=('CALL-HOME',side,offset)
                    elif offset>=0x70:r[MEM+i]=('CALL-DATA',offset)
        return[((a[2],b[2]),abstract(regs))]
    def run(self):
        todo=deque(self.incoming)
        while todo:
            key=todo.popleft();self.iterations+=1
            for dest,inv in self.step(key,self.incoming[key]):
                self.edges.add((key,dest));previous=self.incoming.get(dest);joined=inv if previous is None else(previous[0]&inv[0],previous[1]&inv[1])
                if previous!=joined:self.incoming[dest]=joined;todo.append(dest)
            assert self.iterations<20000
        for key,inv in self.incoming.items():
            for dest,after in self.step(key,inv):assert self.incoming[dest][0]<=after[0]and self.incoming[dest][1]<=after[1]
        assert self.visits==[set(range(237)),set(range(237))]
        return dict(words=237,frame=224,CFG_nodes=len(self.incoming),CFG_edges=len(self.edges),worklist_steps=self.iterations,
            effects=dict(Counter(self.effects.values())),complete_loop_fixed_point=True,all_private_data_compared_before_helpers=True,ordered_public_memory_and_FP_transitions=True,
            arbitrary_FP_transition_and_FCSR_functions=True,physical_raw_fault_PC_private_prefix_identity=False,source_installed=False,matching_credit=0,
            invariants=[dict(locations=key,affine_equalities=sorted(inv[0]),constants=sorted(inv[1]))for key,inv in sorted(self.incoming.items(),key=lambda row:repr(row[0]))],edges=sorted(self.edges,key=repr))
def qualify(left,right):
    report=Relation(left,right).run();controls=[]
    changes=[('saved-F26',0x384,1<<16),('descriptor-pointer',0x348,4),('counter-remainder-sign',0x300,1),('channel-byte',0x344,1),
        ('helper-target',0x34C,1),('timer-source',0x40,2),('duration',0x308,1),('private-origin-store',0x14C,4)]
    for pc,w in enumerate(left):
        if w>>26==17 and w>>21&31==16 and w&63 in(0,1,2,60):changes.append(('FP-operand-%03X'%(pc*4),pc*4,1<<16))
    for name,at,mask in changes:
        wrong=left[:];wrong[at//4]^=mask
        try:Relation(wrong,right).run()
        except(AssertionError,KeyError,IndexError):controls.append(name)
        else:raise AssertionError(('ineffective relation control',name,hex(at)))
    report['effective_instruction_controls']=controls;return report
