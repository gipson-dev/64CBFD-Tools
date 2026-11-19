"""Uninstalled nearest-height recovery; no normalization or matching credit."""
import hashlib,json,os,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_nearest_height_15104634_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM=SPEC['entry'],SPEC['rom'];SELECTED=SPEC['selected']
BUILD='conker/build/game-nearest-height-15104634-private/qualified';sha=lambda b:hashlib.sha256(b).hexdigest()
SYMS=dict(D_800D3300=0x800D3300,D_800A2370=0x800A2370,func_1510F800=0x1510F800,func_150A3A70=0x150A3A70)
def checked(raw,refs):
    if len(raw)!=1088 or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Nearest-height recovery words/bindings changed')
    return raw,refs
def prepare():
    base=ROOT/'conker/build/game-nearest-height-15104634-private/baseline'
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n=='README.md'or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Uninstalled recovery input changed: '+n)
    assert(ROOT/SOURCE).read_text()==SPEC['old_source']and 's32 func_15104634() {\n    return 0;\n}'in SPEC['old_source']
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True)
    before,bd=compile_owner(ROOT,out,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,out,SELECTED,'after');assert not bd and not ad
    raw,refs=checked(*payload(after,FUNCTION));words=bound_blob(raw,refs,SYMS)
    truth=list(struct.unpack_from('>272I',(ROOT/'conker/conker.us.bin').read_bytes(),ROM));assert len(words)==272 and (-words[0])&65535==224
    assert words[:10]==truth[:10]and same_functions(before,after,(FUNCTION,))==4 and normalized_pools(before)==normalized_pools(after)
    assert [(w&65535)for w in words if w>>26==9 and w>>21&31==29 and w>>16&31!=29 and 0<(w&65535)<224]==[(w&65535)for w in truth if w>>26==9 and w>>21&31==29 and w>>16&31!=29 and 0<(w&65535)<224]
    differences=sum(a!=b for a,b in zip(words,truth));assert differences==121
    report=dict(body_words=272,slot_words=275,frame=224,real_word_differences=differences,unchanged_raw_neighbors=4,diagnostics=0,
        saved_F20_F22_opening_exact=True,private_array_bases=[0x60,0x6C,0x78],candidate_capacity=24,profile='existing O2/g3',
        frozen_inputs=len(SPEC['predecessor']['inputs']),source_installed=False,matching_credit=0,raw_sha256=sha(raw),
        production_ELF_sha256=sha((ROOT/'conker/build/conker.us.elf').read_bytes()),normalization_and_linked_adoption_not_qualified=True)
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(out=out,raw=raw,refs=refs,words=words,truth=truth,report=report)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
