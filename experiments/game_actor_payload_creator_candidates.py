"""Recover the actor selector and eight-byte payload creator packet."""
import argparse
import itertools
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_record_constructor_candidates as compiler

ENTRY, ROM, WORDS = 0x1506AA48, 0x97EF8, 38
FUNCTION = 'func_1506AA48'
SOURCE = 'conker/src/game/generated_97AA0.c'
ORIGINAL = 's32 func_1506AA48() {\n    return 0;\n}'
OWNER_RECORD = '''typedef struct {
    u8 *object;
    u8 selector;
} ObjectSelector97AA0;
'''
PACKET = '''typedef struct {
    u32 first, second;
} PayloadPair97AA0;
typedef struct {
    ObjectSelector97AA0 target;
    PayloadPair97AA0 payload;
} ActorPayload97AA0;
typedef char ActorPayloadSize97AA0[(sizeof(ActorPayload97AA0) == 16) ? 1 : -1];
'''
DECLARATIONS = '''void *func_15149130(s16, s8, s8, s8, u8, u8, s32, u8, s32);
void *memcpy(void *, const void *, unsigned int);
'''
BASE = '''void func_1506AA48(u8 *actor, const PayloadPair97AA0 *data) {
    ActorPayload97AA0 packet;
    u8 *created;

    packet.target.object = actor;
    packet.target.selector = actor[0x3B];
    packet.payload = *data;
    created = func_15149130(10, 7, 0x23, -1, 1, 0x21, sizeof(packet), 0xFF, 1);
    if (created != NULL) {
        memcpy(created + 0x28, &packet, sizeof(packet));
    }
}'''
SELECTED = BASE.replace('    ActorPayload97AA0 packet;\n    u8 *created;',
    '    u8 *created;\n    ActorPayload97AA0 packet;')


def candidates():
    for created_first, volatile, snapshot in itertools.product((False, True), range(4), (False, True)):
        body = BASE
        if created_first:
            body = body.replace('    ActorPayload97AA0 packet;\n    u8 *created;',
                '    u8 *created;\n    ActorPayload97AA0 packet;')
        if volatile & 1:
            body = body.replace('u8 *actor,', 'u8 *volatile actor,')
        if volatile & 2:
            body = body.replace('*data)', '*volatile data)')
        if snapshot:
            body = body.replace('    packet.target.object = actor;',
                '    u8 *owner = actor;\n    const PayloadPair97AA0 *payload = data;\n\n'
                '    packet.target.object = owner;')
            body = body.replace('actor[0x3B]', 'owner[0x3B]').replace('packet.payload = *data;', 'packet.payload = *payload;')
        yield 'created%d-volatile%d-snapshot%d' % (created_first, volatile, snapshot), body


def compile_candidate(root, out, name, body=SELECTED, profile='o2g3'):
    with patch.multiple(compiler, ENTRY=ENTRY, ROM=ROM, WORDS=WORDS, FUNCTION=FUNCTION,
            RECORD=OWNER_RECORD + PACKET, DECLARATIONS=DECLARATIONS):
        return compiler.compile_candidate(root, out, name, body, profile)


def recovered_owner(before, body):
    if before.count(ORIGINAL) != 1 or before.count(OWNER_RECORD) != 1:
        raise ValueError('Expected the original creator placeholder and selector record')
    return before.replace(OWNER_RECORD, OWNER_RECORD + '\n' + PACKET + '\n' + DECLARATIONS, 1).replace(ORIGINAL, body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', action='store_true')
    parser.add_argument('--filter', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-payload-creator'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in candidates():
        if args.filter not in name:
            continue
        for profile in compiler.PROFILES if args.profiles else ('o2g3',):
            meta, words = compile_candidate(root, out, name + '-' + profile, body, profile)
            records.append(meta)
            print(meta['name'], meta['body_words'], hex(meta['frame']), meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
