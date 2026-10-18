"""Test a first-slot/four-slot projection scan without changing production."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.experiments import game_route_projection_unrolled_fit as unrolled
from tools.experiments.game_remaining_donor_candidates import compile_owner as normal_owner

source=unrolled.source
BUILD='conker/build/game-route-projection-grouped-fit'
EXPECTED={
    'counter-next':(327,120,308,'8e4eb2133ab40414def0a4532113ca81401dbd2aec1b183942a6ad41f5e11ffd'),
    'counter-current':(327,120,304,'66e5c12da305bf5b49738577acdc697e185a10cd744583b2e41558cdd5f243e2'),
    'counter-first':(325,112,309,'ce4dfb52bd311127f4fa1795c1c7f402d51f9ea9aa6049c413ff4a6f2c323d37'),
    'pointer-group':(325,120,303,'4bb0bc38a2d12f048f03f370bcb5170eaf5e372a57145a586ded73096e4bae2c'),
}


def forms():
    body=unrolled.SELECTED
    lo=body.index('                    cursor = node + 1;')
    hi=body.index('                    i = D_80087290;',lo)
    block=body[lo:hi].split('\n',1)[1]
    indented='\n'.join('    '+line for line in block.rstrip().splitlines())+'\n'
    for counter,word in (('next',False),('current',False),('first',True)):
        loop=('                    '+counter+' = 1;\n                    do {\n'+
            '                        cursor = node + '+counter+';\n'+indented+
            '                        '+counter+' += 4;\n                    } while ('+counter+' != 5);\n')
        b=body[:lo]+loop+body[hi:]
        if word:b=b.replace('    u8 '+counter+';','    s32 '+counter+';')
        yield 'counter-'+counter,b
    loop=('                    cursor = node + 1;\n                    do {\n'+indented+
        '                        cursor += 4;\n                    } while (cursor != node + 5);\n')
    yield 'pointer-group',body[:lo]+loop+body[hi:]


def measure(root,out,name,body,normal=False):
    return source.measure(root,out,name,body,normal)


def qualify(root,out):
    inputs=source.freeze(root,out);results=[]
    compilers=(source.neighbor.baseline.model.compile_owner,normal_owner)
    baselines=[]
    for normal,compile_owner in enumerate(compilers):
        obj,diagnostics=compile_owner(root,out,inputs['conker/src/game/generated_B3020.c'].decode(),'owner-before-'+str(normal))
        if diagnostics:raise ValueError('Changed grouped-scan baseline diagnostics')
        baselines.append(obj)
    for name,body in forms():
        pair=[]
        for normal in (False,True):
            obj,words,row=measure(root,out,('normal-' if normal else 'owner-')+name,body,normal)
            if row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['raw_sha256'])!=EXPECTED[name]:
                raise ValueError('Changed rejected grouped-scan shape')
            row['neighbors']=source.neighbor.same_functions(baselines[normal],obj,(source.FUNCTION,))
            if row['neighbors']!=72 or source.neighbor.normalized_pools(baselines[normal])!=source.neighbor.normalized_pools(obj):
                raise ValueError('Changed grouped-scan neighbors/pools')
            row.update(name=name,normal_profile=normal,installable=False)
            pair.append((words,row));results.append(row)
        if pair[0][0]!=pair[1][0] or pair[0][1]['bindings']!=pair[1][1]['bindings']:
            raise ValueError('Grouped-scan target changed between profiles')
    source.freeze(root,out)
    (out/'qualified-screens.json').write_text(json.dumps(results,indent=2)+'\n')
    return results


def audit(root,out):
    inputs=source.freeze(root,out);rows=json.loads((out/'qualified-screens.json').read_text())
    if len(rows)!=8:raise ValueError('Missing/duplicate grouped screens')
    expected_bodies=dict(forms())
    for index,row in enumerate(rows):
        name=list(expected_bodies)[index//2];normal=bool(index&1)
        if row['name']!=name or row['normal_profile']!=normal or row.get('installable') is not False:
            raise ValueError('Changed grouped screen identity')
        label=('normal-' if normal else 'owner-')+name;obj=out/(label+'.o')
        expected=source.recovered_owner(inputs['conker/src/game/generated_B3020.c'].decode(),expected_bodies[name])
        if (out/(label+'.c')).read_text()!=expected.replace('\r\n','\n'):
            raise ValueError('Changed complete grouped source')
        text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
        raw=text[f['value']:f['value']+f['size']]
        bindings={str(at-f['value']):v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
        if (len(raw)//4,(-int.from_bytes(raw[:4],'big'))&65535,row['differences'],hashlib.sha256(raw).hexdigest())!=EXPECTED[name] or \
                (row['words'],row['frame'],row['differences'],row['raw_sha256'])!=EXPECTED[name] or \
                json.loads(json.dumps(bindings))!=row['bindings'] or (out/(label+'-diagnostics.txt')).read_text():
            raise ValueError('Changed grouped object/bindings/diagnostics')
        before=out/('owner-before-'+str(int(normal))+'.o')
        if source.neighbor.same_functions(before,obj,(source.FUNCTION,))!=72 or \
                source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
            raise ValueError('Changed grouped neighbors/pools')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal',action='store_true');parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD;rows=[]
    if args.qualify or args.audit:
        results=audit(root,out) if args.audit else qualify(root,out)
        print(json.dumps(dict(screens=len(results),all_rejected=True,neighbors_per_screen=72)));raise SystemExit(0)
    for name,body in forms():
        label=('normal-' if args.normal else 'owner-')+name
        _,_,row=measure(root,out,label,body,args.normal);row['name']=label;rows.append(row)
        print(json.dumps({k:row[k] for k in ('name','words','frame','differences','saved','diagnostics')}),flush=True)
    (out/('screens-normal.json' if args.normal else 'screens-owner.json')).write_text(json.dumps(rows,indent=2)+'\n')
