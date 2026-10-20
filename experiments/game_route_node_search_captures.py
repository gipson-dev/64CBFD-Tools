"""Close route-search captures with addressable C and one checked slot mapping.

This is partial layout qualification, not a complete byte-match recipe.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import game_route_node_search_loop as prior
from tools.pad_generated_object import ELF_HEADER, SECTION_HEADER, parse_object


core = prior.prior
BUILD = prior.BUILD + '/captures/qualified'
FUNCTION, ENTRY, ROM, WORDS = prior.FUNCTION, prior.ENTRY, prior.ROM, prior.WORDS
# IDO keeps this typed incoming lvalue addressable; *(&avoid) alone is folded.
SELECTED = prior.SELECTED.replace('avoid[i]', '(*(u8 **)&avoid)[i]')
RAW_SHA = 'c9cc61e01da4a0bf630aa5ff8a88a5f4b3c3a4a1709e2fd8142a56110fd5b9b7'
BINDING_SHA = 'd773bb14cc8b0e5c4f019c38b74b90010d7d46e5cc0dd2786ab3dd0e2e6d2161'
NORMALIZED_SHA = '9a685456fec70e6faf985bb68efd18af68f2112b5500bdf6d981027048e2612e'
SLOT_WORDS = {99: 0xAFB805FC, 149: 0x8FB805FC, 323: 0x8FAF05FC,
              355: 0x8FAE05FC, 377: 0x8FAE05FC}
MEMORY = (32, 33, 35, 36, 37, 40, 41, 43, 49, 53, 57, 61)


def normalize(raw, bindings):
    if len(raw) != 2140 or hashlib.sha256(raw).hexdigest() != RAW_SHA:
        raise ValueError('Route capture source words changed')
    if hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest() != BINDING_SHA:
        raise ValueError('Route capture source bindings changed')
    words = list(struct.unpack('>535I', raw))
    old = {i: w for i, w in enumerate(words)
           if w >> 26 in MEMORY and w >> 21 & 31 == 29 and w & 65535 == 0x5FC}
    if old != SLOT_WORDS:
        raise ValueError('Unknown route table-home accesses')
    for word in words:
        if word >> 21 & 31 == 29 and word & 65535 == 0x60:
            if word >> 26 in MEMORY or word >> 26 == 9:
                raise ValueError('Route table-home destination is occupied')
    if any(i * 4 in bindings for i in SLOT_WORDS):
        raise ValueError('Unexpected binding on a route frame displacement')
    for i, expected in SLOT_WORDS.items():
        if words[i] != expected or expected >> 26 not in (35, 43):
            raise ValueError('Unknown route capture expected word')
        words[i] = expected & 0xFFFF0000 | 0x60
    result = struct.pack('>535I', *words)
    if hashlib.sha256(result).hexdigest() != NORMALIZED_SHA:
        raise ValueError('Route capture output changed')
    return result, copy.deepcopy(bindings)


def normalize_object(obj, output):
    text, functions, bindings = parse_object(obj)
    raw, local = core.payload(obj)
    changed, moved = normalize(raw, local)
    if moved != local:
        raise ValueError('Route capture altered relocation bindings')
    at = functions[FUNCTION]['value']
    if text[at:at + len(raw)] != raw:
        raise ValueError('Route capture object extent changed')
    expected = text[:at] + changed + text[at + len(raw):]
    data = obj.read_bytes()
    header = ELF_HEADER.unpack_from(data)
    section = SECTION_HEADER.unpack_from(data, header[6] + functions[FUNCTION]['section'] * header[11])
    at, size = section[4], section[5]
    if section[1] != 1 or size != len(text) or data[at:at + size] != text:
        raise ValueError('Unknown route capture ELF text section')
    output.write_bytes(data[:at] + expected + data[at + size:])
    actual, af, ab = parse_object(output)
    if actual != expected or af != functions or ab != bindings:
        raise ValueError('Route capture fixture changed other bytes or metadata')
    return output


def qualify(root, output):
    obj, raw_words, row = core.compile_candidate(root, output, 'selected-True', SELECTED, True)
    normalized = normalize_object(obj, output / 'selected-normalized.o')
    image, functions = core.link_owner(root, output, normalized, core.OWNER)
    words = list(struct.unpack_from('>535I', image, functions[FUNCTION]['value']))
    truth = struct.unpack_from('>539I', (root / 'conker/conker.us.bin').read_bytes(), ROM)
    differences = sum(a != b for a, b in zip(words, truth)) + 4
    result = dict(raw_words=len(raw_words), words=len(words), frame=(-words[0]) & 65535,
        raw_differences=row['differences'], differences=differences,
        raw_SHA256=RAW_SHA, normalized_SHA256=NORMALIZED_SHA, output_bindings=14,
        slot_displacements_changed=5, all535_origins_retained=True,
        inserted_instructions=0, omitted_instructions=0, partial_layout=True,
        installed=False, matching_credit=0)
    (output / 'capture-qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    return obj, raw_words, normalized, words, result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root, root / BUILD)[-1], indent=2))


if __name__ == '__main__':
    main()
