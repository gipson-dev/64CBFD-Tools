"""Recover the ordered frame/view coordinator and software-page age pass."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_view_matrix_prepare as previous
from tools.experiments import game_packet_rectangle as engine
from tools.tests import view_matrix_prepare_checkpoint as checkpoint
from tools.pad_generated_object import parse_object
from tools import pad_c_object
from tools.experiments.game_actor_classifier_candidates import sections

BUILD = 'conker/build/game-frame-sequence'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'game_45B80','func_15019130',0x15019130,0x465E0,185
PATHS = dict(previous.ALL_PATHS,upstream='conker/asm/nonmatchings/game_45B80/func_1501878C.s')
BASELINE = dict(previous.ALL_BASELINE,**checkpoint.AFTER,
    upstream='dd67261a3a124a4ed359fb91fc3552f801e1888562f3659c63c0e8794ae90d5f')
build = previous.build
DECLARATIONS = '''/* Frame-coordinator interfaces recovered from their integer call sites. */
extern u8 D_800DCD27;
void func_1510D864(void);
s32 func_1509BA04(s32);
s32 func_1509BBA0(s32);
s32 func_1501E400(s32);
void func_15034F20(void);
void func_1510B690(void);
void func_1510F800(s32);
s32 func_15113180(void);
s32 func_15113E54(s32);
s32 func_15114188(void);
void func_15044A28(void);
s32 func_150242F8(s32, s32);
s32 func_1501EC38(s32);
s32 func_15020EC4(s32);
s32 func_1501E2F8(s32);
s32 func_15087CC0(void);
void func_1504ADD0(void);
s32 func_1510FC34(s32);
void func_15094EA0(s32);
s32 func_15112A80(s32);
s32 func_151749F8(s32, s32);
s32 func_15188B74(s32);
void func_1516706C(void);
s32 func_151671E8(void);
void func_1502BEE4(void);
s32 func_150A0D8C(void);
s32 func_15113218(void);
s32 func_151738C4(s32);
s32 func_1502C1A4(void);
s32 func_15113C88(void);
s32 func_150636F0(void);
s32 func_15183D28(void);
s32 func_151670C0(void);
s32 func_15177A94(void);
s32 func_151814FC(void);
void func_1517F75C(void);
void func_1517F7B4(void);
s32 func_15036148(void);
void func_1515D6C8(void);

'''
INITIAL = '''/* Run ordered frame/view passes, then age all software-page records. */
s32 func_15019130(void) {
    s32 view;
    u8 slot;
    u32 *page;

    func_1510D864();
    func_1509BA04(0);
    func_1509BBA0(2);
    D_800DCD27 = 0;
    func_10004250();
    func_1501E400(0);
    func_15034F20();
    func_1510B690();
    func_1510F800(0);
    func_15113180();
    if (D_800BEAC0 == 0) {
        func_15113E54(1);
    }
    if (D_800BEAC0 == 0) {
        func_15114188();
    }
    func_15044A28();
    func_15018DFC();
    func_150242F8(1, 0);
    func_1501EC38(0);
    func_150242F8(0, 0);
    func_15020EC4(0);
    func_1501E2F8(0);
    if (*(s8 *)&D_800D23A9 != 0) {
        func_15087CC0();
    }
    func_15122AE0();
    func_1504ADD0();
    func_1510F800(0);
    for (view = 0; view <= D_80082FA0; view++) {
        func_1510FC34(view);
    }
    func_1510B690();
    for (slot = 0; slot <= D_80082FA0; slot++) {
        func_15094EA0(slot);
    }
    func_15112A80(0);
    func_151749F8(D_800BE9F0, 0);
    func_1501C860();
    func_1511FC20(D_800BE9C0);
    func_15188B74(0);
    if (D_800BEAC0 == 0) {
        func_1516706C();
        func_151671E8();
    }
    func_1502BEE4();
    if (D_800BE616 == 0) {
        func_150A0D8C();
    }
    func_15113218();
    func_15188B74(1);
    func_151738C4(D_800BE9F0);
    func_1502C1A4();
    func_15113C88();
    if (D_800CC2B0 != 0) {
        func_150636F0();
    }
    if (D_800BEAC0 == 0) {
        func_15183D28();
        func_151670C0();
        func_15177A94();
    }
    if (D_800BEAC0 == 0) {
        func_151814FC();
    }
    func_1517F75C();
    func_1517F7B4();
    func_15036148();
    func_1515D6C8();

    /* The legacy pointer declaration labels this table's address, not its value. */
    for (page = (u32 *)&D_80043B40; page < (u32 *)&D_80044B20; page += 2) {
        page[1]++;
    }
    return 1;
}'''
RAW_SHA256 = 'dbcbe78409e04795168d1e760db8592e2cf2b52aae4129b0046bbf34f24fdbe4'
SLOT_SHA256 = 'db23322789f9b3e81cddb0417c857bd1d4cd58255f6612a88b96548354c9ec49'
STRUCTURAL_SHA256 = '5d548804c0c295717377c04238424b3aa4fd8f6bf5735ac41a2127ab4ee4d97e'
SERIALIZATION = (
    (('D_80088894','D_800884D4'),(1,0),((0x80088894,0,16,0,65521),(0x800884D4,0,16,0,65521))),
    (('D_80084190','D_80084930'),(1,0),((0x80084190,0,16,0,65521),(0x80084930,0,16,0,65521))),
)
RELOCATIONS = {
    12: [['R_MIPS_26','func_1510D864']],
    20: [['R_MIPS_26','func_1509BA04']],
    28: [['R_MIPS_26','func_1509BBA0']],
    36: [['R_MIPS_HI16','D_800DCD27']],
    40: [['R_MIPS_26','func_10004250']],
    44: [['R_MIPS_LO16','D_800DCD27']],
    48: [['R_MIPS_26','func_1501E400']],
    56: [['R_MIPS_26','func_15034F20']],
    64: [['R_MIPS_26','func_1510B690']],
    72: [['R_MIPS_26','func_1510F800']],
    80: [['R_MIPS_26','func_15113180']],
    88: [['R_MIPS_HI16','D_800BEAC0']],
    92: [['R_MIPS_LO16','D_800BEAC0']],
    104: [['R_MIPS_26','func_15113E54']],
    112: [['R_MIPS_HI16','D_800BEAC0']],
    116: [['R_MIPS_LO16','D_800BEAC0']],
    128: [['R_MIPS_26','func_15114188']],
    136: [['R_MIPS_26','func_15044A28']],
    144: [['R_MIPS_26','func_15018DFC']],
    156: [['R_MIPS_26','func_150242F8']],
    164: [['R_MIPS_26','func_1501EC38']],
    176: [['R_MIPS_26','func_150242F8']],
    184: [['R_MIPS_26','func_15020EC4']],
    192: [['R_MIPS_26','func_1501E2F8']],
    200: [['R_MIPS_HI16','D_800D23A9']],
    204: [['R_MIPS_LO16','D_800D23A9']],
    216: [['R_MIPS_26','func_15087CC0']],
    224: [['R_MIPS_26','func_15122AE0']],
    232: [['R_MIPS_26','func_1504ADD0']],
    240: [['R_MIPS_26','func_1510F800']],
    248: [['R_MIPS_HI16','D_80082FA0']],
    252: [['R_MIPS_LO16','D_80082FA0']],
    272: [['R_MIPS_26','func_1510FC34']],
    304: [['R_MIPS_26','func_1510B690']],
    328: [['R_MIPS_26','func_15094EA0']],
    364: [['R_MIPS_26','func_15112A80']],
    372: [['R_MIPS_HI16','D_800BE9F0']],
    376: [['R_MIPS_LO16','D_800BE9F0']],
    384: [['R_MIPS_26','func_151749F8']],
    392: [['R_MIPS_26','func_1501C860']],
    400: [['R_MIPS_HI16','D_800BE9C0']],
    404: [['R_MIPS_26','func_1511FC20']],
    408: [['R_MIPS_LO16','D_800BE9C0']],
    412: [['R_MIPS_26','func_15188B74']],
    420: [['R_MIPS_HI16','D_800BEAC0']],
    424: [['R_MIPS_LO16','D_800BEAC0']],
    436: [['R_MIPS_26','func_1516706C']],
    444: [['R_MIPS_26','func_151671E8']],
    452: [['R_MIPS_26','func_1502BEE4']],
    460: [['R_MIPS_HI16','D_800BE616']],
    464: [['R_MIPS_LO16','D_800BE616']],
    476: [['R_MIPS_26','func_150A0D8C']],
    484: [['R_MIPS_26','func_15113218']],
    492: [['R_MIPS_26','func_15188B74']],
    500: [['R_MIPS_26','func_151738C4']],
    508: [['R_MIPS_26','func_1502C1A4']],
    516: [['R_MIPS_26','func_15113C88']],
    524: [['R_MIPS_HI16','D_800CC2B0']],
    528: [['R_MIPS_LO16','D_800CC2B0']],
    540: [['R_MIPS_26','func_150636F0']],
    548: [['R_MIPS_HI16','D_800BEAC0']],
    552: [['R_MIPS_LO16','D_800BEAC0']],
    564: [['R_MIPS_26','func_15183D28']],
    572: [['R_MIPS_26','func_151670C0']],
    580: [['R_MIPS_26','func_15177A94']],
    588: [['R_MIPS_HI16','D_800BEAC0']],
    592: [['R_MIPS_LO16','D_800BEAC0']],
    604: [['R_MIPS_26','func_151814FC']],
    612: [['R_MIPS_26','func_1517F75C']],
    620: [['R_MIPS_26','func_1517F7B4']],
    628: [['R_MIPS_26','func_15036148']],
    636: [['R_MIPS_26','func_1515D6C8']],
    644: [['R_MIPS_HI16','D_80043B40']],
    648: [['R_MIPS_HI16','D_80043B40']],
    652: [['R_MIPS_LO16','D_80043B40']],
    656: [['R_MIPS_LO16','D_80043B40']],
}
RELOCATIONS = {a:[tuple(v) for v in rows] for a,rows in RELOCATIONS.items()}
WARNING_SITES = (
    ('func_15018F08','arg0 = func_15174B48(arg0, D_800BE9F0, arg1);'),
    ('func_15019BB8','temp_v0 = func_1501A490(arg0, sp2A, 0, 0, 0, 0);'),
    ('func_15019BB8','temp_v0 = func_151674F8((void *)temp_v0, 4, sp2A, 0);'),
    ('func_15019E60','func_15043384(func_151E8620(func_1501A490(arg0, 0xFF, 0, 0, 0, 0)));'),
)


def freeze(root,out):
    out.mkdir(parents=True,exist_ok=True)
    from tools.tests import frame_sequence_checkpoint as installed
    read = Path.read_bytes
    def previous_input(path):
        return installed.previous_input(read(path),path,root)
    with patch.object(Path,'read_bytes',previous_input), patch.multiple(engine,PATHS=PATHS,BASELINE=BASELINE):
        engine.freeze(root,out)


def recovered_owner(before,body=None):
    lo,hi = build.function_span(before,FUNCTION)
    if before[lo:hi] != 's32 func_15019130() {\n    return 0;\n}':
        raise ValueError('Unknown frame-sequence predecessor')
    result = before[:lo]+(SELECTED if body is None else body)+before[hi:]
    for old in ('// few loops\n','/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_15019130.s. */\n'):
        if result.count(old) != 1:
            raise ValueError('Unknown frame-sequence recovery annotation')
        result = result.replace(old,'',1)
    proto = 's32 func_15019130();'
    if result.count(proto) != 1:
        raise ValueError('Unknown frame-sequence prototype')
    anchor = '/* Generated placeholder declarations. */\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown frame-sequence declaration anchor')
    return result.replace(proto,'s32 func_15019130(void);',1).replace(anchor,DECLARATIONS+anchor,1)


def forms():
    yield 'pair-pointer-limit',INITIAL
    yield 'pair-pointer-equal',INITIAL.replace('page < (u32 *)&D_80044B20','page != (u32 *)&D_80044B20')
    yield 'pair-pointer-fixed',INITIAL.replace('page < (u32 *)&D_80044B20','page != (u32 *)&D_80043B40 + 1016')
    yield 'indexed-ages',INITIAL.replace('    u32 *page;\n','').replace(
        'for (page = (u32 *)&D_80043B40; page < (u32 *)&D_80044B20; page += 2) {\n        page[1]++;',
        'for (view = 0; view < 508; view++) {\n        ((u32 *)&D_80043B40)[view * 2 + 1]++;')
    yield 'signed-flag-value',INITIAL.replace('*(s8 *)&D_800D23A9','(s8)D_800D23A9')
    yield 'reverse-cursor-declarations',INITIAL.replace('    s32 view;\n    u8 slot;', '    u8 slot;\n    s32 view;')


SELECTED = dict(forms())['indexed-ages']


def warning_sites(text,diagnostics):
    lines,source_lines = diagnostics.splitlines(),text.splitlines(keepends=True)
    if len(lines) != 12:
        raise ValueError('Changed frame owner diagnostic count')
    result = []
    for i,(function,statement) in enumerate(WARNING_SITES):
        header,actual,caret = lines[i*3:i*3+3]
        match = re.fullmatch(r'cfe: Warning 712: [^\n]+, line (\d+): illegal combination of pointer and integer',header)
        if match is None or actual.strip() != statement or re.fullmatch(r' [-]+\^',caret) is None:
            raise ValueError('Unknown frame owner diagnostic')
        number = int(match[1])
        if not 0 < number <= len(source_lines) or source_lines[number-1].strip() != statement:
            raise ValueError('Frame owner diagnostic does not identify its physical source line')
        offset = sum(map(len,source_lines[:number-1]))
        lo,hi = build.function_span(text,function)
        if not lo <= offset < hi:
            raise ValueError('Frame owner diagnostic moved to another function')
        result.append((function,712,statement,caret))
    return result


def measure(root,out,label='selected',body=None):
    if label == 'baseline':
        raise ValueError('Reserved immutable fixture label')
    freeze(root,out)
    obj,diagnostics = build.compile_owner(root,out,recovered_owner((out/'before-dispatch_owner').read_text(),body),label)
    raw,functions,rel = parse_object(obj)
    f = functions[FUNCTION]
    data,placed = build.link_owner(root,out,obj,OWNER)
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth = struct.unpack_from('>185I',(out/'before-retail_rom').read_bytes(),ROM)
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a != b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a != b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def checked_object(obj):
    text,functions,rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']}
    pools = {n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw) != 740 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown frame sequence object/bindings/pools')
    return raw,bindings


def qualify(root,out):
    obj,words,row = measure(root,out,'qualified')
    checked_object(obj)
    before = (out/'before-dispatch_owner').read_text()
    _,diagnostics = build.compile_owner(root,out,before,'owner-before')
    expected_warnings = warning_sites(before,diagnostics)
    actual_warnings = warning_sites(recovered_owner(before),row['diagnostics'])
    if actual_warnings != expected_warnings or (row['words'],row['frame'],row['differences']) != (185,40,0):
        raise ValueError('Unknown frame sequence shape or new owner warnings')
    padded = out/'qualified-padded.s'
    padded.write_text(pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,
        word_patches_path=out/'before-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        check=True,capture_output=True)
    data,functions = build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value']+740]
    if f['size'] != 740 or slot != (out/'before-retail_rom').read_bytes()[ROM:ROM+740]:
        raise ValueError('Frame sequence is not byte exact')
    target = out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes() != slot:
        raise ValueError('Changed frame sequence first slot prediction')
    row = dict(row,slot_bytes=740,body_bytes=740,new_guards=0,byte_exact=True,
        target_diagnostics_empty=True,preserved_owner_warnings=4,slot_sha256=hashlib.sha256(slot).hexdigest())
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown frame sequence predecessor ELF')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY,12) or len(slot) != 740 or hashlib.sha256(slot).hexdigest() != SLOT_SHA256:
        raise ValueError('Unknown frame sequence predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before,ENTRY,740)
    result[at:at+740] = slot
    struct.pack_into('>I',result,row[0]+8,740)
    return bytes(result)


def expected_inputs(root,out):
    return dict(elf=serialize_metadata(slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes())),
        dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text()).encode())


def serialize_metadata(data):
    from tools.tests import test_game_actor_burst_packet_match as symbols
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols
    if hashlib.sha256(data).hexdigest() != STRUCTURAL_SHA256:
        raise ValueError('Unknown frame sequence structural prediction')
    result = bytearray(data)
    with patch.object(symbols,'SERIALIZATION',SERIALIZATION):
        symbols.apply_burst_symbol_serialization(result)
    if canonical_symbols(result) != canonical_symbols(data) or sum(a != b for a,b in zip(data,result)) != 16:
        raise ValueError('Changed frame sequence symbol/string serialization accounting')
    return bytes(result)


def prelink_prediction(root,out):
    _,padded,_,_ = qualify(root,out)
    capture = out/'link-inputs.json'
    if not capture.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()} != BASELINE:
            raise ValueError('Frame link capture must precede installation')
        (out/'before-linkscript').write_bytes((root/'conker/build/conker.ld').read_bytes())
        (out/'before-owner.o').write_bytes((root/'conker/build/src'/ (OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Changed frame sequence pre-install link capture')
    link = (out/'before-linkscript').read_text()
    needle = 'build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle) != 1:
        raise ValueError('Expected one frame owner text selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script = out/(name+'.ld')
        script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result = subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:
            raise ValueError(result.stderr)
    before = (out/'before-elf').read_bytes()
    if (out/'prelink-baseline.elf').read_bytes() != before:
        raise ValueError('Frame linked inputs do not reproduce the predecessor')
    expected = expected_inputs(root,out)
    predicted = (out/'prelink-prediction.elf').read_bytes()
    if predicted != expected['elf']:
        raise ValueError('Frame link differs from complete slot/extent prediction')
    hashes = {k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial = out/'initial-prediction.json'
    if not initial.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()} != BASELINE:
            raise ValueError('Frame prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text()) != hashes:
        raise ValueError('Changed first frame sequence prediction')
    row = dict(after=hashes,changed_ELF_bytes=sum(a != b for a,b in zip(before,predicted)),
        metadata_exclusions=0,metadata_serialization_bytes=16,slot_bytes=740,body_bytes=740,new_guards=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    args = parser.parse_args()
    if args.qualify or args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD) if args.prelink else
            qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    for label,body in forms() if args.screens else (('selected',SELECTED),):
        row = measure(args.root,args.root/BUILD,label,body)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256')}),flush=True)


if __name__ == '__main__':
    main()
