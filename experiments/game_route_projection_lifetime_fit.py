"""Fit route projection phase-local roles without changing production code."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.experiments import game_route_projection_setup as source

BUILD='conker/build/game-route-projection-lifetime-fit'


def phase_body():
    body=source.MODEL.replace('    s8 mode;','    s32 mode;')
    # The common projection IDs are not live across the initialization cycle.
    marker='        current = record[0x4B];'
    at=body.rindex(marker)
    head,tail=body[:at],body[at:]
    for old,new in (('current','selectedID'),('previous','oldID'),('distance','best')):
        tail=re.sub(r'\b'+old+r'\b',new,tail)
    body=head+tail
    body=body.replace('    u8 first;','    u8 first;\n    u8 selectedID;\n    u8 oldID;')
    return body


def forms():
    body=phase_body()
    yield 'phase-local',body
    for shape in ('copy','scope','return'):
        b=body.replace('    u8 *object;','    u8 *entryObject;\n    u8 *object;')
        b=b.replace('    object = *(u8 **)(actor + 0x318);\n    if (object != 0) {',
            '    entryObject = *(u8 **)(actor + 0x318);\n    if (entryObject != 0) {')
        marker='        if (*(s8 *)(record + 0x30) == 2) {'
        b=b.replace(marker,'        object = entryObject;\n'+marker)
        if shape=='scope':
            b=b.replace('    u8 *object;\n','').replace('    if (entryObject != 0) {',
                '    if (entryObject != 0) {\n        u8 *object;')
        elif shape=='return':
            b=b.replace('    if (entryObject != 0) {',
                '    if (entryObject == 0) { return; }\n    {')
        yield 'entry-'+shape,b


def declaration_forms():
    body=source.MODEL.replace('    s8 mode;\n','')
    body=re.sub(r'\bmode\b','i',body)
    for width in ('byte','word'):
        b=body if width=='byte' else body.replace('    u8 candidate;','    s32 candidate;')
        for place in ('old','last','before-floats'):
            selected=b
            if place!='old':
                selected=selected.replace('    u8 *object;\n','')
                marker='    f32 dx;' if place=='before-floats' else '\n    object ='
                selected=selected.replace(marker,'    u8 *object;\n'+marker)
            yield 'declaration-'+width+'-'+place,selected


def carrier_forms():
    # The signed index also carries entry pointer bits under the original 32-bit ABI.
    body=dict(declaration_forms())['declaration-byte-last']
    body=body.replace('    object = *(u8 **)(actor + 0x318);\n    if (object != 0) {',
        '    i = *(s32 *)(actor + 0x318);\n    if (i != 0) {')
    marker='        if (*(s8 *)(record + 0x30) == 2) {'
    body=body.replace(marker,'        object = (u8 *)(u32)i;\n'+marker)
    for width in ('byte','word'):
        b=body if width=='byte' else body.replace('    u8 candidate;','    s32 candidate;')
        yield 'carrier-'+width,b
        # Capture the selected address once, retaining the class read on each arm.
        c=b.replace('    u8 *node;','    u8 *node;\n    u8 *candidateNode;')
        c=c.replace('                            i = D_800D23A8;',
            '                            i = D_800D23A8;\n                            candidateNode = D_800D2350 + candidate * 0x10;')
        c=c.replace('D_800D2350[candidate * 0x10 + 0xF]','candidateNode[0xF]')
        yield 'carrier-'+width+'-address',c


def peeled_forms():
    body=dict(carrier_forms())['carrier-byte']
    lo=body.index('                    for (j = 0; j < 5; j++) {')
    hi=body.index('                    i = D_80087290;',lo)
    loop=body[lo:hi]
    block=loop.split('\n',1)[1].rsplit('                    }\n',1)[0]
    first='\n'.join(line[4:] for line in block.rstrip().splitlines())+'\n'
    first=first.replace('node[j + 9]','node[9]').replace('candidate','firstCandidate')
    tail=loop.replace('j = 0;','j = 1;')
    for width in ('byte','word'):
        b=body[:lo]+first+tail+body[hi:]
        b=b.replace('    u8 candidate;','    u8 firstCandidate;\n    '+('u8' if width=='byte' else 's32')+' candidate;')
        yield 'peeled-'+width,b
        c=b.replace('    u8 *node;','    u8 *node;\n    u8 *candidateNode;')
        c=c.replace('                            i = D_800D23A8;',
            '                            i = D_800D23A8;\n                            candidateNode = D_800D2350 + candidate * 0x10;')
        c=c.replace('D_800D2350[candidate * 0x10 + 0xF]','candidateNode[0xF]')
        yield 'peeled-'+width+'-address',c


def lifetime_forms():
    for width in ('byte','word'):
        b=dict(carrier_forms())['carrier-'+width]
        b=b.replace('    u8 *object;\n','').replace('    f32 targetZ;',
            '    u8 *object;\n    f32 targetZ;')
        yield 'lifetime-'+width+'-object',b
        at=b.rindex('        current = record[0x4B];')
        b=b[:at]+re.sub(r'\bdistance\b','best',b[at:])
        yield 'lifetime-'+width+'-distance',b
        b=b[:at]+re.sub(r'\bpreviousNode\b','node',b[at:])
        b=b.replace('    u8 *previousNode;\n','')
        yield 'lifetime-'+width+'-node',b


SELECTED=dict(lifetime_forms())['lifetime-byte-object']
RAW_SHA='6c76a9f1bf9e0e0cdcf4818da5e0fc75b0278b5acad183e5d530d3bb29630970'
BINDINGS={
    44:[('R_MIPS_HI16','D_8008FDBC')],56:[('R_MIPS_LO16','D_8008FDBC')],
    60:[('R_MIPS_HI16','D_80087290')],76:[('R_MIPS_LO16','D_80087290')],
    132:[('R_MIPS_HI16','D_800D2350')],148:[('R_MIPS_LO16','D_800D2350')],
    136:[('R_MIPS_HI16','D_800D23A8')],140:[('R_MIPS_LO16','D_800D23A8')],
    516:[('R_MIPS_HI16','D_800D2350')],524:[('R_MIPS_LO16','D_800D2350')],
    520:[('R_MIPS_HI16','D_8009DA08')],532:[('R_MIPS_LO16','D_8009DA08')],
    576:[('R_MIPS_26','func_1508907C')],696:[('R_MIPS_26','func_1512D560')],
    716:[('R_MIPS_HI16','D_800D2350')],724:[('R_MIPS_LO16','D_800D2350')],
    888:[('R_MIPS_26','func_1508907C')],1136:[('R_MIPS_26','func_1512D560')],
}


def checked(obj):
    text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1208 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown projection lifetime candidate or bindings')
    return raw,bindings


def qualify(root,out):
    values=source.freeze(root,out);obj,words,row=measure(root,out,'qualified',SELECTED);checked(obj)
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    before,diagnostics=compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(302,120,301,72) or \
            source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
        raise ValueError('Changed projection lifetime/normal-profile neighbor evidence')
    if words[12]>>26!=20 or words[13]!=0x8FBF002C or words[23]!=0xAFA6003C:
        raise ValueError('Lost conditional object capture')
    try:source.require_retail_contract(words)
    except ValueError:row['installable']=False
    else:raise ValueError('Incomplete lifetime fit unexpectedly passed retail extent gate')
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def measure(root,out,name,body):
    obj,words,row=source.measure(root,out,name,body,True)
    row['name']=name
    return obj,words,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='');parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    if args.qualify:
        print(json.dumps(qualify(root,out)[2],indent=2));raise SystemExit(0)
    rows=[]
    for name,body in (*forms(),*declaration_forms(),*carrier_forms(),*peeled_forms(),*lifetime_forms()):
        if args.filter not in name:continue
        _,_,row=measure(root,out,name,body);rows.append(row)
        print(json.dumps({k:row[k] for k in ('name','words','frame','differences','saved','diagnostics')}),flush=True)
    (out/('screens-'+(args.filter or 'all')+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
