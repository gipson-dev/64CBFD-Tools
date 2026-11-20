"""Private semantic recovery of the map-trail constructor; no matching credit."""
import csv
import hashlib
import json
import os
import re
from pathlib import Path
import struct
import subprocess

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
BUILD = 'conker/build/game-map-trail-constructor-15105ce0-private'
OUT = ROOT / BUILD
SOURCE = 'conker/src/game/generated_133190.c'
FUNCTION = 'func_15105CE0'
ENTRY, ROM, WORDS, FRAME = 0x15105CE0, 0x133190, 235, 0xD8
STUB = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_133190/func_15105CE0.s")'
ORIGINAL_SOURCE_SHA = '8a76c58d6ded9205ea6b5a2291fe9e3c25ee70f4b4f051f19e04da47424ca6f3'

PREAMBLE = '''typedef struct { f32 x, y, z; } MapTrailPoint133190;
/* The same 80-byte packet is emitted by func_15104C44. */
typedef struct {
    s16 duration;
    u8 enabled, reserved03;
    MapTrailPoint133190 points[4];
    s8 flag;
    u8 reserved35[3];
    s32 pieces;
    f32 width, spread;
    s16 minimum, maximum;
    u8 red, green, blue, alpha, state;
    u8 reserved4D[3];
} MapTrailPacket133190;
typedef struct {
    u32 flags00, zero04;
    s16 code08, lifetime;
    u32 zero0C, zero10;
    u8 rgba14[4], rgba18[4];
    u8 value1C, paletteIndex;
    s16 value1E, value20, value22;
    f32 scale, extentX, extentY;
    MapTrailPoint133190 position, velocity, acceleration;
    f32 zero54;
    u32 flags58, zero5C;
    u8 value60, value61;
    s8 value62, value63, value64, value65;
    u8 value66, pad67;
    s16 zero68;
    u8 pad6A[2];
    f32 coefficient;
} MapTrailEffect133190;
typedef struct {
    u8 header[0x10];
    MapTrailPacket133190 packet;
    void *extra;
    f32 reciprocal;
    s16 timer;
    u16 reserved6A;
    void *children[2];
    u8 scratch[0x10];
    s32 segmentBytes;
} MapTrailRecord133190;
extern MapTrailPoint133190 D_800A5480;
extern f32 D_800A2410, D_800A2414;
void *func_15167A68(s32, s32, s32, s32, u8, u8);
s32 func_150ADA20(void);
void func_15106214(MapTrailRecord133190 *);
void func_15106610(MapTrailRecord133190 *);
void *func_15130280(MapTrailEffect133190 *, u8, void *, s32, u8, s32);
void *memcpy(void *, const void *, u32);
'''

BODY = '''/* Allocate a sampled map trail and attach an effect at each endpoint. */
void *func_15105CE0(MapTrailPacket133190 *packet, s32 extraBytes, u8 priority, s32 context) {
    s32 pieces;
    s32 pointBytes;
    MapTrailRecord133190 *record;
    u32 firstFlag;
    MapTrailEffect133190 effect;
    u8 i;

    pieces = packet->pieces;
    pointBytes = (pieces + 2) * sizeof(MapTrailPoint133190);
    record = func_15167A68(0x40, context,
                          pieces * 0x34 + pointBytes + extraBytes + 0x88,
                          1, priority, 1);
    if (record == 0) {
        return 0;
    }
    memcpy(&record->packet, packet, sizeof(*packet));
    /* Each sampled segment occupies thirteen 32-bit words. */
    record->extra = (u8 *)record + (((u32)pieces * 13U) << 2) + pointBytes + 0x88;
    record->reciprocal = 1.0f / (f32)(packet->pieces + 1);
    record->timer = (u32)func_150ADA20() % (packet->maximum + 1) + packet->minimum;
    func_15106214(record);
    func_15106610(record);
    record->children[0] = 0;
    record->children[1] = 0;
    bzero(record->scratch, sizeof(record->scratch));
    record->segmentBytes = record->packet.pieces * 0x30 + 0x60;

    effect.paletteIndex = 0x2B;
    effect.code08 = 0x4404;
    effect.flags00 = 0x200005;
    effect.zero04 = 0;
    effect.lifetime = 300;
    effect.zero0C = 0;
    effect.zero10 = 0;
    effect.rgba14[0] = 0xFF;
    effect.rgba14[1] = 0xFF;
    effect.rgba14[2] = 0xFF;
    effect.rgba14[3] = 0xFF;
    effect.rgba18[0] = packet->red;
    effect.rgba18[1] = packet->green;
    effect.rgba18[2] = packet->blue;
    effect.rgba18[3] = packet->alpha;
    effect.value1C = 0xFF;
    effect.velocity = D_800A5480;
    effect.acceleration = D_800A5480;
    effect.value1E = 1;
    effect.value20 = 0xFF;
    effect.value22 = 1;
    effect.flags58 = 0xC000;
    effect.value60 = 6;
    effect.value61 = 6;
    effect.value62 = -1;
    effect.value63 = -1;
    effect.value64 = -1;
    effect.value65 = 0;
    effect.zero5C = 0;
    effect.value66 = 0xFF;
    effect.zero68 = 0;
    effect.zero54 = 0.0f;
    effect.scale = 1.0f;
    effect.coefficient = D_800A2410;
    effect.extentY = (packet->spread * D_800A2414) * 200.0f;
    effect.extentX = effect.extentY;
    for (i = 0; i < 2; i++) {
        effect.position = packet->points[i == 0 ? 0 : 3];
        firstFlag = func_150ADA20() != 0 ? 0x40 : 0;
        effect.flags58 = (func_150ADA20() != 0 ? 0x80 : 0) | firstFlag;
        record->children[i] = func_15130280(&effect, 0, 0, 0, priority, context);
    }
    return record;
}'''

def source():
    snapshot = OUT / 'baseline' / SOURCE
    path = snapshot if snapshot.exists() else ROOT / SOURCE
    assert hashlib.sha256(path.read_bytes()).hexdigest() == ORIGINAL_SOURCE_SHA, 'Owner source changed'
    before = path.read_text()
    assert before.count(STUB) == 1
    return before, before.replace(STUB, PREAMBLE + '\n' + BODY, 1)

def screen():
    out = OUT / 'screen'
    out.mkdir(parents=True, exist_ok=True)
    before, after = source()
    old, old_diagnostics = compile_owner(ROOT, out, before, 'before')
    obj, diagnostics = compile_owner(ROOT, out, after, 'candidate')
    raw, refs = payload(obj, FUNCTION)
    symbols = {'memcpy': 0x10022EC0, 'bzero': 0x100226F0}
    for rows in refs.values():
        for _, name in rows:
            symbols.setdefault(name, int(name.split('_')[1], 16) if '_' in name else 0)
    words = bound_blob(raw, refs, symbols)
    retail = struct.unpack_from('>%dI' % WORDS, (ROOT / 'conker/conker.us.bin').read_bytes(), ROM)
    disassembly = subprocess.run(['mips-linux-gnu-objdump', '-dr', str(obj)], capture_output=True, text=True, check=True)
    (out / 'candidate-disassembly.txt').write_text(disassembly.stdout)
    old_pools, new_pools = normalized_pools(old), normalized_pools(obj)
    assert old_pools == new_pools, 'Owner pools changed'
    clean_diagnostics = lambda text: re.sub(r'\S+\.c, line \d+:', '<owner>:', text)
    assert clean_diagnostics(old_diagnostics) == clean_diagnostics(diagnostics), 'New compiler diagnostic'
    result = dict(function=FUNCTION, source_installed=False, credit=0,
                  words=len(words), frame=(-words[0]) & 65535,
                  positional_differences=sum(a != b for a, b in zip(words, retail)) + abs(len(words)-WORDS),
                  unchanged_neighbors=same_functions(old, obj, (FUNCTION,)),
                  pools_unchanged=True, old_pools=repr(old_pools), new_pools=repr(new_pools),
                  raw_sha256=hashlib.sha256(raw).hexdigest(),
                  diagnostics=diagnostics, original_diagnostics=old_diagnostics)
    (out / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('old_pools','new_pools','diagnostics','original_diagnostics')}))
    return result

def caller_census():
    """Literal ROM JAL census; this cannot rule out computed callers."""
    rom=(ROOT/'conker/conker.us.bin').read_bytes()
    word=struct.pack('>I',0x0C000000|((ENTRY>>2)&0x03FFFFFF))
    offsets=[];at=0
    while True:
        at=rom.find(word,at)
        if at<0:break
        if at%4==0:offsets.append(at)
        at+=1
    assert offsets == [0x132440,0x134A70,0x134D58,0x1352BC], offsets
    with (ROOT/'conker/retail_layout.us.txt').open() as stream:layout=list(csv.DictReader(stream))
    result=[]
    for offset in offsets:
        address=ENTRY+offset-ROM
        owners=[row for row in layout if int(row['address'],0)<=address<int(row['end'],0)]
        assert len(owners)==1
        result.append(dict(rom=offset,address=address,caller=owners[0]['function'],owner=owners[0]['filename']))
    return dict(direct_JALs=result,arbitrary_computed_callers_excluded=False,
                complete_parent_execution_qualified=False)

if __name__ == '__main__':
    screen()
