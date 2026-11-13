"""Qualify two direct C replacements for existing assembly wrappers."""
import csv,hashlib,io,json,os,subprocess,sys
from pathlib import Path
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.experiments.game_remaining_donor_candidates import body,compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
OUT=ROOT/'conker/build/game-random-effect-pair-150d6388-match'
MANIFEST=json.loads(Path(__file__).with_name('game_random_effect_pair_150d6388_manifest.json').read_text())
NAMES=tuple(MANIFEST['targets']);OWNER=MANIFEST['owner']
def snippets():
    return {n:((MANIFEST['declarations']+'\n') if i==0 else '')+MANIFEST['targets'][n]['comment']+'\n'+MANIFEST['targets'][n]['body'] for i,n in enumerate(NAMES)}
def proposal(source):
    selected=snippets();pragmas={n:MANIFEST['targets'][n]['pragma'] for n in NAMES}
    if all(source.count(pragmas[n])==1 for n in NAMES):
        for n in NAMES:source=source.replace(pragmas[n],selected[n],1)
        return source,False
    if all(source.count(selected[n])==1 for n in NAMES):return source,True
    raise ValueError('Unknown or partial predecessor')
def payload(path,name):
    text,funcs,refs=parse_object(path);a=funcs[name]['value'];n=funcs[name]['size']
    return text[a:a+n],{i-a:v for i,v in refs.items()if a<=i<a+n}
def assemble(text,label):
    src=OUT/(label+'.s');obj=src.with_suffix('.o');src.write_text(text)
    result=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(src)],cwd=ROOT/'conker',capture_output=True,text=True)
    if result.returncode:raise ValueError(result.stderr)
    return obj
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);live=(ROOT/MANIFEST['source']).read_text();selected,installed=proposal(live)
    original=live
    if installed:
        for n,snippet in snippets().items():original=original.replace(snippet,MANIFEST['targets'][n]['pragma'],1)
    before,bd=compile_owner(ROOT,OUT,original,'baseline');after,ad=compile_owner(ROOT,OUT,selected,'selected')
    if same_functions(before,after)!=17 or normalized_pools(before)!=normalized_pools(after) or sections(before)['.reginfo'][1]!=sections(after)['.reginfo'][1] or diagnostic_rows(bd)!=diagnostic_rows(ad):raise ValueError('Owner, pools, register metadata or diagnostics changed')
    guards=ROOT/'conker/retail_word_patches.us.csv'
    if any(row['function'] in NAMES for row in csv.DictReader(io.StringIO(guards.read_text()))):raise ValueError('Unexpected target word guards')
    asm=(ROOT/MANIFEST['assembly']).read_text();retail={}
    for n,spec in MANIFEST['targets'].items():
        marker='glabel '+n+'\n';end='endlabel '+n;fragment=marker+asm.split(marker,1)[1].split(end,1)[0]+end
        retail[n]=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment+'\n.size '+n+',.-'+n+'\n',n+'-retail')
        raw,refs=payload(after,n);truth,trefs=payload(retail[n],n)
        if len(raw)!=spec['size'] or hashlib.sha256(raw).hexdigest()!=spec['sha256'] or (raw,refs)!=(truth,trefs) or payload(before,n)!=(truth,trefs):raise ValueError('Direct body or bindings differ: '+n)
    one=assemble(pad_generated_object.emit_padded_assembly(after,ROOT/MANIFEST['assembly'],filename=OWNER,word_patches_path=guards),'generated')
    two=assemble(pad_c_object.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',OWNER,word_patches_path=guards),'generic')
    if same_functions(one,two)!=17 or any(payload(one,n)!=payload(retail[n],n) for n in NAMES):raise ValueError('Independent padders disagree')
    production=ROOT/'conker/build/src/game/generated_1028F0.c.o'
    if one.read_bytes()!=production.read_bytes():raise ValueError('Padded production owner differs')
    return {'source':selected,'before':before,'after':after,'retail':retail,'generated':one,'generic':two,'installed':installed}
