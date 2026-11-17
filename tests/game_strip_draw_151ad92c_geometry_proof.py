"""Relate one complete generic geometry sample and its induction boundary."""
from pathlib import Path
from collections import Counter
import json,struct
from tools.tests import game_strip_draw_151ad92c_entry_proof as opening
from tools.tests import game_strip_draw_151ad92c_basis_row_proof as row
from tools.tests.game_perpendicular_offset_1519ef90_proof import Terms
from tools.tests import game_strip_draw_151ad92c_geometry_normalization as normal
e=opening.e

def cuts(words,side):
    head=0x151AD9F0-0x151AD92C if side=='retail' else normal.index(0x1B9C)*4
    post=next(at for at,name in opening.cuts(words).items()if name=='empty')
    return head,{head:'row',post:'post'}

def roles(state,side,end):
    count=state.r[10 if side=='retail'else 8]
    common=(state.r[4],state.r[16],state.r[17],state.r[29],state.r[7],count,
        state.r[13 if side=='retail'else 12],state.r[31 if side=='retail'else 13],
        state.r[9],state.f[20],state.f[28])
    if end=='post':return common
    index=state.r[8 if side=='retail'else 3]
    cursor=state.r[3 if side=='retail'else 5]
    assert index==e.add(row.INDEX,1),('sample index',side,index)
    assert cursor==e.scale(e.add(row.INDEX,1),24),('sample cursor',side,cursor)
    if side=='retail':assert state.r[11]==e.add(row.INDEX,2),('next index',state.r[11])
    return common+(index,cursor)

def prove(truth,candidate):
    terms=Terms();answers=[]
    for side,words in(('retail',truth),('raw',candidate)):
        start,stops=cuts(words,side)
        answers.append(opening.Program(words,terms).paths(start,stops,row.State(side)))
    left,right=answers
    assert left.keys()==right.keys(),('path predicates',len(left),len(right))
    for key,a in left.items():
        b=right[key]
        for name,x,y in(('private bytes',a.frame(),b.frame()),('ordered stores and FP status',a.trace,b.trace),('public bytes',a.public,b.public),('stable reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition),('live roles',roles(a,'retail',key[0]),roles(b,'raw',key[0]))):
            if x!=y:
                at=next((i for i,(u,v)in enumerate(zip(x,y))if u!=v),None)if isinstance(x,(list,tuple))else None
                raise AssertionError(('complete geometry relation',key[0],name,at,repr(x[at]if at is not None else x)[:650],repr(y[at]if at is not None else y)[:650]))
    return dict(paths=len(left),ends=dict(Counter(key[0]for key in left)),all_320_private_bytes=True,combined_ordered_stores_and_FP_status=True,stable_reads=True,loop_invariant_advanced=True,terms=len(terms.values),source_installed=False,c_match_credit=0)

def prefix(truth,candidate):
    terms=Terms();answers=[]
    for side,words in(('retail',truth),('raw',candidate)):
        _,stops=cuts(words,side)
        answers.append(opening.Program(words,terms).paths(0,stops,opening.State()))
    left,right=answers
    assert left.keys()==right.keys(),('entry path predicates',len(left),len(right))
    for key,a in left.items():
        b=right[key];end=key[0]
        def live(s,side):
            count=s.r[10 if side=='retail'else 8]
            values=(s.r[4],s.r[16],s.r[17],s.r[29],s.r[7],count,s.r[13 if side=='retail'else 12],s.r[31 if side=='retail'else 13],s.r[9],s.f[20],s.f[28])
            if end=='row':
                assert s.r[8 if side=='retail'else 3]==0
                assert s.r[3 if side=='retail'else 5]==0
                if side=='retail':assert s.r[11]==1
            return values
        for name,x,y in(('all private',a.frame(),b.frame()),('ordered effects',a.trace,b.trace),('public',a.public,b.public),('reads',a.read_set,b.read_set),('FP status',a.fcsr,b.fcsr),('FP condition',a.condition,b.condition),('live roles',live(a,'retail'),live(b,'raw'))):
            assert x==y,('entry geometry invariant',end,name,repr(x)[:600],repr(y)[:600])
    return dict(paths=len(left),ends=dict(Counter(key[0]for key in left)),all_320_private_bytes=True,geometry_invariant_established=True,empty_count_boundary=True)

def controls(truth,candidate):
    from tools.tests.game_strip_update_151ad174_proof import alternate
    renamed=[alternate(w)for w in candidate]
    positive=dict(prefix=prefix(truth,renamed),generic=prove(truth,renamed))
    changes=[]
    for name,before,after in(('wrong-cached-Z-home',0xC7A00100,0xC7A00104),('wrong-point-stride',0x24A50018,0x24A5001C),('wrong-row-index-delay',0x00C01825,0x24C30001)):
        assert candidate.count(before)==1;changes.append((name,candidate.index(before),after))
    branch=normal.index(0x1F20);assert candidate[branch]>>26==5
    changes.append(('inverted-geometry-backedge',branch,candidate[branch]^1<<26))
    rejected=[]
    for name,index,value in changes:
        bad=candidate[:];bad[index]=value
        try:prove(truth,bad)
        except AssertionError as error:
            reason=str(error);assert not any(s in reason for s in('unsupported','unbounded','escaped code')),reason
            rejected.append(dict(name=name,index=index,rejected=reason[:240]))
        else:raise AssertionError(('ineffective geometry control',name))
    return dict(independent_GPR_allocation_positive=positive,effective_controls=rejected)
