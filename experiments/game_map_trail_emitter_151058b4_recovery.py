"""Private map-trail emitter recovery; original frame and concrete retail normalization remain open."""
import hashlib,json,os,re,struct
from pathlib import Path
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
SPEC=json.loads(Path(__file__).with_name('game_map_trail_emitter_151058b4_manifest.json').read_text());FUNCTION=SPEC['function'];SOURCE=SPEC['source'];ENTRY=SPEC['entry'];ROM=SPEC['rom'];FRAGMENT=SPEC['fragment'];TYPES=SPEC['types']
PACKET=ROOT/'conker/build/game-map-trail-emitter-151058b4-private';sha=lambda b:hashlib.sha256(b).hexdigest()
def prepare():
    base=PACKET/'baseline';out=PACKET/'qualified';out.mkdir(exist_ok=True)
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n=='README.md'or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Frozen map-trail input changed: '+n)
    assert(ROOT/SOURCE).read_text()==SPEC['old_source']
    before,bd=compile_owner(ROOT,out,SPEC['old_source'],'before');after,ad=compile_owner(ROOT,out,SPEC['selected'],'after')
    diagnostic=lambda s:re.sub(r'[\w./-]+\.c, line \d+:','<owner>:',s)
    assert diagnostic(bd)==SPEC['diagnostics_before']and diagnostic(ad)==SPEC['diagnostics_after']and bd.count('cfe: Warning')==5 and ad.count('cfe: Warning')==2
    raw,refs=payload(after,FUNCTION);original,orefs=payload(before,FUNCTION)
    assert len(raw)==788 and sha(raw)==SPEC['raw_sha256']and json.loads(json.dumps(refs))==SPEC['refs']
    assert len(original)==788 and sha(original)==SPEC['original_raw_sha256']and json.loads(json.dumps(orefs))==SPEC['original_refs']
    words,truth=bound_blob(raw,refs),bound_blob(original,orefs);rom=(ROOT/'conker/conker.us.bin').read_bytes()
    assert struct.pack('>197I',*truth)==rom[ROM:ROM+788]
    assert len(words)==197 and (-words[0])&65535==248 and sum(a!=b for a,b in zip(words,truth))==24
    assert same_functions(before,after,(FUNCTION,))==10 and normalized_pools(before)==normalized_pools(after)
    child=list(struct.unpack_from('>38I',rom,0x1897A0))
    assert child[5]==0x240E000A and child[6]==0xAC8E0010 and child[32]==0x2406003C
    report=dict(raw_words=197,retail_words=197,raw_frame=248,retail_frame=240,aligned_word_differences=24,
        unchanged_owner_neighbors=10,pools_unchanged=True,warnings_before=5,warnings_after=2,wrapper_typing_warnings_removed=3,
        source_installed=False,matching_credit=0,frame_physical_homes_public_prefix_and_concrete_layout_open=True,
        actual_consumer_60_byte_copy_pinned=True,full_consumer_not_qualified=True)
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');return dict(out=out,words=words,truth=truth,raw=raw,refs=refs,report=report)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
