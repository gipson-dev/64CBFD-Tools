"""Private scalar return-typing fits of the complete texture vertex scanner."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_texture_vertex_span as source
from tools.experiments import game_texture_vertex_span_fit as fit

BUILD=fit.BUILD+'/return-types'
RETURN='    return (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;'
SIGNED='((s32)vertexBase + ((maximum + 1) << 4) - (s32)*firstVertex)'


def finish(body,statement):
    assert body.count(RETURN)==1
    return body.replace(RETURN,statement)


def scalar_variants():
    body=fit.HOMES
    yield 'homes',body
    expressions=(('signed-address-operands',SIGNED+' >> 4'),
        ('signed-difference-first','((s32)vertexBase - (s32)*firstVertex + ((maximum + 1) << 4)) >> 4'),
        ('signed-scale-first','(((maximum + 1) << 4) + (s32)vertexBase - (s32)*firstVertex) >> 4'),
        ('signed-byte-multiply','((s32)vertexBase + (maximum + 1) * 16 - (s32)*firstVertex) >> 4'),
        ('unsigned-result','(u32)((s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4)'),
        ('signed-difference-cast','((s32)(vertexBase - *firstVertex) + ((maximum + 1) << 4)) >> 4'))
    for label,expression in expressions:
        yield label,finish(body,'    return '+expression+';')
    base=body.replace('    u32 vertexBase;','    s32 vertexBase;').replace(
        'vertexBase < *firstVertex','(u32)vertexBase < *firstVertex')
    yield 'signed-base',finish(base,'    return '+SIGNED+' >> 4;')
    output=body.replace('u32 *firstVertex','s32 *firstVertex').replace(
        'vertexBase < *firstVertex','vertexBase < (u32)*firstVertex')
    yield 'signed-output',finish(output,'    return '+SIGNED+' >> 4;')
    yield 'signed-base-and-output',finish(base.replace('u32 *firstVertex','s32 *firstVertex').replace(
        '(u32)vertexBase < *firstVertex','(u32)vertexBase < (u32)*firstVertex'),
        '    return (vertexBase + ((maximum + 1) << 4) - *firstVertex) >> 4;')
    yield 'unsigned-return-type',body.replace('s32 func_1510BF60(', 'u32 func_1510BF60(',1)


def local_variants():
    for name in ('count','i','minimum','opcode','foundVertex'):
        yield 'span-in-'+name,finish(fit.HOMES,'    '+name+
            ' = (s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex);\n    return '+name+' >> 4;')
        yield 'signed-span-in-'+name,finish(fit.HOMES,'    '+name+' = '+SIGNED+';\n    return '+name+' >> 4;')
    for name in ('i','minimum','count'):
        yield 'distance-in-'+name,finish(fit.HOMES,'    '+name+' = (s32)(vertexBase - *firstVertex);\n'+
            '    return ('+name+' + ((maximum + 1) << 4)) >> 4;')


def exit_variants():
    expression='(s32)(vertexBase + ((maximum + 1) << 4) - *firstVertex)'
    for name in ('minimum','i','count','foundVertex'):
        body=finish(fit.HOMES,'    return '+name+' >> 4;')
        for condition in ('opcode == -33','nested > 0'):
            body=body.replace('if ('+condition+') { break; }',
                'if ('+condition+') { '+name+' = '+expression+'; break; }')
        yield 'exit-span-in-'+name,body
        yield 'exit-span-parts-in-'+name,body.replace(name+' = '+expression+';',
            name+' = (s32)vertexBase + ((maximum + 1) << 4); '+name+' -= (s32)*firstVertex;')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    groups=dict(scalar=scalar_variants,locals=local_variants,exits=exit_variants)
    parser.add_argument('--group',choices=groups,default='scalar')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    out.mkdir(exist_ok=True)
    rows=[]
    for label,body in groups[args.group]():
        row,words,_=fit.measure(root,out,label,body)
        row['opening_words']=[hex(w) for w in words[15:26]]
        row['return_words']=[hex(w) for w in words[-16:]]
        rows.append(row)
        print(json.dumps({key:value for key,value in row.items() if key!='diff_offsets'}),flush=True)
    (out/(args.group+'-screens.json')).write_text(json.dumps(rows,indent=2)+'\n')


if __name__=='__main__':
    main()
