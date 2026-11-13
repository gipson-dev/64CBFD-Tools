"""Derive the retail stream from the 82-word alias-aware candidate.

This is only a structural screen, not approval to install word patches.
The transformations need an independent semantic and fault/owner audit.
"""
from pathlib import Path
import json,struct
from tools.experiments.game_paired_ground_constructor_match import payload
root=Path(__import__('os').environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve();out=root/'conker/build/game-menu-load-151e22bc-durable';name='func_151E22BC'
raw,refs=payload(out/'alias-00.o',name);retail,trefs=payload(out/'retail.o',name)
w=list(struct.unpack('>82I',raw));assembled=list(struct.unpack('>82I',retail))
rom=(Path('conker/conker.us.bin')).read_bytes();truth=list(struct.unpack_from('>82I',rom,0x20f76c))
# The extracted assembly spells the final jlabel without its emitted suffix,
# so use the bound ROM branch words and retain only real external relocations.
for offset,entries in list(trefs.items()):
    kept=[entry for entry in entries if entry[0]!='R_MIPS_PC16']
    if kept:trefs[offset]=kept;truth[offset//4]=assembled[offset//4]
    else:del trefs[offset]
origins=list(range(82));origins[58:65]=[62,63,64,58,59,60,61];origins[70:72]=[71,70]
assert len(set(origins))==82
# Each changed byte load feeds only a byte store before that temporary is
# overwritten; sign extension cannot alter the stored low byte.
load_store_pairs=((40,41),(42,44),(50,52),(53,54),(55,57),(58,60),
                  (62,64),(65,68),(69,72),(73,74),(75,77))
for load,store in load_store_pairs:
    a,b=truth[load],truth[store];x,y=w[origins[load]],w[origins[store]]
    assert a>>26==36 and b>>26==40 and (a>>16&31)==(b>>16&31),(load,store)
    assert x>>26==32 and y>>26==40 and (x>>16&31)==(y>>16&31),(load,store)
    assert (a>>21&31)==2 and (b>>21&31)==3 and (x>>21&31)==4 and (y>>21&31)==2
# Both reordered writes have the same base and distinct constant byte offsets.
assert all(truth[i]>>26==40 for i in (70,71))
assert (truth[70]>>21&31)==(truth[71]>>21&31)==3
assert {truth[70]&65535,truth[71]&65535}=={3,0x11}
assert truth[9]==0x24090004 and truth[24]==0x312300ff
renames=[];load_changes=[];branches=[];result=[];newrefs={}
for at,origin in enumerate(origins):
    value=w[origin];wanted=truth[at];op=value>>26;target_op=wanted>>26
    if at==24:
        assert value==0x24020004 and wanted==0x312300ff
        value=wanted
    else:
        if op!=target_op:
            assert op==32 and target_op==36,(at,origin,hex(value),hex(wanted))
            value=(value&0x03ffffff)|(target_op<<26);load_changes.append(at);op=target_op
        if op==0:
            assert (value&0x7ff)==(wanted&0x7ff),(at,hex(value),hex(wanted))
            fields=(21,16,11)
        elif op in (2,3):
            assert (value&0x3ffffff)==(wanted&0x3ffffff),(at,hex(value),hex(wanted))
            fields=()
        else:
            fields=(21,16)
            if (value&65535)!=(wanted&65535):
                assert at in (59,63) and op==4,(at,origin,hex(value),hex(wanted))
                branches.append({'position':at,'from':origin,'old':value&65535,'new':wanted&65535})
                value=(value&~65535)|(wanted&65535)
        for shift in fields:
            a=(value>>shift)&31;b=(wanted>>shift)&31
            if a!=b:
                assert a not in (0,29,31) and b not in (0,29,31),(at,shift,a,b)
                value=(value&~(31<<shift))|(b<<shift);renames.append((at,shift,a,b))
    result.append(value)
    if origin*4 in refs:
        newrefs[at*4]=[(kind,'jtbl_800AB994' if symbol=='.rodata' else symbol) for kind,symbol in refs[origin*4]]
issues=[{'index':i,'from':origins[i],'actual':hex(a),'retail':hex(b),'ours':newrefs.get(i*4),'expected':trefs.get(i*4)}
        for i,(a,b) in enumerate(zip(result,truth)) if a!=b or newrefs.get(i*4)!=trefs.get(i*4)]
report={'words':82,'origins':origins,'register_field_edits':renames,'signed_to_unsigned_byte_loads':load_changes,
        'constant_equivalence_at_24':'t1 is 4, so andi t1,255 equals immediate 4',
        'repositioned_branch_targets':branches,'reordered_distinct_settings_stores':[70,71],
        'table_binding':'jtbl_800AB994','issues':issues,'semantic_proof_incomplete':True,'uncredited':True}
(out/'derive-private.json').write_text(json.dumps(report,indent=2)+'\n')
print({k:v for k,v in report.items() if k not in ('origins','register_field_edits','issues')},flush=True)
print('issues',issues,flush=True);assert not issues
