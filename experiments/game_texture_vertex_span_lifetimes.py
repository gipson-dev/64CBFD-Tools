"""Bounded live-role reuse and shift-loop endpoint fits of the full scanner."""
import argparse
import json
from pathlib import Path
import re

from tools.experiments import game_texture_vertex_span_fit as fit
from tools.experiments import game_texture_vertex_span as source

BUILD=fit.BUILD+'/lifetimes'
CALL='    func_1510D0EC(resource, &extent, 3, 0);'
COUNT_OPCODE_ROLES={'stage = 0;':'stage','maximum = 0;':'maximum','nested = 0;':'nested',
    'trimFirst = 0;':'trimFirst','opcode = 3;':'count','opcode = *(s8 *)commands;':'opcode'}


def reuse(body,mapping):
    header,tail=body.split(CALL,1)
    return header+CALL+re.sub(r'\b('+'|'.join(mapping)+r')\b',lambda m:mapping[m[0]],tail)


def role_variants():
    yield 'homes',fit.HOMES
    for old,new in (('foundVertex','count'),('foundVertex','minimum'),('foundVertex','i'),
            ('count','foundVertex'),('count','opcode'),('i','foundVertex')):
        yield old+'-as-'+new,reuse(fit.HOMES,{old:new})
    yield 'count-opcode-and-found-index',reuse(fit.HOMES,{'count':'opcode','foundVertex':'i'})


def endpoint(body,shape):
    for count in (3,6):
        original='for (indexCursor = indices, indexEnd = indexCursor + %d; indexCursor < indexEnd; indexCursor++)'%count
        alternatives={
            'end-first':'for (indexEnd = indices + %d, indexCursor = indices; indexCursor < indexEnd; indexCursor++)'%count,
            'end-before-loop':'indexEnd = indices + %d;\n                    for (indexCursor = indices; indexCursor < indexEnd; indexCursor++)'%count,
            'cursor-from-end':'for (indexEnd = indices + %d, indexCursor = indexEnd - %d; indexCursor < indexEnd; indexCursor++)'%(count,count),
            'constant-end':'for (indexCursor = indices, indexEnd = indices + %d; indexCursor < indexEnd; indexCursor++)'%count,
            'cursor-from-end-count':'for (indexEnd = indices + %d, indexCursor = indexEnd - count; indexCursor < indexEnd; indexCursor++)'%count,
        }
        assert original in body
        body=body.replace(original,alternatives[shape])
    return body


def endpoint_variants():
    for shape in ('end-first','end-before-loop','cursor-from-end','constant-end','cursor-from-end-count'):
        yield shape,endpoint(fit.HOMES,shape)
    yield 'swapped-pointer-roles',reuse(fit.HOMES,{'indexCursor':'indexEnd','indexEnd':'indexCursor'})


def induction_variants():
    start='                for (i = 0; i < count; i++) {'
    for label,marker in (('before-decode','                if (opcode == 5) {'),
            ('before-triangle-test','            } else if (opcode == 5 || opcode == 6 || (opcode >> 4) == 1) {'),
            ('stage-entry','            if (opcode == -33) { break; }')):
        body=fit.HOMES.replace(start,'                for (; i < count; i++) {')
        if label=='before-triangle-test':
            # Keep the assignment inside the triangle arm, immediately at entry.
            body=body.replace(marker,marker+'\n                i = 0;')
        else:
            body=body.replace(marker,'                i = 0;\n'+marker)
        yield 'index-init-'+label,body
        yield 'index-init-'+label+'-flag-count',reuse(body,{'foundVertex':'count'})
    body=fit.HOMES.replace(start,'                for (; i < count; i++) {').replace(
        '                if (opcode == 5) {','                i = 0;\n                if (opcode == 5) {')
    for shape in ('end-first','cursor-from-end-count'):
        yield 'index-init-before-decode-'+shape,endpoint(body,shape)
    for label,expression in (('ternary','opcode == 5 ? 3 : opcode == 6 ? 6 : 12'),
            ('nested-if',None)):
        body=fit.HOMES
        for count in (3,6,12):
            body=body.replace('                    count = %d;\n'%count,'')
        value='                count = '+expression+';\n' if expression else '''                if (opcode == 5) { count = 3; }
                else if (opcode == 6) { count = 6; }
                else { count = 12; }
'''
        yield 'count-before-decode-'+label,body.replace('                if (opcode == 5) {',
            value+'                if (opcode == 5) {',1)


def copy_variants():
    stage='        } else if (stage == 2) {'
    triangle='            } else if (opcode == 5 || opcode == 6 || (opcode >> 4) == 1) {'
    for label,marker in (('decode-copy',triangle),('stage-copy',stage)):
        head,tail=fit.HOMES.split(marker,1)
        tail=re.sub(r'\bopcode\b','count',tail)
        yield label,head+marker+'\n                count = opcode;'+tail
    head,tail=fit.HOMES.split(stage,1)
    yield 'outer-copy-stage-use',(head+stage+re.sub(r'\bopcode\b','count',tail)).replace(
        '        opcode = *(s8 *)commands;','        opcode = *(s8 *)commands;\n        count = opcode;',1)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    groups=dict(roles=role_variants,endpoints=endpoint_variants,induction=induction_variants,copies=copy_variants)
    parser.add_argument('--group',choices=groups,default='roles')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    out.mkdir(exist_ok=True)
    source.freeze(root,root/source.BUILD)
    rows=[]
    for label,body in groups[args.group]():
        row,words,_=fit.measure(root,out,label,body)
        row['opening_words']=[hex(word) for word in words[15:25]]
        rows.append(row)
        print(json.dumps({key:value for key,value in row.items() if key!='diff_offsets'}),flush=True)
    (out/(args.group+'-screens.json')).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
