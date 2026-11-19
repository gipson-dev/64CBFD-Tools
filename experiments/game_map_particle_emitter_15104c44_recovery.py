"""Complete private map-particle emitter; layout normalization is not installed."""
import hashlib,json,os,re,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_map_particle_emitter_15104c44_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object'];ENTRY,ROM=SPEC['entry'],SPEC['rom']
SELECTED,FRAGMENT=SPEC['selected'],SPEC['fragment'];BUILD='conker/build/game-map-particle-emitter-15104c44-private/qualified'
SYMS={n:int(n.split('_')[1],16)for pairs in SPEC['refs'].values()for _,n in pairs};sha=lambda b:hashlib.sha256(b).hexdigest()
def checked(raw,refs):
    if len(raw)!=948 or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Map-particle raw words/bindings changed')
    return raw,refs
def prepare():
    base=ROOT/'conker/build/game-map-particle-emitter-15104c44-private/baseline'
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n=='README.md'or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Uninstalled map-particle input changed: '+n)
    assert(ROOT/SOURCE).read_text()==SPEC['old_source']
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    before,bd=compile_owner(ROOT,out,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,out,SELECTED,'after')
    diag=lambda s:re.sub(r'[\w./-]+\.c, line \d+:','<owner>:',s)
    assert diag(bd)==diag(ad)==SPEC['normalized_diagnostics']and bd.count('cfe: Warning')==5
    raw,refs=checked(*payload(after,FUNCTION));truth=list(struct.unpack_from('>237I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));words=bound_blob(raw,refs,SYMS)
    assert bound_blob(*payload(before,FUNCTION))==truth and len(words)==237 and(-words[0])&65535==224
    assert same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
    homes=lambda ws:sorted({w&65535 for w in ws if w>>26==9 and w>>21&31==29 and w>>16&31!=29})
    assert homes(words)==homes(truth)==[0x70,0x74,0x78,0x7C,0x80,0x88,0x8C]
    assert sum(a!=b for a,b in zip(words,truth))==52
    report=dict(body_words=237,retail_words=237,frame=224,word_differences=52,unchanged_owner_neighbors=10,constant_pools_unchanged=True,
        unchanged_owner_warnings=5,new_diagnostics=0,private_homes=homes(words),source_installed=False,matching_credit=0,
        concrete_guards_both_padders_GNU_Make_and_image_gates_pending=True,raw_sha256=sha(raw))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(out=out,raw=raw,refs=refs,truth=truth,words=words,report=report)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
