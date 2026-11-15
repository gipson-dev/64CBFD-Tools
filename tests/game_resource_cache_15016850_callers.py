"""The authentic caller's two-word JAL window; full parent remains unqualified."""
import itertools,json,struct
from tools.tests import game_resource_cache_15016850_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary

def reads(w):
    op,rs,rt,fn=w>>26,w>>21&31,w>>16&31,w&63
    if not w or op in(3,15):return set()
    if op==0:
        assert fn in(0,33,37,42);return{rt}if fn==0 else{rs,rt}
    if op in(4,5,20,21,40,41,43):return{rs,rt}
    assert op in(6,7,9,22,23,35,36);return{rs}

def return_use_proof(rom,changed_caller=False,changed_killer=False):
    def word(pc):return struct.unpack_from('>I',rom,pc-0x15000000+0x2d4b0)[0]
    # Both callees kill incoming V0 before any read. The second does so in
    # an ordinary branch delay slot, which executes for both branch outcomes.
    for entry,length in((0x15083da0,4),(0x1508295c,9)):
        prefix=[word(entry+i*4)for i in range(length)]
        if changed_killer and entry==0x1508295c:prefix[-1]=prefix[-1]&~(31<<16)|3<<16
        assert all(2 not in reads(w)for w in prefix)
        if entry==0x15083da0:assert prefix[-1]==0x00001025
        else:assert prefix[-2]>>26==4 and prefix[-1]>>26==15 and prefix[-1]>>16&31==2
    pending=[0x15017074];seen=set();cuts=set()
    while pending:
        pc=pending.pop()
        if pc in seen:continue
        assert 0x15017074<=pc<=0x150170e0;seen.add(pc);w=word(pc)
        if changed_caller and pc==0x1501707c:assert w==0x00002825;w=0x00402825
        assert 2 not in reads(w),('Cache return used before overwrite',hex(pc))
        op=w>>26
        if op==3:
            assert 2 not in reads(word(pc+4));target=0x10000000|((w&0x3ffffff)<<2)
            assert target in(0x15083da0,0x1508295c);cuts.add(target);continue
        if op in(4,5,6,7,20,21,22,23):
            assert 2 not in reads(word(pc+4));target=pc+4+4*(((w&65535)^32768)-32768)
            pending.extend((target,pc+8))
        else:pending.append(pc+4)
    assert cuts=={0x15083da0,0x1508295c}
    return len(seen)

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();allwords=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0xc000000|((g.source.ENTRY>>2)&0x3ffffff)
    assert[i*4 for i,w in enumerate(allwords)if w==jal]==[0x4451c]and not[i for i,w in enumerate(allwords)if w==g.source.ENTRY]
    start,end=0x1501706c,0x15017074;window=struct.unpack_from('>2I',rom,0x4451c);assert window==(jal,0)
    continuation=return_use_proof(rom)
    for caller,killer in((True,False),(False,True)):
        try:return_use_proof(rom,caller,killer)
        except AssertionError:pass
        else:raise AssertionError('Ineffective return-use proof control')
    programs=[g.source.bound(*payload(g.source.OUT/n,g.source.NAME))for n in(('retail.o','selected.o','guarded.o')if (g.source.OUT/'guarded.o').is_file()else('retail.o','selected.o'))];count=0
    for response,mode,phase in itertools.product((0,2),range(16),(0,8)):
        initial,args=g.fixture((1,187,2),response,mode,phase);want,calls,obs=g.model(initial,args)
        for words in programs:
            code=dict(zip(range(g.source.ENTRY,g.source.ENTRY+len(words)*4,4),words));code[end]=0
            m=g.Oracle(window,initial,args,entry=start,connected=code);saved=m.r[16:24];stack=m.r[29];fp=m.f[20:];m.code=WindowCode(m.code,m);m.code.ends=(end,)
            try:m.run()
            except WindowBoundary:pass
            else:raise AssertionError('Missing original caller boundary')
            assert(g.public(m.memory),m.calls,m.cache_observations)==(g.public(want),calls,obs)
            assert(m.r[16:24],m.r[29],m.f[20:])==(saved,stack,fp)
        count+=1
    report=dict(direct_sites=1,caller_cases=count,streams=len(programs),original_window_words=2,literal_pointer_count=0,result_ignored_proven=True,continuation_words=continuation,return_proof_controls=2,complete_parent_or_return_contract_claimed=False,private=True)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
