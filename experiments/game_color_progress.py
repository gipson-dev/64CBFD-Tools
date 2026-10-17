"""Recover the signed color-progress accessor without replacing its arithmetic."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_color_state_submit as previous
from tools.tests import color_state_submit_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments.game_graphics_task_submit import same_functions

BUILD = 'conker/build/game-color-progress'
OWNER,FUNCTION,ENTRY,ROM,WORDS = 'generated_1AC2F0','func_1517EF00',0x1517EF00,0x1AC3B0,43
PATHS = dict(previous.PATHS,progress_caller_owner='conker/src/game/generated_205C90.c',
    progress_caller_original='conker/asm/205C90.s')
BASELINE = dict(previous.BASELINE,**checkpoint.AFTER,
    progress_caller_owner='4bd2a441bfd4d77bbc90bfa1e5f217487b11ed77274720a296b4f60d3f36f0f3',
    progress_caller_original='1486d7fdf9a87e5aff20f0dfc427862fd4a55a322990f7e95e082a9666994ff2')
build = previous.build
INITIAL = '''/* Return the channel's signed progress, preserving the 32-bit scaled product. */
s32 func_1517EF00(s32 channel) {
    s32 progress = D_800DDDC0[channel];

    if (progress == 0) {
        if (D_800DDE28[channel] != 0) {
            progress = (s32)((u32)D_800DDDB0[channel] * 255U) / D_800DDE28[channel];
            if (progress > 255) {
                progress = 255;
            }
        } else {
            progress = 255;
        }
        if (D_800DDDAC[channel] == 0) {
            progress = (s32)(255U - (u32)progress);
        }
    }
    return progress;
}'''
SELECTED=INITIAL.replace('s32 progress = D_800DDDC0[channel];','s32 progress;').replace(
    'if (progress == 0) {','if (D_800DDDC0[channel] != 0) {\n        progress = D_800DDDC0[channel];\n    } else {')
RAW_SHA='d66d0a02b48bea527d8547d34a8c33c9216e7e148eca9c55558313f49075b608'
BINDINGS={}
for hi,lo,name in ((0,8,'D_800DDDC0'),(0xC,0x90,'D_800DDDAC'),
        (0x10,0x2C,'D_800DDE28'),(0x30,0x40,'D_800DDDB0')):
    BINDINGS[hi]=[('R_MIPS_HI16',name)];BINDINGS[lo]=[('R_MIPS_LO16',name)]


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,relative in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import color_progress_checkpoint as installed
            data=installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown color progress input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed color progress fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517EF00() {\n    return 0;\n}':raise ValueError('Unknown color progress predecessor')
    return before[:lo]+(SELECTED if body is None else body)+before[hi:]


def parts(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return text[f['value']:f['value']+f['size']],{at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']}


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    data,placed=build.link_owner(root,out,obj,OWNER);f=placed[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>43I',(out/'before-retail_rom').read_bytes(),ROM))
    raw,bindings=parts(obj)
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        frame=-(words[0]&65535)+65536 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def screens():
    split=SELECTED
    yield 'initial',INITIAL
    yield 'split-busy',split
    yield 'split-signed-inverse',split.replace('(s32)(255U - (u32)progress)','255 - progress')
    yield 'split-ternary',split.replace('''        if (D_800DDE28[channel] != 0) {
            progress = (s32)((u32)D_800DDDB0[channel] * 255U) / D_800DDE28[channel];
            if (progress > 255) {
                progress = 255;
            }
        } else {
            progress = 255;
        }''','''        progress = D_800DDE28[channel] != 0 ?
            (s32)((u32)D_800DDDB0[channel] * 255U) / D_800DDE28[channel] : 255;
        if (progress > 255) {
            progress = 255;
        }''')


def checked_parts(data,bindings):
    if len(data)!=172 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete progress words/bindings')


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    checked_parts(*parts(obj))
    if row['diagnostics'] or row['differences'] or row['frame'] or row['words']!=43 or row['pools']:
        raise ValueError('Complete color progress is not a direct match')
    before,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'neighbor-before')
    if diagnostics:raise ValueError('Unexpected progress predecessor diagnostics')
    neighbors=same_functions(before,obj,(FUNCTION,))
    padded=previous.padded_object(root,out,obj,'color_provider_original','qualified',OWNER)
    old_padded=previous.padded_object(root,out,before,'color_provider_original','neighbor-before',OWNER)
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Progress padded neighbors changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=172 or data[f['value']:f['value']+172]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+172]:
        raise ValueError('Padded progress routine differs from retail')
    row.update(direct=True,byte_exact=True,guards=0,unchanged_raw_neighbors=neighbors,
        unchanged_padded_neighbors=neighbors,not_installed=True,no_matching_credit=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screens',action='store_true');parser.add_argument('--qualify',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    if args.qualify:print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
    else:
        for label,body in screens() if args.screens else (('selected',SELECTED),):
            print(json.dumps(measure(root,root/BUILD,label,body)[2],indent=2),flush=True)
