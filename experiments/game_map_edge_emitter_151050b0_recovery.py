"""Private map-edge emitter recovery; concrete retail normalization remains open."""
import hashlib,json,os,re,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_map_edge_emitter_151050b0_manifest.json').read_text());FUNCTION=SPEC['function'];SOURCE=SPEC['source'];ENTRY=SPEC['entry'];ROM=SPEC['rom'];FRAGMENT=SPEC['fragment']
PACKET=ROOT/'conker/build/game-map-edge-emitter-151050b0-private';sha=lambda b:hashlib.sha256(b).hexdigest()
def prepare():
    base=PACKET/'baseline';out=PACKET/'qualified';out.mkdir(exist_ok=True)
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n=='README.md'or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Frozen map-edge input changed: '+n)
    assert(ROOT/SOURCE).read_text()==SPEC['old_source']
    before,bd=compile_owner(ROOT,out,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,out,SPEC['selected'],'after')
    diagnostic=lambda s:re.sub(r'[\w./-]+\.c, line \d+:','<owner>:',s)
    assert diagnostic(bd)==diagnostic(ad)==SPEC['normalized_diagnostics']and bd.count('cfe: Warning')==5
    raw,refs=payload(after,FUNCTION);original,orefs=payload(before,FUNCTION)
    assert len(raw)==1100 and sha(raw)==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['refs']
    assert len(original)==1116 and sha(original)==SPEC['original_raw_sha256']and json.loads(json.dumps(orefs))==SPEC['original_refs']
    words,truth=bound_blob(raw,refs),bound_blob(original,orefs);rom=(ROOT/'conker/conker.us.bin').read_bytes()
    assert struct.pack('>279I',*truth)==rom[ROM:ROM+1116]
    assert len(words)==275 and (-words[0])&65535==208 and sum(a!=b for a,b in zip(words,truth))==267
    assert same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
    # The actual consumer begins by copying all 48 descriptor bytes.
    child=list(struct.unpack_from('>100I',rom,0x134448));assert child[:3]==[0x27BDFF78,0xAFB00030,0x00C08025]and child[15]==0x250B0030
    homes=lambda ws:sorted({w&65535 for w in ws if w>>26==9 and w>>21&31==29 and w>>16&31!=29})
    assert homes(words)==homes(truth)==[0x84,0x90,0x9C]
    report=dict(raw_words=275,retail_words=279,frame=208,aligned_word_differences=267,unchanged_owner_neighbors=10,pools_unchanged=True,unchanged_warnings=5,private_homes={'raw':homes(words),'retail':homes(truth)},source_installed=False,matching_credit=0,
       concrete_layout_GNU_Make_full_image_gates_pending=True,consumer_48_byte_copy_contract_observed=True,full_consumer_not_qualified=True)
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return dict(out=out,words=words,truth=truth,raw=raw,refs=refs,report=report)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
