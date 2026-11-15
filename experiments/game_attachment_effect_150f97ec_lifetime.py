"""Private O1 lifetime screens; dimensional fits are deliberately uncredited."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,sys
from tools.experiments.game_remaining_donor_candidates import compile_owner,body,function_span
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path.cwd())).resolve()
BUILD='conker/build/game-actor-joint-effect-150f97ec-private';OUT=ROOT/BUILD
SOURCE='conker/src/game/generated_124920.c';NAME='func_150F97EC';ENTRY=0x150F97EC;ROM=0x126C9C;SIZE=356
MANIFEST=json.loads(Path(__file__).with_name('game_attachment_effect_150f97ec_lifetime_manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def immutable():
    record=json.loads((OUT/'production-baseline/fingerprints.json').read_text())
    for name,want in record['inputs'].items():assert sha(ROOT/name)==want,name
    return len(record['inputs'])
def symbols():return {row[1]:row[2][1] for row in symbol_rows((ROOT/'conker/build/conker.us.elf').read_bytes())}
def compile_isolated(text,label):
    path=OUT/(label+'.c');obj=path.with_suffix('.o');path.write_text(text)
    includes=('.', 'include', 'include/2.0L', 'include/2.0L/PR', 'include/libc', 'src/libultra/os', 'src/libultra/audio', 'src/libultra/io')
    command=[str(ROOT/'ido/ido5.3_recomp/cc'),'-c','-32','-G','0','-Xfullwarn','-Xcpluscomm','-signed','-nostdinc','-non_shared','-Wab,-r4300_mul','-D_LANGUAGE_C','-D_FINALROM','-DF3DEX_GBI_2','-D_MIPS_SZLONG=32','-woff','649,838',*[a for p in includes for a in ('-I',p)],'-O1','-g3','-mips2','-o32','-o',str(obj.relative_to(ROOT/'conker')),str(path.relative_to(ROOT/'conker'))]
    p=subprocess.run(command,cwd=ROOT/'conker',capture_output=True,text=True);diagnostic=p.stdout+p.stderr;assert p.returncode==0 and not diagnostic,diagnostic
    return obj
def multiply_one(words):
    """Track actual literal operands, rather than matching one MUL opcode."""
    g=[None]*32;g[0]=0;f=[None]*32;observed=[]
    for i,w in enumerate(words):
        op,rs,rt,rd,fn=w>>26,w>>21&31,w>>16&31,w>>11&31,w&63
        if op==3:
            for reg in (1,2,3,*range(4,16),24,25):g[reg]=None
            f[:20]=[None]*20
        elif op==15:g[rt]=(w&65535)<<16
        elif op in (9,13):g[rt]=None if g[rs] is None else ((g[rs]+(((w&65535)^32768)-32768))&0xffffffff if op==9 else g[rs]|(w&65535))
        elif op in (32,33,35,36,37):g[rt]=None
        elif op==17:
            fs,ft,fd=w>>11&31,w>>16&31,w>>6&31
            if rs==4:f[fs]=g[rt]
            elif rs==0:g[rt]=f[fs]
            elif rs==16:
                if fn==2 and 0x3f800000 in (f[fs],f[ft]):observed.append(i)
                if fn in (0,1,2,3,5,6,7,32):f[fd]=None
        elif op==49:f[rt]=None
        g[0]=0
    return observed
def programs():
    result={'retail':list(struct.unpack_from('>89I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))}
    for label in MANIFEST['candidates']:result[label]=bound_blob(*payload(OUT/('lifetime-'+label+'.o'),NAME),symbols())
    return result
def main():
    count=immutable();reports=[];truth=list(struct.unpack_from('>89I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM))
    for label,item in MANIFEST['candidates'].items():
        obj=compile_isolated(item['source'],'lifetime-'+label);raw,refs=payload(obj,NAME)
        assert hashlib.sha256(raw).hexdigest()==item['raw_sha256'] and {str(k):[list(x) for x in v] for k,v in refs.items()}==item['relocations'],label
        ws=bound_blob(raw,refs,symbols());assert (len(ws),(-ws[0])&65535)==(item['words'],item['frame'])
        reports.append(dict(label=label,words=len(ws),frame=item['frame'],differing_words=sum(a!=b for a,b in zip(ws,truth))+abs(len(ws)-89),multiply_one=multiply_one(ws)))
    old=(ROOT/SOURCE).read_text();base,bd=compile_owner(ROOT,OUT,old,'lifetime-owner-before')
    selected=MANIFEST['candidates']['conditional_pair']['source'];a,b=function_span(selected,NAME);preamble=selected[:a].replace('#include <ultra64.h>','')
    proposed=old.replace('#include <ultra64.h>','#include <ultra64.h>\n'+preamble,1).replace(body(old,NAME),selected[a:b])
    candidate,ad=compile_owner(ROOT,OUT,proposed,'lifetime-owner-after')
    assert bd==ad and same_functions(base,candidate,(NAME,))==16 and normalized_pools(base)==normalized_pools(candidate)
    assert multiply_one(programs()['retail']) and all(r['multiply_one'] for r in reports)
    assert immutable()==count
    result=dict(frozen_inputs=count,neighbors=16,profiles=reports,production_unchanged=True,c_match_credit=0,owner_O1_integration_pending=True)
    (OUT/'lifetime-source.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
