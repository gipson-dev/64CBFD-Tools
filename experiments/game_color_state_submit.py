"""Recover the leaf color-state submitter and its precise six-argument interface."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_sequence_event_scan as previous
from tools.tests import sequence_event_scan_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.pad_generated_object import emit_padded_assembly
from tools.experiments.game_graphics_task_submit import same_functions
import subprocess

BUILD = 'conker/build/game-color-state-submit'
OWNER,FUNCTION,ENTRY,ROM,WORDS = 'generated_1AC2F0','func_1517EE40',0x1517EE40,0x1AC2F0,48
PATHS = dict(previous.PATHS,color_owner='conker/src/game/generated_1AC2F0.c',
    color_pair_caller_owner='conker/src/game/generated_1A0100.c',color_pair_caller_original='conker/asm/1A0100.s')
BASELINE = dict(previous.BASELINE,**checkpoint.AFTER,
    color_owner='495aefce2035807b7b0e7b5da2627f63e28593abd295dc2a11b890fb3f213634',
    color_pair_caller_owner='26d36c8badf8011477c7e6a1c0cfbc1ec350ff5772c55f39db80f07e4eef291e',
    color_pair_caller_original='ad048990b60e48ced56bf90140bba42892200b24fee39f147100a73129d4674c')
build = previous.build
DECLARATIONS = '''extern s8 D_800DDDAC[];
extern u8 D_800DDDC0[];
'''
INITIAL = '''/* Publish a channel's RGB transition when its mode or active state requires it. */
void func_1517EE40(s32 red, s32 green, s32 blue, s32 duration, s8 mode, s32 channel) {
    u8 *color;

    if (mode != D_800DDDAC[channel] ||
        D_800DDDB0[channel] < D_800DDE28[channel] ||
        D_800DDDC0[channel] != 0) {
        color = &D_800DDDA0[channel * 3];
        color[1] = green;
        color[2] = blue;
        color[0] = red;
        D_800DDE28[channel] = duration;
        D_800DDDB0[channel] = 0;
        D_800DDDAC[channel] = mode;
        D_800DDDC0[channel] = 0;
    }
}'''
SELECTED = INITIAL
RAW_SHA='3fc4ac5a61a8d3a7bd976be0860b1847317b50340157c306f3e69e302b0c41d7'
BINDINGS={}
for hi,lo,name in ((0x10,0x14,'D_800DDDAC'),(0x28,0x40,'D_800DDDB0'),
        (0x34,0x3C,'D_800DDE28'),(0x44,0x58,'D_800DDDC0'),(0x64,0x68,'D_800DDDA0'),
        (0x7C,0x90,'D_800DDE28'),(0x94,0xA0,'D_800DDDB0'),(0xA4,0xB0,'D_800DDDC0')):
    BINDINGS[hi]=[('R_MIPS_HI16',name)];BINDINGS[lo]=[('R_MIPS_LO16',name)]
CALLERS = (
    ('view_list_caller_owner','generated_49D30','view_list_caller_original',True,
        'void func_1517EE40(s32, s32, s32, s32, s32, s32);',
        'void func_1517EE40(s32, s32, s32, s32, s8, s32);'),
    ('color_pair_caller_owner','generated_1A0100','color_pair_caller_original',False,
        'void func_1517EE40(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s32 arg4,',
        'void func_1517EE40(s32 arg0, s32 arg1, s32 arg2, s32 arg3, s8 arg4,'),
)


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,relative in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import color_state_submit_checkpoint as installed
            data=installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown color submit input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed color submit fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517EE40() {\n    return 0;\n}':raise ValueError('Unknown color submit predecessor')
    marker='#include <ultra64.h>\n'
    if before.count(marker)!=1 or 'extern s8 D_800DDDAC[];' in before:raise ValueError('Unknown color submit declarations')
    return (before[:lo]+(SELECTED if body is None else body)+before[hi:]).replace(marker,marker+DECLARATIONS,1)


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    data,placed=build.link_owner(root,out,obj,OWNER)
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=list(struct.unpack_from('>48I',(out/'before-retail_rom').read_bytes(),ROM))
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        frame=-(words[0]&65535)+65536 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        bindings={at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def recovered_caller(before,old,new):
    if before.count(old)!=1:raise ValueError('Unknown color caller declaration')
    return before.replace(old,new,1)


def padded_object(root,out,obj,original,label,owner):
    script=out/(label+'-padded.s');script.write_text(emit_padded_assembly(obj,out/('before-'+original),
        word_patches_path=out/'before-guards',filename=owner));padded=script.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(script)],capture_output=True,check=True)
    return padded


def parts(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    data=text[f['value']:f['value']+f['size']]
    return data,{at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']}


def checked_parts(data,bindings):
    if len(data)!=192 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete color words/bindings')


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    checked_parts(*parts(obj))
    if row['diagnostics'] or row['differences'] or row['frame']!=8 or row['words']!=48 or row['pools']:
        raise ValueError('Complete color submitter is not a direct match')
    before,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'neighbor-before')
    if diagnostics:raise ValueError('Unexpected predecessor diagnostics')
    neighbors=same_functions(before,obj,(FUNCTION,));padded=padded_object(root,out,obj,'color_provider_original','qualified',OWNER)
    old_padded=padded_object(root,out,before,'color_provider_original','neighbor-before',OWNER)
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Color padded neighbors changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=192 or data[f['value']:f['value']+192]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+192]:
        raise ValueError('Padded color routine differs from retail')
    callers=[]
    for key,owner,original,no_unroll,old,new in CALLERS:
        content=(out/('before-'+key)).read_text();objects=[];padded_callers=[]
        for stage,text in (('before',content),('after',recovered_caller(content,old,new))):
            caller,diagnostics=compile_owner(root,out,text,key+'-'+stage,no_unroll)
            if diagnostics:raise ValueError('Color caller diagnostics: '+diagnostics)
            objects.append(caller);padded_callers.append(padded_object(root,out,caller,original,key+'-'+stage,owner))
        raw_count=same_functions(*objects,());padded_count=same_functions(*padded_callers,())
        if raw_count!=padded_count:raise ValueError('Color caller function sets changed')
        callers.append(dict(owner=owner,unchanged_raw_functions=raw_count,unchanged_padded_functions=padded_count))
    row.update(direct=True,byte_exact=True,guards=0,unchanged_raw_neighbors=neighbors,
        unchanged_padded_neighbors=neighbors,typed_callers=callers,not_installed=True,no_matching_credit=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--qualify',action='store_true');args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1] if args.qualify else measure(root,root/BUILD,'initial',SELECTED)[2],indent=2),flush=True)
