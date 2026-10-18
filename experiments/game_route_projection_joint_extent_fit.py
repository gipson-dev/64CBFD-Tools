"""Combine the retail split scan with the recovered common-phase node lifetime."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_projection_call_lifetime_fit as prior
from tools.experiments import game_route_projection_unrolled_fit as unrolled

BUILD='conker/build/game-route-projection-joint-extent-fit'
EXPECTED={
    'old-split-common-node':(321,120,220,'4c41fce9ef61cc9627b5ab9355835697c46afce7cf474b4a309735411f7dd629'),
    'old-split-common-node-ids':(318,120,269,'0eeff87bf5e9b533af71073fc43bbe68457fd453995c1c1600a42be81ea56841'),
    'typed-split-candidateNode':(320,120,291,'9d78413431ce9a0c366c9020cd0577582d83ca1eaba969575c56a35b9be0ee9f'),
    'typed-split-currentNode':(320,120,289,'e757c09106e76a5acf40ba8f6e6d0941f01c0714a86f656691e786da47591661'),
    'typed-split-ids-candidateNode':(320,120,291,'3999fa9390041615cfe87f473545d8bddb822264007e55629d48c42aae66153d'),
    'typed-split-ids-currentNode':(320,120,289,'e757c09106e76a5acf40ba8f6e6d0941f01c0714a86f656691e786da47591661'),
    'typed-loop-split-candidateNode':(317,112,283,'588aa191d10cd936043b6cf3d58aec29de40c441345e71eaa191537714388b9c'),
    'typed-loop-split-currentNode':(317,112,283,'2efa5e2819b6c2c1ce6208c0bbe147f742b87e5020c034ca1dcff0146e025354'),
}


def common_node(body):
    at=body.rindex('        current = record[0x4B];')
    head,tail=body[:at],body[at:]
    head=head.replace('    u8 *previousNode;','    u8 *candidateNode;')
    tail=re.sub(r'\bpreviousNode\b','node',tail)
    return head+tail


def split_scan(body,split=False,capture='candidateNode'):
    body=body.replace('    s32 j;','    u8 *cursor;')
    lo=body.index('                    for (j = 0; j < 5; j++) {')
    hi=body.index('                    i = D_80087290;',lo)
    blocks=[]
    for slot in range(5):
        if slot==1:blocks.append('                    cursor = (u8 *)node + 1;\n')
        candidate='next' if split and slot>=2 else 'candidate'
        location='node->neighbors[0]' if slot==0 else 'cursor[0x%X]'%(slot+8)
        blocks.append('                    '+candidate+' = '+location+';\n')
        blocks.append('                    if ('+candidate+' != 0xFF) {\n')
        blocks.append('                        i = D_800D23A8;\n')
        if slot>=2:
            blocks.append('                        '+capture+' = (ProjectionNode *)D_800D2350 + '+candidate+';\n')
            field=capture+'->routeClass'
        else:field='((ProjectionNode *)D_800D2350)['+candidate+'].routeClass'
        blocks.append('                        if ((i == 0 && '+field+' == 3) ||\n'+
            '                            (i != 0 && '+field+' != 3)) {\n'+
            '                            record[0x4B] = '+candidate+';\n'+
            '                        }\n                    }\n')
    return body[:lo]+''.join(blocks)+body[hi:]


def forms():
    yield 'old-split-common-node',common_node(unrolled.SELECTED)
    yield 'old-split-common-node-ids',prior.phase_ids(common_node(unrolled.SELECTED),'first','next')
    for split in (False,True):
        for capture in ('candidateNode','currentNode'):
            name='typed-split-'+('ids-' if split else '')+capture
            yield name,split_scan(prior.SELECTED,split,capture)
    for capture in ('candidateNode','currentNode'):
        body=prior.SELECTED.replace('                            candidateNode = (ProjectionNode *)D_800D2350 + candidate;',
            '                            if (j >= 2) {\n                                '+capture+' = (ProjectionNode *)D_800D2350 + candidate;\n                            }')
        field='(j < 2 ? ((ProjectionNode *)D_800D2350)[candidate].routeClass : '+capture+'->routeClass)'
        body=body.replace('candidateNode->routeClass',field)
        yield 'typed-loop-split-'+capture,body


def audit(root,out):
    values=prior.prior.freeze(root,out);rows=[]
    baseline,diagnostics=prior.prior.normal_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'normal-owner-before')
    if diagnostics:raise ValueError('Changed joint-extent owner baseline')
    truth=struct.unpack_from('>321I',values['conker/conker.us.bin'],prior.source.ROM)
    for name,body in forms():
        obj=out/(name+'.o');row=json.loads((out/(name+'.json')).read_text())
        expected=prior.source.recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
        if (out/(name+'.c')).read_text()!=expected.replace('\r\n','\n'):raise ValueError('Changed joint-extent C screen')
        text,functions,rel=prior.source.neighbor.parse_object(obj);f=functions[prior.source.FUNCTION]
        raw=text[f['value']:f['value']+f['size']]
        data=prior.prior.sections(out/(name+'.elf'))['.text'][1]
        words=list(struct.unpack_from('>%dI'%(len(raw)//4),data,f['value']))
        actual=(len(words),(-words[0])&65535,sum(a!=b for a,b in zip(words,truth))+abs(len(words)-321),hashlib.sha256(raw).hexdigest())
        bindings={str(at-f['value']):v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
        if actual!=EXPECTED[name] or tuple(row[k] for k in ('words','frame','differences','raw_sha256'))!=actual or \
                json.loads(json.dumps(bindings))!=row['bindings'] or row['diagnostics'] or (out/(name+'-diagnostics.txt')).read_text():
            raise ValueError('Changed joint-extent words/bindings/diagnostics')
        if prior.source.neighbor.same_functions(baseline,obj,(prior.source.FUNCTION,))!=72 or \
                prior.source.neighbor.normalized_pools(baseline)!=prior.source.neighbor.normalized_pools(obj):
            raise ValueError('Changed joint-extent neighbors/pools')
        row.update(name=name,neighbors=72,installable=False,matching_credit=0);rows.append(row)
    if len(rows)!=8:raise ValueError('Incomplete joint-extent screens')
    (out/'screen-audit.json').write_text(json.dumps(rows,indent=2)+'\n');return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--filter',default='')
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.audit:
        print(json.dumps(dict(rejected_screens=len(audit(root,out)),neighbors_each=72)));raise SystemExit(0)
    for name,body in forms():
        if args.filter not in name:continue
        _,_,row=prior.measure(root,out,name,body)
        print(json.dumps(dict(name=name,**{k:row[k] for k in ('words','frame','differences','raw_sha256','diagnostics')})),flush=True)
