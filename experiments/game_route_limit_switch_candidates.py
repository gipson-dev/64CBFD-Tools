"""Recover the complete route selector limit switch and its original table."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_slot_reservation_candidates as previous
from tools.experiments.game_route_projection_integration import compile_profile
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object

BUILD='conker/build/game-route-limit-switch'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508E6D0',0x1508E6D0,0xBBB80,44
SOURCE=previous.SOURCE
TABLE,TABLE_ROM=0x8009DA94,0x242554
ORIGINAL='s32 func_1508E6D0() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS[SOURCE]='cdb960c419dc4fee3c450de5c59dabc488e538cb1f1de75a3422f5c1d63b6521'
INPUTS['conker/asm/data/2424E0.rodata.s']='c734fe5ab4d490c6c84cfdb1d4e3d3be1e573a0f3d7f6bc26c352f208efe420a'
INPUTS['conker/asm/CB3D0.s']='dcbd723600e63455ecdcef33eef8929dac0bf75a81ee39d960d044d34a743f06'
SELECTED='''/* Return the limit for the selected route type. */
s32 func_1508E6D0(s32 type) {
    switch (type) {
        case 63: return 1800;
        case 20: return 3200;
        case 34: return 500;
        case 35: return 10000;
        case 22: return 100000;
        case 21: return 500;
        case 33: return 500;
        case 36: return 100000;
        case 25:
        case 64: return 500;
        case 9: return 5000;
        case 56: return 5000;
        case 24:
        case 65: return 100000;
        case 3: return 750;
        case 55: return 1500;
        default: return 100000;
    }
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown route-limit switch predecessor')
    return before.replace(ORIGINAL,body.rstrip())


def payload(obj):
    text,functions,bindings=parse_object(obj);f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    words=list(struct.unpack('>%dI'%(len(raw)//4),raw))
    end=max(i for i,w in enumerate(words) if w==0x03E00008)+2
    if any(words[end:]):raise ValueError('Nonzero switch alignment tail')
    return raw[:end*4],{a-f['value']:v for a,v in bindings.items() if f['value']<=a<f['value']+end*4}


def compile_candidate(root,out,name='selected',body=SELECTED,normal=False,whole=False):
    values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal)
    raw,bindings=payload(obj)
    result=dict(words=len(raw)//4,diagnostics=diagnostics,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    if not whole:
        script=obj.with_suffix('.ld');elf=obj.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(ENTRY,TABLE))
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
            '-o',str(elf),str(obj)],check=True,capture_output=True)
        linked=sections(elf);text=linked['.text'][1][:len(raw)];pool=linked.get('.rodata',(TABLE,b''))[1]
        truth=values['conker/conker.us.bin'][ROM:ROM+WORDS*4]
        result.update(word_differences=sum(a!=b for a,b in zip(struct.iter_unpack('>I',text),struct.iter_unpack('>I',truth)))+abs(len(text)-len(truth))//4,
            table_bytes=len(pool),table_equal=pool[:252]==values['conker/conker.us.bin'][TABLE_ROM:TABLE_ROM+252])
    (out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return obj,result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--normal',action='store_true')
    parser.add_argument('--whole',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(compile_candidate(root,root/BUILD,normal=args.normal,whole=args.whole)[1],indent=2))
