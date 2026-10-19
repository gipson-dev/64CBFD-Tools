"""Recover both modes of the complete type-to-code lookup."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_limit_switch_candidates as previous
from tools.experiments.game_route_projection_integration import compile_profile
from tools.experiments.game_actor_classifier_candidates import sections

BUILD='conker/build/game-route-mode-code'
OWNER,FUNCTION,ENTRY,ROM,WORDS='generated_B3020','func_1508E780',0x1508E780,0xBBC30,71
SOURCE=previous.SOURCE
TABLE,TABLE_ROM,GLOBAL=0x8009DB90,0x242650,0x800D23B0
ORIGINAL='s32 func_1508E780() {\n    return 0;\n}'
INPUTS=dict(previous.INPUTS)
INPUTS.update({
    SOURCE:'ae4ff8288c031c13f92b513b7fd38658de904e66b3b12c7c8f64531458b58abc',
    'conker/retail_word_patches.us.csv':'4bf9c3985355aa28638ceab3610d581701b20e25a69937ed8e85bdad71c15df4',
    'conker/build/conker.us.elf':'50c875272f3f2d883d70b453cbb3a92582d0f65fd0b1ef351b88ce10f8108f72'})
DECLARATIONS='extern s32 D_800D23B0;\n'
SELECTED='''/* Return the mode-dependent code for the selected type. */
s32 func_1508E780(s32 type) {
    if (*(s16 *)((u8 *)D_800D23B0 + 0x16BC) != 0xB8) {
        switch (type) {
            case 20: return 0x28;
            case 63: return 0x2F;
            case 34: return 0x56;
            case 35: return 0x16;
            case 22: return 0x24;
            case 21: return 0x4B;
            case 33: return 0x58;
            case 36: return 0x63;
            case 25: return 0x57;
            case 64: return 0x21;
            case 9: return 0x1D;
            case 56: return 0x7B;
            case 57: return 0x82;
            case 55: return 0x85;
            case 24: return 0x55;
            case 65: return 0x2E;
            case 37: return 0x1060;
            default: return -1;
        }
    } else {
        switch (type) {
            case 8: return -1;
            case 1: return 0x105C;
            case 16: return 0x1019;
            case 2: return 0x1059;
        }
    }
    return -1;
}
'''


def freeze(root,out):
    with patch.object(previous,'INPUTS',INPUTS):return previous.freeze(root,out)


def recovered_owner(before,body=SELECTED):
    if before.count(ORIGINAL)!=1:raise ValueError('Unknown mode-code switch predecessor')
    return before.replace(ORIGINAL,body.rstrip())


def payload(obj):
    with patch.object(previous,'FUNCTION',FUNCTION):return previous.payload(obj)


def compile_candidate(root,out,name='selected',body=SELECTED,normal=False,whole=False):
    values=freeze(root,out)
    unit=recovered_owner(values[SOURCE].decode(),body) if whole else '#include <ultra64.h>\n'+DECLARATIONS+body
    obj,diagnostics=compile_profile(root,out,unit,name,normal);raw,bindings=payload(obj)
    result=dict(words=len(raw)//4,diagnostics=diagnostics,raw_SHA256=hashlib.sha256(raw).hexdigest(),bindings=bindings)
    if not whole:
        script=obj.with_suffix('.ld');elf=obj.with_suffix('.elf')
        script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } .rodata 0x%X : SUBALIGN(4) { *(.rodata) } }\n'%(ENTRY,TABLE))
        subprocess.run(['mips-linux-gnu-ld','-m','elf32btsmip','-T',str(script),'-e',FUNCTION,
            '--defsym=D_800D23B0=0x%X'%GLOBAL,'-o',str(elf),str(obj)],check=True,capture_output=True)
        linked=sections(elf);text=linked['.text'][1][:len(raw)];pool=linked.get('.rodata',(TABLE,b''))[1]
        truth=values['conker/conker.us.bin'][ROM:ROM+WORDS*4]
        result.update(word_differences=sum(a!=b for a,b in zip(struct.iter_unpack('>I',text),struct.iter_unpack('>I',truth)))+abs(len(text)-len(truth))//4,
            table_bytes=len(pool),table_equal=pool[:228]==values['conker/conker.us.bin'][TABLE_ROM:TABLE_ROM+228])
    (out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');return obj,result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--normal',action='store_true')
    parser.add_argument('--whole',action='store_true');args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    print(json.dumps(compile_candidate(root,root/BUILD,normal=args.normal,whole=args.whole)[1],indent=2))
