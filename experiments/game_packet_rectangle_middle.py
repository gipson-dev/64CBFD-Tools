"""Continue rectangle middle-block fitting from the qualified 71-word boundary."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_fitting as previous
from tools.tests import packet_rectangle_fitting_checkpoint as checkpoint

BUILD='conker/build/game-packet-rectangle-middle'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
PATHS=previous.PATHS
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER)
build=previous.build
INITIAL=previous.SELECTED
SELECTED=INITIAL


def freeze(root,out):
    with patch.object(previous,'BASELINE',BASELINE):
        previous.freeze(root,out)


def recovered_owner(before,selected=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!=INITIAL.split('\n',1)[1].rstrip():
        raise ValueError('Unknown rectangle-middle predecessor')
    body=SELECTED if selected is None else selected
    return before[:lo]+body.split('\n',1)[1].rstrip()+before[hi:]


def measure(root,out,label='selected',selected=None):
    with patch.multiple(previous,BASELINE=BASELINE,recovered_owner=recovered_owner):
        return previous.measure(root,out,label,selected)


def forms():
    yield 'predecessor',INITIAL
    yield 'mixed-product',INITIAL.replace('* 32.0f','* 32')
    yield 'mixed-outer',INITIAL.replace('32.0f -','32 -')
    word_fraction=INITIAL.replace('    s32 fractionalT;', '    u32 fractionalT;')
    word_coordinates=INITIAL.replace('    s32 textureS;', '    u32 textureS;').replace(
        '    s32 textureT;', '    u32 textureT;')
    yield 'word-fractional-T',word_fraction
    yield 'word-texture-coordinates',word_coordinates
    yield 'word-fraction-and-coordinates',word_coordinates.replace('    s32 fractionalT;', '    u32 fractionalT;')
    yield 'word-steps',INITIAL.replace('    s32 stepS;', '    u32 stepS;').replace('    s32 stepT;', '    u32 stepT;')
    signed_s=INITIAL.replace('textureS = (s32)((u32)(s32)(', 'textureS = (s32)(').replace(
        '(f32)integerScaleX) + (u32)sOffset + 0x2000u);','(f32)integerScaleX) + sOffset + 0x2000;')
    signed_t=INITIAL.replace('textureT = (s32)((u32)fractionalT + (u32)insetTOffset + 0x2000u);',
        'textureT = fractionalT + insetTOffset + 0x2000;').replace(
        'textureT = (s32)((u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT);',
        'textureT = ((packet->descriptor->unk6 + 255) << 5) - fractionalT;')
    yield 'control-signed-S-arithmetic',signed_s
    yield 'control-signed-T-arithmetic',signed_t
    yield 'control-signed-coordinate-arithmetic',signed_s.replace(
        'textureT = (s32)((u32)fractionalT + (u32)insetTOffset + 0x2000u);',
        'textureT = fractionalT + insetTOffset + 0x2000;').replace(
        'textureT = (s32)((u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT);',
        'textureT = ((packet->descriptor->unk6 + 255) << 5) - fractionalT;')
    quarter=(
        ('(s32)((u32)integerX << 2)','integerX'),
        ('(s32)((u32)integerY << 2)','integerY'),
        ('(s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2)',
         '((s32)((f32)widthAdjust + width - 1.0f) + integerX)'),
        ('(s32)((u32)((s32)(height - 1.0f) + integerY) << 2)',
         '((s32)(height - 1.0f) + integerY)'))
    for label,kind in (('signed-multiply-quarter','signed'),('unsigned-multiply-quarter','unsigned'),
            ('wide-multiply-quarter','wide'),('signed-shift-quarter','shift')):
        body=INITIAL
        for old,value in quarter:
            if kind=='signed':
                new='('+value+' * 4)'
            elif kind=='unsigned':
                new='(s32)((u32)'+value+' * 4u)'
            elif kind=='wide':
                value=value.replace('(s32)((f32)widthAdjust','(s64)(s32)((f32)widthAdjust').replace(
                    '(s32)(height','(s64)(s32)(height') if value.startswith('(') else '(s64)'+value
                new='(s32)('+value+' * 4)'
            else:
                new='('+value+' << 2)'
            if body.count(old)!=1:
                raise ValueError('Unknown quarter-pixel expression')
            body=body.replace(old,new,1)
        yield label,body
        yield label+'-mixed-product',body.replace('* 32.0f','* 32')
        yield label+'-mixed-outer',body.replace('32.0f -','32 -')
    x_step='            stepS = (u16)(0u - (u32)stepS);\n'
    x_origin='            textureS = (packet->descriptor->unk4 + 255) << 5;\n'
    y_step='            stepT = (u16)(0u - (u32)stepT);\n'
    y_origin='            textureT = (s32)((u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT);\n'
    for x,y in ((1,0),(0,1),(1,1)):
        body=INITIAL
        if x:
            body=body.replace(x_step+x_origin,x_origin+x_step)
        if y:
            body=body.replace(y_step+y_origin,y_origin+y_step)
        label='flip-order-%d%d'%(x,y)
        yield label,body
        yield label+'-mixed-product',body.replace('* 32.0f','* 32')
    yield 'inline-height',INITIAL.replace('    height = D_800D2C88;\n','').replace(
        '(height - 1.0f)','(D_800D2C88 - 1.0f)')
    yield 'half-animation-delta',INITIAL.replace('    s32 animationDelta;','    u16 animationDelta;')
    yield 'inline-animation-delta',INITIAL.replace('    s32 animationDelta;\n','').replace(
        '        animationDelta = packet->animationStep * D_800BE9A0;\n','').replace(
        'animationDelta','(packet->animationStep * D_800BE9A0)')
    for mask in (3,):
        body=INITIAL
        for bit,old,new in ((1,'if (flipFlags != 0)','if (packet->flipFlags != 0)'),
                (2,'if (flipFlags & 1)','if (packet->flipFlags & 1)'),
                (4,'if (flipFlags & 2)','if (packet->flipFlags & 2)')):
            if mask&bit:
                body=body.replace(old,new)
        yield 'byte-tests-%d'%mask,body
        yield 'byte-tests-%d-mixed-product'%mask,body.replace('* 32.0f','* 32')
        yield 'byte-tests-%d-word-cache'%mask,body.replace('    s32 flipFlags;', '    u32 flipFlags;')
        yield 'byte-tests-%d-word-cache-mixed-product'%mask,body.replace('    s32 flipFlags;',
            '    u32 flipFlags;').replace('* 32.0f','* 32')
    after_fraction=INITIAL.replace('    flipFlags = packet->flipFlags;\n','').replace(
        '    textureT = (s32)((u32)fractionalT',
        '    flipFlags = packet->flipFlags;\n    textureT = (s32)((u32)fractionalT',1)
    yield 'flags-after-fractional-T',after_fraction
    yield 'flags-after-fractional-T-mixed-product',after_fraction.replace('* 32.0f','* 32')
    masked=INITIAL.replace('flipFlags = packet->flipFlags;', 'flipFlags = packet->flipFlags & 3;').replace(
        'if (flipFlags != 0)', 'if (packet->flipFlags != 0)')
    yield 'masked-flag-cache',masked
    yield 'masked-flag-cache-mixed-product',masked.replace('* 32.0f','* 32')
    yield 'masked-word-flag-cache',masked.replace('    s32 flipFlags;', '    u32 flipFlags;')
    yield 'masked-word-flag-cache-mixed-product',masked.replace('    s32 flipFlags;', '    u32 flipFlags;').replace(
        '* 32.0f','* 32')
    start=INITIAL.index('    if (flipFlags != 0) {')
    end=INITIAL.index('    gSPScisTextureRectangle',start)
    block=INITIAL[start:end].splitlines()
    if block[-1]!='    }':
        raise ValueError('Unknown rectangle flip-block boundary')
    linear=INITIAL[:start]+'    if (flipFlags == 0) {\n        goto emit_rectangle;\n    }\n'+(
        '\n'.join(line[4:] if line.startswith('    ') else line for line in block[1:-1]))+'\nemit_rectangle:\n'+INITIAL[end:]
    yield 'linear-flip-block',linear
    yield 'linear-flip-block-mixed-product',linear.replace('* 32.0f','* 32')
    inner_mask=INITIAL.replace('    if (flipFlags != 0) {',
        '    if (flipFlags != 0) {\n        flipFlags &= 3;',1)
    yield 'inner-flag-mask',inner_mask
    yield 'inner-flag-mask-mixed-product',inner_mask.replace('* 32.0f','* 32')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens',action='store_true')
    args=parser.parse_args()
    for label,body in forms() if args.screens else [('selected',SELECTED)]:
        row=measure(args.root,args.root/BUILD,label,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics')}),flush=True)


if __name__=='__main__':
    main()
