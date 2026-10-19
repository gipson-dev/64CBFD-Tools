"""Recover the complete slot-state transfer before fitting compiler layout."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_route_mode_code_candidates as previous
from tools.experiments.game_route_projection_integration import compile_profile
from tools.experiments.game_remaining_donor_candidates import link_owner

BUILD='conker/build/game-slot-state-transfer'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508E89C',0x1508E89C,0xBBD4C,189
SOURCE=previous.SOURCE
ORIGINAL='s32 func_1508E89C() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'dea4dfd12a77af3cc6f98c79d89b8854f1d6e13b56e83fb0beb7771a3d09daed',
    'conker/retail_word_patches.us.csv':'2bccb21a86652810e61c0522563b25ad229a791c1acc397a8989344810d6816e',
    'conker/build/conker.us.elf':'f384fac3ed0d844cbe5f1c6165ff7ac36a3690bc62c157c7bcf9c63e14728f5e'})
DECLARATIONS='''extern u8 D_800D18A4[];
extern u16 D_800D18A2;
extern u16 D_800D18A0;
extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern s32 D_800BE9F0;
extern s32 D_800D2E48;
extern s8 D_8008FD94;
s32 func_150859AC(s16, s32);
void func_15085710(s16, s32, s32);
void func_15062800(u8 *, u8 *);
u8 *func_1509B570(s32);
void func_15128774(u8 *, u8 *);
'''
ACTOR_TYPE='typedef struct { u8 bytes[0x32C]; } SlotTransferActor;\n'
INITIAL='''/* Transfer slot state and restore the destination actor's control fields. */
s32 func_1508E89C(s32 destinationSlot, s32 sourceSlot) {
    s32 savedHalfword;
    u8 linkedSlot;
    u8 *destination;
    u8 *script;
    s32 scriptOffset;
    s32 actorIndex;
    u32 sourceBit;
    u32 inverseDestination;

    if (D_800D18A4[destinationSlot] >= 0x33 &&
        !(D_800D18A2 & (1U << destinationSlot))) {
        sourceBit = 1U << sourceSlot;
        inverseDestination = ~(1U << destinationSlot);
        D_800D18A0 &= inverseDestination;
        D_800D18A2 |= 1U << destinationSlot;
        D_800D18A0 |= sourceBit;
        func_15085710((s16)destinationSlot, 2, func_150859AC((s16)sourceSlot, 3));
        func_15085710((s16)sourceSlot, 2, 0);
        if (*(s32 *)((u8 *)D_800D23B0 + 0x18) != 0) {
            *(s32 *)((u8 *)D_800D23B0 + 0x18) &= inverseDestination;
            *(s32 *)((u8 *)D_800D23B0 + 0x18) |= sourceBit;
        }
        if ((u8 *)D_800D23B0 + 0x9C != 0) {
            ((s32 *)((u8 *)D_800D23B0 + 0x9C))[destinationSlot] =
                ((s32 *)((u8 *)D_800D23B0 + 0x9C))[sourceSlot];
        }
        if ((u8 *)D_800D23B0 + 0x39C != 0) {
            ((s32 *)((u8 *)D_800D23B0 + 0x39C))[destinationSlot] =
                ((s32 *)((u8 *)D_800D23B0 + 0x39C))[sourceSlot];
        }
        if ((u8 *)D_800D23B0 + 0x3DC != 0) {
            ((s32 *)((u8 *)D_800D23B0 + 0x3DC))[destinationSlot] =
                ((s32 *)((u8 *)D_800D23B0 + 0x3DC))[sourceSlot];
        }
        if ((u8 *)D_800D23B0 + 0xEB0 != 0) {
            ((s32 *)((u8 *)D_800D23B0 + 0xEB0))[destinationSlot] =
                ((s32 *)((u8 *)D_800D23B0 + 0xEB0))[sourceSlot];
            if (((s32 *)((u8 *)D_800D23B0 + 0xEB0))[destinationSlot] >= 0) {
                ((s32 *)((u8 *)D_800D23B0 + 0xF70))[
                    ((s32 *)((u8 *)D_800D23B0 + 0xEB0))[destinationSlot]] = destinationSlot;
            }
        }
        ((s32 *)((u8 *)D_800D23B0 + 0x16C0))[destinationSlot] =
            ((s32 *)((u8 *)D_800D23B0 + 0x16C0))[sourceSlot];
        destination = (u8 *)((u32)D_800CC2D0 + (u32)destinationSlot * 0x32C);
        savedHalfword = *(s16 *)(*(u8 **)(destination + 0x31C) + 0x1AA);
        func_15062800((u8 *)((u32)D_800CC2D0 + (u32)sourceSlot * 0x32C), destination);
        if (D_800BE9F0 == 0x3F && destination[0x13C] >= 100) {
            linkedSlot = destination[0x13C] - 100;
            script = func_1509B570(D_800D2E48);
            if (script != 0) {
                scriptOffset = D_800CC2D0[(u32)linkedSlot * 0x32C + 0x3B] - 20;
                actorIndex = (s32)((u32)destination - (u32)D_800CC2D0) / 0x32C;
                ((s32 *)(script + 0x24B8))[scriptOffset] = actorIndex | 0x2000;
                ((s32 *)(script + 0x24DC))[scriptOffset] = actorIndex;
            }
        }
        (*(u8 **)(destination + 0x31C))[0x84] = 0;
        destination[0x125] = 0x5A;
        *(s16 *)(*(u8 **)(destination + 0x31C) + 0x1AA) = savedHalfword;
        (*(u8 **)(destination + 0x31C))[0x1AF] = 0x40;
        func_15128774(*(u8 **)(destination + 0x318), destination);
        D_8008FD94++;
    }
    return 0;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    body=FITTED if body is None else body
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown slot-transfer predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=FITTED if body is None else body
    values=freeze(root,out);unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>189I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    typed=ACTOR_TYPE+INITIAL.replace('D_800CC2D0[(u32)linkedSlot * 0x32C + 0x3B]',
        '((SlotTransferActor *)D_800CC2D0)[linkedSlot].bytes[0x3B]').replace(
        '(s32)((u32)destination - (u32)D_800CC2D0) / 0x32C',
        '(SlotTransferActor *)destination - (SlotTransferActor *)D_800CC2D0')
    yield 'typed-script',typed
    pointer=INITIAL.replace('(s32)((u32)destination - (u32)D_800CC2D0) / 0x32C',
        '(destination - D_800CC2D0) / 0x32C')
    yield 'pointer-difference',pointer
    typed_initial=typed.replace('(u8 *)((u32)D_800CC2D0 + (u32)destinationSlot * 0x32C)',
        '((SlotTransferActor *)D_800CC2D0)[destinationSlot].bytes').replace(
        '(u8 *)((u32)D_800CC2D0 + (u32)sourceSlot * 0x32C)',
        '((SlotTransferActor *)D_800CC2D0)[sourceSlot].bytes')
    yield 'typed-actors',typed_initial
    for label,base in (('initial',INITIAL),('typed',typed_initial)):
        integer=base
        for offset in ('0x9C','0x39C','0x3DC','0xEB0'):
            integer=integer.replace('if ((u8 *)D_800D23B0 + '+offset+' != 0)',
                'if ((u32)D_800D23B0 + '+offset+' != 0)')
        yield label+'-integer-checks',integer
        yield label+'-unsigned-order-checks',integer.replace(' != 0) {\n            ((s32 *)((u8 *)D_800D23B0',
            ' > 0U) {\n            ((s32 *)((u8 *)D_800D23B0')
    for label in ('cast','scaled','address'):
        unit=typed_initial
        for offset in (0x9C,0x39C,0x3DC,0xEB0):
            old='(u8 *)D_800D23B0 + 0x%X != 0'%offset
            new={'cast':'(s32 *)((u8 *)D_800D23B0 + 0x%X) != 0'%offset,
                'scaled':'(s32 *)D_800D23B0 + 0x%X != 0'%(offset//4),
                'address':'&((s32 *)D_800D23B0)[0x%X] != 0'%(offset//4)}[label]
            unit=unit.replace(old,new)
        yield 'check-views-'+label,unit
    assign=typed_initial.replace('        sourceBit = 1U << sourceSlot;\n        inverseDestination = ~(1U << destinationSlot);',
        '        inverseDestination = ~(1U << destinationSlot);\n        sourceBit = 1U << sourceSlot;')
    yield 'roles-inverse-first',assign
    declarations=typed_initial.replace('    u32 sourceBit;\n    u32 inverseDestination;',
        '    u32 inverseDestination;\n    u32 sourceBit;')
    yield 'roles-declarations',declarations
    yield 'roles-both',assign.replace('    u32 sourceBit;\n    u32 inverseDestination;',
        '    u32 inverseDestination;\n    u32 sourceBit;')
    yield 'roles-half-after-byte',assign.replace('    s32 savedHalfword;\n    u8 linkedSlot;',
        '    u8 linkedSlot;\n    s32 savedHalfword;')
    old='''    s32 savedHalfword;
    u8 linkedSlot;
    u8 *destination;
    u8 *script;
    s32 scriptOffset;
    s32 actorIndex;
    u32 sourceBit;
    u32 inverseDestination;'''
    declarations=dict(savedHalfword='s32',linkedSlot='u8',destination='u8 *',script='u8 *',
        scriptOffset='s32',actorIndex='s32',sourceBit='u32',inverseDestination='u32')
    for label,order in (
            ('index-first',('actorIndex','savedHalfword','script','scriptOffset','linkedSlot','destination','sourceBit','inverseDestination')),
            ('offset-first',('scriptOffset','savedHalfword','actorIndex','script','linkedSlot','destination','sourceBit','inverseDestination')),
            ('destination-first',('destination','savedHalfword','scriptOffset','actorIndex','linkedSlot','script','sourceBit','inverseDestination'))):
        home=assign.replace(old,'\n'.join('    '+declarations[name]+('' if declarations[name].endswith('*') else ' ')+name+';' for name in order))
        if label=='index-first':homes_base=home
        yield 'homes-'+label,home
    cached=assign.replace('    s32 savedHalfword;','    s32 score;\n    s32 savedHalfword;',1).replace(
        '        func_15085710((s16)destinationSlot, 2, func_150859AC((s16)sourceSlot, 3));',
        '        score = func_150859AC((s16)sourceSlot, 3);\n        func_15085710((s16)destinationSlot, 2, score);')
    yield 'homes-named-score',cached
    for label,unit in (('base',assign),('score',cached)):
        yield 'homes-named-short-'+label,unit.replace('    s32 savedHalfword;',
            '    s32 sourceHalf;\n    s32 savedHalfword;',1).replace(
            '        func_15085710((s16)destinationSlot, 2, func_150859AC((s16)sourceSlot, 3));',
            '        sourceHalf = (s16)sourceSlot;\n        func_15085710((s16)destinationSlot, 2, func_150859AC(sourceHalf, 3));').replace(
            '        score = func_150859AC((s16)sourceSlot, 3);',
            '        sourceHalf = (s16)sourceSlot;\n        score = func_150859AC(sourceHalf, 3);').replace(
            'func_15085710((s16)sourceSlot, 2, 0);','func_15085710(sourceHalf, 2, 0);')
    for label in ('signed-add','cast-result'):
        unit=homes_base
        for offset in (0x9C,0x39C,0x3DC,0xEB0):
            old='(u8 *)D_800D23B0 + 0x%X != 0'%offset
            new=('D_800D23B0 + 0x%X != 0' if label=='signed-add' else
                 '(s32)((u8 *)D_800D23B0 + 0x%X) != 0')%offset
            unit=unit.replace(old,new)
        yield 'address-'+label,unit
    pointer=homes_base.replace('u8 *destination;','SlotTransferActor *destination;').replace(
        'destination = ((SlotTransferActor *)D_800CC2D0)[destinationSlot].bytes;',
        'destination = &((SlotTransferActor *)D_800CC2D0)[destinationSlot];').replace(
        'destination + ','destination->bytes + ').replace('destination[','destination->bytes[').replace(
        ', destination);',', destination->bytes);').replace('(SlotTransferActor *)destination -','destination -')
    yield 'address-typed-destination',pointer
    fields=homes_base.replace('    s32 actorIndex;','    s32 actorIndex;\n    s32 *field;',1)
    for offset in (0x9C,0x39C,0x3DC,0xEB0):
        fields=fields.replace('        if ((u8 *)D_800D23B0 + 0x%X != 0) {'%offset,
            '        field = (s32 *)((u8 *)D_800D23B0 + 0x%X);\n        if (field != 0) {'%offset).replace(
            '((s32 *)((u8 *)D_800D23B0 + 0x%X))[destinationSlot] =\n                ((s32 *)((u8 *)D_800D23B0 + 0x%X))[sourceSlot];'%(offset,offset),
            'field[destinationSlot] = field[sourceSlot];')
    yield 'address-named-fields',fields
    table_type='''typedef struct {
    u8 pad00[0x18];
    s32 flags;
    u8 pad1C[0x80];
    s32 field9C[16];
    u8 padDC[0x2C0];
    s32 field39C[16];
    s32 field3DC[16];
    u8 pad41C[0xA94];
    s32 fieldEB0[16];
    u8 padEF0[0x80];
    s32 fieldF70[16];
    u8 padFB0[0x710];
    s32 field16C0[16];
} SlotTransferTable;
'''
    # Typed field views test address formation without caching the mutable global.
    table=table_type+homes_base
    table=table.replace('*(s32 *)((u8 *)D_800D23B0 + 0x18)',
        '((SlotTransferTable *)D_800D23B0)->flags')
    for offset in (0x9C,0x39C,0x3DC,0xEB0,0xF70,0x16C0):
        field='((SlotTransferTable *)D_800D23B0)->field%X'%offset
        table=table.replace('((s32 *)((u8 *)D_800D23B0 + 0x%X))'%offset,field)
        table=table.replace('(u8 *)D_800D23B0 + 0x%X != 0'%offset,field+' != 0')
    yield 'address-table-fields',table
    addressed=table
    for offset in (0x9C,0x39C,0x3DC,0xEB0):
        field='((SlotTransferTable *)D_800D23B0)->field%X'%offset
        addressed=addressed.replace('if ('+field+' != 0)', 'if (&'+field+'[0] != 0)')
    yield 'address-table-elements',addressed


FITTED=next(unit for name,unit in candidates() if name=='homes-index-first')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--normal',action='store_true')
    parser.add_argument('--whole',action='store_true');parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    if args.screens:
        for name,unit in candidates():
            if args.filter not in name:continue
            row=compile_candidate(root,root/BUILD,name,unit,normal=args.normal)[2]
            print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
    else:print(json.dumps(compile_candidate(root,root/BUILD,normal=args.normal,whole=args.whole)[2],indent=2))
