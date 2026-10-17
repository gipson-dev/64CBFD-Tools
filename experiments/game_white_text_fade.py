"""Qualify the complete white-fade candidate while rejecting its private lifetime gap."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_text_reveal_renderer as previous
from tools.experiments import game_dual_buffer_fade as fade
from tools.experiments import game_dual_fade_argument_home as home
from tools.tests import text_reveal_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions

BUILD='conker/build/game-white-text-fade'
OWNER,FUNCTION,ENTRY,ROM,SIZE='generated_FC5F0','func_150D0534',0x150D0534,0xFD9E4,284
PATHS,BASELINE=dict(previous.PATHS),dict(previous.BASELINE,**checkpoint.AFTER)
PATHS['white_home_source']='tools/experiments/game_dual_fade_argument_home.py'
BASELINE['white_home_source']='46ec7210a7e5c7418d2375dbd9f4b2bdf45e82bdec98c2a32cfa6bdaf406c3cd'
build,compile_owner,parse_object,projection=previous.build,previous.compile_owner,previous.parse_object,previous.projection


def white_body(text):
    return text.replace('func_150D01A0',FUNCTION).replace('*countdown = 8;','*countdown = 20;').replace(
        'count * 31','count * 12').replace('0xCE, 0xC4, 0x61','255, 255, 255').replace('0x92, 0xBE, 0x81','20, 20, 128')


SELECTED=white_body(home.SELECTED)
RAW_SHA='29756ae705f6061063b52afccdde45adc69960fae2844f6c6f99d6d723ad50be'
BINDINGS={56:[('R_MIPS_HI16','D_800BE9E4')],76:[('R_MIPS_LO16','D_800BE9E4')],
    124:[('R_MIPS_26','func_1504332C')],160:[('R_MIPS_26','func_15042D94')],
    208:[('R_MIPS_26','func_1504332C')],248:[('R_MIPS_26','func_15042D94')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,path in PATHS.items():
        data=(root/path).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Changed white-fade live input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed white-fade frozen input: '+key)


def recovered_owner(before,body=SELECTED):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_150D0534() {\n    return 0;\n}':raise ValueError('Unknown white-fade predecessor')
    return before[:lo]+body+before[hi:]


def parts(obj):
    data,fs,rs=parse_object(obj);f=fs[FUNCTION]
    return data[f['value']:f['value']+f['size']],{a-f['value']:r for a,r in rs.items() if f['value']<=a<f['value']+f['size']}


def checked_parts(raw,bindings):
    if len(raw)!=276 or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Changed complete white-fade words/bindings')


def require_installable(words):
    if len(words)!=71:raise ValueError('White-fade complete retail slot required')
    raise ValueError('White-fade S0/private/full-image gates remain unresolved')


def padded_object(root,out,obj,label):return previous.padded_object(root,out,obj,label)


def qualify(root,out):
    freeze(root,out);before=(out/'before-tile_owner').read_text()
    obj,diag=compile_owner(root,out,recovered_owner(before),'candidate')
    old,old_diag=compile_owner(root,out,before,'owner-before')
    if diag or old_diag:raise ValueError('White-fade compiler diagnostics')
    checked_parts(*parts(obj))
    pools=lambda p:{n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old)!=pools(obj):raise ValueError('White-fade pools changed')
    neighbors=same_functions(old,obj,(FUNCTION,))
    padded=padded_object(root,out,obj,'candidate')
    if same_functions(padded_object(root,out,old,'owner-before'),padded,(FUNCTION,))!=neighbors:
        raise ValueError('White-fade padded neighbors changed')
    images=[]
    for path in (obj,padded):
        data,fs=build.link_owner(root,out,path,OWNER)
        images.append(list(struct.unpack_from('>71I',data,fs[FUNCTION]['value'])))
    if images[0]!=images[1] or images[0][-2:]!=[0,0]:raise ValueError('Unknown white-fade raw/padded slot tail')
    truth=list(struct.unpack_from('>71I',(out/'before-retail_rom').read_bytes(),ROM))
    differences=sum(a!=b for a,b in zip(images[0],truth))
    if differences!=62:raise ValueError('Unknown white-fade literal gap')
    row=dict(candidate_words=69,retail_body_words=70,slot_words=71,frame=48,record_home=48,
        weight_home=36,state_home=28,saved_ra_home=20,saves_s0=False,bindings=6,
        full_slot_word_differences=differences,new_guards=0,unchanged_raw_padded_neighbors=neighbors,installed=False)
    (out/'candidate-audit.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded,images,row


def variants():
    staged=SELECTED.replace('s32 currentWeight = 255;','u8 currentWeight = 255;').replace(
        'previousWeight = (count * 12) & 255;\n        currentWeight = (255 - previousWeight) & 255;',
        'previousWeight = count * 12;\n        currentWeight = 255 - (previousWeight & 255);\n        previousWeight &= 255;')
    array=staged.replace('        func_15042D94(20, 20, 128,\n            *(s32 *)(*(u8 **)&record + 0x40 + (*(u8 **)&record)[0x3D] * 4));',
        '        state = *(u8 **)&record + 0x28;\n        func_15042D94(20, 20, 128,\n            ((s32 *)(state + 0x18))[state[0x15]]);').replace(
        '*(s32 *)(state + 0x18 + (state[0x15] ^ 1) * 4)','((s32 *)(state + 0x18))[state[0x15] ^ 1]')
    branch=array.replace('s32 previousWeight = 0;','s32 previousWeight;').replace('u8 currentWeight = 255;','u8 currentWeight;').replace(
        '*countdown = count - (u32) D_800BE9E4;\n    }',
        '*countdown = count - (u32) D_800BE9E4;\n    } else {\n        previousWeight = 0;\n        currentWeight = 255;\n    }')
    return {'normal':white_body(fade.SELECTED),'argument-home':SELECTED,'staged-byte':staged,'staged-array':array,
        'branch-staged-array':branch,'weight-byte':SELECTED.replace('s32 previousWeight = 0;','u8 previousWeight = 0;'),
        'both-byte':SELECTED.replace('s32 previousWeight = 0;','u8 previousWeight = 0;').replace('s32 currentWeight = 255;','u8 currentWeight = 255;'),
        'staged-byte-weight':array.replace('s32 previousWeight = 0;','u8 previousWeight = 0;')}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
