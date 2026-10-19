"""Recover distance-clamped sine scoring with cached bounds and live eligibility."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_actor_target_timer_matching as previous
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-actor-sine-selector'
SOURCE,OWNER=previous.SOURCE,previous.OWNER
FUNCTION,ENTRY,ROM,WORDS='func_15089F9C',0x15089F9C,0xB744C,136
ORIGINAL='s32 func_15089F9C() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({SOURCE:'faf1daec7d177ba36d35c8ee90c52ef5a253925f0e94cc6100ebbf56cfac52c8',
    'conker/retail_word_patches.us.csv':'bc019c19bbd9b3ae7078f19ed2833ace7895879f76a2ed9e237aeaca1a5a08b8',
    'conker/build/conker.us.elf':'3010db543bf9dd6844ebe7e8eb2b8a7587378d2d23060e5e3c5b9ff6b464fa62',
    'conker/src/libultra/gu/sinf.c':'ae271497692ea1a00abd96bcfed9209458cf8ea694b0df385aa5dddf9fc1a679',
    'conker/asm/nonmatchings/libultra/gu/sinf/sinf.s':'aaa2e4b725d2370cf7cc8f09860753184858f98c2a54635bc4ffad935b5916bd',
    'conker/asm/data/2275E0.data.s':'9c912a5b5595b37b590fb8da13727bf91e1c495b0ff0f297231347417e7d700e',
    'conker/asm/data/23D850.rodata.s':'2867f07fb855cc2f1fef892f626a80b9e509a834d6b2f944d94804afd983be1e',
    'conker/asm/data/2C920.rodata.s':'63b19e902d5b4ee59816782c60057764e8250f8091e7e069f3950f08d37b7acc'})
DECLARATIONS='''extern s32 D_800D23B0;
extern u8 D_800CC2D0[];
extern f32 D_8009DA44;
extern f32 D_8009DA48;
extern f32 D_8009DA4C;
extern f32 D_8009DA50;
extern f32 D_8009DA54;
extern f32 D_8009DA58;
'''
INITIAL='''/* Select the first eligible actor with the greatest distance-weighted sine score. */
s32 func_15089F9C(s32 slot) {
    u8 *state = (u8 *)D_800D23B0;
    s32 *states = (s32 *)(state + 0xE64);
    s32 count = *(s32 *)(state + 0x10);
    u32 activeMask = *(u32 *)(state + 0x14);
    s32 selected = -1;
    s32 slotOffset = slot * 4;
    s32 i;
    u32 bit;
    u8 *actor;
    u8 *sourceActor;
    f32 minimum;
    f32 maximum;
    f32 best;
    f32 factor;
    f32 dx;
    f32 dz;
    f32 distance;
    f32 score;

    if (*(s32 *)(state + slotOffset + 0x15C) == 0) {
        minimum = D_8009DA44;
        maximum = D_8009DA48;
    } else {
        minimum = D_8009DA4C;
        maximum = 8000.0f;
    }
    best = D_8009DA50;
    for (i = 0; i < count; i++) {
        bit = 1U << i;
        if ((states[i] != 3) && (activeMask & bit) &&
            (*(u32 *)((u8 *)D_800D23B0 + slotOffset + 0x16C0) & (bit << 16))) {
            factor = D_8009DA58 / (maximum - minimum);
            actor = D_800CC2D0 + i * 0x32C;
            if (actor != 0) {
                sourceActor = D_800CC2D0 + slot * 0x32C;
                dx = *(f32 *)(sourceActor + 0x14) - *(f32 *)(actor + 0x14);
                dz = *(f32 *)(sourceActor + 0x1C) - *(f32 *)(actor + 0x1C);
                distance = sqrtf(dx * dx + dz * dz);
            } else {
                distance = 32000.0f;
            }
            if (maximum < distance) {
                distance = maximum;
            }
            if (distance < minimum) {
                distance = minimum;
            }
            score = sinf((distance - minimum) * factor + D_8009DA54) + 1.0f;
            if (best < score) {
                best = score;
                selected = i;
            }
        }
    }
    return selected;
}
'''
compile_profile,link_owner=previous.compile_profile,previous.link_owner


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=None):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown sine-selector predecessor')
    return before.replace(ORIGINAL,DECLARATIONS+'\n'+(SELECTED if body is None else body).rstrip())


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']];words=struct.unpack('>%dI'%(len(raw)//4),raw)
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero sine-selector alignment tail')
    return raw[:end*4],{at-f['value']:v for at,v in bindings.items() if f['value']<=at<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    body=SELECTED if body is None else body;values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    image,functions=link_owner(root,out,obj,OWNER);at=functions[FUNCTION]['value']
    words=list(struct.unpack_from('>%dI'%(len(raw)//4),image,at));truth=struct.unpack_from('>136I',values['conker/conker.us.bin'],ROM)
    row=dict(words=len(words),frame=(-words[0])&65535,diagnostics=diagnostics,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    (out/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def candidates():
    yield 'initial',INITIAL
    yield 'state-read-order',INITIAL.replace('    s32 count = *(s32 *)(state + 0x10);\n    u32 activeMask = *(u32 *)(state + 0x14);',
        '    u32 activeMask = *(u32 *)(state + 0x14);\n    s32 count = *(s32 *)(state + 0x10);')
    base=INITIAL.replace('    u8 *state = (u8 *)D_800D23B0;\n','').replace('(state +','((u8 *)D_800D23B0 +')
    yield 'no-context-local',base
    yield 'loop-cursor',INITIAL.replace('states[i]','*states').replace('i < count; i++','i < count; i++, states++')


def lifetime_candidates():
    for order in ('initial','state-read-order'):
        base=dict(candidates())[order]
        phase=base.replace('    f32 score;','    f32 score;\n    f32 phase;').replace(
            '    for (i = 0;', '    phase = D_8009DA54;\n    for (i = 0;').replace(
            ' * factor + D_8009DA54',' * factor + phase')
        yield order+'-cached-phase',phase
        guarded=phase.replace('    phase = D_8009DA54;\n    for',
            '    if (count <= 0) {\n        return selected;\n    }\n    phase = D_8009DA54;\n    for')
        yield order+'-positive-phase',guarded


def fit_candidates():
    base=dict(lifetime_candidates())['state-read-order-cached-phase']
    wrapped=base.replace('    phase = D_8009DA54;\n    for',
        '    if (count > 0) {\n    phase = D_8009DA54;\n    for').replace(
        '    return selected;','    }\n    return selected;')
    yield 'positive-block',wrapped
    signed=wrapped.replace('u32 activeMask = *(u32 *)','s32 activeMask = *(s32 *)')
    yield 'signed-active-mask',signed
    for name,unit in (('unsigned',wrapped),('signed',signed)):
        short=unit.replace('    u8 *sourceActor;\n','').replace(
            '                sourceActor = D_800CC2D0 + slot * 0x32C;\n','').replace(
            '*(f32 *)(sourceActor + 0x14)','*(f32 *)(D_800CC2D0 + slot * 0x32C + 0x14)').replace(
            '*(f32 *)(sourceActor + 0x1C)','*(f32 *)(D_800CC2D0 + slot * 0x32C + 0x1C)')
        yield name+'-direct-source',short
        yield name+'-reuse-distance',short.replace('    f32 score;\n','').replace('score','distance')


def shape_candidates():
    base=dict(fit_candidates())['positive-block']
    opening='''        if ((states[i] != 3) && (activeMask & bit) &&
            (*(u32 *)((u8 *)D_800D23B0 + slotOffset + 0x16C0) & (bit << 16))) {'''
    guards='''        if (states[i] == 3) { continue; }
        if ((activeMask & bit) == 0) { continue; }
        if ((*(u32 *)((u8 *)D_800D23B0 + slotOffset + 0x16C0) & (bit << 16)) == 0) { continue; }'''
    flattened=base.replace(opening,guards).replace('                selected = i;\n            }\n        }','                selected = i;\n            }')
    if flattened==base:raise ValueError('Missing selector eligibility block')
    yield 'continue-gates',flattened
    for label,unit in (('block',base),('continue',flattened)):
        do=unit.replace('    phase = D_8009DA54;\n    for (i = 0; i < count; i++) {',
            '    phase = D_8009DA54;\n    i = 0;\n    do {').replace('    }\n    }\n    return selected;',
            '    } while (++i < count);\n    }\n    return selected;')
        yield label+'-do-loop',do
        cursor=unit.replace('states[i]','*states').replace('i < count; i++','i < count; i++, states++')
        yield label+'-cursor',cursor
    late=flattened.replace('    u32 activeMask = *(u32 *)(state + 0x14);\n','    u32 activeMask;\n').replace(
        '    best = D_8009DA50;','    activeMask = *(u32 *)(state + 0x14);\n    best = D_8009DA50;')
    yield 'late-mask-capture',late


def priority_candidates():
    for label,body in (('cached',dict(lifetime_candidates())['state-read-order-cached-phase']),
                       ('guarded',dict(shape_candidates())['block-do-loop'])):
        yield label+'-register-mask',body.replace('    u32 activeMask','    register u32 activeMask')
        yield label+'-register-count-mask',body.replace('    u32 activeMask','    register u32 activeMask').replace('    s32 count','    register s32 count')
        yield label+'-register-phase',body.replace('    f32 phase;','    register f32 phase;')


def literal_candidates():
    base=dict(shape_candidates())['block-do-loop']
    constants={'D_8009DA44':'750.0f','D_8009DA48':'3500.0f','D_8009DA4C':'1500.0f',
        'D_8009DA50':'-1000000.0f','D_8009DA54':'-1.570796371f','D_8009DA58':'6.283185482f'}
    for label,names in (('tau',('D_8009DA58',)),('phase',('D_8009DA54',)),
                        ('phase-tau',('D_8009DA54','D_8009DA58')),('all',tuple(constants))):
        body=base
        for name in names:body=body.replace(name,constants[name])
        yield 'literal-'+label,body


def advisory_candidates():
    base=dict(shape_candidates())['block-do-loop']
    old='''        if ((states[i] != 3) && (activeMask & bit) &&
            (*(u32 *)((u8 *)D_800D23B0 + slotOffset + 0x16C0) & (bit << 16))) {'''
    nested=base.replace(old,'''        if ((states[i] != 3) && (activeMask & bit)) {
        if (*(u32 *)((u8 *)D_800D23B0 + slotOffset + 0x16C0) & (bit << 16)) {''').replace(
        '                selected = i;\n            }\n        }','                selected = i;\n            }\n        }\n        }')
    yield 'nested-gates',nested
    for label,unit in (('base',base),('nested',nested)):
        reordered=unit.replace('''            factor = D_8009DA58 / (maximum - minimum);
            actor = D_800CC2D0 + i * 0x32C;''','''            actor = D_800CC2D0 + i * 0x32C;
            factor = D_8009DA58 / (maximum - minimum);''')
        yield label+'-early-actor-address',reordered


SELECTED=dict(shape_candidates())['block-do-loop']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--screens',action='store_true')
    p.add_argument('--lifetimes',action='store_true');p.add_argument('--fit',action='store_true')
    p.add_argument('--shapes',action='store_true');p.add_argument('--normal',action='store_true')
    p.add_argument('--priority',action='store_true');p.add_argument('--literals',action='store_true')
    p.add_argument('--advisory',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[2]
    for name,body in (advisory_candidates() if args.advisory else literal_candidates() if args.literals else priority_candidates() if args.priority else shape_candidates() if args.shapes else fit_candidates() if args.fit else lifetime_candidates() if args.lifetimes else candidates() if args.screens else [('selected',SELECTED)]):
        if args.normal:name+='-normal'
        _,_,row=compile_candidate(root,root/BUILD,name,body,normal=args.normal)
        print(json.dumps(dict(name=name,**{k:v for k,v in row.items() if k!='bindings'})),flush=True)
