"""Screen real narrowed step roles against the rectangle's observed CSE homes."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_macro_lifetime as previous

BUILD='conker/build/game-packet-rectangle-step-lifetime'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
PATHS,BASELINE,build=previous.PATHS,previous.BASELINE,previous.build
INITIAL=SELECTED=previous.SELECTED
PREDECESSOR_FREEZE=previous.freeze
recovered_owner=previous.recovered_owner


def freeze(root,out):
    from tools.tests import packed_point_transform_checkpoint as checkpoint
    read=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,root)):
        PREDECESSOR_FREEZE(root,out)


def measure(root,out,label='selected',body=None):
    from tools.tests import packed_point_transform_checkpoint as checkpoint
    read=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:checkpoint.previous_input(read(p),p,root)):
        return previous.measure(root,out,label,SELECTED if body is None else body)


def staged_rectangle(narrow_x):
    start=INITIAL.index('    gSPScisTextureRectangle')
    end=INITIAL.index('\n\n    if (packet->descriptor->unkA',start)
    block='''    {
        Gfx *rectangle = output++;
        rectangle->words.w0 = _SHIFTL(G_TEXRECT, 24, 8) |
            _SHIFTL(MAX((s16)(s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2), 0), 12, 12) |
            _SHIFTL(MAX((s16)(s32)((u32)((s32)(height - 1.0f) + integerY) << 2), 0), 0, 12);
        integerX = X_PHASE;
        integerY = (s32)((u32)integerY << 2);
        rectangle->words.w1 = _SHIFTL(0, 24, 3) |
            _SHIFTL(MAX((s16)integerX, 0), 12, 12) |
            _SHIFTL(MAX((s16)integerY, 0), 0, 12);
        gImmp1(output++, G_RDPHALF_1,
            _SHIFTL(textureS - (((s16)integerX < 0) ?
                (((s16)stepS < 0) ? MAX(((s16)integerX * (s16)stepS) >> 7, 0) :
                    MIN(((s16)integerX * (s16)stepS) >> 7, 0)) : 0), 16, 16) |
            _SHIFTL(textureT - ((integerY < 0) ?
                (((s16)stepT < 0) ? MAX(((s16)integerY * (s16)stepT) >> 7, 0) :
                    MIN(((s16)integerY * (s16)stepT) >> 7, 0)) : 0), 0, 16));
        gImmp1(output++, G_RDPHALF_2, _SHIFTL(stepS, 16, 16) | _SHIFTL(stepT, 0, 16));
    }'''
    phase='(s16)((u32)integerX << 2)' if narrow_x else '(s32)((u32)integerX << 2)'
    return INITIAL[:start]+block.replace('X_PHASE',phase)+INITIAL[end:]


def forms():
    yield 'predecessor',INITIAL
    for kind in ('u16','s16'):
        for roles in (('S',),('T',),('S','T')):
            body=INITIAL
            for role in roles:
                body=body.replace('    s32 step'+role+';', '    '+kind+' step'+role+';',1)
            yield 'step-'+kind+'-'+''.join(roles),body
    split=INITIAL.replace('    s32 stepT;', '    s32 originalStepT;\n    s32 stepT;',1).replace(
        '    stepT = numerator / integerScaleY;',
        '    originalStepT = numerator / integerScaleY;\n    stepT = originalStepT;',1).replace(
        '(u16)(0u - (u32)stepT)', '(u16)(0u - (u32)originalStepT)',1)
    yield 'original-T-full',split
    yield 'original-T-u16-T',split.replace('    s32 stepT;', '    u16 stepT;',1)
    yield 'original-T-u16-ST',split.replace('    s32 stepT;', '    u16 stepT;',1).replace(
        '    s32 stepS;', '    u16 stepS;',1)
    yield 'staged-corners-narrow-X',staged_rectangle(True)
    yield 'staged-corners-full-X',staged_rectangle(False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    for label,body in forms():
        if args.filter and args.filter not in label:
            continue
        row=measure(args.root,args.root/BUILD,label,body)[2]
        physical=previous.shape(args.root/BUILD,label)
        print(json.dumps(dict({k:row[k] for k in ('label','words','frame','differences','diagnostics')},
            **{k:physical[k] for k in ('prefix','suffix','slot_suffix')})),flush=True)


if __name__=='__main__':
    main()
