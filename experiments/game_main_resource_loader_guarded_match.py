"""Normalize only the complete loader's closed private/register differences."""
import argparse
import csv
import hashlib
import io
import struct
from pathlib import Path

from tools.experiments import game_main_resource_loader_remaining_schedule as schedule
from tools.pad_generated_object import parse_object


SOURCE_SHA = 'f43fa661893aadea680107f8ebe446bdad763489b5558996c8a906802beca058'
GUARDS_SHA = '5eace9a1e712613397671e3d8d61acfcbd1ceaa4a7a73d4377b15d97ff7400c6'
SPILLS = (0x98, 0x9C, 0xB8, 0xC8, 0xD8, 0xF0, 0x108, 0x384,
    0x3AC, 0x3C4, 0x3D4, 0x3EC, 0x3FC, 0x414)
RETURN = (0xB0, 0xB4)
CLEANUP = (0x3BC, 0x3C0, 0x3CC, 0x3E4, 0x3E8, 0x3F4)
OFFSETS = tuple(sorted(SPILLS+RETURN+CLEANUP))
SELECTED = schedule.SELECTED


def normalized(raw, retail):
    retail = list(retail)
    assert len(raw) == len(retail) == 274
    assert tuple(i*4 for i, (a, b) in enumerate(zip(raw, retail)) if a != b) == OFFSETS
    assert raw[0] == retail[0] == 0x27BDFF88
    assert raw[0x420//4:] == retail[0x420//4:]
    for offset in SPILLS:
        before, after = raw[offset//4], retail[offset//4]
        assert before >> 16 == after >> 16
        assert before >> 26 in (0x23, 0x2B) and before >> 21 & 31 == 29
        assert before & 65535 in (0x50, 0x54)
        assert after & 65535 == (before & 65535)+8
    for offset in (0x3BC, 0x3E4):
        assert (raw[offset//4], retail[offset//4]) == (0x8E040000, 0x8E020000)
    for offset in (0x3C0, 0x3E8):
        assert (raw[offset//4], retail[offset//4]) == (0x50800005, 0x50400005)
    for offset in (0x3CC, 0x3F4):
        assert (raw[offset//4], retail[offset//4]) == (0, 0x00402025)
    assert (raw[0xB0//4], raw[0xB4//4]) == (0x100000DA, 0x24160001)
    assert (retail[0xB0//4], retail[0xB4//4]) == (0x100000DB, 0x24020001)
    assert 0xB4+signed16(retail[0xB0//4])*4 == 0x420
    assert 0xB4+signed16(raw[0xB0//4])*4 == 0x41C
    assert raw[0x41C//4] == retail[0x41C//4] == 0x02C01025
    for offset, word in enumerate(raw):
        if offset*4 not in SPILLS and word >> 26 in (0x23, 0x2B) and word >> 21 & 31 == 29:
            assert word & 65535 not in (0x58, 0x5C)
    words = list(raw)
    for offset in OFFSETS:
        words[offset//4] = retail[offset//4]
    assert words == list(retail)
    return words


def signed16(word):
    value = word & 65535
    return value-65536 if value & 32768 else value


def guard_text(raw, retail, relocations):
    normalized(raw, retail)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    for offset in OFFSETS:
        assert not relocations.get(offset)
        reason = ('Normalize closed main loader private spill pair' if offset in SPILLS else
            'Normalize main loader request-error epilogue join' if offset in RETURN else
            'Normalize closed main loader cleanup value transfer')
        writer.writerow(('generated_6A3D0', schedule.screen.FUNCTION, '0x%X'%offset,
            '0x%08X'%raw[offset//4], '0x%08X'%retail[offset//4], '-', '-', reason, '', '', 'false'))
    return stream.getvalue().encode('ascii')


def qualified_guard_suffix(root):
    original = root/'conker/build/game-main-resource-loader-guarded-audit'
    original.mkdir(exist_ok=True)
    meta, raw = schedule.measure(root, original, 'selected', SELECTED)
    assert (meta['body_words'], meta['frame'], meta['differences']) == (274, 0x78, 22)
    assert (meta['diagnostics'], meta['pool_bytes']) == ('', 0)
    retail = struct.unpack_from('>274I', (root/'conker/conker.us.bin').read_bytes(), schedule.screen.ROM)
    _, functions, relocations = parse_object(original/'selected.o')
    base = functions[schedule.screen.FUNCTION]['value']
    return guard_text(raw, retail, {offset-base:value for offset,value in relocations.items()
        if base <= offset < base+1096})


def current_guard_bytes(root, before):
    assert hashlib.sha256(before).hexdigest() == GUARDS_SHA
    current = (root/'conker/retail_word_patches.us.csv').read_bytes()
    if current == before:
        return current
    assert hashlib.sha256((root/schedule.screen.SOURCE).read_bytes()).hexdigest() == SOURCE_SHA
    assert current == before+qualified_guard_suffix(root)
    return current


def validate_current_guards(root):
    current = (root/'conker/retail_word_patches.us.csv').read_bytes()
    if hashlib.sha256(current).hexdigest() == GUARDS_SHA:
        return current
    assert hashlib.sha256((root/schedule.screen.SOURCE).read_bytes()).hexdigest() == SOURCE_SHA
    suffix = qualified_guard_suffix(root)
    assert current.endswith(suffix)
    assert hashlib.sha256(current[:-len(suffix)]).hexdigest() == GUARDS_SHA
    return current


def installed_words(root, words):
    current = validate_current_guards(root)
    if hashlib.sha256(current).hexdigest() == GUARDS_SHA:
        return words
    retail = struct.unpack_from('>274I', (root/'conker/conker.us.bin').read_bytes(), schedule.screen.ROM)
    return normalized(words, retail)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-guards', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/'conker/build/game-main-resource-loader-guarded-match'
    out.mkdir(exist_ok=True)
    assert hashlib.sha256((root/schedule.screen.SOURCE).read_bytes()).hexdigest() == SOURCE_SHA
    meta, raw = schedule.measure(root, out, 'selected', SELECTED)
    retail = struct.unpack_from('>274I', (root/'conker/conker.us.bin').read_bytes(), schedule.screen.ROM)
    _, functions, relocations = parse_object(out/'selected.o')
    base = functions[schedule.screen.FUNCTION]['value']
    suffix = guard_text(raw, retail, {offset-base:value for offset,value in relocations.items()
        if base <= offset < base+1096})
    target = root/'conker/retail_word_patches.us.csv'
    before = target.read_bytes()
    assert hashlib.sha256(before).hexdigest() == GUARDS_SHA
    (out/'candidate-guards.csv').write_bytes(before+suffix)
    if args.install_guards:
        target.write_bytes(before+suffix)
    print('complete words', meta['body_words'], 'frame', hex(meta['frame']),
        'raw differences', meta['differences'], 'guards', len(OFFSETS), 'installed', args.install_guards)


if __name__ == '__main__':
    main()
