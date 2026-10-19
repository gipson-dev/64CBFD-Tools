"""Recover the complete packed-entry peer lookup and fit ordinary C forms."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_slot_state_transfer_candidates as previous
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.experiments.game_route_projection_integration import compile_profile

BUILD='conker/build/game-packed-peer-lookup'
SOURCE=previous.SOURCE
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508ECC0',0x1508ECC0,0xBC170,63
ORIGINAL='s32 func_1508ECC0() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'6fe4d8408e457541217402b980e22d5bec2a543c78159b9257820c3366073008',
    'conker/retail_word_patches.us.csv':'e0fa6e237c49ab0da592675c5f7ed0ba5151eb440680d7736a152490cae1c49c',
    'conker/build/conker.us.elf':'2de61c0701cc1deb2fe0e0c0334756728c2abbb84525af3d370b531dcb4336d5'})
DECLARATIONS='extern u8 *D_800D23C0;\nextern u32 D_80087380;\n'
INITIAL='''/* Find a different group entry in the first row containing the packed key. */
s32 func_1508ECC0(u16 group, u16 value, u16 peerGroup) {
    u32 rowIndex;
    u32 keyIndex;
    u32 peerIndex;
    u8 *row;
    u16 key;

    for (rowIndex = 0; rowIndex < D_80087380; rowIndex++) {
        row = D_800D23C0 + rowIndex * 24;
        for (keyIndex = 0; keyIndex < *(u16 *)(row + 2); keyIndex++) {
            key = (group << 12) + value;
            if (((u16 *)(row + 8))[keyIndex] == key) {
                for (peerIndex = 0; peerIndex < *(u16 *)(row + 2); peerIndex++) {
                    if ((((u16 *)(row + 8))[peerIndex] >> 12) == peerGroup && peerIndex != keyIndex) {
                        return ((u16 *)(row + 8))[peerIndex] & 0xFFF;
                    }
                }
                return -1;
            }
        }
    }
    return -1;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    body=FITTED if body is None else body
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown packed-peer predecessor')
    return before.replace(ORIGINAL,body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='initial',body=None,normal=False,whole=False):
    body=FITTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value'];words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at))
    truth=struct.unpack_from('>63I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    reused=INITIAL.replace('    u32 peerIndex;\n','').replace('peerIndex','rowIndex')
    yield 'reused-index',reused
    for label,body in (('initial',INITIAL),('reused',reused)):
        yield label+'-signed-index',body.replace('u32 rowIndex','s32 rowIndex').replace('u32 keyIndex','s32 keyIndex').replace('u32 peerIndex','s32 peerIndex')
        yield label+'-outer-key',body.replace('            key = (group << 12) + value;\n','').replace(
            '        for (keyIndex = 0;', '        key = (group << 12) + value;\n        for (keyIndex = 0;')
        counted=body.replace('    u16 key;','    u16 key;\n    u32 count;').replace(
            '        for (keyIndex = 0;', '        count = *(u16 *)(row + 2);\n        for (keyIndex = 0;').replace(
            '< *(u16 *)(row + 2)', '< count')
        yield label+'-counted',counted
    indexed=INITIAL.replace('    u8 *row;\n','').replace('        row = D_800D23C0 + rowIndex * 24;\n','').replace(
        '(row + 2)','(D_800D23C0 + rowIndex * 24 + 2)').replace('(row + 8)','(D_800D23C0 + rowIndex * 24 + 8)')
    typed='''typedef struct {
    u16 unk0;
    u16 count;
    u32 unk4;
    u16 entries[8];
} PackedPeerRow;
'''+indexed.replace('*(u16 *)(D_800D23C0 + rowIndex * 24 + 2)',
        '((PackedPeerRow *)D_800D23C0)[rowIndex].count').replace(
        '((u16 *)(D_800D23C0 + rowIndex * 24 + 8))',
        '((PackedPeerRow *)D_800D23C0)[rowIndex].entries')
    for label,body in (('indexed',indexed),('typed',typed)):
        yield label,body
        for mode in ('casts','masks'):
            explicit=body.replace('u16 group, u16 value, u16 peerGroup','s32 group, s32 value, s32 peerGroup')
            masking=''.join('    '+name+(' = (u16)'+name if mode=='casts' else ' &= 0xFFFF')+';\n' for name in ('group','value','peerGroup'))
            explicit=explicit.replace('    for (rowIndex = 0;',masking+'\n    for (rowIndex = 0;',1)
            yield label+'-'+mode,explicit
    for label,body in (('initial',INITIAL),('typed',typed)):
        parameter=body.replace('u16 peerGroup)', 'u32 keyIndex)').replace('    u32 keyIndex;\n','')
        parameter=parameter.replace('    u16 key;', '    u16 key;\n    u16 peerGroup;').replace(
            '    for (rowIndex = 0;', '    peerGroup = keyIndex;\n    for (rowIndex = 0;',1)
        yield label+'-parameter-index',parameter
    for label,names in (('first-two',('group','value')),('all-three',('group','value','peerGroup'))):
        hinted=typed
        for name in names:hinted=hinted.replace('u16 '+name+(',' if name!='peerGroup' else ')'),
            'register u16 '+name+(',' if name!='peerGroup' else ')'))
        yield 'typed-register-'+label,hinted
    for bits in range(1,8):
        body=typed
        statements=[]
        for i,name in enumerate(('group','value','peerGroup')):
            if bits&(1<<i):
                ending=',' if i<2 else ')'
                body=body.replace('u16 '+name+ending,'u32 '+name+ending)
                statements.append('    '+name+' = (u16)'+name+';')
        body=body.replace('    for (rowIndex = 0;','\n'.join(statements)+'\n    for (rowIndex = 0;',1)
        yield 'typed-width-%d'%bits,body
    for order in (('keyIndex','rowIndex','peerIndex'),('peerIndex','keyIndex','rowIndex'),('rowIndex','peerIndex','keyIndex')):
        old='    u32 rowIndex;\n    u32 keyIndex;\n    u32 peerIndex;'
        body=typed.replace(old,'\n'.join('    u32 '+name+';' for name in order))
        yield 'typed-order-'+'-'.join(order),body
    for label,body in (('initial',INITIAL),('typed',typed)):
        old=body.replace('s32 func_1508ECC0(u16 group, u16 value, u16 peerGroup) {',
            's32 func_1508ECC0(group, value, peerGroup)\nu16 group;\nu16 value;\nu16 peerGroup;\n{')
        yield label+'-old-style',old
        yield label+'-inline-key',body.replace('    u16 key;\n','').replace('            key = (group << 12) + value;\n','').replace(
            '] == key)', '] == (u16)((group << 12) + value))')


FITTED=next(body for name,body in candidates() if name=='typed-width-3')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='');args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    forms=candidates() if args.screens else [('selected',FITTED)]
    for name,body in forms:
        if args.filter not in name:continue
        _,_,row=compile_candidate(root,root/BUILD,name,body)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
