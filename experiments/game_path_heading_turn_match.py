"""Path heading turn: closed copy/schedule fit, owners and literal image proof."""
import csv,hashlib,io,json,re,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_path_heading_turn_candidates as candidate
from tools.experiments import game_path_heading_turn_roles as roles
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object,ELF_HEADER,SECTION_HEADER,SYMBOL,RELOCATION,read_c_string
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/asm/nonmatchings/game_A28B0/func_15077F64.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='c41bae710fe29ede70d4c1adaaaf38a44fbd8b7c6170b80ff7713063f83b3c8f'
GUARD_SHA='0524361a35e42383eeae5543dd7bb876d311824b5515880d8ed907f24c250353'
RAW_SHA='66da28e68fc511bace7d025bcc67ac03bf7c6d503bfd17ef38887db7e0921ed4'
FITTED_ZERO='27bdffd83c08000025080000afbf00148d0300003c0f00008def00009078013f906b021e3c0700000018c88001f9482190e700008d2a0000000b60c024eeffff014c102101c03825844d0008844e000cc4680014448d2000448e8000c46a001c468021a0a3a7001e00003025468084a0460833010c000000461253813c080000250800008d18000093a7001e3c0e0000a70200788d0300000007688001a76821946f007894790076000d684001cd702101f9282300054a03312b00ff316a0080016028251140000401602025000b282330a400ff0080282591ce00003c18000001c4082a502000078fbf00149318000030e600ffa07802500c0000008d0400008fbf001427bd002803e0000800000000'
BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 20: [('R_MIPS_HI16', 'D_800D2104')], 24: [('R_MIPS_LO16', 'D_800D2104')], 56: [('R_MIPS_HI16', 'D_800D1890')], 72: [('R_MIPS_LO16', 'D_800D1890')], 112: [('R_MIPS_26', 'func_1505A630')], 120: [('R_MIPS_HI16', 'D_800D154C')], 124: [('R_MIPS_LO16', 'D_800D154C')], 168: [('R_MIPS_HI16', 'D_80099A3C')], 216: [('R_MIPS_LO16', 'D_80099A3C')], 136: [('R_MIPS_HI16', 'D_800D1891')], 232: [('R_MIPS_LO16', 'D_800D1891')], 244: [('R_MIPS_26', 'func_15056A00')]}
FITTED_BINDINGS={4: [('R_MIPS_HI16', 'D_800D154C')], 8: [('R_MIPS_LO16', 'D_800D154C')], 20: [('R_MIPS_HI16', 'D_800D2104')], 24: [('R_MIPS_LO16', 'D_800D2104')], 36: [('R_MIPS_HI16', 'D_800D1890')], 48: [('R_MIPS_LO16', 'D_800D1890')], 116: [('R_MIPS_26', 'func_1505A630')], 124: [('R_MIPS_HI16', 'D_800D154C')], 128: [('R_MIPS_LO16', 'D_800D154C')], 140: [('R_MIPS_HI16', 'D_80099A3C')], 216: [('R_MIPS_LO16', 'D_80099A3C')], 220: [('R_MIPS_HI16', 'D_800D1891')], 236: [('R_MIPS_LO16', 'D_800D1891')], 248: [('R_MIPS_26', 'func_15056A00')]}
ROWS = [{'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x14',
  'expected': '0x3c0e0000',
  'replacement': '0x3c0f0000',
  'expected_relocations': 'R_MIPS_HI16:D_800D2104',
  'replacement_relocations': 'R_MIPS_HI16:D_800D2104',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x18',
  'expected': '0x8dce0000',
  'replacement': '0x8def0000',
  'expected_relocations': 'R_MIPS_LO16:D_800D2104',
  'replacement_relocations': 'R_MIPS_LO16:D_800D2104',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x1c',
  'expected': '0x906f013f',
  'replacement': '0x9078013f',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x20',
  'expected': '0x906a021e',
  'replacement': '0x906b021e',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x24',
  'expected': '0xc4680014',
  'replacement': '0x3c070000',
  'expected_relocations': '-',
  'replacement_relocations': 'R_MIPS_HI16:D_800D1890',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x28',
  'expected': '0xfc080',
  'replacement': '0x18c880',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x2c',
  'expected': '0x1d8c821',
  'replacement': '0x1f94821',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x30',
  'expected': '0x8f290000',
  'replacement': '0x90e70000',
  'expected_relocations': '-',
  'replacement_relocations': 'R_MIPS_LO16:D_800D1890',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x34',
  'expected': '0xa58c0',
  'replacement': '0x8d2a0000',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x38',
  'expected': '0x3c0f0000',
  'replacement': '0xb60c0',
  'expected_relocations': 'R_MIPS_HI16:D_800D1890',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x3c',
  'expected': '0x12b1021',
  'replacement': '0x24eeffff',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x40',
  'expected': '0x844c0008',
  'replacement': '0x14c1021',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '0x1c03825',
  'insert_after_relocations': '-',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x44',
  'expected': '0x844d000c',
  'replacement': '0x844d0008',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x48',
  'expected': '0x91ef0000',
  'replacement': '0x844e000c',
  'expected_relocations': 'R_MIPS_LO16:D_800D1890',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x4c',
  'expected': '0x448c2000',
  'replacement': '0xc4680014',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x50',
  'expected': '0x448d8000',
  'replacement': '0x448d2000',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x54',
  'expected': '0xc46a001c',
  'replacement': '0x448e8000',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x58',
  'expected': '0x468021a0',
  'replacement': '0xc46a001c',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x5c',
  'expected': '0x25eeffff',
  'replacement': '0x468021a0',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x60',
  'expected': '0xa3ae001e',
  'replacement': '0xa3a7001e',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x84',
  'expected': '0x93a6001e',
  'replacement': '0x93a7001e',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x88',
  'expected': '0x3c0e0000',
  'replacement': '0x3c0e0000',
  'expected_relocations': 'R_MIPS_HI16:D_800D1891',
  'replacement_relocations': 'R_MIPS_HI16:D_80099A3C',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x94',
  'expected': '0x67880',
  'replacement': '0x76880',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x98',
  'expected': '0x1e67821',
  'replacement': '0x1a76821',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0x9c',
  'expected': '0x94790078',
  'replacement': '0x946f0078',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xa0',
  'expected': '0x946a0076',
  'replacement': '0x94790076',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xa4',
  'expected': '0xf7840',
  'replacement': '0xd6840',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xa8',
  'expected': '0x3c020000',
  'replacement': '0x1cd7021',
  'expected_relocations': 'R_MIPS_HI16:D_80099A3C',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xac',
  'expected': '0x32a3823',
  'replacement': '0x1f92823',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xb0',
  'expected': '0x74a03',
  'replacement': '0x54a03',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xb8',
  'expected': '0x316c0080',
  'replacement': '0x316a0080',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xbc',
  'expected': '0x1603825',
  'replacement': '0x1602825',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xc0',
  'expected': '0x11800004',
  'replacement': '0x11400004',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xc8',
  'expected': '0xb2023',
  'replacement': '0xb2823',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xcc',
  'expected': '0x308700ff',
  'replacement': '0x30a400ff',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xd0',
  'expected': '0xe02025',
  'replacement': '0x802825',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xd4',
  'expected': '0x4f1021',
  'replacement': '0x91ce0000',
  'expected_relocations': '-',
  'replacement_relocations': 'R_MIPS_LO16:D_80099A3C',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xd8',
  'expected': '0x90420000',
  'replacement': '0x3c180000',
  'expected_relocations': 'R_MIPS_LO16:D_80099A3C',
  'replacement_relocations': 'R_MIPS_HI16:D_800D1891',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xdc',
  'expected': '0x44082a',
  'replacement': '0x1c4082a',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xe8',
  'expected': '0x91ce0000',
  'replacement': '0x93180000',
  'expected_relocations': 'R_MIPS_LO16:D_800D1891',
  'replacement_relocations': 'R_MIPS_LO16:D_800D1891',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xec',
  'expected': '0x30e500ff',
  'replacement': '0x30e600ff',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'},
 {'filename': 'game_A28B0',
  'function': 'func_15077F64',
  'offset': '0xf0',
  'expected': '0xa06e0250',
  'replacement': '0xa0780250',
  'expected_relocations': '-',
  'replacement_relocations': '-',
  'note': 'Normalize proven heading-turn register schedules and one redundant row copy',
  'insert_after': '',
  'insert_after_relocations': '',
  'omit': 'false'}]

sha=lambda b:hashlib.sha256(b).hexdigest()

def freeze(root,out):
    path=out/'input-sha256.json'
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze heading turn at its predecessor first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game_83300.c','conker/build/src/game_83300.c.o','conker/asm/nonmatchings/game_83300/func_15056A00.s']
        paths += [p.relative_to(root).as_posix() for p in(root/'conker/include').rglob('*.h')]+[p.relative_to(root).as_posix() for p in(root/'conker/asm/nonmatchings/game_A28B0').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));changed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Heading frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Heading protected input changed: '+name)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items() if start<=at<start+size}

def normalized(raw,bindings,truth):
    if len(raw)!=268 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Heading raw body/bindings changed')
    fitted=bytes.fromhex(FITTED_ZERO)
    if roles.bound_blob(fitted,FITTED_BINDINGS)!=list(struct.unpack('>68I',truth)):raise ValueError('Heading original bytes changed')
    result=bytearray();relocs={};patches={int(r['offset'],0):r for r in ROWS}
    parse=lambda s:[] if s=='-' else [tuple(x.split(':',1)) for x in s.split(';')]
    for i in range(0,len(raw),4):
        word=struct.unpack_from('>I',raw,i)[0];r=patches.get(i);rb=bindings.get(i,[])
        if r:
            if word!=int(r['expected'],0) or rb!=parse(r['expected_relocations']):raise ValueError('Heading expected word/binding changed')
            word=int(r['replacement'],0);rb=parse(r['replacement_relocations'])
        if rb:relocs[len(result)]=rb
        result.extend(struct.pack('>I',word))
        if r and r['insert_after']:result.extend(struct.pack('>I',int(r['insert_after'],0)))
    if bytes(result)!=fitted or relocs!=FITTED_BINDINGS:raise ValueError('Heading fitted words/bindings differ')
    roles.prove(roles.bound_blob(fitted,relocs),roles.bound_blob(raw,bindings))
    return bytes(result),relocs

def guard_manifest(before,raw):
    if sha(before)!=GUARD_SHA or sha(raw)!=RAW_SHA:raise ValueError('Heading guard inputs changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(r['function']==FUNCTION for r in reader):raise ValueError('Heading already guarded')
    s=io.StringIO(newline='');csv.DictWriter(s,fields,lineterminator='\r\n').writerows(ROWS)
    return before+s.getvalue().encode()

def assemble_owner(root,out,obj,manifest,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/'owner.s';result=p/'game_A28B0.c.o'
    asm.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,word_patches_path=guards),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def padded_pools(path):
    data=path.read_bytes();h=ELF_HEADER.unpack_from(data);hs=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
    n=hs[h[13]];strings=data[n[4]:n[4]+n[5]];names=[read_c_string(strings,s[0]) for s in hs];by_name={n:i for i,n in enumerate(names)}
    st=hs[by_name['.symtab']];sn=hs[st[6]];ss=data[sn[4]:sn[4]+sn[5]];symbols=[SYMBOL.unpack_from(data,p) for p in range(st[4],st[4]+st[5],st[9] or SYMBOL.size)];result={}
    for i,s in enumerate(hs):
        if not s[2]&2 or names[i]=='.text':continue
        relocations=[]
        for rel in hs:
            if rel[1]!=9 or rel[7]!=i:continue
            for p in range(rel[4],rel[4]+rel[5],rel[9] or RELOCATION.size):
                at,info=RELOCATION.unpack_from(data,p);v=symbols[info>>8]
                relocations.append((at,info&255,read_c_string(ss,v[0]),v[1],v[3],names[v[5]] if v[5]<len(names) else v[5]))
        raw=bytes(s[5]) if s[1]==8 else data[s[4]:s[4]+s[5]]
        result[names[i]]=(s[1],s[2],s[3],s[8],raw,tuple(relocations))
    return result

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();ws=struct.unpack_from('>%dI'%(len(rom)//4),rom)
    q=dict(calls=[i*4 for i,w in enumerate(ws) if w>>26==3 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],tails=[i*4 for i,w in enumerate(ws) if w>>26==2 and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF],pointers=[i*4 for i,w in enumerate(ws) if w==ENTRY])
    if q!=dict(calls=[],tails=[],pointers=[0x22B464]):raise ValueError('Heading caller census changed')
    return q

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Heading literal inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f) for p,n,f,s in symbol_rows(before) if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Heading predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
        raise ValueError('Heading literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:]) for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:]) for p,n,f,s in symbol_rows(after)):raise ValueError('Heading named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text(encoding='utf-8'));old_guards=(out/'frozen'/GUARDS).read_bytes()
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    clean=lambda t:re.sub(r'build/[^\n]+?\.c, line \d+:','<owner>:',t)
    if re.findall(r'Warning (\d+)',od)!=['665']+['712']*10+['709']*2 or clean(od)!=clean(nd):raise ValueError('Heading owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=function_blob(new);fitted,fb=normalized(raw,bindings,truth);new_guards=guard_manifest(old_guards,raw)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial heading guards installed')
    rn=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Heading compact pools changed')
    oo=assemble_owner(root,out,old,old_guards,'predecessor-owner');no=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(oo if not installed else no).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Heading live owner differs')
    if function_blob(no)!=(fitted,fb):raise ValueError('Heading padded target differs')
    pn=same_functions(oo,no,(FUNCTION,))
    if padded_pools(oo)!=padded_pools(no):raise ValueError('Heading padded pools or overflow changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,oo,'predecessor-image');ne=harness.link_image(root,out,no,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Heading live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b) or aa!=bb or changed!=[FUNCTION] or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Heading body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Heading protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=68,raw_words=67,frame=40,row_byte_home=30,guards=42,inserted_copies=1,bindings=14,raw_neighbors=rn,neighbors=pn,all_pools_unchanged=True,unchanged_warning_712=10,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,caller_census=census(root))
    (out/'proposed-owner.c').write_text(ns,encoding='utf-8');(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
