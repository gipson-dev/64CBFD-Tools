"""Private lifetime/layout fits of the complete texture vertex-span scanner."""
import itertools
import argparse
import json
from pathlib import Path
import struct

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_remaining_donor_candidates as build

BUILD=source.BUILD+'/fit'
SEED=dict(source.variants())['explicit-shared-end']


def declare(body,order):
    lo=body.index('    s32 extent;')
    hi=body.index('    func_1510D0EC')
    lines=[line for line in body[lo:hi].splitlines() if line.strip()]
    mapping={line.strip().split()[-1].removesuffix(';').removeprefix('*').split('[')[0]:line for line in lines}
    assert len(mapping)==len(order) and set(mapping)==set(order)
    return body[:lo]+'\n'.join(mapping[name] for name in order)+'\n\n'+body[hi:]


def home_variants():
    order=['extent','vertexBase','indices','indexCursor','indexEnd','count','i','opcode','stage','maximum','nested','trimFirst','foundVertex','minimum']
    scalar=[name for name in order if name!='indices']
    for at in range(len(order)):
        names=scalar[:at]+['indices']+scalar[at:]
        yield 'array-at-'+str(at),declare(SEED,names)
    yield 'retail-homes',declare(SEED,['count','extent','i','opcode','vertexBase','stage','maximum','nested',
        'indices','indexCursor','indexEnd','trimFirst','foundVertex','minimum'])


HOMES=dict(home_variants())['retail-homes']


def return_variants():
    old='    return (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;'
    expressions=(
        ('scaled-first','(s32)(((maximum + 1) << 4) + vertexBase - *firstVertex) >> 4'),
        ('difference-first','(s32)(vertexBase - *firstVertex + ((maximum + 1) << 4)) >> 4'),
        ('sizeof-first','(s32)((maximum + 1) * sizeof(Vtx) + vertexBase - *firstVertex) >> 4'),
        ('multiply-first','(s32)((maximum + 1) * 16 + vertexBase - *firstVertex) >> 4'),
    )
    for label,expression in expressions:
        yield label,HOMES.replace(old,'    return '+expression+';')
    pointer=HOMES.replace('    u32 vertexBase;','    Vtx *vertexBase;').replace(
        'vertexBase = commands->words.w1;','vertexBase = (Vtx *)commands->words.w1;').replace(
        'vertexBase < *firstVertex','(u32)vertexBase < *firstVertex').replace(
        '*firstVertex = vertexBase;','*firstVertex = (u32)vertexBase;').replace(
        old,'    return vertexBase + maximum + 1 - (Vtx *)*firstVertex;')
    yield 'pointer-base',pointer
    yield 'pointer-base-grouped',pointer.replace('vertexBase + maximum + 1','vertexBase + (maximum + 1)')
    typed=pointer.replace('u32 *firstVertex','Vtx **firstVertex').replace(
        '(u32)vertexBase < *firstVertex','vertexBase < *firstVertex').replace(
        '*firstVertex = (u32)vertexBase;','*firstVertex = vertexBase;').replace(
        '*firstVertex += (minimum & 255) << 4;','*firstVertex += minimum & 255;').replace(
        '(Vtx *)*firstVertex','*firstVertex')
    yield 'typed-vertices',typed
    yield 'typed-vertices-grouped',typed.replace('vertexBase + maximum + 1','vertexBase + (maximum + 1)')


def control_variants():
    for label,text in (('homes',HOMES),('seed',SEED)):
        yield label+'-shared-count-end',text.replace('indexEnd = indexCursor + 3','indexEnd = indexCursor + count').replace(
            'indexEnd = indexCursor + 6','indexEnd = indexCursor + count')
        yield label+'-array-count-end',text.replace('indexEnd = indexCursor + 3','indexEnd = indices + count').replace(
            'indexEnd = indexCursor + 6','indexEnd = indices + count')
        switch=text.replace('        if (stage == 0) {','        switch (stage) {\n        case 0:').replace(
            '        } else if (stage == 1) {','            break;\n        case 1:').replace(
            '        } else if (stage == 2) {','            break;\n        case 2:').replace(
            'if (opcode == -33) { break; }','if (opcode == -33) { goto finish; }').replace(
            'if (nested > 0) { break; }','if (nested > 0) { goto finish; }').replace(
            '    return (s32)(vertexBase','finish:\n    return (s32)(vertexBase')
        yield label+'-switch',switch
        yield label+'-switch-shared-count-end',switch.replace('indexEnd = indexCursor + 3','indexEnd = indexCursor + count').replace(
            'indexEnd = indexCursor + 6','indexEnd = indexCursor + count')


def exit_variants():
    expression='(s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4'
    direct=HOMES.replace('if (opcode == -33) { break; }','if (opcode == -33) { return '+expression+'; }').replace(
        'if (nested > 0) { break; }','if (nested > 0) { return '+expression+'; }')
    yield 'direct-returns',direct
    yield 'goto-exit',HOMES.replace('if (opcode == -33) { break; }','if (opcode == -33) { goto finish; }').replace(
        'if (nested > 0) { break; }','if (nested > 0) { goto finish; }').replace(
        '    return (s32)(vertexBase','finish:\n    return (s32)(vertexBase')
    combined=HOMES.replace('''            if (opcode == -33) { break; }
            if (opcode == -3) {
                nested++;
                if (nested > 0) { break; }
            } else if (opcode == 1) {''','''            if (opcode == -33 || (opcode == -3 && ++nested > 0)) {
                return '''+expression+''';
            }
            if (opcode == -3) {
            } else if (opcode == 1) {''')
    yield 'combined-exit',combined
    lines=('    stage = 0;','    maximum = 0;','    nested = 0;','    trimFirst = 0;')
    for index,order in enumerate(itertools.permutations(lines)):
        yield 'initialization-order-'+str(index),HOMES.replace('\n'.join(lines),'\n'.join(order))
    yield 'chained-initialization',HOMES.replace('\n'.join(lines),'    stage = maximum = nested = trimFirst = 0;')


def advisory_variants():
    named=HOMES.replace('    s32 minimum;','    s32 minimum;\n    s32 endCode;').replace(
        '    stage = 0;','    endCode = -33;\n    stage = 0;').replace('opcode == -33','opcode == endCode').replace(
        '                    *firstVertex += (minimum & 255) << 4;',
        '                    *firstVertex += (minimum & 255) << 4;\n                    endCode = -33;')
    reused=HOMES.replace('    stage = 0;','    minimum = -33;\n    stage = 0;').replace(
        'opcode == -33','opcode == minimum').replace('                    *firstVertex += (minimum & 255) << 4;',
        '                    *firstVertex += (minimum & 255) << 4;\n                    minimum = -33;')
    tail=HOMES.replace('    stage = 0;','    minimum = -33;\n    stage = 0;').replace(
        'opcode == -33','opcode == minimum').replace('        commands++;\n    }',
        '        minimum = -33;\n        commands++;\n    }')
    for label,text in (('homes',HOMES),('named-end',named),('reused-end',reused),('tail-end',tail)):
        if label!='homes':
            yield label,text
        yield label+'-capture-first',text.replace('if (opcode == -33) { break; }',
            'if (opcode == -33) { i = *firstVertex; break; }').replace(
            'if (opcode == endCode) { break; }','if (opcode == endCode) { i = *firstVertex; break; }').replace(
            'if (opcode == minimum) { break; }','if (opcode == minimum) { i = *firstVertex; break; }').replace(
            'if (nested > 0) { break; }','if (nested > 0) { i = *firstVertex; break; }').replace(
            '((maximum + 1) << 4) - *firstVertex','((maximum + 1) << 4) - (u32)i')


def variants():
    yield 'seed',SEED
    cursor=SEED.replace('    s32 *indexCursor;\n    s32 *indexEnd;',
        '    s32 *indexEnd;\n    s32 *indexCursor;')
    span=lambda body:body.replace('    s32 extent;','    s32 extent;\n    s32 span;').replace(
        '    return (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;',
        '    span = vertexBase + ((maximum + 1) << 4) - *firstVertex;\n    return span >> 4;')
    for label,body in (('seed',SEED),('cursor-order',cursor)):
        if label!='seed':
            yield label,body
        yield label+'-span-local',span(body)
        for size in (13,14,15,16,20,24):
            yield label+'-capacity-'+str(size),body.replace('indices[12]','indices[%d]'%size)
        for index,order in enumerate(itertools.permutations(('count','maximum','minimum'))):
            text=body
            for name in order:
                text=text.replace('    s32 '+name+';\n','')
            text=text.replace('    s32 i;',''.join('    s32 '+name+';\n' for name in order)+'    s32 i;')
            yield label+'-scalar-order-'+str(index),text
        for n in (3,6):
            before='for (indexCursor = indices, indexEnd = indexCursor + %d; indexCursor < indexEnd; indexCursor++)'%n
            after='indexCursor = indices;\n                    indexEnd = indexCursor + %d;\n                    for (; indexCursor < indexEnd; indexCursor++)'%n
            body=body.replace(before,after)
        yield label+'-separate-end-assignments',body
        yield label+'-separate-end-span',span(body)
    for shape in ((4,3),(3,4)):
        name='matrix-array-%dx%d'%shape
        body=SEED.replace('    s32 indices[12];','    s32 triangles[%d][%d];\n    s32 *indices;'%shape).replace(
            '    stage = 0;','    indices = &triangles[0][0];\n    stage = 0;')
        yield name,body
        yield name+'-cursor-order',body.replace('    s32 *indexCursor;\n    s32 *indexEnd;',
            '    s32 *indexEnd;\n    s32 *indexCursor;')


def measure(root,out,label,body):
    source.freeze(root,root/source.BUILD)
    before=(root/source.BUILD/'before-owner').read_text()
    obj,diagnostics=build.compile_owner(root,out,source.recover(before,body),label)
    data,functions=build.link_owner(root,out,obj,source.OWNER)
    info=functions[source.FUNCTION]
    words=list(struct.unpack_from('>%dI'%(info['size']//4),data,info['value']))
    retail=list(struct.unpack_from('>339I',(root/'conker/conker.us.bin').read_bytes(),source.ROM))
    call=words.index(0x0D44343B)
    homes=[w&65535 for w in words[:call+2] if w>>16==0x27A5]
    assert len(homes)==1
    row=dict(label=label,bytes=info['size'],frame=(0x10000-(words[0]&65535))&65535,
        differences=sum(a!=b for a,b in zip(words,retail))+abs(len(words)-len(retail)),
        diagnostics=diagnostics,extent_home=homes[0],word_at_2C=hex(words[11]),
        stack_stores=sorted({w&65535 for w in words if w>>26==43 and w>>21&31==29}),
        diff_offsets=[i*4 for i,(a,b) in enumerate(zip(words,retail)) if a!=b])
    return row,words,obj


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    groups=dict(shape=variants,homes=home_variants,returns=return_variants,
        control=control_variants,exits=exit_variants,advisory=advisory_variants)
    parser.add_argument('--group',choices=groups,default='shape')
    parser.add_argument('--all',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    out.mkdir(exist_ok=True)
    filenames=dict(shape='screens.json',homes='homes-screens.json',returns='return-screens.json',
        control='control-screens.json',exits='exit-screens.json',advisory='advisory-screens.json')
    for name in (groups if args.all else (args.group,)):
        rows=[]
        for label,body in groups[name]():
            row,_,_=measure(root,out,label,body)
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='diff_offsets'}),flush=True)
        (out/filenames[name]).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
