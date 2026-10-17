"""Complete dual-buffer fade candidate; reject its unresolved retail lifetime gap."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_link_event_callback as previous
from tools.tests import link_event_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly

BUILD='conker/build/game-dual-buffer-fade'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_FC5F0','func_150D01A0',0x150D01A0,0xFD650,276
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**checkpoint.AFTER)
for key,path,sha in (
    ('link_source','tools/experiments/game_link_event_callback.py','edea955044d44f553fd7302066f44598bc427ac5c93cf8f0ffc7e8871adbc068'),
    ('link_tests','tools/tests/test_game_link_event_callback.py','ba6d39ccdeb52f29a4cdeafb88b4629a4efa2478ccb339579b4d64309bde074a'),
    ('link_checkpoint','tools/tests/link_event_checkpoint.py','4c3751e55ffa9cb152706ab4833db3fcfbb376cdc48dec0be5c1d0024c325116'),
    ('fade_renderer','conker/src/game_70200.c','1b6c11aa53cc96e351f51671daae61669726ff89f45806bc47082d56414dca6b'),
    ('fade_table','conker/asm/data/22D350.rodata.s','1a547f787647501f83fb528379bab87abfcf21a2a13b5a5cc00971003f8c3aeb')):
    PATHS[key],BASELINE[key]=path,sha
build,compile_owner,projection,parse_object=previous.build,previous.compile_owner,previous.projection,previous.parse_object
PROTOTYPES='''void func_1504332C(u8, u8, u8, u8);
void func_15042D94(s32, s32, u8, s32, ...);
'''
SELECTED='''/* Blend the live text buffer and its predecessor using the signed countdown. */
s32 func_150D01A0(u8 *record) {
    s8 *countdown;
    s32 count;
    s32 previousWeight = 0;
    s32 currentWeight = 255;
    u8 *state;

    countdown = *(s8 **)(record + 0x48);
    if (record[0x30] & 1) {
        *countdown = 8;
    }
    count = *countdown;
    if (count > 0) {
        previousWeight = (count * 31) & 255;
        currentWeight = (255 - previousWeight) & 255;
        *countdown = count - (u32) D_800BE9E4;
    }
    if (currentWeight != 0) {
        func_1504332C(0xCE, 0xC4, 0x61, currentWeight);
        func_15042D94(0x92, 0xBE, 0x81,
            *(s32 *)(record + 0x40 + record[0x3D] * 4));
    }
    if (previousWeight != 0) {
        state = record + 0x28;
        func_1504332C(0xCE, 0xC4, 0x61, previousWeight & 255);
        func_15042D94(0x92, 0xBE, 0x81,
            *(s32 *)(state + 0x18 + (state[0x15] ^ 1) * 4));
    }
    return 1;
}'''
RAW_SHA='e0058c9fb6336f0c05c7eac7b85bc0ba35b0f5307850d6aa4886b97763c942a7'
BINDINGS={56:[('R_MIPS_HI16','D_800BE9E4')],68:[('R_MIPS_LO16','D_800BE9E4')],
    120:[('R_MIPS_26','func_1504332C')],152:[('R_MIPS_26','func_15042D94')],
    188:[('R_MIPS_26','func_1504332C')],228:[('R_MIPS_26','func_15042D94')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import text_buffer_constructor_checkpoint as latest
            data=latest.previous_input(data,path,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed dual-buffer live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed dual-buffer frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150D01A0() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n')!=1:
        raise ValueError('Unknown dual-buffer placeholder')
    return (before[:lo]+body+before[hi:]).replace('#include <ultra64.h>\n','#include <ultra64.h>\n'+PROTOTYPES,1)


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=260 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed dual-buffer words/bindings')


def require_installable(words):
    if len(words)!=69:raise ValueError('Dual-buffer retail extent/lifetimes remain unresolved')
    raise ValueError('Dual-buffer literal/private/caller/fault/image gates remain unqualified')


def padded_object(root,out,obj,label):
    text=emit_padded_assembly(obj,out/'before-tile_original',word_patches_path=out/'before-guards',
        filename=OWNER,rodata_symbol='D_800A0860')
    asm=out/(label+'-padded.s');asm.write_text(text);target=asm.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(target),str(asm)],capture_output=True,check=True)
    return target


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('Dual-buffer compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('Dual-buffer owner pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,))
    padded,old_padded=padded_object(root,out,obj,'candidate'),padded_object(root,out,old,'owner-before')
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Dual-buffer padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER);f=fs[FUNCTION]
        images.append(list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value'])))
    if images[0]!=images[1]:raise ValueError('Unexpected dual-buffer normalization')
    row=dict(words=65,retail_words=69,frame=48,new_guards=0,bindings=6,
        unchanged_raw_padded_neighbors=neighbors,saved_s0='record',previous_weight_home=36,
        retail_saved_s0='previousWeight',retail_record_home=48,retail_state_home=32,installable=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


def profile_compile(root,out,body,label,flags):
    run=subprocess.run
    def invoke(command,*args,**kwargs):
        if str(command[0])==str(root/'ido/ido5.3_recomp/cc'):
            command=[x for x in command if x not in ('-O2','-g3')]+list(flags)
        return run(command,*args,**kwargs)
    with patch.object(subprocess,'run',side_effect=invoke):
        return compile_owner(root,out,recovered_owner((out/'before-tile_owner').read_text(),body),label)


def profiles(root,out):
    freeze(root,out);rows=[]
    branch=SELECTED.replace('s32 previousWeight = 0;','s32 previousWeight;').replace('s32 currentWeight = 255;','u8 currentWeight;').replace(
        '*countdown = count - (u32) D_800BE9E4;\n    }',
        '*countdown = count - (u32) D_800BE9E4;\n    } else {\n        previousWeight = 0;\n        currentWeight = 255;\n    }')
    for label,body,flags in (
            ('normal',SELECTED,('-O2','-g3')),('nodebug',SELECTED,('-O2',)),
            ('o1',SELECTED,('-O1','-g3')),('branch-weights',branch,('-O2','-g3')),
            ('register-branch',branch.replace('s32 previousWeight;','register s32 previousWeight;'),('-O2','-g3')),
            ('staged-weight',SELECTED.replace('previousWeight = (count * 31) & 255;\n        currentWeight = (255 - previousWeight) & 255;',
                'previousWeight = count << 5;\n        previousWeight -= count;\n        currentWeight = 255 - (previousWeight & 255);\n        previousWeight &= 255;'),('-O2','-g3'))):
        obj,diag=profile_compile(root,out,body,'profile-'+label,flags)
        raw,bindings=parts(obj);words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
        if diag:raise ValueError('Dual-buffer profile diagnostics')
        rows.append(dict(label=label,flags=flags,words=len(words),frame=(-words[0])&65535,
            sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,installable=False))
    (out/'profiles.json').write_text(json.dumps(rows,indent=2)+'\n')
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profiles',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    print(json.dumps(profiles(root,out) if args.profiles else qualify(root,out)[-1],indent=2),flush=True)
