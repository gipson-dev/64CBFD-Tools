"""Checked ten-word captured-count normalization; no production installer."""
from pathlib import Path
import csv,hashlib,io,json,struct,subprocess
from tools.experiments import game_record_payload_tables_15017114_candidates as draft
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
ROOT,OUT,NAME,ENTRY,ROM,SOURCE,BUILD=draft.ROOT,draft.OUT,draft.NAME,draft.ENTRY,draft.ROM,draft.SOURCE,draft.BUILD
SIZE=draft.BODY_SIZE;SLOT_SIZE=draft.SIZE;SDK={'allocate_memory','bzero'}
PIN=json.loads(Path(__file__).with_name('game_record_payload_tables_15017114_manifest.json').read_text())
RAW_REFS={int(k):[tuple(row)for row in rows]for k,rows in PIN['raw_refs'].items()}

def normalize(raw,refs):
    if len(raw)!=484 or hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256']or refs!=RAW_REFS:raise ValueError('Payload initializer words or bindings changed')
    a=list(struct.unpack('>121I',raw));order=list(range(0,0x40,4))+[0x44,0x40,0x4c,0x50,0x54,0x48]+list(range(0x58,484,4))
    assert sorted(order)==list(range(0,484,4));result=[];bindings={}
    for i,pc in enumerate(order):
        w=a[pc//4]
        if pc==0x24:assert w==0x3c020000;w=(w&~(31<<16))|(16<<16)
        elif pc==0x28:assert w==0x90420000;w=(w&~(31<<21|31<<16))|(16<<21)|(16<<16)
        elif pc==0x34:assert w==0x00028880;w=(w&~(31<<16))|(16<<16)
        elif pc==0x48:assert w==0x00408025;w=(w&~(31<<21|31<<11))|(16<<21)|(19<<11)
        elif pc==0x8c:assert w==0x02002825;w=(w&~(31<<21))|(19<<21)
        result.append(w)
        if pc in refs:bindings[i*4]=refs[pc]
    return struct.pack('>121I',*result),bindings

def main():
    before=(OUT/'production-baseline'/SOURCE).read_text();candidate=draft.proposed(before);live=(ROOT/SOURCE).read_text();installed=live==candidate
    assert live==(candidate if installed else before)
    base,d1=compile_owner(ROOT,OUT,before,'baseline');obj,d2=compile_owner(ROOT,OUT,candidate,'selected')
    assert d1==d2==''and same_functions(base,obj,(NAME,))==2 and normalized_pools(base)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);symbols=draft.symbols()
    from tools.tests.game_record_payload_tables_15017114_proof import prove
    prove(bound_blob(raw,refs,symbols),bound_blob(normal,nrefs,symbols))
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert struct.pack('>121I',*bound_blob(normal,nrefs,symbols))==truth
    controls=0
    for i in range(121):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed source word accepted')
    for pc,rows in refs.items():
        try:normalize(raw,{**refs,pc:[(kind,name+'_changed')for kind,name in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed source binding accepted')
    original=(ROOT/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));rows=[]
    rel=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-'
    for i,(a,b)in enumerate(zip(struct.unpack('>121I',raw),struct.unpack('>121I',normal))):
        pc=i*4;er,rr=refs.get(pc,[]),nrefs.get(pc,[])
        if a!=b or er!=rr:rows.append(dict(filename='generated_43D00',function=NAME,offset='0x%X'%pc,expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(er),replacement_relocations=rel(rr),note='Preserve proved captured-byte-count lifetime and first-allocation delay schedule',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==10
    existing=[r for r in csv.DictReader(io.StringIO(original.decode()))if r['function']==NAME]
    if installed:assert existing==rows;guards=original
    else:
        assert not existing;stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n'if b'\r\n'in original else'\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards)
    asm=(ROOT/'conker/asm/43D00.s').read_text();a=asm.index('glabel '+NAME+'\n');b=asm.index('endlabel '+NAME,a)+len('endlabel '+NAME)
    (OUT/'retail.s').write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+asm[a:b]+'\n.size '+NAME+',.-'+NAME+'\n')
    (OUT/'guarded.s').write_text(pg.emit_padded_assembly(obj,ROOT/'conker/asm/43D00.s',filename='generated_43D00',word_patches_path=OUT/'proposed-guards.csv'))
    for label in('retail','guarded'):
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(OUT/(label+'.o')),str(OUT/(label+'.s'))],cwd=ROOT/'conker',capture_output=True,text=True)
        assert q.returncode==0,q.stderr
        assert struct.pack('>121I',*bound_blob(*payload(OUT/(label+'.o'),NAME),symbols))==truth
    assert same_functions(OUT/'production-baseline/conker/build/src/game/generated_43D00.c.o',OUT/'guarded.o',(NAME,))==2
    report=dict(words=121,slot_words=123,alignment_words=2,frame=72,saved_registers=6,guards=10,insertions=0,omissions=0,binding_sites=21,neighbors=2,corruption_controls=controls,raw_sha256=PIN['raw_sha256'],installed=installed,uncredited=not installed)
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
