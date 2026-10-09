"""Owner-link setup fitting and three closed T6/T7 allocation permutations."""
import argparse
import csv
import io
import json
import struct
from pathlib import Path

from tools.experiments import game_owner_link_setup_candidates as recovery
from tools.pad_generated_object import parse_object

ENTRY,ROM,WORDS=recovery.ENTRY,recovery.ROM,recovery.WORDS
FUNCTION,SOURCE,ORIGINAL=recovery.FUNCTION,recovery.SOURCE,recovery.ORIGINAL
TYPES,DECLARATIONS,SYMBOLS=recovery.TYPES,recovery.DECLARATIONS,recovery.SYMBOLS
REGIONS=((0x64,0xA4),(0x168,0x1E4),(0x25C,0x2C0))
SELECTED=recovery.SELECTED.replace(
    '    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;\n',
    '').replace('    u8 *created;',
    '    struct { OwnerLinkPacket2348 packet; OwnerLinkRequest2348 request; } work;\n    u8 *created;')
SELECTED=SELECTED.replace('packet.','work.packet.').replace('request.','work.request.').replace(
    '&packet','&work.packet').replace('&request','&work.request').replace(
    'pair = actor + 0x28;', 'pair = *(u8 **)&actor + 0x28;')
for _offset in ('0x18','0x14','0x10'):
    _old='*(u8 **)(pair + '+_offset+') = created;\n    if (created != NULL) {\n        memcpy(created + 0x150, &work.packet, 48);'
    _new='*(u8 **)(pair + '+_offset+') = created;\n    if (created != NULL) {\n        memcpy((*(u8 **)(pair + '+_offset+')) + 0x150, &work.packet, 48);'
    assert _old in SELECTED
    SELECTED=SELECTED.replace(_old,_new,1)


def operands(word):
    op=word>>26
    rs,rt,rd=word>>21&31,word>>16&31,word>>11&31
    if op==0:
        fn=word&63
        if fn==0:
            return {rt},{rd}
        if fn in (33,35,37):
            return {rs,rt},{rd}
        if fn==8:
            return {rs},set()
    if op in (8,9,12,13,14):
        return {rs},{rt}
    if op==15:
        return set(),{rt}
    if op in (33,35,36,37):
        return {rs},{rt}
    if op in (40,41,43):
        return {rs,rt},set()
    if op==49:
        return {rs},set()
    if op==57:
        return {rs},set()
    if op==17:
        fmt=word>>21&31
        return ({rt},set()) if fmt==4 else (set(),{rt}) if fmt==0 else (set(),set())
    if op in (4,5):
        return {rs,rt},set()
    if op==3:
        return set(),{1,2,3,*range(4,16),24,25,31}
    raise ValueError('unsupported proof word 0x%08X'%word)


def permute(word):
    op=word>>26
    if op not in (8,9,15,35,36,40,43):
        return word
    shifts=(16,) if op==15 else (21,16)
    for shift in shifts:
        value=word>>shift&31
        if value in (14,15):
            word^=1<<shift
    return word


def normalize(words):
    if len(words)!=210 or (-words[0])&65535!=168:
        raise ValueError('complete retail length/frame required')
    result=list(words)
    for begin,end in REGIONS:
        for i in range(begin//4,end//4):
            result[i]=permute(result[i])
    return result


def certify(words):
    result=normalize(words)
    changed=[i*4 for i,(a,b) in enumerate(zip(words,result)) if a!=b]
    if len(changed)!=25:
        raise ValueError('expected exactly25 allocation words')
    for begin,end in REGIONS:
        defined=set()
        for offset in range(begin,end,4):
            word=words[offset//4]
            if word>>26 in (3,4,5):
                raise ValueError('permutation region is not straight-line')
            reads,writes=operands(word)
            if (reads & {14,15})-defined:
                raise ValueError('live input crosses permutation boundary')
            defined |= writes & {14,15}
        live={14,15}
        for word in words[end//4:]:
            reads,writes=operands(word)
            if reads & live:
                raise ValueError('live output crosses permutation boundary')
            live -= writes
            if not live:
                break
        if live:
            raise ValueError('unclosed permutation region')
    return dict(offsets=changed,regions=REGIONS,registers=(14,15),
        straight_line=True,no_live_inputs_or_outputs=True,retail_lookup=False)


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def guard_rows(obj):
    text,functions,relocations=parse_object(obj)
    fn=functions[FUNCTION]
    words=list(struct.unpack_from('>210I',text,fn['value']))
    proof=certify(words)
    result=normalize(words)
    rows=[]
    for offset in proof['offsets']:
        rel=relocations.get(fn['value']+offset,[])
        spec=';'.join(kind+':'+name for kind,name in rel) or '-'
        rows.append(dict(filename='generated_1DF510',function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%words[offset//4],replacement='0x%08X'%result[offset//4],
            expected_relocations=spec,replacement_relocations=spec,
            note='Normalize three closed owner-link setup T6/T7 allocation permutations',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-owner-link-setup-matching'
    rows=[]
    for profile in recovery.compiler.PROFILES if args.profiles else ('o2g3',):
        meta,words=compile_candidate(root,out,'selected-'+profile,profile=profile)
        if profile=='o2g3':
            meta['certificate']=certify(words)
            meta['normalized_words']=normalize(words)
            stream=io.StringIO()
            guards=guard_rows(out/('selected-'+profile+'.o'))
            writer=csv.DictWriter(stream,fieldnames=list(guards[0]),lineterminator='\n')
            writer.writerows(guards)
            (out/'guards.csv').write_text(stream.getvalue())
        rows.append(meta)
        print(profile,meta['body_words'],hex(meta['frame']),meta['differences'],flush=True)
    (out/'measurements.json').write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
