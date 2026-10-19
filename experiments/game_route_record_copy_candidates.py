"""Recover the route record copy while preserving destination identity/state."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_event_dispatch_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD = 'conker/build/game-route-record-copy'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_B3020', 'func_150885EC', 0x150885EC, 0xB5A9C, 40
SOURCE = previous.SOURCE
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_B3020/func_150885EC.s")'
INPUTS = dict(previous.INPUTS)
INPUTS[SOURCE] = 'ec3fd9786e52b63698d7d2a723e31479f0941441e7b25c523bda71c92272fb3b'
INPUTS['conker/asm/nonmatchings/generated_B3020/func_150885EC.s'] = 'fa53c1e57e0adc20d2eb72d62f8d9ef10904448671a84efe382736d58a025151'
INPUTS['conker/asm/libultra/libc/bcopy.s'] = 'e48e1e17cef4688b86b21141f7b2355d16aaf074956a46346f9f941a8c3df759'
DECLARATIONS = 'extern u8 *D_800872A0;\n'
INITIAL = '''/* Copy a route record while keeping the destination's identity and state. */
void func_150885EC(s32 sourceIndex, s32 destinationIndex) {
    s32 savedId;
    s32 savedState;
    u8 *table;
    u32 destinationOffset;

    table = D_800872A0;
    if (table != 0) {
        destinationOffset = (u32)destinationIndex * 0x84;
        savedId = *(s8 *)((u32)table + destinationOffset + 0x31);
        savedState = *(s8 *)((u32)table + destinationOffset + 0x30);
        bcopy((u8 *)((u32)sourceIndex * 0x84 + (u32)table),
              (u8 *)(destinationOffset + (u32)table), 0x84);
        D_800872A0[destinationOffset + 0x31] = savedId;
        D_800872A0[destinationOffset + 0x30] = savedState;
    }
}
'''
SELECTED = INITIAL.replace('(u8 *)(destinationOffset + (u32)table)','table + destinationOffset').replace(
    '    u32 destinationOffset;\n','').replace(
    '        destinationOffset = (u32)destinationIndex * 0x84;\n','').replace(
    'destinationOffset','((u32)destinationIndex * 0x84)')


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):
        return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:
        raise ValueError('Unknown route-copy assembly predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):
        return previous.payload(obj)


def compile_candidate(root,out,name='selected',body=SELECTED,whole=False,normal=False):
    values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+'\n'+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal)
    image,functions=link_owner(root,out,obj,OWNER)
    raw,bindings=payload(obj);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>40I',values['conker/conker.us.bin'],ROM)
    row=dict(name=name,words=len(words),frame=(-words[0])&65535,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        diagnostics=diagnostics,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def candidates():
    yield 'initial',INITIAL
    no_table=INITIAL.replace('    u8 *table;\n','').replace('    table = D_800872A0;\n','').replace(
        'table != 0','D_800872A0 != 0').replace('(u32)table','(u32)D_800872A0')
    for label,body,base in (('table',INITIAL,'table'),('global',no_table,'D_800872A0')):
        pointer=body.replace('*(s8 *)((u32)'+base+' + destinationOffset',
            '*(s8 *)('+base+' + destinationOffset')
        for field,unit in (('integer-fields',body),('pointer-fields',pointer)):
            yield label+'-'+field,unit
            yield label+'-'+field+'-pointer-destination',unit.replace(
                '(u8 *)(destinationOffset + (u32)'+base+')',base+' + destinationOffset')
            yield label+'-'+field+'-reverse-destination',unit.replace(
                '(u8 *)(destinationOffset + (u32)'+base+')','(u8 *)((u32)'+base+' + destinationOffset)')
    fitted=INITIAL.replace('(u8 *)(destinationOffset + (u32)table)','table + destinationOffset')
    for kind,body in (('unsigned',fitted),('signed',fitted.replace('u32 destinationOffset;','s32 destinationOffset;'))):
        yield 'offset-'+kind,body
        yield 'offset-'+kind+'-first-destination',body.replace('table + destinationOffset,','destinationOffset + table,')
        yield 'offset-'+kind+'-register-table',body.replace('    u8 *table;','    register u8 *table;')
    for name,body in (('integer',INITIAL),('pointer',fitted),('offset-first',fitted.replace(
            'table + destinationOffset,','destinationOffset + table,'))):
        repeated=body.replace('    u32 destinationOffset;\n','').replace(
            '        destinationOffset = (u32)destinationIndex * 0x84;\n','').replace(
            'destinationOffset','((u32)destinationIndex * 0x84)')
        yield 'repeated-destination-'+name,repeated


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--whole',action='store_true')
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in candidates() if args.screens else [('selected',SELECTED)]:
        if args.filter and args.filter not in name:continue
        row=compile_candidate(root,root/BUILD,name,body,whole=args.whole)[2]
        print(json.dumps(row,indent=2) if not args.screens else
            json.dumps({key:row[key] for key in ('name','words','frame','differences','raw_SHA256')}),flush=True)
