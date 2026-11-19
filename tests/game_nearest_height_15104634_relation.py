"""Paired per-PC equality invariant; complete CFG, ordered memory and FP effects.

Registers are related by value, not by spelling. No FP rewrite, memory exclusion,
path bound, loop unroll bound or assumption about candidate indices is used.
This proves emitted-code relations, not portable C's capacity or literal raw
temporary-register dumps at a fault.
"""
from collections import deque,Counter
from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_nearest_height_15104634_recovery import SYMS

F=lambda n:32+n
CC,CSR,HI,LO=64,65,66,67
ALL=68

class Relation:
    def __init__(self,a,b):
        assert len(a)==len(b)==272
        self.words=a,b;self.incoming={0:frozenset((i,i)for i in range(ALL))}
        self.edges=set();self.visits=set();self.effects={};self.iterations=0
    def instruction(self,pc,rel):
        self.visits.add(pc);a,b=(s[pc]for s in self.words)
        def fields(w):return w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63,w&65535
        op,rs,rt,rd,sa,fn,imm=fields(a);bp,bs,bt,bd,ba,bf,bi=fields(b)
        assert (op,fn if op in(0,17)else None)==(bp,bf if bp in(0,17)else None),('opcode',pc,hex(a),hex(b))
        rel=set(rel)
        def same(x,y):assert(x,y)in rel,('live operand',pc,x,y,hex(a),hex(b))
        def write(x,y,copy=None):
            assert x!=0 and y!=0,('unsupported write to architectural zero',pc)
            before=rel.copy();rel.difference_update((l,r)for l,r in before if l==x or r==y)
            rel.add((x,y))
            if copy:
                sx,sy=copy
                rel.update((x,r)for l,r in before if l==sx and r!=y)
                rel.update((l,y)for l,r in before if r==sy and l!=x)
            assert(0,0)in rel
        def effect(kind):self.effects[pc]=kind
        if not a and not b:return frozenset(rel)
        if op==0:
            assert fn==bf and sa==ba
            if fn==8:
                assert rt==bt==rd==bd==sa==ba==0
                same(rs,bs);effect('return')
            elif fn==0:
                assert rs==bs==0
                same(rt,bt);write(rd,bd)
            elif fn in(33,35,37):
                same(rs,bs);same(rt,bt)
                copy=(rs,bs)if rt==bt==0 and fn in(33,35,37)else(rt,bt)if rs==bs==0 and fn in(33,37)else None
                write(rd,bd,copy)
            else:raise AssertionError(('SPECIAL',pc,fn))
        elif op==15:
            assert imm==bi;write(rt,bt,(0,0)if imm==0 else None)
        elif op in(9,12):
            assert imm==bi;same(rs,bs);write(rt,bt,(rs,bs)if op==9 and imm==0 else None)
        elif op in(33,35,49,53):
            assert imm==bi;same(rs,bs);effect('read')
            if op==53:assert rt==bt and rt%2==0 and rt<31
            write(F(rt)if op in(49,53)else rt,F(bt)if op in(49,53)else bt)
            if op==53:write(F(rt+1),F(bt+1))
        elif op in(43,57,61):
            assert imm==bi;same(rs,bs);same(F(rt)if op in(57,61)else rt,F(bt)if op in(57,61)else bt)
            if op==61:
                assert rt==bt and rt%2==0 and rt<31
                same(F(rt+1),F(bt+1))
            effect('write')
        elif op==17:
            assert rs==bs
            if rs==0:same(F(rd),F(bd));write(rt,bt,(F(rd),F(bd)))
            elif rs==4:same(rt,bt);write(F(rd),F(bd),(rt,bt))
            elif rs in(16,20):
                assert fn==32 if rs==20 else fn in(0,1,2,6,7,13,60)
                same(F(rd),F(bd))
                if fn in(0,1,2,60):same(F(rt),F(bt))
                else:assert rt==bt==0
                if fn==6:write(F(sa),F(ba),(F(rd),F(bd)))
                elif fn==7:write(F(sa),F(ba))
                else:
                    assert fn in(0,1,2,13,32,60),('FP',pc,fn)
                    same(CSR,CSR);write(CSR,CSR);effect('ordered-FP')
                    if fn==60:write(CC,CC)
                    else:write(F(sa),F(ba))
            else:raise AssertionError(('COP1',pc,rs))
        elif op==3:
            assert a==b;write(31,31);effect('call')
        else:raise AssertionError(('ordinary opcode',pc,op))
        return frozenset(rel)
    def step(self,pc,rel):
        a,b=(s[pc]for s in self.words);op=a>>26;rs=a>>21&31;rt=a>>16&31
        branch=op in(1,4,5,6,7,20,21,22,23)or(op==17 and rs==8)
        def same(x,y):assert(x,y)in rel,('branch operand',pc,x,y)
        if branch:
            self.visits.add(pc);assert a>>26==b>>26 and a&65535==b&65535
            bs,bt=b>>21&31,b>>16&31
            if op==17:assert rs==bs and rt==bt;same(CC,CC)
            elif op==1:assert rt==bt;same(rs,bs)
            else:
                same(rs,bs)
                if op in(4,5,20,21):same(rt,bt)
                else:assert rt==bt==0
            offset=((a&65535)^32768)-32768;target=pc+1+offset
            likely=op in(20,21,22,23)or(op==17 and bool(rt&2))or(op==1 and rt in(2,3))
            after=self.instruction(pc+1,rel)
            return[(target,after),(pc+2,rel if likely else after)]
        after=self.instruction(pc,rel)
        if op==3:
            after=self.instruction(pc+1,after)
            # Both providers occur before the first allocation divergence.
            assert all((i,i)in after for i in range(ALL)),('call input state',pc)
            return[(pc+2,frozenset((i,i)for i in range(ALL)))]
        if op==0 and a&63==8:
            after=self.instruction(pc+1,after)
            for i in(0,2,*range(16,24),28,29,30,31,*range(F(20),F(32)),CSR,HI,LO):
                assert(i,i)in after,('ABI return',pc,i)
            return[]
        return[(pc+1,after)]
    def run(self):
        pending=deque([0])
        while pending:
            pc=pending.popleft();self.iterations+=1
            assert 0<=pc<272
            for dest,rel in self.step(pc,self.incoming[pc]):
                self.edges.add((pc,dest));previous=self.incoming.get(dest)
                joined=rel if previous is None else previous&rel
                if previous!=joined:self.incoming[dest]=joined;pending.append(dest)
            assert self.iterations<50000
        assert self.visits==set(range(272)),('unvisited',sorted(set(range(272))-self.visits))
        # Recheck every stable edge; the receipt is a fixed-point certificate,
        # not evidence from a single traversal or a finite execution sample.
        for pc,rel in self.incoming.items():
            for dest,after in self.step(pc,rel):assert self.incoming[dest]<=after
        maps={str(pc*4):sorted([list(v)for v in rel])for pc,rel in sorted(self.incoming.items())}
        return dict(words=272,CFG_nodes=len(self.incoming),CFG_edges=len(self.edges),all_body_words_checked=len(self.visits),
            worklist_steps=self.iterations,effects=dict(Counter(self.effects.values())),
            ordered_memory_and_FP_effects_equal=True,branch_delay_slots_checked=True,loop_fixed_point_checked=True,
            arbitrary_synchronized_initial_memory_and_FCSR=True,raw_literal_temporary_register_identity=False,
            portable_C_capacity_not_proved=True,source_installed=False,matching_credit=0,invariants=maps)

def qualify(prepared):
    left,right=prepared['truth'],prepared['words'];report=Relation(left,right).run();controls=[]
    for name,at,mask in [('coordinate-home',0x100,4),('FP-product',0x120,1<<11),('branch-target',0x150,1),('delay-index-store',0x158,1<<16),('return-RA-restore',0x42C,1<<16),('saved-FP-pair',0x430,1<<16)]:
        wrong=right[:];wrong[at//4]^=mask
        try:Relation(left,wrong).run()
        except (AssertionError,IndexError):controls.append(name)
        else:raise AssertionError(('ineffective relation negative',name,at))
    report['effective_instruction_controls']=controls
    return report
