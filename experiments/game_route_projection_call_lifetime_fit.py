"""Recover selected-node call lifetime with existing semantic node/ID carriers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.experiments import game_route_projection_profile_source_fit as prior

source=prior.source
INPUTS=prior.INPUTS
BUILD='conker/build/game-route-projection-call-lifetime-fit'
EXPECTED={
    'node-lifetime':(335,120,311,'3489534941741d693be663d176f5a0317142535fc75abd62513d10721befb305'),
    'first-next':(332,120,308,'f6d642eebc322dffb62d59710eef588cb9995ff23ac5d2467095d1741fb6336f'),
    'candidate-next':(332,120,308,'bbfdc656951caeaa4cabb1541d24e442ed8f4968ed454e4ec329dbe3af015997'),
    'node-first-next':(332,120,308,'e5621efda3c7e361133cf75a9044a98381c0172a132f23b388bcf0044ae63e9f'),
    'typed-table-loop':(334,120,311,'3da1e04e27d6ce0cb5dc181cb9ba121a6a75fdedebc5330dbad8b8b2a03a4e92'),
    'typed-table-node':(335,120,312,'18a01dd8d8f8e172af3ea3b74ceb928d7e4d8f49db30944ecf947484ea31f49c'),
    'two-slot-prefix':(282,120,297,'6e49730ba50dc394a16a7687b57a7ff287c32b9a3cf9a7e5de7fa1e67c20b078'),
    'two-slot-prefix-inline':(290,120,301,'09d3507bef6d9a68ae0de9657302006dabb7558f57dc98af0ed10d15f10515f1'),
    'unsigned-counter':(335,120,311,'3489534941741d693be663d176f5a0317142535fc75abd62513d10721befb305'),
    'unequal-bound':(335,120,311,'3489534941741d693be663d176f5a0317142535fc75abd62513d10721befb305'),
}


def phase_ids(body,current,previous):
    at=body.rindex('        current = record[0x4B];')
    tail=body[at:]
    for old,new in (('current',current),('previous',previous)):
        tail=re.sub(r'\b'+old+r'\b',new,tail)
    return body[:at]+tail


def node_lifetime(body):
    at=body.rindex('        current = record[0x4B];')
    head,tail=body[:at],body[at:]
    head=head.replace('ProjectionNode *previousNode;','ProjectionNode *candidateNode;')
    head=head.replace('                            i = D_800D23A8;',
        '                            i = D_800D23A8;\n                            candidateNode = (ProjectionNode *)D_800D2350 + candidate;')
    head=head.replace('((ProjectionNode *)D_800D2350)[candidate].routeClass','candidateNode->routeClass')
    tail=re.sub(r'\bpreviousNode\b','node',tail)
    return head+tail


def forms():
    body=prior.SELECTED
    yield 'node-lifetime',node_lifetime(body)
    yield 'first-next',phase_ids(body,'first','next')
    yield 'candidate-next',phase_ids(body,'candidate','next')
    yield 'node-first-next',phase_ids(node_lifetime(body),'first','next')


def prefix_forms():
    body=node_lifetime(prior.SELECTED)
    body=body.replace('                        if ((candidate = node->neighbors[j]) != 0xFF)',
        '                        candidate = node->neighbors[j];\n                        if (candidate != 0xFF)')
    lo=body.index('                    for (j = 0; j < 5; j++) {')
    hi=body.index('                    i = D_80087290;',lo)
    loop=body[lo:hi];inner=loop.split('\n',1)[1].rsplit('                    }\n',1)[0]
    single='\n'.join(line[4:] for line in inner.rstrip().splitlines())+'\n'
    prefix=''.join(single.replace('neighbors[j]','neighbors[%d]'%i) for i in range(2))
    tail=loop.replace('j = 0','j = 2')
    yield 'two-slot-prefix',body[:lo]+prefix+tail+body[hi:]
    prefix=prefix.replace('                        candidateNode = (ProjectionNode *)D_800D2350 + candidate;\n','')
    prefix=prefix.replace('candidateNode->routeClass','((ProjectionNode *)D_800D2350)[candidate].routeClass')
    yield 'two-slot-prefix-inline',body[:lo]+prefix+tail+body[hi:]


def counter_forms():
    body=node_lifetime(prior.SELECTED)
    yield 'unsigned-counter',body.replace('    s32 j;','    u32 j;')
    yield 'unequal-bound',body.replace('j < 5','j != 5')


SELECTED=node_lifetime(prior.SELECTED)
RAW_SHA='3489534941741d693be663d176f5a0317142535fc75abd62513d10721befb305'
BINDINGS=dict(prior.BINDINGS)
BINDINGS[1032]=BINDINGS.pop(1028);BINDINGS[1268]=BINDINGS.pop(1264)


def checked(obj):
    text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1340 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown node call-lifetime body or bindings')
    words=list(struct.unpack('>335I',raw))
    if words[:10]!=[0x27BDFF88,0xAFB50028,0xAFB2001C,0x00809025,0x00A0A825,
            0xAFBF002C,0xAFB40024,0xAFB30020,0xAFB10018,0xAFB00014] or \
            (words[29],words[30],words[164],words[168],words[257],words[260])!=(
                0x3C100000,0x26100000,0x9253004B,0x9254004A,0xAFA30048,0x8FB10048):
        raise ValueError('Lost joint saved-role/selected-node spill contract')
    return raw,bindings


def measure(root,out,name,body):
    return prior.measure(root,out,name,body,True)


def typed_source(body):
    definition='\n'.join(line[4:] for line in prior.nodes.NODE.rstrip().splitlines())+'\n'
    prefix=prior.PREFIX.replace('extern u8 *D_800D2350;',definition+'extern ProjectionNode *D_800D2350;')
    body=body.replace(prior.nodes.NODE,'').replace('(ProjectionNode *)D_800D2350','D_800D2350')
    return prefix+body


def typed_table(root,out,name,body):
    prior.freeze(root,out)
    obj,diagnostics=prior.normal_owner(root,out,typed_source(body),name)
    data,functions=source.neighbor.baseline.model.link_owner(root,out,obj,source.OWNER);f=functions[source.FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION];raw=text[f['value']:f['value']+f['size']]
    truth=struct.unpack_from('>321I',(root/'conker/conker.us.bin').read_bytes(),source.ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-321),
        raw_sha256=hashlib.sha256(raw).hexdigest(),diagnostics=diagnostics,
        bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def qualify(root,out):
    values=prior.freeze(root,out)
    before,diagnostics=prior.normal_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'normal-owner-before')
    obj,words,row=measure(root,out,'qualified',SELECTED);checked(obj)
    row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(335,120,311,72) or \
            source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
        raise ValueError('Changed joint call-lifetime owner/shape/pools')
    row.update(installable=False,matching_credit=0,production_profile_unchanged=True)
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def all_screens():
    for name,body in (*forms(),*prefix_forms(),*counter_forms()):yield name,body,False
    yield 'typed-table-loop',prior.SELECTED,True
    yield 'typed-table-node',SELECTED,True


def audit_screens(root,out):
    values=prior.freeze(root,out);rows=[]
    truth=struct.unpack_from('>321I',values['conker/conker.us.bin'],source.ROM)
    for name,body,isolated in all_screens():
        row=json.loads((out/(name+'.json')).read_text());obj=out/(name+'.o')
        expected=typed_source(body) if isolated else source.recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
        if (out/(name+'.c')).read_text()!=expected.replace('\r\n','\n'):raise ValueError('Changed lifetime screen source')
        text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
        raw=text[f['value']:f['value']+f['size']]
        data=prior.sections(out/(name+'.elf'))['.text'][1]
        words=list(struct.unpack_from('>%dI'%(len(raw)//4),data,f['value']))
        actual=(len(words),(-words[0])&65535,sum(a!=b for a,b in zip(words,truth))+abs(len(words)-321),hashlib.sha256(raw).hexdigest())
        bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
        if actual!=EXPECTED[name] or tuple(row[k] for k in ('words','frame','differences','raw_sha256'))!=actual or \
                json.loads(json.dumps(bindings))!=row['bindings'] or row['diagnostics'] or (out/(name+'-diagnostics.txt')).read_text():
            raise ValueError('Changed lifetime screen words/bindings/diagnostics')
        if isolated:
            if set(functions)!={source.FUNCTION}:raise ValueError('Isolated typed-table scope expanded')
        else:
            before=out/'normal-owner-before.o';row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
            if row['neighbors']!=72 or source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
                raise ValueError('Changed call-lifetime screen neighbors/pools')
        row.update(name=name,isolated=isolated,installable=False,matching_credit=0);rows.append(row)
    if {r['name'] for r in rows}!=set(EXPECTED):raise ValueError('Incomplete lifetime screens')
    (out/'screen-audit.json').write_text(json.dumps(rows,indent=2)+'\n');return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--typed-table',action='store_true')
    parser.add_argument('--prefixes',action='store_true');parser.add_argument('--counters',action='store_true')
    parser.add_argument('--qualify',action='store_true');parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.qualify or args.audit:
        print(json.dumps(dict(rejected_screens=len(audit_screens(root,out))) if args.audit else qualify(root,out)[2],indent=2))
        raise SystemExit(0)
    for name,body in ((('typed-table-loop',prior.SELECTED),('typed-table-node',node_lifetime(prior.SELECTED))) if args.typed_table else counter_forms() if args.counters else prefix_forms() if args.prefixes else forms()):
        _,_,row=(typed_table if args.typed_table else measure)(root,out,name,body)
        print(json.dumps(dict(name=name,**{k:row[k] for k in ('words','frame','differences','raw_sha256','diagnostics')})),flush=True)
