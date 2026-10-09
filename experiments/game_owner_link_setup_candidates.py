"""Recover all three owner-link setup requests and reusable attachment packets."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x151B2348, 0x1DF7F8, 210
FUNCTION = 'func_151B2348'
SOURCE = 'conker/src/game/generated_1DF510.c'
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_1DF510/func_151B2348.s")'
TYPES = '''typedef struct { f32 x, y, z; } OwnerLinkVector2348;
typedef struct {
    u8 *owner;
    u8 code, kind, reserved06[2];
    OwnerLinkVector2348 offset;
} OwnerLinkEndpoint2348;
typedef struct {
    OwnerLinkEndpoint2348 first, second;
    u8 *actor;
    u8 route, reserved2D[3];
} OwnerLinkPacket2348;
typedef struct {
    u8 flags, reserved01;
    s16 duration;
    OwnerLinkVector2348 start, end;
    u8 active, enabled, extra, reserved1F;
    f32 width;
    u8 kind, reserved25[3];
    f32 distance, limitA, limitB;
    u8 tail, reserved35[3];
} OwnerLinkRequest2348;
'''
DECLARATIONS = '''extern OwnerLinkVector2348 D_800AA350, D_800AA35C, D_800AA320;
extern OwnerLinkVector2348 D_800AA338, D_800AA32C, D_800AA344;
extern f32 D_800AA380, D_800AA384;
u8 *func_151B30B0(void *, f32, s32, u8, s32);
void *memcpy(void *, const void *, u32);
'''
SYMBOLS = dict(D_800AA350=0x800AA350, D_800AA35C=0x800AA35C, D_800AA320=0x800AA320,
    D_800AA338=0x800AA338, D_800AA32C=0x800AA32C, D_800AA344=0x800AA344,
    D_800AA380=0x800AA380, D_800AA384=0x800AA384, func_151B30B0=0x151B30B0, memcpy=0x10022EC0)
SELECTED = '''void func_151B2348(u8 *actor) {
    OwnerLinkPacket2348 packet;
    OwnerLinkRequest2348 request;
    u8 *second = *(u8 **)(actor + 0x30);
    u8 *first = *(u8 **)(actor + 0x28);
    u8 *pair;
    u8 *created;

    packet.route = 2;
    packet.actor = actor;
    packet.first.owner = second;
    packet.first.code = second[0x3B];
    packet.first.kind = 5;
    packet.first.offset = D_800AA350;
    packet.second.owner = second;
    packet.second.code = second[0x3B];
    packet.second.kind = 10;
    packet.second.offset = D_800AA35C;
    request.tail = 0;
    request.flags = 0;
    request.duration = 1000;
    request.start.x = *(f32 *)(second + 0x14);
    request.start.y = *(f32 *)(second + 0x18);
    request.start.z = *(f32 *)(second + 0x1C);
    request.end.x = *(f32 *)(second + 0x14);
    request.end.y = *(f32 *)(second + 0x18);
    request.end.z = *(f32 *)(second + 0x1C);
    request.active = 1;
    request.enabled = 1;
    request.extra = 0;
    request.kind = 3;
    request.width = 5.0f;
    request.distance = 80.0f;
    request.limitA = D_800AA380;
    request.limitB = D_800AA384;
    created = func_151B30B0(&request, 0.0015f, 48, 255, 0);
    pair = actor + 0x28;
    *(u8 **)(pair + 0x18) = created;
    if (created != NULL) {
        memcpy(created + 0x150, &packet, 48);
    }

    packet.route = 1;
    packet.first.owner = first;
    packet.first.code = first[0x3B];
    packet.first.kind = 5;
    packet.first.offset = D_800AA320;
    packet.second.owner = second;
    packet.second.code = second[0x3B];
    packet.second.kind = 5;
    packet.second.offset = D_800AA338;
    request.start.x = *(f32 *)(first + 0x14);
    request.start.y = *(f32 *)(first + 0x18);
    request.start.z = *(f32 *)(first + 0x1C);
    request.end.x = *(f32 *)(second + 0x14);
    request.end.y = *(f32 *)(second + 0x18);
    request.end.z = *(f32 *)(second + 0x1C);
    request.extra = 0;
    request.distance = 170.0f;
    created = func_151B30B0(&request, 0.0015f, 48, 255, 0);
    *(u8 **)(pair + 0x14) = created;
    if (created != NULL) {
        memcpy(created + 0x150, &packet, 48);
    }

    packet.route = 0;
    packet.first.owner = first;
    packet.first.code = first[0x3B];
    packet.first.kind = 5;
    packet.first.offset = D_800AA32C;
    packet.second.owner = second;
    packet.second.code = second[0x3B];
    packet.second.kind = 10;
    packet.second.offset = D_800AA344;
    request.start.x = *(f32 *)(first + 0x14);
    request.start.y = *(f32 *)(first + 0x18);
    request.start.z = *(f32 *)(first + 0x1C);
    request.end.x = *(f32 *)(second + 0x14);
    request.end.y = *(f32 *)(second + 0x18);
    request.end.z = *(f32 *)(second + 0x1C);
    request.extra = 0;
    created = func_151B30B0(&request, 0.0015f, 48, 255, 0);
    *(u8 **)(pair + 0x10) = created;
    if (created != NULL) {
        memcpy(created + 0x150, &packet, 48);
    }
}'''


def candidates():
    yield 'selected', SELECTED
    yield 'request-first', SELECTED.replace('    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;',
        '    OwnerLinkRequest2348 request;\n    OwnerLinkPacket2348 packet;')
    yield 'volatile-actor', SELECTED.replace('u8 *actor)', 'u8 *volatile actor)')
    yield 'request-first-volatile-actor', SELECTED.replace('u8 *actor)', 'u8 *volatile actor)').replace(
        '    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;',
        '    OwnerLinkRequest2348 request;\n    OwnerLinkPacket2348 packet;')
    grouped = SELECTED.replace('    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;',
        '    struct { OwnerLinkPacket2348 packet; OwnerLinkRequest2348 request; } work;').replace(
        'packet.', 'work.packet.').replace('request.', 'work.request.').replace('&packet', '&work.packet').replace('&request', '&work.request')
    for name,body in (('separate',SELECTED),('grouped',grouped)):
        yield name+'-register-pair',body.replace('    u8 *pair;', '    register u8 *pair;')
        yield name+'-register-created',body.replace('    u8 *created;', '    register u8 *created;')
        yield name+'-register-both',body.replace('    u8 *pair;', '    register u8 *pair;').replace('    u8 *created;', '    register u8 *created;')
        yield name+'-actor-home',body.replace('    u8 *second =', '    u8 **actorHome = &actor;\n    u8 *second =').replace(
            'packet.actor = actor;', 'packet.actor = *actorHome;').replace('pair = actor + 0x28;', 'pair = *actorHome + 0x28;')
        yield name+'-volatile-actor',body.replace('u8 *actor)', 'u8 *volatile actor)')
        yield name+'-reuse-actor',body.replace('    u8 *pair;\n', '').replace(
            'pair = actor + 0x28;', 'actor += 0x28;').replace('(pair + ', '(actor + ')
    yield 'grouped',grouped


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-owner-link-setup'
    records = []
    for name, body in candidates():
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, _ = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
