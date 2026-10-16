"""Recover one view's live fixed-matrix pair and combined output."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_point_slot_provider as previous
from tools.experiments import game_packet_rectangle as engine
from tools.tests import point_slot_provider_checkpoint as checkpoint
from tools.pad_generated_object import parse_object, emit_padded_assembly
from tools.experiments.game_actor_classifier_candidates import sections

BUILD = 'conker/build/game-view-matrix-prepare'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_C1D70', 'func_15094EA0', 0x15094EA0, 0xC2350, 40
PATHS = previous.PATHS
BASELINE = dict(previous.BASELINE, **checkpoint.AFTER)
build = previous.build
DECLARATIONS = '''extern Mtx *D_800DC2A0[];
void func_150A7A48(f32 left[4][4], f32 right[4][4], f32 product[4][4]);
'''
INITIAL = '''/* Convert the view's live fixed matrix pair, then combine them in order. */
void func_15094EA0(s32 index) {
    f32 model[4][4];
    f32 projection[4][4];

    guMtxL2F(model, D_800DC2A0[D_800BE9C0] + index);
    guMtxL2F(projection, (Mtx *)(D_800BE628 + index * 0x180 +
        D_800BE9C0 * 0x40 + 0x100));
    func_150A7A48(model, projection, D_800D2CA8[index]);
}'''
RAW_SHA256 = 'f3b4ac2e90b166ef949183076ddd7856cd1d78d20136cae6faf0791dab589762'
SLOT_SHA256 = 'e75104f8192e2cc6efdb864042ff6d4a70d2fe911494ac2592cfcfe283849ca6'
RELOCATIONS = {
    12: [['R_MIPS_HI16','D_800BE9C0']],
    16: [['R_MIPS_LO16','D_800BE9C0']],
    24: [['R_MIPS_HI16','D_800DC2A0']],
    36: [['R_MIPS_LO16','D_800DC2A0']],
    48: [['R_MIPS_26','guMtxL2F']],
    60: [['R_MIPS_HI16','D_800BE628']],
    64: [['R_MIPS_HI16','D_800BE9C0']],
    68: [['R_MIPS_LO16','D_800BE9C0']],
    72: [['R_MIPS_LO16','D_800BE628']],
    104: [['R_MIPS_26','guMtxL2F']],
    116: [['R_MIPS_HI16','D_800D2CA8']],
    120: [['R_MIPS_LO16','D_800D2CA8']],
    136: [['R_MIPS_26','func_150A7A48']],
}
RELOCATIONS = {at:[tuple(v) for v in rows] for at,rows in RELOCATIONS.items()}
INTERFACE_PATHS = dict(caller='conker/asm/nonmatchings/game_45B80/func_15019130.s',
    gu_api='conker/include/2.0L/PR/gu.h')
INTERFACE_BASELINE = dict(caller='ce3f6e240cec6e4e8ee5c74e979f0a2ce91c14e364b7a24e3f0781f77e67b619',
    gu_api='bc7761b1d0688b009d82a17776e21782842b652eb5b257088458b9fee8c63cff')
ALL_PATHS, ALL_BASELINE = dict(PATHS,**INTERFACE_PATHS), dict(BASELINE,**INTERFACE_BASELINE)


def freeze(root, out):
    from tools.tests import view_matrix_prepare_checkpoint as current
    out.mkdir(parents=True, exist_ok=True)
    read = Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:current.previous_input(read(p),p,root)), \
            patch.multiple(engine, PATHS=PATHS, BASELINE=BASELINE):
        engine.freeze(root, out)
    for key,path in INTERFACE_PATHS.items():
        current = (root/path).read_bytes()
        if hashlib.sha256(current).hexdigest() != INTERFACE_BASELINE[key]:
            raise ValueError('Changed matrix preparation interface input: '+key)
        fixture = out/('before-'+key)
        if not fixture.exists():
            fixture.write_bytes(current)
        if fixture.read_bytes() != current:
            raise ValueError('Changed matrix preparation interface fixture: '+key)


def recovered_owner(before, body=None, declarations=DECLARATIONS):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15094EA0() {\n    return 0;\n}':
        raise ValueError('Unknown view matrix preparation predecessor')
    result = before[:lo] + (SELECTED if body is None else body) + before[hi:]
    anchor = 'extern f32 D_800D9B20;\n'
    if result.count(anchor) != 1:
        raise ValueError('Unknown view matrix declaration anchor')
    return result.replace(anchor, anchor+declarations, 1)


def forms():
    yield 'typed-pair', INITIAL, DECLARATIONS
    yield 'expanded-view-stride', INITIAL.replace('index * 0x180', '(index * 4 - index) * 0x80'), DECLARATIONS
    yield 'offset-first-output', INITIAL.replace('D_800D2CA8[index]',
        '(f32 (*)[4])(index * 0x40 + (u8 *)D_800D2CA8)'), DECLARATIONS
    yield 'expanded-and-output', INITIAL.replace('index * 0x180', '(index * 4 - index) * 0x80').replace(
        'D_800D2CA8[index]', '(f32 (*)[4])(index * 0x40 + (u8 *)D_800D2CA8)'), DECLARATIONS
    yield 'reversed-local-declarations', INITIAL.replace('    f32 model[4][4];\n    f32 projection[4][4];',
        '    f32 projection[4][4];\n    f32 model[4][4];'), DECLARATIONS
    byte = INITIAL.replace('D_800DC2A0[D_800BE9C0] + index',
        '(Mtx *)(D_800DC2A0[D_800BE9C0] + index * 0x40)')
    yield 'byte-table', byte, DECLARATIONS.replace('extern Mtx *', 'extern u8 *')
    yield 'typed-byte-table', INITIAL.replace('D_800DC2A0[D_800BE9C0] + index',
        '((Mtx *)D_800DC2A0[D_800BE9C0]) + index'), DECLARATIONS.replace('extern Mtx *', 'extern u8 *')
    view = INITIAL.replace('    f32 projection[4][4];', '    f32 projection[4][4];\n    u8 *view;').replace(
        '    guMtxL2F(projection, (Mtx *)(D_800BE628 + index * 0x180 +',
        '    view = D_800BE628 + index * 0x180;\n    guMtxL2F(projection, (Mtx *)(view +')
    yield 'view-stage', view, DECLARATIONS
    yield 'view-stage-first', view.replace('    u8 *view;\n', '').replace(
        '    f32 model[4][4];', '    u8 *view;\n    f32 model[4][4];'), DECLARATIONS
    yield 'view-stage-reversed-sum', view.replace('D_800BE628 + index * 0x180',
        'index * 0x180 + D_800BE628'), DECLARATIONS
    yield 'view-stage-expanded', view.replace('index * 0x180', '(index * 4 - index) * 0x80'), DECLARATIONS
    yield 'group-view-offset', INITIAL.replace('D_800BE628 + index * 0x180 +\n        D_800BE9C0 * 0x40 + 0x100',
        'D_800BE628 + (index * 0x180 + D_800BE9C0 * 0x40 + 0x100)'), DECLARATIONS
    yield 'group-page-offset', INITIAL.replace('D_800BE628 + index * 0x180 +\n        D_800BE9C0 * 0x40 + 0x100',
        'D_800BE628 + index * 0x180 + (D_800BE9C0 * 0x40 + 0x100)'), DECLARATIONS
    for label, address in (
            ('view-record', '(u8 *)(((ProjectedViewFrame95760 *)D_800BE628) + index)'),
            ('view-record-array', '(u8 *)&((ProjectedViewFrame95760 *)D_800BE628)[index]'),
            ('matrix-bank', '(u8 *)(((Mtx (*)[6])D_800BE628) + index)')):
        yield label, INITIAL.replace('D_800BE628 + index * 0x180', address), DECLARATIONS
    yield 'matrix-bank-slot', INITIAL.replace('(Mtx *)(D_800BE628 + index * 0x180 +\n        D_800BE9C0 * 0x40 + 0x100)',
        '&((Mtx (*)[6])D_800BE628)[index][D_800BE9C0 + 4]'), DECLARATIONS


SELECTED = {label:body for label,body,_ in forms()}['view-record']


def measure(root, out, label='selected', body=None, declarations=DECLARATIONS):
    if label == 'baseline':
        raise ValueError('Reserved immutable fixture label')
    freeze(root, out)
    obj, diagnostics = build.compile_owner(root,out,recovered_owner((out/'before-packet_owner').read_text(),body,declarations),label)
    raw, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    data, placed = build.link_owner(root,out,obj,OWNER)
    linked = placed[FUNCTION]
    words = list(struct.unpack_from('>%dI'%(f['size']//4),data,linked['value']))
    truth = struct.unpack_from('>40I',(out/'before-retail_rom').read_bytes(),ROM)
    row = dict(label=label,words=len(words),frame=(-words[0])&65535,
        differences=sum(a != b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(raw[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items()
            if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a != b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj, words, row


def checked_object(obj):
    text, functions, rel = parse_object(obj)
    f = functions[FUNCTION]
    raw = text[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:v for a,v in rel.items() if f['value'] <= a < f['value']+f['size']}
    pools = {n:d for n,(_,d) in sections(obj).items()
        if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw) != 160 or hashlib.sha256(raw).hexdigest() != RAW_SHA256 or bindings != RELOCATIONS or pools:
        raise ValueError('Unknown view matrix preparation object/bindings/pools')
    return raw, bindings


def qualify(root, out):
    obj, words, row = measure(root,out,'qualified')
    checked_object(obj)
    if (row['words'],row['frame'],row['differences'],row['diagnostics']) != (40,152,0,''):
        raise ValueError('Unknown view matrix preparation compiler shape')
    padded = out/'qualified-padded.s'
    padded.write_text(emit_padded_assembly(obj,root/PATHS['packet_original'],filename=OWNER,
        word_patches_path=out/'before-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded.with_suffix('.o')),str(padded)],
        capture_output=True,check=True)
    data, functions = build.link_owner(root,out,padded.with_suffix('.o'),OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value']+160]
    if f['size'] != 160 or slot != (out/'before-retail_rom').read_bytes()[ROM:ROM+160]:
        raise ValueError('View matrix preparation is not byte exact')
    target = out/'predicted-slot.bin'
    if not target.exists():
        target.write_bytes(slot)
    if target.read_bytes() != slot:
        raise ValueError('Changed matrix preparation first slot prediction')
    row = dict(row,slot_bytes=160,body_bytes=160,new_guards=0,byte_exact=True,
        slot_sha256=hashlib.sha256(slot).hexdigest())
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return obj,padded.with_suffix('.o'),words,None,row


def slot_expected_image(before, slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest() != BASELINE['elf']:
        raise ValueError('Unknown matrix preparation predecessor image')
    row = next(r for r in symbol_rows(before) if r[1] == FUNCTION)
    if row[2][1:3] != (ENTRY,12) or len(slot) != 160 or hashlib.sha256(slot).hexdigest() != SLOT_SHA256:
        raise ValueError('Unknown matrix preparation predecessor extent')
    result = bytearray(before)
    at = elf_slot_offset(before,ENTRY,160)
    result[at:at+160] = slot
    struct.pack_into('>I',result,row[0]+8,160)
    return bytes(result)


def expected_inputs(root, out):
    return dict(elf=slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes()),
        packet_owner=recovered_owner((out/'before-packet_owner').read_text()).encode())


def prelink_prediction(root, out):
    from tools.experiments import game_projected_packet_draw as core
    with patch.multiple(core,PATHS=ALL_PATHS,BASELINE=ALL_BASELINE,qualify=qualify,expected_inputs=expected_inputs):
        row = core.prelink_prediction(root,out)
    row.pop('draw_guards')
    row.pop('projected_guards')
    row.update(slot_bytes=160,body_bytes=160,new_guards=0,matched_functions=1,metadata_serialization_bytes=0)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--screens',action='store_true')
    parser.add_argument('--filter',default='')
    parser.add_argument('--qualify',action='store_true')
    parser.add_argument('--prelink',action='store_true')
    args = parser.parse_args()
    if args.qualify or args.prelink:
        print(json.dumps(prelink_prediction(args.root,args.root/BUILD) if args.prelink else
            qualify(args.root,args.root/BUILD)[-1],indent=2))
        return
    for label,body,declarations in forms() if args.screens else (('selected',SELECTED,DECLARATIONS),):
        if args.filter and args.filter not in label:
            continue
        row = measure(args.root,args.root/BUILD,label,body,declarations)[2]
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256')}),flush=True)


if __name__ == '__main__':
    main()
