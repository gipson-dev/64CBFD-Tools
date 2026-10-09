"""Recover the two retained link requests and late-captured owner effect."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_owner_link_setup_candidates as setup

ENTRY, ROM, WORDS = 0x151B2690, 0x1DFB40, 176
FUNCTION = 'func_151B2690'
SOURCE = setup.SOURCE
ORIGINAL = '#pragma GLOBAL_ASM("asm/nonmatchings/generated_1DF510/func_151B2690.s")'
EXTRA_TYPES = '''typedef struct {
    OwnerLinkEndpoint2348 endpoint;
    OwnerLinkVector2348 end;
    f32 width;
    u8 *actor;
} OwnerEffectPacket2690;
'''
TYPES = setup.TYPES + EXTRA_TYPES
EXTRA_DECLARATIONS = '''extern OwnerLinkVector2348 D_800AA368, D_800AA374;
extern f32 D_800AA388, D_800AA38C;
void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
'''
DECLARATIONS = setup.DECLARATIONS + EXTRA_DECLARATIONS
SYMBOLS = dict(D_800AA320=0x800AA320, D_800AA32C=0x800AA32C,
    D_800AA368=0x800AA368, D_800AA374=0x800AA374,
    D_800AA388=0x800AA388, D_800AA38C=0x800AA38C,
    func_151B30B0=0x151B30B0, func_15149130=0x15149130, memcpy=0x10022EC0)
LOCALS = ('    u8 *endpoint = *(u8 **)(actor + 0x28);',
    '    u8 *pair;', '    u8 *created;')
WORKSPACE = '    struct { OwnerEffectPacket2690 effect; OwnerLinkPacket2348 packet; OwnerLinkRequest2348 request; } work;'
SELECTED = '''void func_151B2690(u8 *actor) {
    u8 *endpoint = *(u8 **)(actor + 0x28);
    u8 *pair;
    struct { OwnerEffectPacket2690 effect; OwnerLinkPacket2348 packet; OwnerLinkRequest2348 request; } work;
    u8 *created;

    work.packet.actor = actor;
    work.packet.route = 1;
    work.packet.first.owner = endpoint;
    work.packet.first.code = endpoint[0x3B];
    work.packet.first.kind = 5;
    work.packet.first.offset = D_800AA320;
    work.packet.second.owner = endpoint;
    work.packet.second.code = endpoint[0x3B];
    work.packet.second.kind = 2;
    work.packet.second.offset = D_800AA368;
    work.request.tail = 0;
    work.request.flags = 0;
    work.request.duration = 100;
    work.request.start.x = *(f32 *)(endpoint + 0x14);
    work.request.start.y = *(f32 *)(endpoint + 0x18);
    work.request.start.z = *(f32 *)(endpoint + 0x1C);
    work.request.end.x = *(f32 *)(endpoint + 0x14);
    work.request.end.y = *(f32 *)(endpoint + 0x18);
    work.request.end.z = *(f32 *)(endpoint + 0x1C);
    work.request.active = 1;
    work.request.enabled = 1;
    work.request.extra = 1;
    work.request.kind = 3;
    work.request.width = 5.0f;
    work.request.distance = 180.0f;
    work.request.limitA = D_800AA388;
    work.request.limitB = D_800AA38C;
    created = func_151B30B0(&work.request, 0.0015f, 48, 255, 0);
    pair = *(u8 **)&actor + 0x28;
    *(u8 **)(pair + 0x14) = created;
    if (created != NULL) {
        memcpy((*(u8 **)(pair + 0x14)) + 0x150, &work.packet, 48);
    }

    work.packet.route = 0;
    work.packet.first.offset = D_800AA32C;
    work.packet.second.offset = D_800AA374;
    work.request.extra = 1;
    created = func_151B30B0(&work.request, 0.0015f, 48, 255, 0);
    *(u8 **)(pair + 0x10) = created;
    if (created != NULL) {
        memcpy((*(u8 **)(pair + 0x10)) + 0x150, &work.packet, 48);
    }

    work.effect.endpoint.owner = endpoint;
    work.effect.endpoint.code = endpoint[0x3B];
    work.effect.endpoint.kind = 2;
    work.effect.endpoint.offset = D_800AA368;
    work.effect.end = D_800AA374;
    work.effect.width = 5.0f;
    work.effect.actor = *(u8 **)&actor;
    created = func_15149130(300, -1, -1, 0, 0, 19, 40, 255, 1);
    *(u8 **)(pair + 0x1C) = created;
    if (created != NULL) {
        memcpy((*(u8 **)(pair + 0x1C)) + 0x28, &work.effect, 40);
    }
}'''


def candidates():
    yield 'selected', SELECTED
    beginning, statements = SELECTED.split('\n\n', 1)
    for order in itertools.permutations(range(3)):
        for position in range(4):
            lines = [LOCALS[i] for i in order]
            lines.insert(position, WORKSPACE)
            body = 'void func_151B2690(u8 *actor) {\n' + '\n'.join(lines) + '\n\n' + statements
            for copy in ('slot', 'local'):
                value = body
                if copy == 'local':
                    for offset, delta in (('0x14','0x150'),('0x10','0x150'),('0x1C','0x28')):
                        value = value.replace('(*(u8 **)(pair + '+offset+')) + '+delta, 'created + '+delta)
                yield 'order-'+''.join(map(str,order))+'-work'+str(position)+'-'+copy, value
    yield 'plain-actor', SELECTED.replace('*(u8 **)&actor', 'actor')
    yield 'volatile-actor', SELECTED.replace('u8 *actor)', 'u8 *volatile actor)')
    separate = SELECTED.replace(WORKSPACE,
        '    OwnerEffectPacket2690 effect;\n    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;')
    yield 'separate', separate.replace('work.', '')
    yield 'request-first', separate.replace('    OwnerEffectPacket2690 effect;\n    OwnerLinkPacket2348 packet;\n    OwnerLinkRequest2348 request;',
        '    OwnerLinkRequest2348 request;\n    OwnerLinkPacket2348 packet;\n    OwnerEffectPacket2690 effect;').replace('work.', '')


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    out.mkdir(parents=True, exist_ok=True)
    with patch.multiple(setup.compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=TYPES, DECLARATIONS=DECLARATIONS, SYMBOLS=SYMBOLS):
        return setup.compiler.compile_candidate(root, out, name, body, profile)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-owner-companion-setup'
    records = []
    for name, body in candidates():
        for profile in setup.compiler.PROFILES if args.profiles and name == 'selected' else ('o2g3',):
            meta, words = compile_candidate(root, out, name+'-'+profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out/'measurements.json').write_text(json.dumps(records, indent=2)+'\n')


if __name__ == '__main__':
    main()
