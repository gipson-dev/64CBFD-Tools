"""Validate a structural retail derivation; this is not semantic approval."""
from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-texture-tile-151ed29c-durable';name='func_151ED29C'
raw,refs=payload(out/'coords-02.o',name);orig,trefs=payload(out/'retail.o',name)
w=list(struct.unpack('>102I',raw));truth=list(struct.unpack('>101I',orig))
alignment=json.loads((out/'flow-alignment.json').read_text());assert not alignment['unmatched']
origins=alignment['origins'];assert len(origins)==101 and len(set(origins))==101 and set(range(102))-set(origins)=={12}
assert w[12]>>26==12 and w[12]&65535==31
changes=[];newrefs={};problems=[];result=[]
for at,origin in enumerate(origins):
    value=w[origin];wanted=truth[at];op=value>>26
    if op==0:
        if (value&0x7ff)!=(wanted&0x7ff):problems.append((at,'r-opcode',hex(value),hex(wanted)));continue
        fields=(21,16,11)
    elif op in (2,3):fields=()
    else:
        if (value>>26)!=(wanted>>26) or (value&65535)!=(wanted&65535):problems.append((at,'opcode-immediate',hex(value),hex(wanted)));continue
        fields=(21,16)
    for shift in fields:
        a,b=value>>shift&31,wanted>>shift&31
        if a!=b:
            changes.append((at,origin,shift,a,b));value=(value&~(31<<shift))|(b<<shift)
    result.append(value)
    actual=refs.get(origin*4,[]);expected=[x for x in trefs.get(at*4,[]) if x[0]!='R_MIPS_PC16']
    if actual!=expected:problems.append((at,'relocations',actual,expected))
    if actual:newrefs[at*4]=actual
    if value!=wanted:problems.append((at,'word',hex(value),hex(wanted)))
report={'retail_words':101,'compiler_words':102,'omitted_index':12,'moved_positions':sum(i!=j for i,j in enumerate(origins)),
        'register_field_edits':len(changes),'register_edits_involving_zero':[c for c in changes if 0 in c[3:]],
        'zero_sites':[(at,origin,hex(w[origin]),hex(truth[at])) for at,origin,shift,a,b in changes if 0 in (a,b)],
        'problems':problems,'semantic_proof_incomplete':True,'uncredited':True}
(out/'derive-screen.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert not report['problems'] and not report['register_edits_involving_zero']
