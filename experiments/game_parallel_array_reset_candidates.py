"""Recover two mutable-bound reset loops with cached output-array pointers."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_round_robin_slot_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-parallel-array-reset'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508DA1C',0x1508DA1C,0xBAECC,52
ORIGINAL='s32 func_1508DA1C() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'66972bed4e1550955f49fb477d54b866bda66046d2b1f6d25a458e59fa5b7cd7',
    'conker/retail_word_patches.us.csv':'c5c75bcb2a7775fe376378308fec352c35f41584f6c4c11b8121dc76acead55f',
    'conker/build/conker.us.elf':'6e6583fb815a0e3d160444feed792fdd05cab6cb7f7aedb4c92ccb282d8d59e2'})
DECLARATIONS='extern s32 D_800D23B0;\n'
INITIAL='''/* Reset the cached arrays while reloading their current context bounds. */
void func_1508DA1C(void) {
    u8 *state = (u8 *)D_800D23B0;
    s32 *first = (s32 *)(state + 0xEB0);
    s32 *ids = (s32 *)(state + 0xF70);
    s32 *values = (s32 *)(state + 0xFF0);
    s32 *enabled = (s32 *)(state + 0x1070);
    s32 *owners = (s32 *)(state + 0x10F0);
    s32 *pending = (s32 *)(state + 0x12F4);
    s32 i;

    for (i = 0; i < *(s32 *)(state + 0x10); i++) {
        first[i] = -1;
        state = (u8 *)D_800D23B0;
    }
    for (i = 0; i < *(s32 *)(state + 0xEA4); i++) {
        ids[i] = -1;
        values[i] = 0;
        owners[i] = -1;
        enabled[i] = 1;
        pending[i] = 0;
        state = (u8 *)D_800D23B0;
    }
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown parallel-reset predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(FITTED if body is None else body).rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>52I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    pointers=INITIAL.replace('        first[i] = -1;','        *first++ = -1;').replace(
        '        ids[i] = -1;','        *ids++ = -1;').replace('        values[i] = 0;','        *values++ = 0;').replace(
        '        owners[i] = -1;','        *owners++ = -1;').replace('        enabled[i] = 1;','        *enabled++ = 1;').replace(
        '        pending[i] = 0;','        *pending++ = 0;')
    yield 'pointer-walk',pointers
    for label,body in (('indexed',INITIAL),('walk',pointers)):
        for where in ('first','before-arrays'):
            moved=body.replace('    s32 i;\n','')
            marker='    u8 *state' if where=='first' else '    s32 *first'
            moved=moved.replace(marker,'    s32 i;\n'+marker,1)
            yield label+'-index-'+where,moved
        yield label+'-second-state-direct',body.replace('i < *(s32 *)(state + 0xEA4)',
            'i < *(s32 *)((u8 *)D_800D23B0 + 0xEA4)').replace(
            '        pending[i] = 0;\n        state = (u8 *)D_800D23B0;','        pending[i] = 0;').replace(
            '        *pending++ = 0;\n        state = (u8 *)D_800D23B0;','        *pending++ = 0;')


def fitting_candidates():
    base=dict(candidates())['indexed-second-state-direct']
    for marker in ('u8 *state','s32 *first','s32 *ids','s32 *values','s32 *enabled','s32 *owners','s32 *pending'):
        body=base.replace('    s32 i;\n','').replace('    '+marker,'    s32 i = 0;\n    '+marker,1).replace(
            '    for (i = 0; i < *(s32 *)(state + 0x10); i++)','    for (; i < *(s32 *)(state + 0x10); i++)')
        yield 'index-init-'+marker.split('*')[-1],body
    yield 'first-pointer-walk',base.replace('        first[i] = -1;','        *first++ = -1;')
    yield 'other-pointer-walk',base.replace('        ids[i] = -1;','        *ids++ = -1;').replace(
        '        values[i] = 0;','        *values++ = 0;').replace('        owners[i] = -1;','        *owners++ = -1;').replace(
        '        enabled[i] = 1;','        *enabled++ = 1;').replace('        pending[i] = 0;','        *pending++ = 0;')
    reused=base.replace('first','cursor').replace(
        '    for (i = 0; i < *(s32 *)((u8 *)D_800D23B0 + 0xEA4); i++) {',
        '    cursor = ids;\n    for (i = 0; i < *(s32 *)((u8 *)D_800D23B0 + 0xEA4); i++) {').replace(
        '        ids[i] = -1;','        cursor[i] = -1;')
    yield 'shared-cursor',reused
    yield 'shared-cursor-walk',reused.replace('        cursor[i] = -1;','        *cursor++ = -1;')
    for label,body in (('indexed',base),('shared',reused)):
        before='    s32 *first = (s32 *)(state + 0xEB0);\n' if label=='indexed' else '    s32 *cursor = (s32 *)(state + 0xEB0);\n'
        for at in ('ids','values','enabled','owners','pending'):
            after='    s32 *'+at+' ='
            lines=body.splitlines(keepends=True);target=next(line for line in lines if line.startswith(after))
            swapped=body.replace(before,'').replace(target,target+before)
            yield label+'-first-after-'+at,swapped


FITTED=dict(fitting_candidates())['index-init-pending']
for old,new in (('first','resetEB0'),('ids','resetF70'),('values','resetFF0'),
        ('enabled','reset1070'),('owners','reset10F0'),('pending','reset12F4')):
    FITTED=FITTED.replace(old,new)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--fitting',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (fitting_candidates() if args.fitting else candidates() if args.screens else [('selected',FITTED)]):
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
