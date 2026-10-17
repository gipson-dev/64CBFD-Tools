"""Qualify the complete burst C body and two closed retail normalization groups."""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import struct

from tools.experiments import game_owner_burst_literal_candidates as literal
from tools.experiments.game_graphics_task_submit import same_functions

source=literal.source
BUILD='conker/build/game-owner-burst-match'
OWNER,FUNCTION,ENTRY,ROM,SIZE=source.OWNER,source.FUNCTION,source.ENTRY,source.ROM,source.SIZE
RAW_SHA='f5a54eea68420c05735c7f2b3e65f9ddbae01123fa1e9dc9d6275812b9305907'
PATHS,BASELINE=dict(source.PATHS),dict(source.BASELINE)
for key,path,sha in (
    ('owner_burst_2d14_recovery','tools/experiments/game_owner_burst_emitter.py','0e7c8cb53dc17625a1353fbeb081c50b38d28074264068d315b07881d1c5cf15'),
    ('owner_burst_2d14_tests','tools/tests/test_game_owner_burst_emitter.py','841877d84d1c1e6ff15e7f7bc105d1205c8da1e0e2e9a124440d5192e528bb38'),
    ('owner_burst_2d14_frame_tests','tools/tests/test_game_owner_burst_frame_trace.py','578c5b3d94967731ba8f94ea91e7150bab403e6ec14e7cc460cef03ad5b1ec07'),
    ('owner_burst_2d14_local_tests','tools/tests/test_game_owner_burst_uopt_local_trace.py','f6aecfebbc3fbf9c1b6e57e5990bcededda5e24a3767b636260f4e03aab0bdaf'),
    ('owner_burst_2d14_literal_table','conker/asm/data/246410.rodata.s','099c96d6783eead1dd67a8db6fe2371203a37b9ae6fe876db51ff7568ba4dbdb')):
    if key in PATHS:raise ValueError('Duplicate owner-burst checkpoint key: '+key)
    PATHS[key],BASELINE[key]=path,sha
GUARDS=(
    (0x080,0x92230222,0x92220222),(0x08C,0x92230222,0x92220222),
    (0x09C,0x11230008,0x10490008),(0x0A0,0x00601025,0x00401825),
    (0x0A4,0x50400007,0x50600007),(0x0A8,0xA2030005,0xA2020005),
    (0x0BC,0x92230222,0x92220222),(0x0C0,0xA2030005,0xA2020005),
    (0x1EC,0xAFB400B0,0x02E02025),(0x1F0,0xAFB500B4,0x03C02825),
    (0x1F4,0xAFB600A8,0x46085400),(0x1F8,0xAFB200AC,0x46048183),
    (0x1FC,0x46085400,0xE7B000D0),(0x200,0x02E02025,0xE7A600D4),
    (0x204,0x03C02825,0xAFB400B0),(0x208,0x24070002,0xAFB500B4),
    (0x20C,0x46048183,0xAFB600A8),(0x210,0xE7B000D0,0xAFB200AC),
    (0x214,0xE7A600D4,0x8E2601D4),(0x218,0x8E2601D4,0x24070002),
)


def form():return next(f for f in literal.forms() if f[0]=='literal-gap-created')


def freeze(root,out):
    source.freeze(root,out)
    from tools.tests import owner_burst_checkpoint as latest
    for key,path in PATHS.items():
        data=latest.previous_input((root/path).read_bytes(),path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed burst match predecessor: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed burst match frozen input: '+key)


def guard_text(before):
    rows=list(csv.DictReader(io.StringIO(before)))
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in rows):raise ValueError('Existing burst guards')
    newline='\r\n' if before.endswith('\r\n') else '\n'
    if not before.endswith('\n'):raise ValueError('Incomplete burst guard predecessor line')
    extra=[]
    for offset,expected,replacement in GUARDS:
        note=('Normalize closed burst state V0 V1 allocation cycle' if offset<0x100
            else 'Preserve retail burst transform setup dependency schedule')
        extra.append('%s,%s,0x%X,0x%08X,0x%08X,-,-,%s,,,false%s'%
            (OWNER,FUNCTION,offset,expected,replacement,note,newline))
    return before+''.join(extra)


def swap_state_registers(word):
    op=word>>26;fields=()
    if op==0 and word&63==37:fields=(21,16,11)
    elif op in (4,20):fields=(21,16)
    elif op in (36,40):fields=(16,)
    for shift in fields:
        register=word>>shift&31
        if register in (2,3):word=(word&~(31<<shift))|((5-register)<<shift)
    return word


def prove_groups(words,truth,bindings):
    if len(words)!=288 or len(truth)!=288 or len(GUARDS)!=20 or words[0]!=truth[0] or words[0]!=0x27BDFEB0:
        raise ValueError('Changed burst frame/extent or normalization budget')
    if [(i*4,a,b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b]!=list(GUARDS):
        raise ValueError('Unaccounted burst words')
    if any(offset in bindings for offset,_,_ in GUARDS):raise ValueError('Unexpected burst normalization relocation')
    for offset in range(0x80,0xC4,4):
        current=swap_state_registers(words[offset//4])
        if offset==0x9C:current=(current&~((31<<21)|(31<<16)))|((current>>16&31)<<21)|((current>>21&31)<<16)
        if current!=truth[offset//4]:raise ValueError('Burst state cycle is not closed')
    if words[0xC4//4]!=truth[0xC4//4] or truth[0xC4//4]!=0x92220222:
        raise ValueError('Burst state cycle no longer ends at the next definition')
    a=words[0x1EC//4:0x21C//4];b=truth[0x1EC//4:0x21C//4]
    if Counter(a)!=Counter(b) or len(set(a))!=12:raise ValueError('Burst setup is not a closed permutation')
    chains=((0x46085400,0x46048183,0xE7B000D0,0xE7A600D4),
        (0xAFB400B0,0xAFB500B4,0xAFB600A8,0xAFB200AC))
    for chain in chains:
        if any([sequence.index(w) for w in chain]!=sorted(sequence.index(w) for w in chain) for sequence in (a,b)):
            raise ValueError('Burst setup dependency order changed')
    return dict(closed_state_cycle_words=8,closed_setup_permutation_words=12,
        arithmetic_and_pointer_store_chains_preserved=True,insertions=0,omissions=0,
        frame_or_address_rewrites=0,normalization_relocations=0)


def qualify(root,out):
    freeze(root,out)
    label,body,types=form();obj,words,row=literal.measure(root,out,label,body,types)
    if (row['words'],row['frame'],row['differences'],row['raw_sha'])!=(288,336,20,RAW_SHA):
        raise ValueError('Changed complete burst retail-frame body')
    truth=list(struct.unpack_from('>288I',(out/'before-retail_rom').read_bytes(),ROM))
    groups=prove_groups(words,truth,source.parts(obj)[1])
    guards=out/'expected-guards.csv';guards.write_bytes(guard_text((out/'before-guards').read_bytes().decode()).encode())
    padded=literal.padded_object(root,out,obj,'candidate',guards)
    data,functions=source.build.link_owner(root,out,padded,OWNER)
    exact=list(struct.unpack_from('>288I',data,functions[FUNCTION]['value']))
    if exact!=truth:raise ValueError('Complete guarded burst does not match retail')
    old,diagnostics=source.compile_owner(root,out,(out/'before-record_gate_owner').read_text(),'owner-before')
    if diagnostics:raise ValueError('Changed burst before owner')
    if same_functions(source.padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=11:
        raise ValueError('Changed burst normalized neighbors')
    row.update(groups=groups,new_guards=20,unguarded_words=268,guarded_byte_exact=True,
        unchanged_padded_neighbors=11,installed=False,matching_credit=0)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,[words,exact],row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];row=qualify(root,root/BUILD)[-1]
    print(json.dumps({k:v for k,v in row.items() if k!='bindings'},indent=2),flush=True)
