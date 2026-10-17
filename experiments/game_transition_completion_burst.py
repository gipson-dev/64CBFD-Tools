"""Uninstalled complete C candidate for the transition completion burst.

Equal instruction count and public behavior are not installation permission.
The candidate still has a larger frame and different private instructions.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_fixed_transition_constructor as previous
from tools.tests import fixed_transition_checkpoint as checkpoint
from tools.experiments.game_graphics_task_submit import same_functions
from tools.pad_generated_object import emit_padded_assembly, parse_object

BUILD = 'conker/build/game-transition-completion-burst'
OWNER, FUNCTION, ENTRY, ROM, WORDS = 'generated_FC5F0', 'func_150CF800', 0x150CF800, 0xFCCB0, 251
SIZE = WORDS * 4
FACTORY, ALLOCATOR, MEMCPY = previous.FACTORY, previous.ALLOCATOR, previous.MEMCPY
RANDOM, RANDOM_FLOAT, DIRECTION, SINE, TAG = 0x150ADA20, 0x150ADA68, 0x15143874, 0x15047D60, 0x151D8EBC
MODE, TIMESTEP, TAG_TABLE, POOL = previous.MODE, 0x800BE9A4, 0x8008FCD0, 0x800A0860
PATHS, BASELINE = dict(previous.PATHS), dict(previous.BASELINE, **checkpoint.AFTER)
EXTRA = {
    'burst_constants': ('conker/asm/data/245320.rodata.s', '19a3d2ec69f9e1b51157e05046424c56eee070b672b17ddef6646dc772d4e64d'),
    'burst_dispatch_table': ('conker/asm/data/22F730.rodata.s', 'dbc2d365d91e5a6d0ddc0689cfe7a0c235989f7004e7d6acd3607cee70e9a174'),
    'burst_tag_table': ('conker/asm/data/234790.rodata.s', '7a5cc54bca152c95f83b7335f660f68df469a9a43e0f966ea258950bfac2983e'),
    'burst_dispatcher': ('conker/asm/17CAF0.s', 'a312244a25c771c8c66ffaaa5e148c251cf544d82f5a0908e64f8c5c2446a25e'),
    'burst_tag_owner': ('conker/src/game_2062D0.c', 'f0e096816c0414498b58bc39260a553c196898eb06f04ea106d0317d6a6df1a4'),
    'burst_direction_owner': ('conker/src/game_16EE20.c', '7acc24c75dc922e9aa72027a030b4c8e43b0d2a2d9bc5f8c2a17fccb3dba7810'),
}
for key, (path, sha) in EXTRA.items():
    PATHS[key], BASELINE[key] = path, sha
build, compile_owner, projection = previous.build, previous.compile_owner, previous.projection
DECLARATIONS = '''extern f32 D_800BE9A4;
extern u8 (*D_8008FCD0[])(void);
s32 func_150ADA20(void);
f32 func_150ADA68(void);
void func_15143874(s16, f32, f32 *, f32 *);
f32 sinf(f32);
typedef struct {
    f32 x, y;
} BurstPositionFC5F0;
typedef struct {
    BurstPositionFC5F0 position;
    f32 scale[2];
    u8 tag;
    s16 id;
    u16 flags;
    s16 size0, size1;
    u8 kind, field1B, field1C, field1D, duration, field1F;
    u8 field20, field21, field22, opacity;
    s32 field24, field28, field2C, field30, field34, field38, field3C;
    u8 field40, field41;
    TransitionViewFC5F0 view;
    f32 field48, field4C, field50, field54;
} BurstDescriptorFC5F0;
typedef struct {
    f32 velocityX, velocityY, acceleration, floor;
} BurstPayloadFC5F0;
'''
CANDIDATE = '''/* Advance the transition and emit randomized children on completion. */
s32 func_150CF800(u8 *record) {
    BurstDescriptorFC5F0 descriptor;
    BurstPayloadFC5F0 payload;
    TransitionPayloadFC5F0 *transition;
    f32 progress;
    f32 scale;
    u8 *child;
    s8 count;
    s32 flag0, flag1;

    if (record[0x70] & 1) {
        transition = (TransitionPayloadFC5F0 *)(record + 0x70);
        transition->field04 += 0.1900000125f * D_800BE9A4;
        progress = transition->field04;
        if (progress >= 1.0f) {
            transition->field04 = 1.0f;
            transition->state &= ~1;
            count = (func_150ADA20() & 3) + 2;
            payload.floor = *(f32 *)(record + 0x14) + 15.0f;
            descriptor.position = *(BurstPositionFC5F0 *)(record + 0x10);
            descriptor.size0 = 12;
            descriptor.size1 = 21;
            descriptor.field1B = 0xFF;
            descriptor.field1C = 0xFF;
            descriptor.field1D = 0xFF;
            descriptor.field1F = 0xFF;
            descriptor.field20 = 0xFF;
            descriptor.field21 = 0xFF;
            descriptor.field22 = 0xFF;
            descriptor.opacity = 0xFF;
            descriptor.kind = 0;
            descriptor.field24 = 0;
            descriptor.field28 = 0x200004;
            descriptor.field2C = 0x9F0601;
            descriptor.field40 = 0;
            descriptor.field41 = 10;
            descriptor.field30 = 23;
            descriptor.field34 = 68;
            descriptor.field38 = 128;
            descriptor.field3C = 32;
            descriptor.field48 = 1.0f;
            descriptor.field4C = 1.0f;
            descriptor.field54 = 0.0f;
            descriptor.field50 = 0.0f;
            descriptor.view.byte = D_80082FA0;
            if (count > 0) {
                const f32 twoAndHalf = 2.5f;
                const f32 two = 2.0f;
                do {
                    descriptor.duration = func_150ADA20() % 101U + 155;
                    descriptor.tag = D_8008FCD0[2]();
                    flag1 = func_150ADA20();
                    func_15143874((s16)((u32)flag1 % 65U - 160),
                        func_150ADA68() * two + twoAndHalf, &payload.velocityX, &payload.velocityY);
                    payload.acceleration = func_150ADA68() * 0.3330000043f + 0.4040000141f;
                    scale = func_150ADA68() * 1.789999962f + 1.699999928f;
                    descriptor.scale[0] = scale;
                    descriptor.scale[1] = scale;
                    descriptor.id = func_150ADA20() % 26U + 30;
                    flag0 = 0;
                    if (func_150ADA20() & 1) {
                        flag0 = 2;
                    }
                    if (func_150ADA20() & 1) {
                        flag1 = 4;
                    } else {
                        flag1 = 0;
                    }
                    descriptor.flags = flag1 | 1 | flag0 | 0x38;
                    child = func_1515548C(&descriptor, 13, 0, 0, 16, record[0xC], record[1]);
                    if (child != 0) {
                        memcpy(child + 0x70, &payload, 16);
                    }
                    count--;
                } while (count > 0);
            }
            progress = transition->field04;
        }
        *(f32 *)(record + 0x10) = transition->field08 + progress * transition->field0C;
        *(f32 *)(record + 0x14) = sinf(transition->field04 * 3.141592741f) * -17.5f + 72.0f;
    }
    return 1;
}'''
POOL_BYTES = bytes.fromhex('3e428f5d3fd999993fe51eb83eced9173eaa7efa40490fdb')
RAW_SHA = '7078b69bf81d2546d26b134ae2a7e48cf1763e36b53029102e13469467ed7940'
BINDINGS = {at:[(kind,name)] for name,hi,lo in (
    ('.rodata',96,100), ('D_800BE9A4',104,108), ('D_80082FA0',296,300),
    ('.rodata',436,440), ('.rodata',444,448), ('.rodata',452,456), ('.rodata',460,464),
    ('D_8008FCD0',480,488), ('.rodata',864,880))
    for at,kind in ((hi,'R_MIPS_HI16'),(lo,'R_MIPS_LO16'))}
BINDINGS.update({at:[('R_MIPS_26',name)] for at,name in (
    (168,'func_150ADA20'), (508,'func_150ADA20'), (556,'func_150ADA20'), (564,'func_150ADA68'),
    (624,'func_15143874'), (632,'func_150ADA68'), (648,'func_150ADA68'), (668,'func_150ADA20'),
    (692,'func_150ADA20'), (716,'func_150ADA20'), (796,'func_1515548C'), (816,'memcpy'), (892,'sinf'))})


def checked_parts(raw, bindings):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=BINDINGS:
        raise ValueError('Unknown burst candidate words/bindings')


def freeze(root, out):
    out.mkdir(parents=True, exist_ok=True)
    for key, path in PATHS.items():
        data = (root / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            from tools.tests import transition_child_motion_checkpoint as installed
            data = installed.previous_input(data, path, root)
        if hashlib.sha256(data).hexdigest() != BASELINE[key]:
            raise ValueError('Unknown burst input: ' + key)
        target = out / ('before-' + key)
        if not target.exists():
            target.write_bytes(data)
        if target.read_bytes() != data:
            raise ValueError('Changed burst fixture: ' + key)


def recovered_owner(before, body=CANDIDATE):
    lo, hi = build.function_span(before, FUNCTION)
    if before[lo:hi] != 's32 func_150CF800() {\n    return 0;\n}' or before.count('void func_151CF898') != 1:
        raise ValueError('Unknown burst predecessor')
    return (before[:lo] + body + before[hi:]).replace('void func_151CF898', DECLARATIONS + 'void func_151CF898', 1)


def link_raw(root, out, obj):
    # Only the newly owned temporary link script changes; not the build rules.
    run = subprocess.run
    def invoke(command, *args, **kwargs):
        if str(command[0]) == 'mips-linux-gnu-ld':
            script = Path(command[command.index('-T') + 1])
            text = script.read_text()
            if not text.endswith(' }\n') or '.rodata' in text:
                raise ValueError('Unknown private burst link script')
            script.write_text(text[:-3] + ' .rodata 0x800A0860 : { *(.rodata) } }\n')
        return run(command, *args, **kwargs)
    with patch.object(subprocess, 'run', side_effect=invoke):
        return build.link_owner(root, out, obj, OWNER)


def padded_object(root, out, obj, label):
    text = emit_padded_assembly(obj, out / 'before-tile_original',
        word_patches_path=out / 'before-guards', filename=OWNER, rodata_symbol='D_800A0860')
    path = out / (label + '-padded.s')
    path.write_text(text)
    target = path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as', '-EB', '-march=vr4300', '-o', str(target), str(path)], capture_output=True, check=True)
    return target


def qualify(root, out, body=CANDIDATE, label='candidate'):
    freeze(root, out)
    before = (out / 'before-tile_owner').read_text()
    obj, diag = compile_owner(root, out, recovered_owner(before, body), label)
    old, old_diag = compile_owner(root, out, before, 'owner-before')
    if diag or old_diag:
        raise ValueError('Burst compiler diagnostics')
    sections = projection.sections(obj)
    if sections['.rodata'][1] != POOL_BYTES + bytes(8):
        raise ValueError('Unknown burst literal pool')
    if POOL_BYTES != (out / 'before-retail_rom').read_bytes()[0x245320:0x245338]:
        raise ValueError('Burst pool does not reproduce retail')
    neighbors = same_functions(old, obj, (FUNCTION,))
    padded = padded_object(root, out, obj, label)
    old_padded = padded_object(root, out, old, 'owner-before')
    if same_functions(old_padded, padded, (FUNCTION,)) != neighbors:
        raise ValueError('Burst padded neighbors changed')
    truth = list(struct.unpack_from('>251I', (out / 'before-retail_rom').read_bytes(), ROM))
    images = []
    for path, linker in ((obj, link_raw), (padded, build.link_owner)):
        data, functions = linker(root, out, path) if linker == link_raw else linker(root, out, path, OWNER)
        f = functions[FUNCTION]
        images.append(list(struct.unpack_from('>%dI' % (f['size'] // 4), data, f['value'])))
    if images[0] != images[1]:
        raise ValueError('Burst padder changed candidate instructions')
    raw, functions, relocations = parse_object(obj)
    f = functions[FUNCTION]
    target = raw[f['value']:f['value']+f['size']]
    bindings = {a-f['value']:r for a,r in relocations.items() if f['value'] <= a < f['value']+f['size']}
    if body==CANDIDATE:
        checked_parts(target, bindings)
    changes = [i for i, (a, b) in enumerate(zip(truth, images[0])) if a != b]
    row = dict(words=len(images[0]), retail_words=WORDS, frame=(-images[0][0]) & 65535,
        retail_frame=264, differing_words=len(changes), differing_indices=changes,
        raw_sha256=hashlib.sha256(target).hexdigest(),bindings=bindings,
        unchanged_raw_padded_neighbors=neighbors, literal_pool_bytes=24, new_guards=0, installable=False)
    (out / (label + '-audit.json')).write_text(json.dumps(row, indent=2) + '\n')
    return obj, padded, images, row


def require_installable(row):
    if not row.get('installable') or row['differing_words'] or row['frame'] != row['retail_frame']:
        raise ValueError('Burst still requires complete word/frame/private qualification')
    raise ValueError('No installation path is authorized by this candidate screen')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2), flush=True)
