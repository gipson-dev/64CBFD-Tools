"""A private, expected-word closed stack-lifetime proposal, not production guards.

Only the unescaped incoming index home and the allocator-live alpha spill move.
No retail instruction is copied. Branch offsets follow the derived edit map.
The source function's frame and physical saved-register homes are untouched.
"""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
import hashlib,json,struct
from tools.tests import game_projection_submit_15035808_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
OUT=recovery.OUT
SOURCE=recovery.WHERE/'candidate.o'

def derive(words):
    words=list(words)
    assert len(words)==345 and words[0]==0x27bdff28
    stores=[i for i,w in enumerate(words)if w==0xafa500dc]
    assert stores==[12,50],stores
    query=[i for i,w in enumerate(words)if w>>26==3 and ((g.ENTRY&0xf0000000)|((w&0x3ffffff)<<2))==g.QUERY]
    assert query==[60] and words[61]==0x90440004,query
    spill=[i for i,w in enumerate(words)if w in(0xafa80088,0x8fa80088,0xafa90088,0x8fa90088)]
    assert len(spill)==2 and words[spill[0]]>>26==43 and words[spill[1]]>>26==35,spill
    assert words[spill[0]]&0x1fffff==words[spill[1]]&0x1fffff
    chunks={i:[w]for i,w in enumerate(words)}
    for i in stores:chunks[i]=[]
    chunks[60]=[words[61],words[60],0xafa500dc];chunks[61]=[]
    for i in spill:chunks[i]=[(words[i]&0xffff0000)|0x80]
    placement={};result=[];origins=[]
    for i,chunk in chunks.items():
        placement[i]=len(result);result.extend(chunk);origins.extend([i]*len(chunk))
    placement[len(words)]=len(result)
    for new_i,old_i in enumerate(origins):
        w=result[new_i];op,rs=w>>26,w>>21&31
        if op in(4,5,6,7,20,21,22,23)or op==17 and rs==8:
            target=old_i+1+(((w&65535)^32768)-32768)
            assert 0<=target<len(words)and chunks[target],('removed branch destination',old_i,target)
            immediate=placement[target]-new_i-1;assert -32768<=immediate<32768
            result[new_i]=(w&0xffff0000)|(immediate&65535)
    assert len(result)==344 and result[0]==words[0]
    receipt=dict(original_words=345,derived_words=344,frame=216,physical_saved_homes_unchanged=True,
        index_home_stores_removed=stores,index_home_store_sunk_to_QUERY_delay=True,
        alpha_spill_expected_word_indices=spill,alpha_spill_SP_before=0x88,alpha_spill_SP_after=0x80,
        copied_retail_words=0,production_guard_rows=0,matching_credit=0)
    return tuple(result),receipt

def run(source=SOURCE,label='matrix-normal-form'):
    assert '/' not in label and '\\'not in label
    raw,refs=payload(source,'func_15035808');words=g.bind(raw,refs)
    selected,report=derive(words)
    report['source_raw_sha256']=hashlib.sha256(raw).hexdigest()
    report['derived_bound_sha256']=hashlib.sha256(struct.pack('>%dI'%len(selected),*selected)).hexdigest()
    report['source_object']=str(source)
    (OUT/(label+'.bin')).write_bytes(struct.pack('>%dI'%len(selected),*selected))
    (OUT/(label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return selected,report
