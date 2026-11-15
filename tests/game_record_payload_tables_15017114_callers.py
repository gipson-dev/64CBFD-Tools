"""Original parent window and first overwrite of the unused payload-table result."""
import itertools,json,struct
from tools.tests import game_record_payload_tables_15017114_oracle as g
from tools.tests.game_record_initializer_150169a0_callers import aligned
from tools.tests.test_game_character_effect_pair import WindowCode,WindowBoundary
START,END,ROM=0x15016ac8,0x15016ad8,0x43f78

def prove_unused_result(rom,forward=False,remove_killer=None):
    def word(pc):
        at=pc-0x15000000+0x2d4b0 if pc>=0x15000000 else pc-0x10000000
        return struct.unpack_from('>I',rom,at)[0]
    def fields(w):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==0:
            if not w:return(),()
            if fn in(0,2,3):return(rt,),(rd,)
            if fn in(33,35,36,37,42,43):return(rs,rt),(rd,)
            if fn==8:return(rs,),()
            if fn in(16,18):return(),(rd,)
            if fn in(25,27):return(rs,rt),()
        if op==15:return(),(rt,)
        if op in(9,10,11,12,13,32,33,35,36,37):return(rs,),(rt,)
        if op in(40,41,43):return(rs,rt),()
        if op==3:return(),(31,)
        raise AssertionError(('unsupported result prefix',hex(w)))
    pc=END;seen=[];calls=[]
    for _ in range(180):
        assert END<=pc<=0x15016b00 or 0x10003c40<=pc<0x10003d80,hex(pc)
        w=word(pc)
        if forward and pc==END:assert w>>26==15;w=0x00402025
        if remove_killer==pc:assert w>>16&31==2;w=(w&~(31<<16))|(3<<16)
        reads,writes=fields(w);seen.append((pc,w));assert 2 not in reads,('old result read',hex(pc),hex(w))
        if 2 in writes:return dict(instructions=len(seen),calls=[hex(t)for t in calls],killer=hex(pc),killer_word=hex(w),prefix_reads_old_v0=False)
        if w>>26==3:
            target=(pc&0xf0000000)|((w&0x3ffffff)<<2);calls.append(target)
            delay=word(pc+4);reads,writes=fields(delay);seen.append((pc+4,delay));assert 2 not in reads and 2 not in writes
            pc=target
        else:pc+=4
    raise AssertionError('No first result overwrite')

def run_window(program,c,changed=None):
    code,entry=program;rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();window=list(struct.unpack_from('>4I',rom,ROM))
    assert window[0]==0x8fa40058 and window[1]&63==33 and window[2]==0x0d405c45 and window[3]>>26==40
    window[2]=0xc000000|((entry>>2)&0x3ffffff)
    if changed=='category-load':window[0]=(window[0]&0xffff0000)|0x54
    if changed=='count-delay':window[3]&=~(31<<16)
    initial=g.fixture(c);want,calls,observations=g.reference(initial,c)
    connected=dict(zip(range(entry,entry+len(code)*4,4),code));connected[END]=0
    m=g.Oracle(window,initial,c,entry=START,connected=connected)
    m.put(m.r[29]+0x58,g.u32(c.category),4)
    add=window[1];m.r[add>>21&31]=c.n;m.r[add>>16&31]=0
    m.r[window[3]>>21&31]=g.COUNT
    m.r[16]=g.PTRS
    saved=(m.r[16:24],m.r[29],m.f[20:]);m.code=WindowCode(m.code,m);m.code.ends=(END,)
    try:m.run()
    except WindowBoundary:pass
    else:raise AssertionError('Missing original parent boundary')
    assert(g.public(m.memory),m.calls,m.payload_observations)==(g.public(want),calls,observations),('caller result',c)
    assert(m.r[16:24],m.r[29],m.f[20:])==saved

def main():
    rom=(g.source.ROOT/'conker/conker.us.bin').read_bytes();jal=0xc000000|((g.source.ENTRY>>2)&0x3ffffff)
    assert aligned(rom,jal)==[ROM+8]and aligned(rom,g.source.ENTRY)==[]
    proof=prove_unused_result(rom);killer=int(proof['killer'],16);controls=0
    for args in((True,None),(False,killer)):
        try:prove_unused_result(rom,*args)
        except AssertionError:controls+=1
        else:raise AssertionError('Ineffective unused-result control')
    count=0;programs=g.source.programs()
    for category,n,phase,mode in itertools.product((-1,0,26,0x7fffffff),(0,2,8),(0,8),(0,15)):
        c=g.Case(category=category,n=n,original=n//2,players=2,phase=phase,mode=mode)
        for program in programs:run_window(program,c)
        count+=1
    for name in('category-load','count-delay'):
        try:run_window(programs[0],g.Case(),name)
        except AssertionError:controls+=1
        else:raise AssertionError(('Ineffective caller control',name))
    report=dict(direct_sites=1,literal_pointers=0,window_words=4,caller_cases=count,streams=len(programs),result_use_proof=proof,effective_controls=controls,complete_parent_or_allocator_claimed=False,uninstalled=True,uncredited=True)
    (g.source.OUT/'caller-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
