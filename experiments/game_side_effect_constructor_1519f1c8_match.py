"""Recover the complete side-effect constructor and check its setup scheduling."""
from functools import lru_cache
from pathlib import Path
import csv,hashlib,io,json,os,struct,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.tests.game_owner_pool import normalized_pools
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-side-effect-constructor-1519f1c8-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_1CC440.c';OWNER='generated_1CC440';NAME='func_1519F1C8'
ENTRY,ROM,SIZE=0x1519F1C8,0x1CC678,496
PIN=json.loads(Path(__file__).with_name('game_side_effect_constructor_1519f1c8_manifest.json').read_text())

@lru_cache(None)
def symbols():return {a[1]:a[2][1] for a in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}

def recover(before):
    after=before.replace('extern s32 D_800BE9E4;',PIN['declarations']+'\nextern s32 D_800BE9E4;',1)
    assert after.count('s32 func_1519F1C8() {\n    return 0;\n}')==1
    after=after.replace('s32 func_1519F1C8() {\n    return 0;\n}',PIN['source'])
    after=after.replace('s32 first;\n    s32 second;\n    s32 third;\n    s32 fourth;','u8 *first;\n    u8 *second;\n    u8 *third;\n    u8 *fourth;')
    return after.replace('s32 r = func_1519F1C8','u8 *r = func_1519F1C8').replace('s32 result;\n        invalid','u8 *result;\n        invalid')

def normalize(raw,refs):
    wanted={int(k):[tuple(v) for v in values] for k,values in PIN['refs'].items()}
    if hashlib.sha256(raw).hexdigest()!=PIN['raw_sha256'] or refs!=wanted:raise ValueError('Constructor instructions or bindings changed')
    words=list(struct.unpack('>124I',raw))
    for i,v in PIN['replacements'].items():words[int(i)]=v
    return struct.pack('>124I',*words),refs

def programs():
    raw,refs=payload(OUT/'qualified.o',NAME);normal,nrefs=normalize(raw,refs)
    return dict(retail=list(struct.unpack_from('>124I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM)),
                candidate=bound_blob(raw,refs,symbols()),guarded=bound_blob(normal,nrefs,symbols()))

def assemble(label,text):
    # Reuse the assembler without changing its consumer or historical stage.
    import subprocess
    src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
    p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    assert p.returncode==0 and not p.stderr,p.stderr
    return obj

def main():
    frozen=OUT/'production-baseline';before=(frozen/SOURCE).read_text();proposed=recover(before);live=(ROOT/SOURCE).read_text();installed=live==proposed;assert live==(proposed if installed else before)
    baseline,bd=compile_owner(ROOT,OUT,before,'baseline');obj,ad=compile_owner(ROOT,OUT,proposed,'qualified');assert bd==ad==''
    assert same_functions(baseline,obj,(NAME,))==38 and normalized_pools(baseline)==normalized_pools(obj)
    raw,refs=payload(obj,NAME);normal,nrefs=normalize(raw,refs);streams=programs();assert streams['retail']==streams['guarded']
    from tools.tests.game_side_effect_constructor_1519f1c8_proof import prove
    proof=prove(streams['candidate'],streams['guarded'])
    controls=0
    for i in range(124):
        bad=bytearray(raw);bad[4*i+3]^=1
        try:normalize(bytes(bad),refs)
        except ValueError:controls+=1
        else:raise AssertionError('Changed word accepted')
    for at,rows in refs.items():
        try:normalize(raw,{**refs,at:[(kind,name+'_changed') for kind,name in rows]})
        except ValueError:controls+=1
        else:raise AssertionError('Changed binding accepted')
    original=(frozen/'conker/retail_word_patches.us.csv').read_bytes();header=next(csv.reader(io.StringIO(original.decode())))
    assert not [r for r in csv.DictReader(io.StringIO(original.decode())) if r['function']==NAME]
    rel=lambda values:';'.join(kind+':'+name for kind,name in values) or '-';patches=[]
    for i,(a,b) in enumerate(zip(struct.unpack('>124I',raw),struct.unpack('>124I',normal))):
        if a!=b:patches.append(dict(filename=OWNER,function=NAME,offset='0x%X'%(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations=rel(refs.get(4*i,[])),replacement_relocations=rel(nrefs.get(4*i,[])),note='Preserve proved independent setup schedule and scratch register roles',insert_after='',insert_after_relocations='',omit='false'))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=header,lineterminator='\r\n' if b'\r\n' in original else '\n');writer.writerows(patches)
    guards=original+stream.getvalue().encode();(OUT/'proposed-guards.csv').write_bytes(guards)
    assert (ROOT/'conker/retail_word_patches.us.csv').read_bytes()==(guards if installed else original)
    for label,text in (('guarded',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=OUT/'proposed-guards.csv')),
                       ('strict',pg.emit_padded_assembly(obj,ROOT/'conker/asm/1CC440.s',filename=OWNER,word_patches_path=OUT/'proposed-guards.csv'))):
        padded=assemble(label,text)
        assert bound_blob(*payload(padded,NAME),symbols())==streams['retail']
        assert same_functions(frozen/'conker/build/src/game/generated_1CC440.c.o',padded,(NAME,))==38
        assert normalized_pools(frozen/'conker/build/src/game/generated_1CC440.c.o')==normalized_pools(padded)
        for delta in (-65536,65536):
            rebased={n:v+delta for n,v in symbols().items()};assert bound_blob(*payload(padded,NAME),rebased)==bound_blob(normal,nrefs,rebased)
    (OUT/'proposed-owner.c').write_text(proposed)
    report=dict(raw_words=124,retail_words=124,frame=184,guards=len(patches),inserted_words=0,omissions=0,neighbors=38,padders=2,independent_rebases=2,corruption_controls=controls,proof=proof,installed=installed,c_match_credit=int(installed))
    (OUT/'match-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
