"""Qualify the complete particle body and derive guarded object candidates."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess
from tools import pad_generated_object as pg
from tools.experiments.game_configurable_particle_15175390_normalization import NAME,ENTRY,ROM,SIZE,SOURCE,SELECTED,EXTRA,RAW_SHA256,RAW_REFS,normalize,proposed
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.game_configurable_particle_15175390_normalization_proof import qualify
BUILD='conker/build/game-configurable-particle-constructor-15175390-match'
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve();OUT=ROOT/BUILD

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    live=(ROOT/SOURCE).read_text();installed='void '+NAME+'(' in live
    before=(OUT/'production-baseline'/SOURCE).read_text() if installed else live
    selected=proposed(before);assert not installed or selected==live
    old,diag=compile_owner(ROOT,OUT,before,'baseline');obj,diag2=compile_owner(ROOT,OUT,selected,'selected');assert diag==diag2==''
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=list(struct.unpack_from('>370I',rom,ROM));assert bound_blob(normal,nrefs)==truth
    assert same_functions(old,obj,(NAME,))==8 and normalized_pools(old)==normalized_pools(obj)=={'.rodata':None,'.data':None}
    controls=0
    for i in range(370):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(k,n+'_changed') for k,n in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed named binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();fields=next(csv.reader(io.StringIO(original.decode())));rows=[]
    rel=lambda rs:';'.join(k+':'+n for k,n in rs) or '-'
    for i,(a,b) in enumerate(zip(struct.unpack('>370I',raw),struct.unpack('>370I',normal))):
        if a!=b or refs.get(i*4,[])!=nrefs.get(i*4,[]):
            rows.append(dict(filename='generated_1A20A0',function=NAME,offset='0x%X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(i*4,[])),note='Normalize configurable particle temporary roles scheduling and proven redundant-operation joins',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==219
    existing=[r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/1A20A0.s').read_text();a=asm.index('glabel '+NAME+'\n');z=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:z]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/1A20A0.s',filename='generated_1A20A0',word_patches_path=OUT/'proposed-guards.csv'))
    for label in ('retail','guarded'):
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,check=True)
        assert bound_blob(*payload(OUT/(label+'.o'),NAME))==truth
    words=struct.unpack('>%dI'%(len(rom)//4),rom[:len(rom)&~3]);jal=0x0c000000|((ENTRY>>2)&0x3ffffff)
    callers=[i*4 for i,w in enumerate(words) if w==jal];assert callers==[0x1b0930,0x1b0b08,0x1b0bbc,0x1b0c58,0x1b0cec]
    report=dict(words=370,frame=184,guards=219,neighbors=8,owner_functions=9,installed=installed,corruption_controls=controls,proof=qualify(bound_blob(raw,refs),truth),direct_callers=callers,raw_sha256=hashlib.sha256(raw).hexdigest())
    (OUT/'raw-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
