"""Screen rectangle snapshot and computed-expression lifetimes without installing."""
import argparse
import itertools
import json
from pathlib import Path
import re
import struct
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_middle as previous
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-packet-rectangle-lifetime'
OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
PATHS,BASELINE,build=previous.PATHS,previous.BASELINE,previous.build
INITIAL=previous.SELECTED
SELECTED=INITIAL
freeze=previous.freeze
RECOVERED_OWNER=previous.recovered_owner


def recovered_owner(before,selected=None):
    body=SELECTED if selected is None else selected
    owner=RECOVERED_OWNER(before,body)
    old='s32 func_15095D34(Gfx *, ProjectedPacket95B08 *, s32, s32, s32);'
    if owner.count(old)!=1:
        raise ValueError('Unknown rectangle lifetime prototype')
    types=['u32' if 'u32 '+name+',' in body else 's32' for name in ('sOffset','insetTOffset')]
    return owner.replace(old,'s32 func_15095D34(Gfx *, ProjectedPacket95B08 *, '+', '.join(types)+', s32);',1)


def measure(root,out,label='selected',selected=None):
    with patch.object(previous,'recovered_owner',recovered_owner):
        return previous.measure(root,out,label,selected)


def snapshot(body,role,kind):
    if kind=='array':
        declaration='    s32 '+role+'[1];'
        access=role+'[0]'
    else:
        declaration='    struct { s32 value; } '+role+';'
        access=role+'.value'
    if body.count('    s32 '+role+';')!=1:
        raise ValueError('Unknown rectangle snapshot declaration')
    body=body.replace('    s32 '+role+';',declaration,1)
    start=body.index('    if (insetTOffset != 0) {')
    return body[:start]+re.sub(r'(?<!->)\b'+role+r'\b',access,body[start:])


def forms():
    yield 'predecessor',INITIAL
    flag='    flipFlags = packet->flipFlags;\n'
    for label,anchor in (('before-S','    textureS ='),('before-Y','    integerY ='),
            ('after-T','    if (flipFlags != 0) {')):
        body=INITIAL.replace(flag,'').replace(anchor,flag+anchor,1)
        yield 'flags-'+label,body
        yield 'flags-'+label+'-mixed',body.replace('* 32.0f','* 32')
    for role in ('flipFlags','fractionalT'):
        for kind in ('array','record'):
            body=snapshot(INITIAL,role,kind)
            yield role+'-'+kind,body
            yield role+'-'+kind+'-mixed',body.replace('* 32.0f','* 32')
    for mask in (1,2,4,5,6):
        body=INITIAL
        for bit,old,new in ((1,'if (flipFlags != 0)','if (packet->flipFlags != 0)'),
                (2,'if (flipFlags & 1)','if (packet->flipFlags & 1)'),
                (4,'if (flipFlags & 2)','if (packet->flipFlags & 2)')):
            if mask&bit:
                body=body.replace(old,new)
        yield 'byte-tests-'+str(mask),body
        yield 'byte-tests-'+str(mask)+'-mixed',body.replace('* 32.0f','* 32')
    # Distinct source snapshots may coalesce, or retain the retail flag copy.
    split=INITIAL.replace('    s32 flipFlags;','    s32 flipFlags;\n    s32 innerFlipFlags;').replace(
        '    if (flipFlags != 0) {','    if (flipFlags != 0) {\n        innerFlipFlags = flipFlags;',1).replace(
        'if (flipFlags &','if (innerFlipFlags &')
    yield 'inner-flag-copy',split
    yield 'inner-flag-copy-mixed',split.replace('* 32.0f','* 32')
    for role in ('fractionalT','flipFlags'):
        body=INITIAL.replace('    s32 '+role+';', '    register s32 '+role+';')
        body=snapshot(body,'flipFlags' if role=='fractionalT' else 'fractionalT','array')
        yield 'register-'+role+'-other-array',body
        yield 'register-'+role+'-other-array-mixed',body.replace('* 32.0f','* 32')
    expression='(u32)((packet->descriptor->unk6 + 255) << 5) - (u32)fractionalT'
    for label,replacement in (
            ('from-texture-T','(u32)((packet->descriptor->unk6 + 255) << 5) - (u32)textureT + (u32)insetTOffset + 0x2000u'),
            ('reverse-difference','0u - ((u32)fractionalT - (u32)((packet->descriptor->unk6 + 255) << 5))')):
        if INITIAL.count(expression)!=1:
            raise ValueError('Unknown fractional-T use')
        body=INITIAL.replace(expression,replacement)
        yield label,body
        yield label+'-mixed',body.replace('* 32.0f','* 32')
    for roles in (('sOffset',),('insetTOffset',),('sOffset','insetTOffset')):
        body=INITIAL
        for role in roles:
            body=body.replace('s32 '+role+',','u32 '+role+',',1)
        label='value-word-arguments-'+'-'.join(roles)
        yield label,body
        yield label+'-mixed',body.replace('* 32.0f','* 32')
    wide=INITIAL.replace('    s32 fractionalT;', '    s64 fractionalT;')
    yield 'value-wide-fractional-T',wide
    yield 'value-wide-fractional-T-mixed',wide.replace('* 32.0f','* 32')
    for label,old,new in (
            ('wide-normal-use','(u32)fractionalT + (u32)insetTOffset','(u32)(s64)fractionalT + (u32)insetTOffset'),
            ('wide-flipped-use','- (u32)fractionalT','- (u32)(s64)fractionalT')):
        body=INITIAL.replace(old,new,1)
        yield 'value-'+label,body
        yield 'value-'+label+'-mixed',body.replace('* 32.0f','* 32')
    for kind in ('u8','s8','u16','s16'):
        body=INITIAL.replace('    s32 flipFlags;', '    '+kind+' flipFlags;')
        yield 'flags-type-'+kind,body
        yield 'flags-type-'+kind+'-mixed',body.replace('* 32.0f','* 32')
    scope=INITIAL.replace('    s32 flipFlags;\n','').replace(flag,
        '    {\n    s32 flipFlags = packet->flipFlags;\n').replace('    gSPScisTextureRectangle',
        '    }\n    gSPScisTextureRectangle',1)
    yield 'flags-type-inner-scope',scope
    yield 'flags-type-inner-scope-mixed',scope.replace('* 32.0f','* 32')
    corners=(('quarterX','(s32)((u32)integerX << 2)'),
        ('quarterY','(s32)((u32)integerY << 2)'),
        ('rightX','(s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2)'),
        ('bottomY','(s32)((u32)((s32)(height - 1.0f) + integerY) << 2)'))
    for label,indices in (('low',(0,1)),('high',(2,3)),('all',(0,1,2,3))):
        body=INITIAL
        assignments=''
        for index in indices:
            name,expression=corners[index]
            if body.count(expression)!=1:
                raise ValueError('Unknown rectangle corner')
            body=body.replace('    s32 animationDelta;', '    s32 '+name+';\n    s32 animationDelta;',1).replace(expression,name,1)
            assignments+='    '+name+' = '+expression+';\n'
        body=body.replace('    gSPScisTextureRectangle',assignments+'    gSPScisTextureRectangle',1)
        yield 'corners-'+label,body
        yield 'corners-'+label+'-mixed',body.replace('* 32.0f','* 32')
    body=INITIAL
    assignments=''
    for name,expression in corners[2:]:
        body=body.replace('    s32 animationDelta;', '    s32 '+name+';\n    s32 animationDelta;',1).replace(expression,name,1)
        assignments+='    '+name+' = '+expression+';\n'
    for name,expression in corners[:2]:
        role='integerX' if name=='quarterX' else 'integerY'
        body=body.replace(expression,role,1)
        assignments+='    '+role+' = '+expression+';\n'
    body=body.replace('    gSPScisTextureRectangle',assignments+'    gSPScisTextureRectangle',1)
    yield 'corners-phase-integers',body
    yield 'corners-phase-integers-mixed',body.replace('* 32.0f','* 32')
    for role in ('integerScaleX','integerScaleY','animationDelta'):
        body=INITIAL.replace('    s32 flipFlags;\n','')
        if role=='integerScaleY':
            body=body.replace(flag,'').replace('    textureT =',flag+'    textureT =',1)
        body=body.replace('flipFlags',role).replace('packet->'+role,'packet->flipFlags')
        yield 'reuse-flag-as-'+role,body
        yield 'reuse-flag-as-'+role+'-mixed',body.replace('* 32.0f','* 32')
    s_initial='''    textureS = (s32)((u32)(s32)(((32.0f - (left - (f32)integerX) * 32.0f) * divisor) /
        (f32)integerScaleX) + (u32)sOffset + 0x2000u);
'''
    for roles in (('S',),('T',),('S','T')):
        body=INITIAL
        if 'S' in roles:
            body=body.replace(s_initial,s_initial.replace('textureS =','sOffset =').replace(' + 0x2000u','')+
                '    textureS = (s32)((u32)sOffset + 0x2000u);\n')
        if 'T' in roles:
            body=body.replace('    textureT = (s32)((u32)fractionalT + (u32)insetTOffset + 0x2000u);',
                '    insetTOffset = (s32)((u32)fractionalT + (u32)insetTOffset);\n'
                '    textureT = (s32)((u32)insetTOffset + 0x2000u);')
        label='formal-update-'+''.join(roles)
        yield label,body
        yield label+'-mixed',body.replace('* 32.0f','* 32')
    # Non-installable probes of read-count priority, not recovered source.
    for count in (1,2,4):
        body=INITIAL.replace('    textureT =','    if (fractionalT) {}\n'*count+'    textureT =',1)
        yield 'priority-probe-'+str(count),body
        yield 'priority-probe-'+str(count)+'-mixed',body.replace('* 32.0f','* 32')
    for roles in (('S',),('T',),('S','T')):
        body=INITIAL
        for role in roles:
            name='step'+role
            original='originalStep'+role
            body=body.replace('    s32 '+name+';', '    s32 '+original+';\n    s32 '+name+';').replace(
                '    '+name+' = numerator / integerScale'+('X' if role=='S' else 'Y')+';',
                '    '+original+' = numerator / integerScale'+('X' if role=='S' else 'Y')+';\n'
                '    '+name+' = '+original+';').replace('(u32)'+name,'(u32)'+original)
        label='original-steps-'+''.join(roles)
        yield label,body
        yield label+'-mixed',body.replace('* 32.0f','* 32')
    start=INITIAL.index('        if (flipFlags & 1) {')
    middle=INITIAL.index('        if (flipFlags & 2) {',start)
    end=INITIAL.index('    gSPScisTextureRectangle',middle)
    closing=INITIAL.rfind('    }',middle,end)
    swapped=INITIAL[:start]+INITIAL[middle:closing]+INITIAL[start:middle]+INITIAL[closing:]
    yield 'reverse-flip-branches',swapped
    yield 'reverse-flip-branches-mixed',swapped.replace('* 32.0f','* 32')
    normal='    textureT = (s32)((u32)fractionalT + (u32)insetTOffset + 0x2000u);\n'
    if INITIAL.count(normal)!=1:
        raise ValueError('Unknown normal texture-T initializer')
    without=INITIAL.replace(normal,'')
    start=without.index('    if (flipFlags != 0) {')
    end=without.index('    gSPScisTextureRectangle',start)
    closing=without.rfind('    }',start,end)
    suffix=without[closing+5:]
    inner=without[start:closing]
    outer=inner.replace('    if (flipFlags != 0) {\n',
        '    if (flipFlags != 0) {\n    '+normal,1)+'    } else {\n    '+normal+'    }'+suffix
    body=without[:start]+outer
    yield 'flow-normal-T-outer-edges',body
    yield 'flow-normal-T-outer-edges-mixed',body.replace('* 32.0f','* 32')
    y_end=inner.rfind('        }')
    routed=inner[:y_end]+'        } else {\n        '+normal+'        }'+inner[y_end+9:]
    body=without[:start]+routed+'    } else {\n    '+normal+'    }'+suffix
    yield 'flow-normal-T-Y-edges',body
    yield 'flow-normal-T-Y-edges-mixed',body.replace('* 32.0f','* 32')
    cast='(s32)(((32.0f - (top - (f32)integerY) * 32.0f) * divisor) / (f32)integerScaleY)'
    expression=INITIAL.replace('    fractionalT = '+cast+';\n','').replace(
        '(u32)fractionalT + (u32)insetTOffset','(u32)(fractionalT = '+cast+') + (u32)insetTOffset',1)
    yield 'flow-assigned-conversion',expression
    yield 'flow-assigned-conversion-mixed',expression.replace('* 32.0f','* 32')
    copied=INITIAL.replace(normal,'    textureT = fractionalT;\n'
        '    textureT = (s32)((u32)textureT + (u32)insetTOffset + 0x2000u);\n')
    yield 'flow-texture-T-copy',copied
    yield 'flow-texture-T-copy-mixed',copied.replace('* 32.0f','* 32')
    for roles in (('S',),('T',),('S','T')):
        body=INITIAL
        for role in roles:
            bit=1 if role=='S' else 2
            body=body.replace('    s32 flipFlags;', '    s32 flip'+role+';\n    s32 flipFlags;').replace(
                '    if (flipFlags != 0) {','    flip'+role+' = flipFlags & '+str(bit)+';\n    if (flipFlags != 0) {',1).replace(
                'if (flipFlags & '+str(bit)+')', 'if (flip'+role+')')
        label='flow-cached-predicate-'+''.join(roles)
        yield label,body
        yield label+'-mixed',body.replace('* 32.0f','* 32')


def shape(out,label):
    raw,functions,_=parse_object(out/(label+'.o'))
    f=functions[FUNCTION]
    data=sections(out/(label+'.elf'))['.text'][1]
    words=struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])
    truth=struct.unpack_from('>346I',(out/'before-retail_rom').read_bytes(),ROM)
    pairs=list(zip(words,truth))
    prefix=len(list(itertools.takewhile(lambda pair:pair[0]==pair[1],pairs)))
    slot_suffix=len(list(itertools.takewhile(lambda pair:pair[0]==pair[1],reversed(pairs))))
    suffix=len(list(itertools.takewhile(lambda pair:pair[0]==pair[1],zip(reversed(words),reversed(truth)))))
    homes=[(hex(i*4),('sw' if word>>26==43 else 'lw' if word>>26==35 else 'lh'),
        (word>>16)&31,hex(word&65535)) for i,word in enumerate(words)
        if word>>26 in (43,35,33) and (word>>21)&31==29 and word&65535<128]
    return dict(prefix=prefix,suffix=suffix,slot_suffix=slot_suffix,homes=homes)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--filter',default='')
    parser.add_argument('--inspect',action='store_true')
    args=parser.parse_args()
    forms_by_name=dict(forms())
    if len(forms_by_name)!=len(list(forms())) or len(set(forms_by_name.values()))!=len(forms_by_name):
        raise ValueError('Duplicate lifetime screen')
    for label,body in forms_by_name.items():
        if args.filter and args.filter not in label:
            continue
        out=args.root/BUILD
        row=json.loads((out/(label+'.json')).read_text()) if args.inspect else measure(args.root,out,label,body)[2]
        print(json.dumps(dict({k:row[k] for k in ('label','words','frame','differences','diagnostics')},
            **shape(out,label))),flush=True)


if __name__=='__main__':
    main()
