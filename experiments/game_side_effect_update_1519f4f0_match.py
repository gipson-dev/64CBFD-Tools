"""Complete side-ring update, with checked private geometry and FP roles."""
from functools import lru_cache
from pathlib import Path
import csv,hashlib,io,json,os,struct,sys,subprocess
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-side-effect-update-1519f4f0-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_1CC440.c';OWNER='generated_1CC440';NAME='func_1519F4F0'
ENTRY,ROM,SIZE=0x1519F4F0,0x1CC9A0,768
PIN=json.loads(Path(__file__).with_name('game_side_effect_update_1519f4f0_manifest.json').read_text())
@lru_cache(None)
def symbols():return {x[1]:x[2][1] for x in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
def recover(before):
    assert before.count('s32 func_1519F4F0() {\n    return 0;\n}')==1
    return before.replace('extern s32 D_800BE9E4;',PIN['declarations']+'\nextern s32 D_800BE9E4;',1).replace('s32 func_1519F4F0() {\n    return 0;\n}',PIN['source'])
def normalize(raw,refs):
    wanted={int(k):[tuple(x) for x in v] for k,v in PIN['refs'].items()}
    if hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=wanted:raise ValueError('Update instructions or bindings changed')
    from tools.tests.game_side_effect_update_1519f4f0_proof import normalize_words
    return struct.pack('>192I',*normalize_words(list(struct.unpack('>192I',raw)))),refs
def programs():
    raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
    return dict(retail=list(struct.unpack_from('>192I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),candidate=bound_blob(raw,refs,symbols()),guarded=bound_blob(normal,nrefs,symbols()))
def assemble(label,text):
    path=OUT/(label+'.s');obj=path.with_suffix('.o');path.write_text(text)
    p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=ROOT/'conker',capture_output=True,text=True);assert p.returncode==0 and not p.stderr,p.stderr
    return obj
def main():
    frozen=OUT/'production-baseline';before=(frozen/SOURCE).read_text();proposed=recover(before);live=(ROOT/SOURCE).read_text();installed=live==proposed;assert live==(proposed if installed else before)
    baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,proposed,'qualified');assert bd==ad==''
    assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);p=programs();assert p['retail']==p['guarded']
    from tools.tests.game_side_effect_update_1519f4f0_proof import qualify
    proof=qualify(p['candidate'],p['guarded']);controls=0
    for i in range(192):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for at,values in refs.items():
        try:normalize(raw,{**refs,at:[(kind,name+'_bad') for kind,name in values]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(frozen/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())));assert not [x for x in csv.DictReader(io.StringIO(original.decode())) if x['function']==NAME]
    rel=lambda rows:';'.join(kind+':'+name for kind,name in rows) or '-';rows=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>192I',raw),struct.unpack('>192I',normal))):
        if a!=b:rows.append(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(4*i,[])),replacement_relocations=rel(nrefs.get(4*i,[])),note='Preserve proved private geometry, FP roles and disjoint ordinary-field scheduling',insert_after='',insert_after_relocations='',omit='false'))
    assert len(rows)==18
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(rows);guards=original+stream.getvalue().encode()
    (OUT/'proposed-guards.csv').write_bytes(guards);assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
    for label,text in (('guarded',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')),
                       ('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/1CC440.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv'))):
        padded=assemble(label,text);assert bound_blob(*payload(padded,NAME),symbols())==p['retail']
        assert same_functions(frozen/'conker/build/src/game/generated_1CC440.c.o',padded,(NAME,))==38 and normalized_pools(frozen/'conker/build/src/game/generated_1CC440.c.o')==normalized_pools(padded)
        for delta in (-65536,65536):
            syms={n:v+delta for n,v in symbols().items()};assert bound_blob(*payload(padded,NAME),syms)==bound_blob(normal,nrefs,syms)
    (OUT/'proposed-owner.c').write_text(proposed)
    report=dict(raw_words=192,retail_words=192,raw_frame=128,retail_frame=120,guards=18,inserted_words=0,omissions=0,neighbors=38,padders=2,independent_rebases=2,corruption_controls=controls,proof=proof,installed=installed,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
