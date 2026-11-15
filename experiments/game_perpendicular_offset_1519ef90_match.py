"""Checked derived parameter home and proved role/schedule normalization."""
import csv,hashlib,io,json,struct,subprocess,sys
from tools.experiments import game_perpendicular_offset_1519ef90_recovery as draft
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from pathlib import Path
ROOT,OUT,SOURCE,NAME,ENTRY,ROM,SIZE,BUILD=draft.ROOT,draft.OUT,draft.SOURCE,draft.NAME,draft.ENTRY,draft.ROM,draft.SIZE,draft.BUILD
OWNER='generated_1CC440'
PIN=json.loads(Path(__file__).with_name('game_perpendicular_offset_1519ef90_match_manifest.json').read_text())
REFS={int(k):[tuple(v) for v in values] for k,values in draft.PIN['refs'].items()}

def normalize(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=draft.PIN['raw_sha256'] or refs!=REFS:raise ValueError('Offset-query instructions or bindings changed')
    words=list(struct.unpack('>92I',raw));words=words[:4]+PIN['inserted_words']+words[4:]
    for i,value in PIN['replacements'].items():words[int(i)]=value
    shifted={at+8 if at>12 else at:values for at,values in refs.items()}
    return struct.pack('>94I',*words),shifted

def assemble(label,text):
    src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
    p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    assert p.returncode==0 and not p.stderr,p.stderr
    return obj

def main():
    frozen=OUT/'production-baseline';before=(frozen/SOURCE).read_text();proposed=draft.recover(before);live=(ROOT/SOURCE).read_text();installed=live==proposed;assert live==(proposed if installed else before)
    baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,proposed,'qualified');assert bd==ad==''
    assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);syms=draft.symbols()
    from tools.tests.game_perpendicular_offset_1519ef90_proof import prove
    proof=prove(bound_blob(raw,refs,syms),bound_blob(normal,nrefs,syms))
    truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE];assert struct.pack('>94I',*bound_blob(normal,nrefs,syms))==truth
    controls=0
    for i in range(92):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for at,rows in refs.items():
        try:normalize(raw,{**refs,at:[(kind,name+'_changed') for kind,name in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(frozen/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));assert not [r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    rel=lambda values:';'.join(kind+':'+name for kind,name in values) or '-';normal_words=struct.unpack('>94I',normal);patches=[]
    for i,w in enumerate(struct.unpack('>92I',raw)):
        new_index=5 if i==4 else i+2 if i>4 else i
        want=normal_words[new_index]
        # Each padder guard accepts one inserted word. Use the next source
        # slot for the derived store, moving its actor load after that store.
        insert=[normal_words[4]] if i==3 else [normal_words[6]] if i==4 else []
        if w!=want or insert:
            patches.append(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%want,expected_relocations=rel(refs.get(i*4,[])),replacement_relocations=rel(nrefs.get(new_index*4,[])),
                note='Preserve proved parameter address, private homes and independent role scheduling',insert_after=';'.join('0x%08X'%v for v in insert),insert_after_relocations='',omit='false'))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(patches)
    guards=original+stream.getvalue().encode();(OUT/'proposed-guards.csv').write_bytes(guards);assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
    texts=(('guarded',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')),
           ('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/1CC440.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv')))
    for label,text in texts:
        padded=assemble(label,text);assert struct.pack('>94I',*bound_blob(*payload(padded,NAME),syms))==truth
        assert same_functions(frozen/'conker/build/src/game/generated_1CC440.c.o',padded,(NAME,))==38 and normalized_pools(frozen/'conker/build/src/game/generated_1CC440.c.o')==normalized_pools(padded)
        for delta in (-65536,65536):
            rebased={n:v+delta for n,v in syms.items()};assert bound_blob(*payload(padded,NAME),rebased)==bound_blob(normal,nrefs,rebased)
    (OUT/'proposed-owner.c').write_text(proposed)
    report=dict(raw_words=92,retail_words=94,frame=64,guards=len(patches),inserted_words=2,omissions=0,neighbors=38,padders=2,independent_rebases=2,corruption_controls=controls,proof=proof,installed=installed,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
