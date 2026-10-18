"""Bounded vector lifetime fitting against a new, strict post-spline checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_vector_builder as model
from tools.experiments import game_route_spline_derivative as derivative
from tools.experiments import game_actor_owned_resource_cleanup as checkpoint

BUILD='conker/build/game-route-vector-lifetime-fit'
INPUTS=dict(model.INPUTS)
INPUTS.update({p:derivative.AFTER[p] for p in ('conker/build/conker.us.elf','conker/retail_word_patches.us.csv')})
RAW_SHA='4f916fe4c212cefecfdfe585fd3448578d0cf62b80560f508e9b8b2650406919'
NAMED_SHA='7b5905ce1dfdc0d4a531873a512cdbdcd73e76ae071311d27bff3d1027ff5470'


def freeze(root,out):
    with patch.object(checkpoint,'INPUTS',INPUTS):return checkpoint.freeze(root,out)


def owner(before,body):
    lo,hi=model.function_span(before,model.FUNCTION)
    if before[lo:hi]!='s32 func_15088F30() {\n    return 0;\n}':raise ValueError('Unknown vector placeholder')
    result=before[:lo]+body.rstrip()+before[hi:]
    declaration='    extern s32 func_15088F30();'
    if result.count(declaration)!=1:raise ValueError('Unknown vector parent prototype')
    headers=[line for line in body.splitlines() if line.startswith('void func_15088F30(')]
    if len(headers)!=1 or not headers[0].endswith(' {'):raise ValueError('Unknown fitting interface')
    return result.replace(declaration,'    extern '+headers[0][:-2]+';')


def forms():
    base=dict(model.forms())['local-outputs-assigned']
    yield 'local-baseline',base
    for mask in range(1,16):
        body=base
        for bit,kind,name in ((1,'u8','record'),(2,'f32','xOutput'),(4,'f32','yOutput'),(8,'f32','zOutput')):
            if mask&bit:body=body.replace(kind+' *'+name+',',kind+' *const '+name+',').replace(kind+' *'+name+')',kind+' *const '+name+')')
        yield 'const-bindings-%02X'%mask,body


def declaration_forms():
    base=dict(model.forms())['local-outputs-assigned']
    named=base.replace('    u8 *cursor;',
        '    u8 **tableSource;\n    s32 pointCount;\n    u8 *cursor;').replace(
        '    slot = 0;', '    tableSource = &D_800D2350;\n    pointCount = 4;\n    slot = 0;').replace(
        'table = D_800D2350;', 'table = *tableSource;').replace('== 4)', '== pointCount)').replace(
        'slot != 4', 'slot != pointCount')
    for label,body in (('local',base),('named',named)):
        header,rest=body.split(' {\n',1);declarations,statements=rest.split('\n\n',1)
        groups=[[],[],[],[]]
        for line in declarations.splitlines():
            group=0 if line in ('    f32 *x;','    f32 *y;','    f32 *z;') else \
                1 if '*' in line else 2 if 's32 ' in line else 3
            groups[group].append(line)
        for order in ((0,1,2,3),(1,2,3,0),(2,3,0,1),(3,0,1,2),(3,2,1,0),(2,1,0,3)):
            yield label+'-declarations-'+''.join(map(str,order)),header+' {\n'+ \
                '\n'.join(line for group in order for line in groups[group])+'\n\n'+statements


def checked_screen(obj,named=False):
    text,functions,rel=model.parse_object(obj);f=functions[model.FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']}
    hi,lo=(60,72) if named else (16,44)
    expected={hi:[('R_MIPS_HI16','D_800D2350')],lo:[('R_MIPS_LO16','D_800D2350')]}
    if len(raw)!=(328 if named else 332) or hashlib.sha256(raw).hexdigest()!=(NAMED_SHA if named else RAW_SHA) or bindings!=expected:
        raise ValueError('Unknown rejected lifetime screen or bindings')
    return raw,bindings


def measure(root,out,name,body):
    values=freeze(root,out)
    obj,diagnostics=model.compile_owner(root,out,owner(values['conker/src/game/generated_B3020.c'].decode(),body),name)
    data,functions=model.link_owner(root,out,obj,model.OWNER);f=functions[model.FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    text,functions,rel=model.parse_object(obj);f=functions[model.FUNCTION]
    truth=list(struct.unpack_from('>83I',values['conker/conker.us.bin'],model.ROM))
    row=dict(name=name,words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-83),
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        saved=[(w>>16&31,w&65535) for w in words if w>>26==43 and w>>21&31==29],
        bindings={at-f['value']:v for at,v in rel.items() if f['value']<=at<f['value']+f['size']})
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def qualify(root,out,screen='all'):
    if screen not in ('all','const','declarations'):raise ValueError('Unknown lifetime screen')
    values=freeze(root,out)
    before,diagnostics=model.compile_owner(root,out,values['conker/src/game/generated_B3020.c'].decode(),'owner-before')
    if diagnostics:raise ValueError('Unexpected baseline compiler diagnostics')
    candidates=[]
    if screen in ('all','const'):candidates.extend(forms())
    if screen in ('all','declarations'):candidates.extend(declaration_forms())
    rows=[]
    for name,body in candidates:
        obj,words,row=measure(root,out,name,body);named=name.startswith('named-')
        checked_screen(obj,named)
        row['neighbors']=model.same_functions(before,obj,(model.FUNCTION,))
        if row['diagnostics'] or row['frame']!=16 or row['neighbors']!=72 or \
                model.normalized_pools(before)!=model.normalized_pools(obj) or row['differences']!=(77 if named else 78):
            raise ValueError('Changed lifetime-screen owner evidence')
        try:model.require_retail_stack_contract(words)
        except ValueError:row['installable']=False
        else:raise ValueError('Rejected lifetime screen unexpectedly passed the stack gate')
        rows.append(row)
    freeze(root,out)
    receipt=dict(screen=screen,candidates=rows,matching_credit=0,frozen_inputs_unchanged=True)
    (out/('qualified-'+screen+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen',choices=('all','const','declarations'),default='all');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    print(json.dumps(qualify(root,out,args.screen),indent=2))
