"""Recover the SDK overlay leaf, unsigned bounds and live viewport pointer."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_color_channel_aggregate as previous
from tools.tests import color_channel_aggregate_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_color_state_submit import padded_object

BUILD='conker/build/game-color-overlay-draw'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517F08C',0x1517F08C,0x1AC53C,197
PATHS=dict(previous.PATHS,overlay_gray_owner='conker/src/game/generated_131620.c',overlay_gray_original='conker/asm/131620.s',
    overlay_mode_owner='conker/src/game/generated_FF5C0.c',overlay_mode_original='conker/asm/FF5C0.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    overlay_gray_owner='0cb21d742f06dfc31ff1d062ebbbfddb94f59516249f5689bf95b67b85737ed7',
    overlay_gray_original='f76e314182708e90d38f73153d44ee6e451cbaa652cbd118cb36f3a1b3d0c488',
    overlay_mode_owner='6a47dbc7bc32a3d2d8ee30f1a35fb4c0c7bd336a88ecbce985b93a267e89cca4',
    overlay_mode_original='849d109da395523d4665a03e1257b145a925c448f11e27fcc611c5ead5b69fc4')
build=previous.build
DECLARATIONS='''typedef struct {
    u8 padding00[0x24];
    f32 top, bottom, left, right;
    u8 padding34[0x14C];
} OverlayViewport1AC2F0;
extern u8 *D_800BE628;
#define OVERLAY_VIEWS_1AC2F0 ((OverlayViewport1AC2F0 *)D_800BE628)
'''
INITIAL='''/* Append the channel's RGBA overlay using the live viewport bounds. */
s32 func_1517F08C(s32 cursor, s32 alpha, s32 red, s32 green, s32 blue, s32 channel) {
    Gfx *commands = (Gfx *)cursor;

    gDPPipeSync(commands++);
    gDPSetCombineMode(commands++, G_CC_PRIMITIVE, G_CC_PRIMITIVE);
    gDPSetPrimColor(commands++, 0, 0, red, green, blue, alpha);
    /* The overlay uses coverage-save with the SDK translucent blender. */
    gDPSetOtherMode(commands++, G_CYC_1CYCLE | G_TP_NONE | G_TF_BILERP |
        G_TC_FILT | G_CD_DISABLE | G_AD_DISABLE | 0xF,
        G_ZS_PRIM | G_RM_XLU_SURF | G_RM_XLU_SURF2);
    gDPFillRectangle(commands++,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].left,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].top,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].right,
        (u32)OVERLAY_VIEWS_1AC2F0[channel].bottom);
    return (s32)commands;
}'''
SELECTED=INITIAL.replace('s32 func_1517F08C(s32 cursor,','Gfx *func_1517F08C(Gfx *commands,').replace(
    '    Gfx *commands = (Gfx *)cursor;\n','').replace('return (s32)commands','return commands').replace(
    'G_ZS_PRIM | G_RM_XLU_SURF | G_RM_XLU_SURF2',
    'G_ZS_PRIM | CVG_DST_SAVE | ((G_RM_XLU_SURF | G_RM_XLU_SURF2) & ~CVG_DST_SAVE)')
RAW_SHA='58cd710b808bd4c64bdc566eb77e92c8acef58cd8cf6dabf1179490a9e43bb62'
BINDINGS={132:[('R_MIPS_HI16','D_800BE628')],136:[('R_MIPS_LO16','D_800BE628')]}
CALLERS=(('overlay_gray_owner','generated_131620','overlay_gray_original'),
    ('overlay_mode_owner','generated_FF5C0','overlay_mode_original'))


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,relative in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import color_overlay_draw_checkpoint as installed
            data=installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown overlay draw input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed overlay draw fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517F08C(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4, s32 arg5) {\n    return 0;\n}':
        raise ValueError('Unknown overlay predecessor')
    marker='#include <ultra64.h>\n'
    if before.count(marker)!=1 or 'OverlayViewport1AC2F0' in before:raise ValueError('Unknown overlay declarations')
    body=SELECTED if body is None else body
    result=(before[:lo]+body+before[hi:]).replace(marker,marker+DECLARATIONS,1)
    if '(Gfx *commands,' in body:
        result=result.replace('return func_1517F08C(\n        arg0,','return (s32)func_1517F08C(\n        (Gfx *)arg0,')
        result=result.replace('return func_1517F08C(arg0,','return (s32)func_1517F08C((Gfx *)arg0,')
        result=result.replace('arg0 = func_1517F08C(arg0,','arg0 = (s32)func_1517F08C((Gfx *)arg0,')
    return result


def parts(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return text[f['value']:f['value']+f['size']],{at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']}


def recovered_caller(before):
    old='s32 func_1517F08C();'
    if before.count(old)!=1:raise ValueError('Unknown external overlay declaration')
    result=before.replace(old,'Gfx *func_1517F08C(Gfx *, s32, s32, s32, s32, s32);',1)
    return result.replace('return func_1517F08C(arg0,','return (s32)func_1517F08C((Gfx *)arg0,').replace(
        'arg0 = func_1517F08C(arg0,','arg0 = (s32)func_1517F08C((Gfx *)arg0,')


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    data,placed=build.link_owner(root,out,obj,OWNER);f=placed[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>197I',(out/'before-retail_rom').read_bytes(),ROM));raw,bindings=parts(obj)
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        frame=-(words[0]&65535)+65536 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def checked_parts(data,bindings):
    if len(data)!=788 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete overlay words/bindings')


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED);checked_parts(*parts(obj))
    if row['diagnostics'] or row['differences'] or row['frame'] or row['words']!=197 or row['pools']:
        raise ValueError('Complete overlay is not a direct match')
    before,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'neighbor-before')
    if diagnostics:raise ValueError('Overlay predecessor diagnostics')
    neighbors=same_functions(before,obj,(FUNCTION,))
    padded=padded_object(root,out,obj,'color_provider_original','qualified',OWNER)
    old_padded=padded_object(root,out,before,'color_provider_original','neighbor-before',OWNER)
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Overlay padded neighbors changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=788 or data[f['value']:f['value']+788]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+788]:
        raise ValueError('Padded overlay differs from retail')
    callers=[]
    for key,owner,original in CALLERS:
        content=(out/('before-'+key)).read_text();objects=[];padded_callers=[]
        for stage,text in (('before',content),('after',recovered_caller(content))):
            caller,diagnostics=compile_owner(root,out,text,key+'-'+stage)
            if diagnostics:raise ValueError('Overlay caller diagnostics: '+diagnostics)
            objects.append(caller);padded_callers.append(padded_object(root,out,caller,original,key+'-'+stage,owner))
        count=same_functions(*objects,())
        if same_functions(*padded_callers,())!=count:raise ValueError('Overlay caller set changed')
        callers.append(dict(owner=owner,unchanged_raw_padded_functions=count))
    row.update(direct=True,byte_exact=True,guards=0,unchanged_raw_padded_neighbors=neighbors,
        typed_callers=callers,not_installed=True,no_matching_credit=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true');parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    pointer=INITIAL.replace('s32 cursor,','Gfx *commands,').replace('    Gfx *commands = (Gfx *)cursor;\n','')
    if args.screens:
        for label,body in (('pointer-word-return',pointer),('pointer-return',pointer.replace('s32 func_1517F08C','Gfx *func_1517F08C').replace('return (s32)commands','return commands'))):
            print(json.dumps(measure(root,root/BUILD,label,body)[2],indent=2),flush=True)
    elif args.qualify:print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
    else:print(json.dumps(measure(root,root/BUILD,'initial',SELECTED)[2],indent=2),flush=True)
