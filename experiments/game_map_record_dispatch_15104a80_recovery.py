"""Uninstalled complete map-record dispatcher; compiler branch shape stays open."""
import hashlib,json,os,re,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_map_record_dispatch_15104a80_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object'];ENTRY,ROM=SPEC['entry'],SPEC['rom']
SELECTED,FRAGMENT=SPEC['selected'],SPEC['fragment'];BUILD='conker/build/game-map-record-dispatch-15104a80-private/qualified'
SYMS={n:int(n.split('_')[1],16)for pairs in SPEC['refs'].values()for _,n in pairs};sha=lambda b:hashlib.sha256(b).hexdigest()
def checked(raw,refs):
    if len(raw)!=440 or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Map-record recovery words/bindings changed')
    return raw,refs
def prepare():
    base=ROOT/'conker/build/game-map-record-dispatch-15104a80-private/baseline'
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n=='README.md'or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Uninstalled map-record input changed: '+n)
    assert(ROOT/SOURCE).read_text()==SPEC['old_source']
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    before,bd=compile_owner(ROOT,out,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,out,SELECTED,'after')
    diag=lambda x:re.sub(r'build/game-map-record-dispatch-15104a80-private/qualified/[\w-]+\.c, line \d+:','<owner>:',x)
    assert diag(bd)==diag(ad)==SPEC['normalized_diagnostics']and bd.count('cfe: Warning')==5
    raw,refs=checked(*payload(after,FUNCTION));original,originalrefs=payload(before,FUNCTION)
    truth=list(struct.unpack_from('>113I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));words=bound_blob(raw,refs,SYMS)
    assert bound_blob(original,originalrefs,SYMS)==truth and len(words)==110 and(-words[0])&65535==104
    assert same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
    homes=lambda ws:sorted({w&65535 for w in ws if w>>26==9 and w>>21&31==29 and w>>16&31!=29})
    assert homes(words)==homes(truth)==[0x24,0x28,0x34,0x40,0x4C]
    differences=sum(a!=b for a,b in zip(words,truth))+3;assert differences==71
    report=dict(body_words=110,retail_words=113,frame=104,word_differences=71,unchanged_owner_neighbors=10,constant_pools_unchanged=True,
        unchanged_owner_warnings=5,new_diagnostics=0,private_homes=[0x24,0x28,0x34,0x40,0x4C],source_installed=False,matching_credit=0,
        branch_shape_and_full_register_fault_relation_not_qualified=True,raw_sha256=sha(raw))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(out=out,raw=raw,refs=refs,truth=truth,words=words,report=report)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
