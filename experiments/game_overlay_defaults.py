"""Recover the complete mode-dependent overlay-channel reset directly from C."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_mirrored_texture_rectangles as previous
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import parse_object

BUILD = 'conker/build/game-overlay-defaults'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_1AC2F0', 'func_15181E18', 0x15181E18, 0x1AF2C8, 50
SIZE = WORDS * 4
PATHS = dict(previous.PATHS, reset_caller_original='conker/asm/CB3D0.s', reset_caller_owner='conker/src/game/generated_CB3D0.c')
BASELINE = dict(previous.BASELINE, reset_caller_original='dcbd723600e63455ecdcef33eef8929dac0bf75a81ee39d960d044d34a743f06',
    reset_caller_owner='898ae03067a45599844b0aadc20161340ebd76f155b04c16ed1b84194418125f')
build, compile_owner, projection = previous.build, previous.compile_owner, previous.projection
DECLARATIONS = 'extern u8 D_800BE616, D_800DDE3C[];\nextern f32 D_800A72B4;\n'
SELECTED = '''/* Reset a channel to its mode-dependent overlay defaults. */
void func_15181E18(s32 channel) {
    u8 *color;
    f32 *projected;

    if (D_800BE616 != 0) {
        color = &D_800DDDA0[channel * 3];
        color[0] = 0;
        color[1] = 0;
        color[2] = 0;
        D_800DDE28[channel] = 25;
        D_800DDDB0[channel] = 0;
        D_800DDDAC[channel] = 0;
        D_800DDDC0[channel] = 0;
        return;
    }
    D_800DDE3C[channel] = 1;
    D_800DDDC8[channel] = 1.0f;
    projected = D_800DDDE8[channel];
    projected[0] = 0.0f;
    projected[1] = 0.0f;
    D_800DDDD8[channel] = D_800A72B4;
}'''
RAW_SHA = '9b171dacb65c9703a0b2b640833a752be493b5383d5f6e4b08a7bf08426a82e0'
BINDINGS = {}
for hi, lo, name in ((0,4,'D_800BE616'), (20,24,'D_800DDDA0'), (36,60,'D_800DDE28'),
        (64,72,'D_800DDDB0'), (76,84,'D_800DDDAC'), (88,100,'D_800DDDC0'), (104,116,'D_800DDE3C'),
        (128,156,'D_800DDDC8'), (144,148,'D_800DDDE8'), (164,176,'D_800A72B4'), (180,188,'D_800DDDD8')):
    BINDINGS[hi], BINDINGS[lo] = [('R_MIPS_HI16',name)], [('R_MIPS_LO16',name)]


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            from tools.tests import overlay_defaults_checkpoint as installed
            data = installed.previous_input(data, path, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown overlay reset input: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed overlay reset fixture: ' + key)


def recovered_owner(before, body=SELECTED):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_15181E18() {\n    return 0;\n}' or before.count('#include <ultra64.h>\n') != 1:
        raise ValueError('Unknown overlay reset source predecessor')
    return (before[:lo] + body + before[hi:]).replace('#include <ultra64.h>\n', '#include <ultra64.h>\n' + DECLARATIONS, 1)


def parts(obj):
    data, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    return data[f['value']:f['value'] + f['size']], {a-f['value']:v for a,v in relocations.items() if f['value'] <= a < f['value']+f['size']}


def checked_parts(raw, bindings, pool):
    if len(raw) != SIZE or hashlib.sha256(raw).hexdigest() != RAW_SHA or bindings != BINDINGS or pool != projection.POOL:
        raise ValueError('Unknown complete overlay reset words, bindings or inherited pool')


def qualify(root, out):
    freeze(root, out)
    obj, diagnostics = compile_owner(root, out, recovered_owner((out/'before-color_owner').read_text()), 'qualified')
    checked_parts(*parts(obj), projection.sections(obj)['.rodata'][1])
    if diagnostics:
        raise ValueError('Overlay reset compiler diagnostics')
    old, diagnostics = compile_owner(root, out, (out/'before-color_owner').read_text(), 'owner-before')
    if diagnostics:
        raise ValueError('Overlay reset predecessor diagnostics')
    neighbors = same_functions(old, obj, (FUNCTION,))
    pools = lambda p: {n:d for n,(_,d) in projection.sections(p).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss'))}
    if pools(old) != pools(obj):
        raise ValueError('Overlay reset changed owner pools')
    padded = projection.padded_object(root, out, obj, 'qualified')
    old_padded = projection.padded_object(root, out, old, 'owner-before')
    if same_functions(old_padded, padded, (FUNCTION,)) != neighbors:
        raise ValueError('Overlay reset changed padded neighbor')
    images = []
    for p in (obj, padded):
        data, functions = build.link_owner(root, out, p, OWNER)
        f = functions[FUNCTION]
        if f['size'] != SIZE or data[f['value']:f['value']+SIZE] != (out/'before-retail_rom').read_bytes()[ROM:ROM+SIZE]:
            raise ValueError('Overlay reset is not a complete direct raw/padded match')
        images.append(list(struct.unpack_from('>50I', data, f['value'])))
    row = dict(words=WORDS, frame=0, differences=0, direct=True, bindings=len(BINDINGS), new_guards=0,
        unchanged_raw_padded_neighbors=neighbors, inherited_pool_unchanged=True, diagnostics='')
    (out/'qualification.json').write_text(json.dumps(row, indent=2)+'\n')
    return obj, padded, images, row


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root/BUILD)[-1], indent=2), flush=True)
