"""Recover the live channel-state aggregate and its saved floating zero."""
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_color_progress as previous
from tools.tests import color_progress_checkpoint as checkpoint
from tools.experiments.game_view_list_setup import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.experiments.game_graphics_task_submit import same_functions
from tools.experiments.game_color_state_submit import padded_object

BUILD='conker/build/game-color-channel-aggregate'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_1AC2F0','func_1517EFDC',0x1517EFDC,0x1AC48C,44
PATHS=dict(previous.PATHS,aggregate_caller_owner='conker/src/game/generated_20AE20.c',
    aggregate_caller_original='conker/asm/20AE20.s')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    aggregate_caller_owner='91c7ba768274a1783570e0c4b40c3080f591a865ecabbe84cf52d19cabea1b7e',
    aggregate_caller_original='b285f38871e2bc048fc6e576c20c731ce3dc743b8ccace0fac036b546daaa8c4')
build=previous.build
SELECTED='''/* Test whether every live channel has positive progress or float state. */
s32 func_1517EFDC(void) {
    s32 channel;
    s32 active = -1;

    for (channel = 0; channel <= D_80082FA0; channel++) {
        if (func_1517EF00(channel) > 0 || D_800DDDC8[channel] > 0.0f) {
            active++;
        }
    }
    if (active == D_80082FA0) {
        return 1;
    }
    return 0;
}'''
RAW_SHA='2a218119a8ddf6a48897a341fb0b7b7049a40c0c5661f93342ebc484928f3af6'
BINDINGS={8:[('R_MIPS_HI16','D_80082FA0')],12:[('R_MIPS_LO16','D_80082FA0')],
    52:[('R_MIPS_HI16','D_800DDDC8')],60:[('R_MIPS_LO16','D_800DDDC8')],
    64:[('R_MIPS_26','func_1517EF00')]}


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    for key,relative in PATHS.items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:
            from tools.tests import color_channel_aggregate_checkpoint as installed
            data=installed.previous_input(data,relative,root)
        if hashlib.sha256(data).hexdigest()!=BASELINE[key]:raise ValueError('Unknown color aggregate input: '+key)
        target=out/('before-'+key)
        if not target.exists():target.write_bytes(data)
        if target.read_bytes()!=data:raise ValueError('Changed color aggregate fixture: '+key)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1517EFDC() {\n    return 0;\n}':raise ValueError('Unknown color aggregate predecessor')
    return before[:lo]+(SELECTED if body is None else body)+before[hi:]


def parts(obj):
    text,functions,relocations=parse_object(obj);f=functions[FUNCTION]
    return text[f['value']:f['value']+f['size']],{at-f['value']:uses for at,uses in relocations.items() if f['value']<=at<f['value']+f['size']}


def measure(root,out,label,body):
    freeze(root,out)
    obj,diagnostics=compile_owner(root,out,recovered_owner((out/'before-color_owner').read_text(),body),label)
    data,placed=build.link_owner(root,out,obj,OWNER);f=placed[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,f['value']))
    truth=list(struct.unpack_from('>44I',(out/'before-retail_rom').read_bytes(),ROM))
    raw,bindings=parts(obj)
    row=dict(label=label,words=len(words),differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),
        frame=-(words[0]&65535)+65536 if words[0]>>16==0x27BD else 0,diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw).hexdigest(),bindings=bindings,
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d})
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n');return obj,words,row


def checked_parts(data,bindings):
    if len(data)!=176 or hashlib.sha256(data).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown complete aggregate words/bindings')


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED);checked_parts(*parts(obj))
    if row['diagnostics'] or row['differences'] or row['frame']!=48 or row['words']!=44 or row['pools']:
        raise ValueError('Complete color aggregate is not a direct match')
    before,diagnostics=compile_owner(root,out,(out/'before-color_owner').read_text(),'neighbor-before')
    if diagnostics:raise ValueError('Unexpected aggregate predecessor diagnostics')
    neighbors=same_functions(before,obj,(FUNCTION,))
    padded=padded_object(root,out,obj,'color_provider_original','qualified',OWNER)
    old_padded=padded_object(root,out,before,'color_provider_original','neighbor-before',OWNER)
    if same_functions(old_padded,padded,(FUNCTION,))!=neighbors:raise ValueError('Aggregate padded neighbors changed')
    data,functions=build.link_owner(root,out,padded,OWNER);f=functions[FUNCTION]
    if f['size']!=176 or data[f['value']:f['value']+176]!=(out/'before-retail_rom').read_bytes()[ROM:ROM+176]:
        raise ValueError('Padded aggregate differs from retail')
    row.update(direct=True,byte_exact=True,guards=0,unchanged_raw_neighbors=neighbors,
        unchanged_padded_neighbors=neighbors,not_installed=True,no_matching_credit=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return obj,padded,words,row


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD)[-1],indent=2),flush=True)
