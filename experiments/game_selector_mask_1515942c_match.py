"""Proved normalization of ten redundant shift masks and closed scratch roles."""
from pathlib import Path
import csv,hashlib,io,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner,body
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-selector-mask-1515942c-match';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_185560.c';NAME='func_1515942C';OWNER='generated_185560'
ENTRY,ROM,SIZE=0x1515942c,0x1868dc,360
PIN=json.loads(Path(__file__).with_name('game_selector_mask_1515942c_manifest.json').read_text())
REFS={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}

def symbols():return {r[1]:r[2][1] for r in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}

def recover(before):
    return before.replace(body(before,NAME),'s32 func_1514ECE0(void *, s16, void **);\n'+PIN['source'])

def normalize(raw,refs):
    if hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=REFS:
        raise ValueError('Selector-mask raw instructions or bindings changed')
    ws=list(struct.unpack('>100I',raw));kept=[i for i in range(100) if i not in PIN['omit']]
    result=[PIN['replacements'].get(str(i),ws[old]) for i,old in enumerate(kept)]
    bindings={i*4:refs[old*4] for i,old in enumerate(kept) if old*4 in refs}
    assert len(result)==90 and bindings==REFS
    return struct.pack('>90I',*result),bindings

def assemble(label,text):
    src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
    q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    assert q.returncode==0 and not q.stderr,q.stderr
    return obj

def main():
    frozen=OUT/'production-baseline';before=(frozen/SOURCE).read_text();proposed=recover(before)
    live=(ROOT/SOURCE).read_text();installed=live==proposed;assert live==(proposed if installed else before)
    baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,proposed,'qualified')
    assert bd.replace('baseline.c','owner.c')==ad.replace('qualified.c','owner.c')
    assert same_functions(baseline,obj,(NAME,))==36 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);syms=symbols();truth=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    from tools.tests.game_selector_mask_1515942c_proof import prove
    proof=prove(bound_blob(raw,refs,syms),bound_blob(normal,nrefs,syms))
    assert struct.pack('>90I',*bound_blob(normal,nrefs,syms))==truth
    controls=0
    for i in range(100):
        bad=bytearray(raw);bad[i*4+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed raw instruction accepted')
    for offset,values in refs.items():
        try:normalize(raw,{**refs,offset:[(kind,name+'_changed') for kind,name in values]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(frozen/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())))
    assert not [r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    replacements=iter(struct.unpack('>90I',normal));patches=[]
    rel=lambda values:';'.join(kind+':'+name for kind,name in values) or '-'
    for i,w in enumerate(struct.unpack('>100I',raw)):
        omit=i in PIN['omit'];want=0 if omit else next(replacements)
        if omit or w!=want:
            patches.append(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*i),expected='0x%08X'%w,replacement='0x%08X'%want,
                expected_relocations=rel(refs.get(4*i,[])),replacement_relocations='-' if omit else rel(refs.get(4*i,[])),
                note='Preserve proved five-bit shifts, closed scratch roles and independent scheduling',insert_after='',insert_after_relocations='',omit=str(omit).lower()))
    assert sum(p['omit']=='true' for p in patches)==10
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(patches)
    guards=original+stream.getvalue().encode();(OUT/'proposed-guards.csv').write_bytes(guards)
    assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
    texts=(('guarded',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')),
           ('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/185560.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv')))
    for label,text in texts:
        padded=assemble(label,text)
        assert struct.pack('>90I',*bound_blob(*payload(padded,NAME),syms))==truth
        assert same_functions(frozen/'conker/build/src/game/generated_185560.c.o',padded,(NAME,))==36
        assert normalized_pools(frozen/'conker/build/src/game/generated_185560.c.o')==normalized_pools(padded)
        for delta in (0x10000,-0x10000):
            rebased={n:v+delta for n,v in syms.items()}
            assert bound_blob(*payload(padded,NAME),rebased)==bound_blob(normal,nrefs,rebased)
    (OUT/'proposed-owner.c').write_text(proposed)
    report=dict(raw_words=100,retail_words=90,frame=64,guards=len(patches),omissions=10,neighbors=36,corruption_controls=controls,
                proof=proof,padders=2,independent_rebases=2,installed=installed,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
