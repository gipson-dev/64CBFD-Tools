"""Discriminate node-address source expressions without production installation."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.experiments import game_route_projection_unrolled_fit as prior

source=prior.source
BUILD='conker/build/game-route-projection-node-expression-fit'
EXPECTED={
    'typed-unrolled':(320,120,289,'4e3f0155aaaac3b6c02d42d43d57ac34986e756d50e287063fa9a7b32b42db08'),
    'typed-loop':(250,128,321,'f96edfd5ce7d807cd837c64e7b5ac8c2cd93a86b3ed5b63c87007d58e5b97bd1'),
    'array-address':(320,120,290,'83c3511fdeead643872096e0a1ef6c710721b191c6a5446e5582ec316e97da09'),
    'shift-address':(320,120,288,'ce72ab08658eb963615f768436ee0877d520f4d09144a237dd1fb9fdfc775bfe'),
}
NODE='''    typedef struct {
        s16 x, y, z;
        u8 reserved[3];
        u8 neighbors[5];
        u8 kind;
        u8 routeClass;
    } ProjectionNode;
'''


def typed(body):
    body=body.replace('    u8 first;',NODE+'    u8 first;')
    for name in ('node','previousNode','currentNode'):
        body=body.replace('    u8 *'+name+';','    ProjectionNode *'+name+';')
        for offset,field in ((0,'x'),(2,'y'),(4,'z')):
            body=body.replace('*(s16 *)('+name+' + '+str(offset)+')',name+'->'+field)
    body=re.sub(r'D_800D2350 \+ (i|current|previous|candidate) \* 0x10',r'(ProjectionNode *)D_800D2350 + \1',body)
    body=body.replace('node[0xE]','node->kind').replace('node[0xF]','node->routeClass')
    body=body.replace('currentNode[0xF]','currentNode->routeClass')
    body=body.replace('node[9]','node->neighbors[0]').replace('node[j + 9]','node->neighbors[j]')
    body=body.replace('cursor = node + 1;','cursor = (u8 *)node + 1;')
    body=body.replace('D_800D2350[candidate * 0x10 + 0xF]',
        '((ProjectionNode *)D_800D2350)[candidate].routeClass')
    return body


def forms():
    body=prior.SELECTED
    yield 'typed-unrolled',typed(body)
    loop=dict(prior.loop_forms())['loop-assigned']
    yield 'typed-loop',typed(loop)
    yield 'array-address',re.sub(r'D_800D2350 \+ (i|current|previous|candidate) \* 0x10',
        r'&((u8 (*)[16])D_800D2350)[\1][0]',body)
    yield 'shift-address',re.sub(r'(i|current|previous|candidate) \* 0x10',r'((u32)\1 << 4)',body)


def screen(root,out):
    results=[]
    for name,body in forms():
        obj,words,row=source.measure(root,out,name,body)
        row.update(name=name,installable=False)
        results.append(row)
        print(json.dumps({k:row[k] for k in ('name','words','frame','differences','raw_sha256','diagnostics')}),flush=True)
    (out/'screens.json').write_text(json.dumps(results,indent=2)+'\n')
    return results


def qualify(root,out):
    values=source.freeze(root,out)
    before,diagnostics=source.neighbor.baseline.model.compile_owner(root,out,
        values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    if diagnostics:raise ValueError('Changed node-expression owner diagnostics')
    results=screen(root,out)
    for row in results:
        name=row['name'];obj=out/(name+'.o')
        if row['diagnostics'] or tuple(row[k] for k in ('words','frame','differences','raw_sha256'))!=EXPECTED[name]:
            raise ValueError('Changed rejected node-expression shape')
        row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
        if row['neighbors']!=72 or source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
            raise ValueError('Changed node-expression neighbors/pools')
    (out/'qualified-screens.json').write_text(json.dumps(results,indent=2)+'\n')
    return results


def audit(root,out):
    values=source.freeze(root,out);rows=json.loads((out/'qualified-screens.json').read_text())
    if [r['name'] for r in rows]!=list(EXPECTED):raise ValueError('Changed node-expression screen identities')
    for row,(name,body) in zip(rows,forms()):
        expected=source.recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
        if (out/(name+'.c')).read_text()!=expected.replace('\r\n','\n'):
            raise ValueError('Changed complete node-expression source')
        obj=out/(name+'.o');text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
        raw=text[f['value']:f['value']+f['size']]
        bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
        if (len(raw)//4,(-int.from_bytes(raw[:4],'big'))&65535,row['differences'],hashlib.sha256(raw).hexdigest())!=EXPECTED[name] or \
                tuple(row[k] for k in ('words','frame','differences','raw_sha256'))!=EXPECTED[name] or \
                json.loads(json.dumps(bindings))!=row['bindings'] or row.get('installable') is not False or \
                (out/(name+'-diagnostics.txt')).read_text():raise ValueError('Changed node-expression object/bindings')
        before=out/'owner-before.o'
        if source.neighbor.same_functions(before,obj,(source.FUNCTION,))!=72 or \
                source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
            raise ValueError('Changed node-expression owner evidence')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.audit:print(json.dumps(dict(rejected_screens=len(audit(root,root/BUILD)))))
    elif args.qualify:qualify(root,root/BUILD)
    else:screen(root,root/BUILD)
