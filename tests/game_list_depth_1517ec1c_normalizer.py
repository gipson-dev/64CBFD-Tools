"""Two commutative FP operands and one closed, dead-boundary FPR swap."""
import hashlib,struct

def fp_access(w):
    op,rs,rt,fs,fd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w>>6&31,w&63
    if op==49:return set(),{rt}
    if op==57:return{rt},set()
    if op!=17:return set(),set()
    if rs==4:return set(),{fs}
    if rs==0:return{fs},set()
    if rs in(16,20):
        return({fs,rt}if fn in(0,1,2,3,50,60,62)else{fs}),({fd}if fn not in(50,60,62)else set())
    return set(),set()

def derive(raw,refs):
    assert len(raw)==540 and hashlib.sha256(raw).hexdigest()=='a81d5b64888448e1af841741ea1bec6b083146b32e6132f3332f9d07464178ac'
    old=list(struct.unpack('>135I',raw));new=list(old)
    for i,fn in((47,2),(51,0)):
        w=old[i];assert w>>26==17 and w>>21&31==16 and w&63==fn
        fs,ft=w>>11&31,w>>16&31
        new[i]=(w&~((31<<11)|(31<<16)))|(ft<<11)|(fs<<16)
    written=set()
    for i in range(78,97):
        reads,writes=fp_access(old[i]);assert not((reads&{10,18})-written),(i,reads,written)
        written|=writes&{10,18}
        w=old[i]
        if w>>26!=17:continue
        rs=w>>21&31
        shifts=(11,)if rs in(0,4)else(6,11,16)if rs in(16,20)else()
        for shift in shifts:
            value=w>>shift&31
            if value in(10,18):new[i]=(new[i]&~(31<<shift))|((28-value)<<shift)
    assert written=={10,18}
    assert not any(fp_access(w)[0]&{10,18}for w in old[97:])
    changes=[i for i,(a,b)in enumerate(zip(old,new))if a!=b]
    assert changes==[47,51,78,87,90,92,93,95,96],changes
    assert all(i*4 not in refs for i in changes)
    proof=dict(guard_count=9,frame=72,insertions=0,omissions=0,origins=list(range(135)),
        commute_indices=[47,51],FPR_swap=[10,18],FPR_region=[78,96],dead_region_inputs=True,dead_region_outputs=True,
        memory_and_branch_order_unchanged=True,FP_exception_priority_not_claimed=True)
    return struct.pack('>135I',*new),refs,proof
