"""Private guard proposal for the independently proved initializer schedule.

No installer: the consumer stays frozen until padder, linked-image, production
and recount gates close. Normalized words derive from pinned semantic C, not
the retail file. Retail is used only by the independent comparison below.
"""
import csv,io,json,struct,subprocess
from tools.experiments import game_record_initializer_150169a0_candidates as draft
from tools.experiments.game_record_initializer_150169a0_schedule import private_projection,omitted,inverse,RAW_SHA256
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_record_initializer_150169a0_proof import prove
from tools import pad_generated_object as pg
ROOT,OUT,NAME,ENTRY,ROM,SIZE,SOURCE,BUILD=draft.ROOT,draft.OUT,draft.NAME,draft.ENTRY,draft.ROM,draft.SIZE,draft.SOURCE,draft.BUILD
SDK={'allocate_memory','bzero'}

def proposed(before):
    assert body(before,NAME)=='s32 func_150169A0() {\n    return 0;\n}'
    return before.replace(body(before,NAME),draft.SELECTED)

def main():
    before=(OUT/'production-baseline'/SOURCE).read_text();candidate=proposed(before);live=(ROOT/SOURCE).read_text()
    installed='void '+NAME+'('in live;assert live==(candidate if installed else before)
    old,d=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'selected')
    assert d==d2==''and same_functions(old,obj,(NAME,))==2
    raw,refs=payload(obj,NAME);normal,nrefs=private_projection(raw,refs)
    programs=draft.programs();words=bound_blob(normal,nrefs,draft.symbols())
    proof=prove(programs[1],(words,programs[0][1],ENTRY))
    truth=programs[0][0];assert words==truth
    pools=normalized_pools(obj);basepools=normalized_pools(old)
    assert set(pools)==set(basepools)and basepools['.rodata']is None
    assert pools['.data']==basepools['.data']
    pool,targets=pools['.rodata'];pool=bytearray(pool);assert len(pool)==336 and len(targets)==79
    for at,owner,pc in targets:
        assert owner==NAME and pc in inverse;struct.pack_into('>I',pool,at,ENTRY+inverse[pc])
    assert bytes(pool)==programs[0][1]
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())))
    oldwords=struct.unpack('>481I',raw);newwords=struct.unpack('>477I',normal);rows=[];dest=0;insertions=0
    rel=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-'
    for i,expected in enumerate(oldwords):
        pc=i*4;er=refs.get(pc,[]);omit=pc in omitted
        at=dest;replacement=0 if omit else newwords[at];rr=[]if omit else nrefs.get(at*4,[])
        if not omit:dest+=1
        insert=not omit and dest*4==0x5f4
        extra=newwords[dest]if insert else None
        xr=nrefs.get(dest*4,[])if insert else[]
        if insert:dest+=1;insertions+=1
        if omit or expected!=replacement or er!=rr or insert:
            rows.append(dict(filename='generated_43D00',function=NAME,offset='0x%X'%pc,expected='0x%08X'%expected,replacement='0x%08X'%replacement,expected_relocations=rel(er),replacement_relocations=rel(rr),note='Restore proved initializer register lifetimes and ordered loop schedule',insert_after='0x%08X'%extra if insert else'',insert_after_relocations=rel(xr)if insert else'',omit=str(omit).lower()))
    assert dest==477 and insertions==1 and sum(r['omit']=='true'for r in rows)==5
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='')
        writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/43D00.s').read_text();a=asm.index('glabel '+NAME+'\n');b=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/43D00.s',filename='generated_43D00',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,text=True)
        assert q.returncode==0,q.stderr;assert bound_blob(*payload(OUT/(label+'.o'),NAME),draft.symbols())==truth
    assert same_functions(OUT/'production-baseline/conker/build/src/game/generated_43D00.c.o',OUT/'guarded.o',(NAME,))==2
    report=dict(raw_words=481,words=477,frame=88,guards=len(rows),omitted_words=5,duplicated_source_words=1,neighbors=2,binding_sites=len(refs),table_entries=79,pool_bytes=336,raw_sha256=RAW_SHA256,proof_paths=proof['symbolic_paths'],installed=installed,uncredited=not installed)
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
