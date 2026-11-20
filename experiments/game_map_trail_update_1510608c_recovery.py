"""Private recovery of the registered map-trail update; no matching credit."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
BUILD = 'conker/build/game-map-trail-update-1510608c-private'
OUT = ROOT / BUILD
SOURCE = 'conker/src/game/generated_133190.c'
FUNCTION = 'func_1510608C'
ENTRY, ROM, WORDS, FRAME = 0x1510608C, 0x13353C, 85, 0x30
STUB = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_133190/func_1510608C.s")'

PREAMBLE = '''typedef struct {
    u8 header[0x40];
    MapTrailPoint133190 position;
} MapTrailChild133190;
extern s32 (*D_80088C10[2])(u8 *, u8 *);
extern s32 D_800BE9E4;
void func_1516972C(struct102 *);
'''

BODY = '''/* Update the trail curve, sample timer and both endpoint effects.
 * The registered callback takes struct102 *; casts expose trail-specific fields.
 */
void func_1510608C(struct102 *node) {
    s32 (*update)(u8 *, u8 *);
    u8 changed = 0;
    u32 random;

    if (((MapTrailRecord133190 *)node)->packet.flag != -1 &&
            (update = D_80088C10[((MapTrailRecord133190 *)node)->packet.flag]) != 0 &&
            update((u8 *)node, &changed) == 0) {
        func_1516972C(node);
    }
    if (((MapTrailRecord133190 *)node)->packet.enabled & 1) {
        ((MapTrailRecord133190 *)node)->packet.duration = (u32)(s32)((MapTrailRecord133190 *)node)->packet.duration - (u32)D_800BE9E4;
        if (((MapTrailRecord133190 *)node)->packet.duration < 0) {
            func_1516972C(node);
        }
    }
    if (changed != 0) {
        func_15106214((MapTrailRecord133190 *)node);
    }
    ((MapTrailRecord133190 *)node)->timer = (u32)(s32)((MapTrailRecord133190 *)node)->timer - (u32)D_800BE9E4;
    if (((MapTrailRecord133190 *)node)->timer < 0) {
        func_15106610((MapTrailRecord133190 *)node);
        random = (u32)func_150ADA20();
        ((MapTrailRecord133190 *)node)->timer = random % (((MapTrailRecord133190 *)node)->packet.maximum + 1) + ((MapTrailRecord133190 *)node)->packet.minimum;
    }
    if (((MapTrailRecord133190 *)node)->children[0] != 0) {
        ((MapTrailChild133190 *)((MapTrailRecord133190 *)node)->children[0])->position = ((MapTrailRecord133190 *)node)->packet.points[0];
    }
    if (((MapTrailRecord133190 *)node)->children[1] != 0) {
        ((MapTrailChild133190 *)((MapTrailRecord133190 *)node)->children[1])->position = ((MapTrailRecord133190 *)node)->packet.points[3];
    }
}'''


def source():
    base = OUT / 'baseline'
    fp = json.loads((base / 'fingerprints.json').read_text())
    snapshot = base / SOURCE
    assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == fp['inputs'][SOURCE]
    before = snapshot.read_text()
    assert before.count(STUB) == 1
    after = before.replace(STUB, PREAMBLE + '\n' + BODY, 1)
    # The real removal service is void(struct102 *); qualify all three old
    # implicit calls in this owner rather than leave conflicting declarations.
    for expression in ('*(u8 **)(arg0 + 0x6C)', '*(u8 **)(arg0 + 0x70)',
                       '*(s32 volatile *)(temp_a1 + 0x30)'):
        old = 'func_1516972C(' + expression + ');'
        assert after.count(old) == 1
        after = after.replace(old, 'func_1516972C((struct102 *)' + expression + ');')
    return before, after


def bind(raw, refs):
    symbols = {'memcpy': 0x10022EC0, 'bzero': 0x100226F0}
    for rows in refs.values():
        for _, name in rows:
            if name.startswith(('D_', 'func_')):
                symbols.setdefault(name, int(name.split('_')[1], 16))
    return bound_blob(raw, refs, symbols)


def screen():
    out = OUT / 'screen'
    out.mkdir(parents=True, exist_ok=True)
    before, after = source()
    old, old_diagnostics = compile_owner(ROOT, out, before, 'before')
    obj, diagnostics = compile_owner(ROOT, out, after, 'candidate')
    raw, refs = payload(obj, FUNCTION)
    words = bind(raw, refs)
    retail = struct.unpack_from('>%dI' % WORDS, (ROOT / 'conker/conker.us.bin').read_bytes(), ROM)
    assert tuple(words) == retail, 'The selected C is no longer a direct match'
    assert ((-words[0]) & 65535) == FRAME
    for label, path in (('before', old), ('candidate', obj)):
        result = subprocess.run(['mips-linux-gnu-objdump', '-dr', str(path)], capture_output=True, text=True, check=True)
        (out / (label + '-disassembly.txt')).write_text(result.stdout)
    assert normalized_pools(old) == normalized_pools(obj), 'Owner pools changed'
    clean = lambda t: re.sub(r'\S+\.c, line \d+:', '<owner>:', t)
    assert clean(old_diagnostics) == clean(diagnostics), (old_diagnostics, diagnostics)
    result = dict(function=FUNCTION, source_installed=False, credit=0,
                  words=len(words), frame=(-words[0]) & 65535,
                  positional_differences=sum(a != b for a, b in zip(words, retail)) + abs(len(words)-WORDS),
                  unchanged_neighbors=same_functions(old, obj, (FUNCTION,)), pools_unchanged=True,
                  raw_sha256=hashlib.sha256(raw).hexdigest(),
                  diagnostics=diagnostics, original_diagnostics=old_diagnostics)
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if 'diagnostics' not in k}))
    return result


def caller_census():
    rom = (ROOT / 'conker/conker.us.bin').read_bytes()
    def offsets(value):
        needle, result, at = struct.pack('>I', value), [], 0
        while True:
            at = rom.find(needle, at)
            if at < 0:
                return result
            if at % 4 == 0:
                result.append(at)
            at += 1
    pointers = offsets(ENTRY)
    direct = offsets(0x0C000000 | ((ENTRY >> 2) & 0x3FFFFFF))
    assert pointers == [0x230C68], pointers
    assert direct == [], direct
    assert 0x8008B4A8 + 0x40 * 0x34 == 0x8008C1A8
    words = struct.unpack_from('>8I', rom, 0x194618)
    assert words == (0x8E0D0008, 0x02002025, 0x0320F809, 0xAE2D0000,
                     0x826E0000, 0x000E7880, 0x028F8821, 0x8E300000)
    structs = (ROOT/'conker/include/structs.h').read_text()
    assert 'void (*unk0)(struct102 *arg0);' in structs
    callbacks = (ROOT/'conker/src/game/generated_133190.c').read_text()
    for name in ('func_15107924', 'func_15107E48'):
        assert 's32 '+name+'(u8 *owner, u8 *changed)' in callbacks
    # Descriptor.unk0 is void(struct102 *). The walker preserves node+8,
    # passes node in A0, and does not use the callback's incidental V0.
    return dict(literal_pointers=pointers, direct_JALs=direct,
                descriptor=0x8008C1A8, kind=64, stride=52,
                caller='func_151670C0', signature='void(struct102 *)',
                callback_table='D_80088C10', callback_signature='s32(u8 *, u8 *)',
                callback_entries=['func_15107924', 'func_15107E48'],
                arbitrary_computed_callers_excluded=False)


if __name__ == '__main__':
    screen()
