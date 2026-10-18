"""Recover the fixed five-neighbor projection scan in the existing owner profile."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.experiments import game_route_projection_lifetime_fit as lifetime

source=lifetime.source
BUILD='conker/build/game-route-projection-unrolled-fit'


def unrolled_body(word=False,separate=False):
    body=lifetime.SELECTED.replace('    s32 j;','    u8 *cursor;')
    if word:body=body.replace('    u8 candidate;','    s32 candidate;')
    lo=body.index('                    for (j = 0; j < 5; j++) {')
    hi=body.index('                    i = D_80087290;',lo)
    blocks=[]
    for slot in range(5):
        if slot==1:blocks.append('                    cursor = node + 1;\n')
        candidate='next' if separate and slot>=2 else 'candidate'
        location='node[9]' if slot==0 else 'cursor[0x%X]'%(slot+8)
        blocks.append('                    '+candidate+' = '+location+';\n')
        blocks.append('                    if ('+candidate+' != 0xFF) {\n')
        blocks.append('                        i = D_800D23A8;\n')
        if slot>=2:
            blocks.append('                        currentNode = D_800D2350 + '+candidate+' * 0x10;\n')
            field='currentNode[0xF]'
        else:field='D_800D2350['+candidate+' * 0x10 + 0xF]'
        blocks.append('                        if ((i == 0 && '+field+' == 3) ||\n'+
            '                            (i != 0 && '+field+' != 3)) {\n'+
            '                            record[0x4B] = '+candidate+';\n'+
            '                        }\n                    }\n')
    return body[:lo]+''.join(blocks)+body[hi:]


def forms():
    for word,separate in ((False,False),(False,True),(True,False),(True,True)):
        yield ('word' if word else 'byte')+('-split' if separate else '-shared'),unrolled_body(word,separate)


def snapshot_forms():
    body=unrolled_body().replace('    u8 preferred;','    volatile u8 preferred;')
    yield 'snapshot',body
    at=body.rindex('        current = record[0x4B];')
    body=body[:at]+re.sub(r'\bdistance\b','best',body[at:])
    yield 'snapshot-distance',body
    # Separate the common-phase byte IDs from the initialization loop's saved IDs.
    head,tail=body[:at],body[at:]
    for old,new in (('current','selectedID'),('previous','oldID')):
        tail=re.sub(r'\b'+old+r'\b',new,tail)
    body=(head+tail).replace('    u8 first;','    u8 first;\n    u8 selectedID;\n    u8 oldID;')
    yield 'snapshot-distance-ids',body


def home_forms():
    body=dict(snapshot_forms())['snapshot-distance']
    lo=body.index('    u8 *node;');hi=body.index('\n\n',lo)
    declarations={re.search(r'(\w+);$',line)[1]:line for line in body[lo:hi].splitlines()}
    order=('first','next','node','previousNode','payload','i','cursor','currentDistance',
        'dx','dz','best','dy','currentNode','candidate','current','previous','preferred','distance','object','targetZ')
    if set(order)!=set(declarations):raise ValueError('Unknown projection declarations')
    for registers in ((),('first','next'),('first','next','candidate'),('candidate','current','previous','first','next')):
        lines=[]
        for name in order:
            line=declarations[name]
            if name in registers:line=line.replace('    u8 ','    register u8 ')
            lines.append(line)
        yield 'homes-'+('-'.join(registers) or 'ordinary'),body[:lo]+'\n'.join(lines)+body[hi:]


def allocation_forms():
    body=dict(home_forms())['homes-ordinary']
    b=body.replace('    f32 distance;','    u8 **tableSource;')
    b=re.sub(r'\bdistance\b','currentDistance',b)
    b=b.replace('D_800D2350','(*tableSource)')
    for position in ('entry','nonnull','scan'):
        c=b
        if position=='entry':
            c=c.replace('    i = *(s32 *)(actor + 0x318);',
                '    tableSource = &D_800D2350;\n    i = *(s32 *)(actor + 0x318);')
        elif position=='nonnull':
            c=c.replace('        object = (u8 *)(u32)i;',
                '        tableSource = &D_800D2350;\n        object = (u8 *)(u32)i;')
        else:
            c=c.replace('            for (i = 0;',
                '            tableSource = &D_800D2350;\n            for (i = 0;')
            marker='            current = record[0x4B];'
            c=c.replace(marker,'            tableSource = &D_800D2350;\n'+marker)
            marker='        current = record[0x4B];'
            at=c.rindex(marker);c=c[:at]+'        tableSource = &D_800D2350;\n'+c[at:]
        yield 'allocation-table-'+position,c


SELECTED=dict(home_forms())['homes-ordinary']
RAW_SHA='2eee0341eb75fa11db9eefb78183ed892110ba1287b1ab35e17083e263dc36b7'
BINDINGS={
    44:[('R_MIPS_HI16','D_8008FDBC')],56:[('R_MIPS_LO16','D_8008FDBC')],
    60:[('R_MIPS_HI16','D_80087290')],76:[('R_MIPS_LO16','D_80087290')],
    116:[('R_MIPS_HI16','D_800D2350')],120:[('R_MIPS_LO16','D_800D2350')],
    132:[('R_MIPS_HI16','D_800D23A8')],136:[('R_MIPS_LO16','D_800D23A8')],
    600:[('R_MIPS_HI16','D_800D2350')],608:[('R_MIPS_LO16','D_800D2350')],
    604:[('R_MIPS_HI16','D_8009DA08')],616:[('R_MIPS_LO16','D_8009DA08')],
    660:[('R_MIPS_26','func_1508907C')],780:[('R_MIPS_26','func_1512D560')],
    796:[('R_MIPS_HI16','D_800D2350')],804:[('R_MIPS_LO16','D_800D2350')],
    976:[('R_MIPS_26','func_1508907C')],1212:[('R_MIPS_26','func_1512D560')],
}


def checked(obj):
    text,functions,rel=source.neighbor.parse_object(obj);f=functions[source.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    if len(raw)!=1284 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown unrolled projection body or bindings')
    return raw,bindings


def qualify(root,out):
    values=source.freeze(root,out);obj,words,row=measure(root,out,'qualified',SELECTED);raw,bindings=checked(obj)
    compiler=source.neighbor.baseline.model.compile_owner
    before,diagnostics=compiler(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    row['neighbors']=source.neighbor.same_functions(before,obj,(source.FUNCTION,))
    if diagnostics or row['diagnostics'] or (row['words'],row['frame'],row['differences'],row['neighbors'])!=(321,120,221,72) or \
            source.neighbor.normalized_pools(before)!=source.neighbor.normalized_pools(obj):
        raise ValueError('Changed unrolled projection/existing-owner evidence')
    normal,normal_words,normal_row=measure(root,out,'qualified-normal',SELECTED,True)
    if checked(normal)!=(raw,bindings) or normal_words!=words or normal_row['diagnostics']:
        raise ValueError('Target changed under the normal compiler profile')
    row.update(installable=False,matching_credit=0,normal_target_identical=True)
    (out/'qualified-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def measure(root,out,name,body,normal=False):
    obj,words,row=source.measure(root,out,name,body,normal)
    row.update(name=name,normal_profile=normal)
    return obj,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normal',action='store_true');parser.add_argument('--snapshots',action='store_true')
    parser.add_argument('--homes',action='store_true');parser.add_argument('--allocation',action='store_true')
    parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD;rows=[]
    if args.qualify:
        print(json.dumps(qualify(root,out)[2],indent=2));raise SystemExit(0)
    for name,body in (allocation_forms() if args.allocation else home_forms() if args.homes else snapshot_forms() if args.snapshots else forms()):
        _,_,row=measure(root,out,('normal-' if args.normal else 'owner-')+name,body,args.normal)
        rows.append(row)
        print(json.dumps({k:row[k] for k in ('name','words','frame','differences','saved','diagnostics')}),flush=True)
    (out/('screens-'+('allocation-' if args.allocation else 'homes-' if args.homes else 'snapshot-' if args.snapshots else '')+('normal' if args.normal else 'owner')+'.json')).write_text(json.dumps(rows,indent=2)+'\n')
