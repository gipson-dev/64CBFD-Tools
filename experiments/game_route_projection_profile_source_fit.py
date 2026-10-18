"""Test original-loop source/profile discriminators on the post-enqueue baseline."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_route_projection_node_expression_fit as nodes
from tools.experiments import game_object_command_enqueue as enqueue
from tools.experiments.game_remaining_donor_candidates import compile_owner as normal_owner
from tools.experiments.game_remaining_donor_candidates import sections
from tools.experiments import game_text_measurer_uopt_trace as allocation
from tools.experiments.game_route_projection_allocation_trace import PREFIX,lifecycle

source=nodes.source
BUILD='conker/build/game-route-projection-profile-source-fit'
INPUTS=dict(source.INPUTS,**enqueue.AFTER)
RAW_SHA='2d403412cfbd435b66ce562202bc048e70177ba4d5840386163f7b99897ef9d6'
BINDINGS={
    44:[('R_MIPS_HI16','D_8008FDBC')],56:[('R_MIPS_LO16','D_8008FDBC')],
    60:[('R_MIPS_HI16','D_80087290')],76:[('R_MIPS_LO16','D_80087290')],
    116:[('R_MIPS_HI16','D_800D2350')],120:[('R_MIPS_LO16','D_800D2350')],
    132:[('R_MIPS_HI16','D_800D23A8')],136:[('R_MIPS_LO16','D_800D23A8')],
    660:[('R_MIPS_HI16','D_800D2350')],668:[('R_MIPS_LO16','D_800D2350')],
    664:[('R_MIPS_HI16','D_8009DA08')],676:[('R_MIPS_LO16','D_8009DA08')],
    716:[('R_MIPS_26','func_1508907C')],836:[('R_MIPS_26','func_1512D560')],
    852:[('R_MIPS_HI16','D_800D2350')],860:[('R_MIPS_LO16','D_800D2350')],
    1028:[('R_MIPS_26','func_1508907C')],1264:[('R_MIPS_26','func_1512D560')],
}
EXPECTED={
    'typed-loop':(334,120,310,RAW_SHA),
    'separated-loop':(334,120,310,RAW_SHA),
    'assigned-address':(334,120,310,RAW_SHA),
    'separated-address':(334,120,310,RAW_SHA),
    'word-candidate':(332,128,295,'1b702ce41dc098032c67feec87859eec723d97e0bac7b57323a16739ab66cdca'),
    'byte-class':(295,120,297,'ab75fa0f387eefdb5f6112ef628362369084c0c3c0239e9462bc30da31f8ba4a'),
    'byte-neighbor':(334,120,310,RAW_SHA),
    'byte-fields':(295,120,297,'ab75fa0f387eefdb5f6112ef628362369084c0c3c0239e9462bc30da31f8ba4a'),
    'byte-address':(296,120,297,'409035783ec82ed0d0fb9a06ab0c2787b96b84ed673acfa8e1e810d3f8be4351'),
    'peeled-typed':(332,120,302,'4c2a271a2db4d999532ac63b68a6b3f9bba37f1f528a16ba358706921d1657b4'),
    'peeled-byte-first':(332,120,302,'02eeb4b0211c4f8a9ac52e1d7f1e212f072762bfa9018ea507e9742aeee33722'),
    'peeled-byte-tail':(294,120,295,'e0881e82fd9957ec6f8ce92981282b85c244cea491c59340012d774704beb80c'),
    'common-byte-current':(334,120,310,'4663882bb191054de57f8099a1eb4068e8ce8f3cc1b9cd2ca529484ce8727685'),
    'common-byte-both':(334,120,310,'88275f32742c7afe82f15c260921d8c42e5927be2b665ee5fd4a98b8f2d4bd92'),
    'phase-ids':(332,128,311,'44926ad8501ec2b04302fb2aa9ce281adeea53ae814b3cecc6c12772a9afe722'),
    'scope-ids':(332,128,311,'8f73b826f90aaf993145fb01017a4991eea998b8c57e87f1466d35b11ccff510'),
}


@contextmanager
def current_inputs():
    with patch.object(source,'INPUTS',INPUTS):yield


def measure(root,out,name,body,normal=True):
    with current_inputs():return source.measure(root,out,name,body,normal)


def freeze(root,out):
    with current_inputs():return source.freeze(root,out)


def forms():
    body=dict(nodes.forms())['typed-loop']
    yield 'typed-loop',body
    separated=body.replace('                        if ((candidate = node->neighbors[j]) != 0xFF)',
        '                        candidate = node->neighbors[j];\n                        if (candidate != 0xFF)')
    if separated==body:raise ValueError('Missing typed-loop assignment boundary')
    yield 'separated-loop',separated
    for name,base in (('assigned-address',body),('separated-address',separated)):
        b=base.replace('                            i = D_800D23A8;',
            '                            i = D_800D23A8;\n                            currentNode = (ProjectionNode *)D_800D2350 + candidate;')
        b=b.replace('((ProjectionNode *)D_800D2350)[candidate].routeClass','currentNode->routeClass')
        yield name,b
    yield 'word-candidate',body.replace('    u8 candidate;','    s32 candidate;')
    field=body.replace('((ProjectionNode *)D_800D2350)[candidate].routeClass',
        'D_800D2350[candidate * 0x10 + 0xF]')
    neighbor=body.replace('node->neighbors[j]','((u8 *)node)[j + 9]')
    yield 'byte-class',field
    yield 'byte-neighbor',neighbor
    both=field.replace('node->neighbors[j]','((u8 *)node)[j + 9]')
    yield 'byte-fields',both
    yield 'byte-address',re.sub(r'\(ProjectionNode \*\)D_800D2350 \+ (i|current|previous|candidate)',
        r'(ProjectionNode *)(D_800D2350 + \1 * 0x10)',both)
    lo=separated.index('                    for (j = 0; j < 5; j++) {')
    hi=separated.index('                    i = D_80087290;',lo)
    loop=separated[lo:hi]
    inner=loop.split('\n',1)[1].rsplit('                    }\n',1)[0]
    first='\n'.join(line[4:] for line in inner.rstrip().splitlines())+'\n'
    first=first.replace('neighbors[j]','neighbors[0]')
    tail=loop.replace('j = 0','j = 1')
    yield 'peeled-typed',separated[:lo]+first+tail+separated[hi:]
    def byte_class(text):
        return text.replace('((ProjectionNode *)D_800D2350)[candidate].routeClass',
            'D_800D2350[candidate * 0x10 + 0xF]')
    yield 'peeled-byte-first',separated[:lo]+byte_class(first)+tail+separated[hi:]
    yield 'peeled-byte-tail',separated[:lo]+first+byte_class(tail)+separated[hi:]
    for names in (('currentNode',),('currentNode','previousNode')):
        b=body
        for name in names:
            b=b.replace('    ProjectionNode *'+name+';','    u8 *'+name+';')
            for offset,field_name in ((0,'x'),(2,'y'),(4,'z')):
                b=b.replace(name+'->'+field_name,'*(s16 *)('+name+' + '+str(offset)+')')
            index='current' if name=='currentNode' else 'previous'
            b=b.replace(name+' = (ProjectionNode *)D_800D2350 + '+index+';',
                name+' = D_800D2350 + '+index+' * 0x10;')
        if len(names)==1:b=b.replace('previousNode = currentNode;','previousNode = (ProjectionNode *)currentNode;')
        yield 'common-byte-'+('current' if len(names)==1 else 'both'),b
    at=body.rindex('        current = record[0x4B];')
    tail=body[at:]
    for old,new in (('current','selectedID'),('previous','oldID')):
        tail=re.sub(r'\b'+old+r'\b',new,tail)
    yield 'phase-ids',(body[:at]+tail).replace('    f32 targetZ;',
        '    f32 targetZ;\n    u8 selectedID;\n    u8 oldID;')
    end=body.rindex('    }')
    common=''.join('    '+line+'\n' for line in body[at:end].rstrip().splitlines())
    yield 'scope-ids',body[:at]+'        {\n            u8 current;\n            u8 previous;\n'+common+'        }\n'+body[end:]


SELECTED=dict(forms())['typed-loop']


def checked(obj):
    text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1336 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown normal-profile projection body or bindings')
    words=list(struct.unpack('>334I',raw))
    if words[:10]!=[0x27BDFF88,0xAFB50028,0xAFB2001C,0x00809025,0x00A0A825,
            0xAFBF002C,0xAFB40024,0xAFB30020,0xAFB10018,0xAFB00014] or \
            words[29]!=0x3C100000 or words[30]!=0x26100000 or words[164]!=0x9253004B or words[168]!=0x9254004A:
        raise ValueError('Lost normal-profile opening saved-role contract')
    return raw,bindings


def audit_screens(root,out):
    values=freeze(root,out);rows=[];truth=list(struct.unpack_from('>321I',values['conker/conker.us.bin'],source.ROM))
    for name,body in forms():
        label='normal-'+name;obj=out/(label+'.o');row=json.loads((out/(label+'.json')).read_text())
        expected=source.recovered_owner(values['conker/src/game/generated_B3020.c'].decode(),body)
        if (out/(label+'.c')).read_text()!=expected.replace('\r\n','\n'):
            raise ValueError('Changed complete profile-screen source: '+name)
        text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
        raw=text[f['value']:f['value']+f['size']];words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
        data=sections(out/(label+'.elf'))['.text'][1]
        linked=list(struct.unpack_from('>%dI'%len(words),data,f['value']))
        actual=(len(words),(-words[0])&65535,sum(a!=b for a,b in zip(linked,truth))+abs(len(words)-321),hashlib.sha256(raw).hexdigest())
        bindings={str(a-f['value']):v for a,v in rel.items() if f['value']<=a<f['value']+f['size']}
        if actual!=EXPECTED[name] or tuple(row[k] for k in ('words','frame','differences','raw_sha256'))!=actual or \
                json.loads(json.dumps(bindings))!=row['bindings'] or row['diagnostics'] or (out/(label+'-diagnostics.txt')).read_text():
            raise ValueError('Changed profile-screen shape/bindings/diagnostics: '+name)
        before=out/'normal-owner-before.o'
        row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
        if row['neighbors']!=72 or source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
            raise ValueError('Changed normal-profile neighbors/pools')
        row.update(name=name,installable=False,matching_credit=0,normal_profile=True);rows.append(row)
    if len(rows)!=16:raise ValueError('Incomplete profile/source screen set')
    (out/'screen-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


def qualify(root,out):
    values=freeze(root,out);before,diagnostics=normal_owner(root,out,
        values['conker/src/game/generated_B3020.c'].decode(),'normal-owner-before')
    if diagnostics:raise ValueError('Changed normal-profile owner diagnostics')
    obj,words,row=measure(root,out,'qualified-normal',SELECTED);checked(obj)
    row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
    if row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(334,120,310,72) or \
            source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
        raise ValueError('Changed normal-profile projection evidence')
    twin,twin_words,twin_row=measure(root,out,'existing-profile',SELECTED,False)
    if twin_row['diagnostics'] or (twin_row['words'],twin_row['frame'],twin_row['differences'],twin_row['raw_sha256'])!=(250,128,321,nodes.EXPECTED['typed-loop'][3]):
        raise ValueError('Changed existing-profile source discriminator')
    row.update(installable=False,matching_credit=0,production_profile_unchanged=True,
        existing_profile=dict(words=250,frame=128,differences=321,raw_sha256=twin_row['raw_sha256']))
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def allocation_facts(text):
    first='IN LOCAL OPTIMIZATION OF '+source.FUNCTION;last='IN REEMISSION OF '+source.FUNCTION
    if text.count(first)!=1 or text.count(last)!=1:raise ValueError('Missing/duplicate normal projection procedure')
    block=text[text.index(first):text.index(last)+len(last)]
    variables=allocation.variable_expressions(block);constraints=allocation.allocation_constraints(block)
    indexed={r['expression']:r for r in constraints}
    if len(variables)!=24 or len(indexed)!=len(constraints) or len(constraints)!=45:
        raise ValueError('Changed normal projection variable/constraint scope')
    names={-8:'anchor_node',-12:'previous_node',-48:'current_node',-50:'current_id',-51:'previous_id',-60:'entry_object'}
    expected={-8:(27,'1547|0',15),-12:(138,'1483|0',2),-48:(135,'907|1',15),
        -50:(78,'875|1',17),-51:(82,'859|0',18),-60:(15,'715|0',-1)}
    roles={}
    for offset,name in names.items():
        matches=[v for v in variables if (v['storage'],v['offset'])==('M',offset)]
        if len(matches)!=1 or matches[0]['expression'] not in indexed:
            raise ValueError('Missing normal projection local: '+name)
        var=matches[0];row=indexed[var['expression']]
        if var['procedure']!=749 or var['identity']!=row['identity'] or \
                (var['expression'],row['identity'],row['color'])!=expected[offset]:
            raise ValueError('Normal projection variable/live-range disagreement')
        roles[name]=dict(offset=offset,expression=var['expression'],identity=row['identity'],color=row['color'])
    for offset,name,expression,identity,color in ((0,'record',18,'1080|0',16),(4,'actor',2,'1144|0',19)):
        matches=[v for v in variables if (v['storage'],v['procedure'],v['offset'],v['expression'],v['identity'])==('P',749,offset,expression,identity)]
        row=indexed[expression]
        if len(matches)!=1 or (row['identity'],row['color'])!=(identity,color):raise ValueError('Changed normal projection parameter allocation')
        roles[name]=dict(offset=offset,expression=expression,identity=identity,color=color)
    if (indexed[286]['identity'],indexed[286]['color'])!=('1493|0',14):raise ValueError('Changed normal projection table-address allocation')
    roles['table_address']=dict(expression=286,identity='1493|0',color=14)
    critical={2,18,27,78,82,286}
    if any(not critical-{key}<=set(indexed[key]['interference']) for key in critical):
        raise ValueError('Changed normal projection saved-role interference')
    return block,dict(variables=variables,constraints=constraints,roles=roles)


def observe(root,out):
    freeze(root,out);work=out/'normal-mode-5'
    if (work/'trace.json').exists():raise ValueError('Retained normal compiler capture exists; audit it instead')
    content=PREFIX+SELECTED
    def compile_baseline(root,work,name,actual):
        if actual!=content:raise ValueError('Changed normal diagnostic source')
        obj,diagnostics=normal_owner(root,work,actual,name);checked(obj)
        if diagnostics or set(source.neighbor.parse_object(obj)[1])!={source.FUNCTION}:
            raise ValueError('Changed isolated normal projection scope/diagnostics')
        return dict(function=source.FUNCTION,raw_sha256=RAW_SHA,words=334,diagnostics=diagnostics),None
    adapter=SimpleNamespace(compile_candidate=compile_baseline,PROFILES={'owner':('-O2','-g3')},
        compiler=SimpleNamespace(parse_object=source.neighbor.parse_object,sections=sections))
    with patch.object(allocation,'screen',adapter):allocation.trace_uopt(root,out,'normal-mode-5',content,5)
    return audit_observation(root,out)


def audit_observation(root,out):
    freeze(root,out);work=out/'normal-mode-5';record=json.loads((work/'trace.json').read_text())
    log=(work/'debugger.txt').read_text();payload=(work/'uoptlist').read_bytes()
    if allocation.compiler_fingerprints(root)!=allocation.COMPILERS or record.get('compiler_sha256')!=allocation.COMPILERS or \
            record.get('exit_code')!=0 or record.get('code_unchanged') is not True:
        raise ValueError('Incomplete/changed normal compiler capture')
    if (work/'baseline.c').read_text()!=PREFIX+SELECTED or \
            hashlib.sha256((work/'baseline.c').read_bytes()).hexdigest()!=record.get('source_sha256') or \
            hashlib.sha256(payload).hexdigest()!=record.get('trace_sha256') or len(payload)!=record.get('bytes'):
        raise ValueError('Changed normal compiler source/listing')
    if log.splitlines().count('Allocate diagnostic stream buffer')!=1 or 'Suppress diagnostic real-number printer' not in log or \
            'Python Exception' in log or 'Error in sourced command' in log:
        raise ValueError('Normal compiler diagnostic probe missing/failed')
    ended=lifecycle(root.resolve(),log);before,after=work/'baseline.o',work/'trace.o';checked(before);checked(after)
    if source.neighbor.parse_object(before)!=source.neighbor.parse_object(after):
        raise ValueError('Normal compiler observation changed text/functions/bindings')
    a,b=sections(before),sections(after)
    if any(a.get(k)!=b.get(k) for k in a.keys()|b.keys() if k.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))):
        raise ValueError('Normal compiler observation changed pools')
    block,facts=allocation_facts(payload.decode())
    row=dict(lifecycle=ended,**facts,raw_sha256=RAW_SHA,target_sha256=hashlib.sha256(block.encode()).hexdigest(),
        debugger_sha256=hashlib.sha256(log.encode()).hexdigest(),suppressed_real_costs_not_interpreted=True,
        installable=False,reused_completed_capture=True)
    (work/'audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--filter',default='typed-loop')
    parser.add_argument('--qualify',action='store_true');parser.add_argument('--audit',action='store_true')
    parser.add_argument('--observe',action='store_true');parser.add_argument('--audit-observation',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.observe or args.audit_observation:
        result=observe(root,out) if args.observe else audit_observation(root,out)
        print(json.dumps({k:v for k,v in result.items() if k not in ('variables','constraints')},indent=2));raise SystemExit(0)
    if args.qualify or args.audit:
        print(json.dumps(dict(rejected_screens=len(audit_screens(root,out))) if args.audit else qualify(root,out)[2],indent=2))
        raise SystemExit(0)
    for name,body in forms():
        if args.filter not in name:continue
        _,_,row=measure(root,out,'normal-'+name,body)
        print(json.dumps(dict(name=name,**{k:row[k] for k in ('words','frame','differences','raw_sha256','diagnostics')})),flush=True)
