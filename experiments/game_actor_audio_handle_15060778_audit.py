"""Private actor-audio ABI proposal screens; no installation or matching credit.

Run from the consumer under WSL with --root .  The complete Game and Init
owners are compiled against one proposed header.  This is a compiler and
dependency audit, not a guest/native, padding, linking or production gate.
"""
import argparse
import csv
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import body, compile_owner
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools.tests.game_owner_pool import normalized_pools

BUILD = 'conker/build/game-actor-audio-15060778-match/public-audit'
GAME = 'conker/src/game_83300.c'
INIT = 'conker/src/init_EB00.c'
HEADER = 'conker/include/functions.h'
FUNCTION = 'func_15060778'
CALLEE = 'func_10010BE8'
DEPENDENT = 'func_10010FFC'
GAME_BODY = '''void func_15060778(s32 arg0, struct127 *arg1, u16 arg2, s32 arg3, s32 arg4, s32 arg5, s32 arg6) {
    s32 handle = 0;
    u16 result;
    u16 *slot = NULL;
    s32 effect = (arg6 & 8) ? 0 : (((u32)arg1->unk184 >> 3) & 0x30);

    switch (arg6 & 3) {
        case 1:
            slot = &arg1->unk8C;
            handle = *slot;
            break;
        case 2:
        case 3:
            slot = &arg1->unk8E;
            handle = *slot;
            if ((arg6 & 3) == 2) {
                break;
            }
            if ((func_1001147C(handle) == arg0) & 0x7FFF) {
                if (arg6 & 4) {
                    func_1000F91C(handle, arg2 + effect * 50, arg3 + arg1->unk13F * 10,
                        effect, 0, (s32)arg1->x_position, (s32)arg1->y_position,
                        (s32)arg1->z_position, arg4, arg5);
                } else {
                    func_1000F85C(handle, 0x10, arg3);
                    func_1000F85C(handle, 8, arg2 + effect * 50);
                }
                return;
            }
            arg0 |= 0x8000;
            break;
    }
    if (arg6 & 4) {
        result = func_10010E78(handle, arg0, arg2 + effect * 50, arg3, effect, 0,
            (s32)arg1->x_position, (s32)arg1->y_position,
            (s32)arg1->z_position, arg4, arg5);
    } else {
        result = func_10010BE8(handle, arg0, arg2 + effect * 50, 0x40, arg3, effect, 1);
    }
    if (slot != NULL) {
        *slot = result;
    }
}'''
FROZEN = {'conker/Makefile': '0fcc34bf14b18545b513f888fa137779223a667daf4b9eb2bdc92734f6877a23',
 'conker/asm/nonmatchings/game_83300/func_15060778.s': '84045eddcfbaefc44d1fa5165e4b0cfefee9183bacf0773aadbedd8842a93965',
 'conker/asm/nonmatchings/init_EB00/func_10010BE8.s': '92011b95647ffcc2007482340c450062cc35b978aa91ad37fcc18a4ee93f583c',
 'conker/asm/nonmatchings/init_EB00/func_10010FFC.s': '3f84304f3bf5550a8616883888113aa70bc309a3efdc49f57218c35fd0f10cc8',
 'conker/build/conker.us.elf': '3c613204b09b0642399ee7d89d9951aa9075789c45ae82834443968adfc7cbed',
 'conker/build/src/game_83300.c.o': 'dca3e7cb2b64c2778dac569fca41355eeaf51f1ce4963aed9d24ff5908f9bdf4',
 'conker/build/src/init_EB00.c.o': 'd8eff52ea164c3a6078e5aec0e3544d74cd963876962acf87ad079ab17e47f32',
 'conker/conker.us.bin': 'f2ce85ad021adccf773bc62f847b4818bca5227bfdd5d14433231f8c663fd382',
 'conker/include/functions.h': 'f01a41af0bdb2caaaeb2c198be68d91515efb39de98a34ba190e090503d5f10b',
 'conker/include/structs.h': 'e97e1a98ebcc522d82b52215078780102e0dd5e47d614bb3a4d4f3bbc94b9653',
 'conker/include/variables.h': '02650aa4bf9fd66156f4e2cbd1e49156b9655eed68c3fae1cab15b1f99063a7d',
 'conker/progress.csv': '7658d1ff6c2e3ae94567606200fcae0b7d08f5752a9ec0484108dc8056c8bdc0',
 'conker/retail_layout.us.txt': 'eb8145837da425d7a55080459d22f11e21e1ac69e8b9d8ad5100ed5750d814f1',
 'conker/retail_word_patches.us.csv': '52b245688cf6f1c40667b3cd6af3310fe0448bc5317be464856fe5e77df3e200',
 'conker/src/game_83300.c': '35125ff9b63b0ddf836b56eafa1831cae32fcf67c3466252a978b4de9b86f1fa',
 'conker/src/init_EB00.c': 'df10767e2955fc9d3e355712d3c5e8b3bf6fa9681ce79b528c50a689105dfb6e'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def proposal(game, init, header):
    """Return a consistent source proposal, with its retail-width rationale."""
    assert GAME_BODY and 's32 handle = 0;' in GAME_BODY
    assert header.count(CALLEE + '(s32 arg0,') == 1
    new_header = header.replace(CALLEE + '(s32 arg0,', CALLEE + '(u16 arg0,')
    old_body = body(init, CALLEE)
    new_body = old_body.replace(CALLEE + '(s32 arg0,', CALLEE + '(u16 arg0,')
    for fragment in ('    volatile s32 normalizedHandle;\n',
                     '    normalizedHandle = arg0 & 0xFFFF;\n',
                     '    arg0 = normalizedHandle;\n'):
        assert new_body.count(fragment) == 1
        new_body = new_body.replace(fragment, '')
    assert new_body != old_body and 'normalizedHandle' not in new_body
    assert CALLEE + '(u16 arg0,' in new_body
    return (game.replace(body(game, FUNCTION), GAME_BODY),
            init.replace(old_body, new_body), new_header)


def function_payload(parsed, name):
    text, functions, relocs = parsed
    start, size = functions[name]['value'], functions[name]['size']
    return (text[start:start + size],
            {offset - start: rows for offset, rows in relocs.items()
             if start <= offset < start + size})


def changes(before, after):
    assert before[1].keys() == after[1].keys(), 'Function set changed'
    return sorted(name for name in before[1]
                  if function_payload(before, name) != function_payload(after, name))


def metrics(parsed, name, retail, symbols):
    raw, refs = function_payload(parsed, name)
    words = bound_blob(raw, refs, symbols)
    expected = list(struct.unpack('>%dI' % (len(retail) // 4), retail))
    differing = [index for index, (a, b) in enumerate(zip(words, expected)) if a != b]
    return dict(words=len(words), frame=(-words[0]) & 65535,
                word_differences=len(differing) + abs(len(words) - len(expected)),
                differences=differing, raw_sha256=sha(raw), bindings=len(refs))


def caller_census(rom, layout):
    address = 0x15060778
    hits = {}
    for name, value in (('jal', 0x0C000000 | ((address >> 2) & 0x3FFFFFF)),
                        ('jump', 0x08000000 | ((address >> 2) & 0x3FFFFFF)),
                        ('aligned_pointer', address)):
        hits[name] = [index * 4 for index, (word,) in enumerate(struct.iter_unpack('>I', rom))
                      if word == value]
    rows = list(csv.DictReader(layout.splitlines()))
    calls = []
    for offset in hits['jal']:
        va = offset - 0x2D4B0 + 0x15000000
        parents = [row for row in rows if row['section'] == 'game'
                   and int(row['address'], 16) <= va < int(row['end'], 16)]
        assert len(parents) == 1, (hex(offset), parents)
        row = parents[0]
        calls.append(dict(rom=offset, address=va, parent=row['function'],
                          owner=row['filename']))
    assert hits['jal'] == [0x81904, 0x8DF34, 0x8DF9C, 0x8E008, 0xA3748]
    assert not hits['jump'] and not hits['aligned_pointer']
    assert [c['parent'] for c in calls] == ['func_150538CC', 'func_15060A30',
                                          'func_15060A9C', 'func_15060B04',
                                          'func_15076250']
    return dict(**hits, calls=calls, scope='Aligned whole-ROM encoding census; indirect computed calls not excluded')


def prepare(root):
    root = Path(root).resolve()
    out = root / BUILD
    out.mkdir(parents=True, exist_ok=True)
    observed = {name: sha((root / name).read_bytes()) for name in FROZEN}
    assert observed == FROZEN, 'Accepted source/image baseline changed'
    assert (root / 'conker/build/conker.us.elf').is_file()
    game, init, header = [(root / name).read_text() for name in (GAME, INIT, HEADER)]
    new_game, new_init, new_header = proposal(game, init, header)
    (out / 'proposed-functions.h').write_text(new_header)
    rom = (root / 'conker/conker.us.bin').read_bytes()
    symbols = {}
    for line in subprocess.check_output(['mips-linux-gnu-nm', '-n',
                                         str(root / 'conker/build/conker.us.elf')], text=True).splitlines():
        columns = line.split()
        if len(columns) == 3:
            try:
                symbols[columns[2]] = int(columns[0], 16)
            except ValueError:
                pass
    artifacts = {}
    for label, source, proposed in (('game-before', game, False),
                                    ('game-proposal', new_game, True),
                                    ('init-before', init, False),
                                    ('init-proposal', new_init, True)):
        if proposed:
            assert source.count('#include "functions.h"') == 1
            source = source.replace('#include "functions.h"', '#include "proposed-functions.h"')
        obj, diagnostic = compile_owner(root, out, source, label)
        artifacts[label] = (obj, parse_object(obj), diagnostic_rows(diagnostic))
    before, after = artifacts['game-before'], artifacts['game-proposal']
    assert changes(before[1], after[1]) == [FUNCTION]
    assert before[2] == after[2] and sum(after[2].values()) == 8
    assert sections(before[0])['.reginfo'] == sections(after[0])['.reginfo']
    assert normalized_pools(before[0]) == normalized_pools(after[0])
    target = metrics(after[1], FUNCTION, rom[0x8DC28:0x8DEE0], symbols)
    assert (target['words'], target['frame'], target['word_differences']) == (174, 88, 8)
    assert target['differences'] == [38, 39, 43, 44, 93, 95, 96, 98]
    # The eight differences change only the offsets of two private spill homes.
    raw, refs = function_payload(after[1], FUNCTION)
    actual_words = bound_blob(raw, refs, symbols)
    retail_words = struct.unpack('>174I', rom[0x8DC28:0x8DEE0])
    homes = {0x40: 0x44, 0x48: 0x54}
    for index in target['differences']:
        a, b = actual_words[index], retail_words[index]
        assert a & 0xFFFF0000 == b & 0xFFFF0000
        assert a >> 26 in (35, 43) and (a >> 21) & 31 == 29
        assert homes[a & 65535] == b & 65535
    target['spill_home_map'] = homes
    before, after = artifacts['init-before'], artifacts['init-proposal']
    affected = changes(before[1], after[1])
    assert affected == [CALLEE, DEPENDENT], affected
    assert before[2] == after[2] and sum(after[2].values()) == 13
    assert sections(before[0])['.reginfo'] == sections(after[0])['.reginfo']
    assert normalized_pools(before[0]) == normalized_pools(after[0])
    callee = metrics(after[1], CALLEE, rom[0x10BE8:0x10E78], symbols)
    assert (callee['words'], callee['frame'], callee['word_differences']) == (164, 88, 73)
    old_callee = metrics(before[1], CALLEE, rom[0x10BE8:0x10E78], symbols)
    assert (old_callee['words'], old_callee['frame'], old_callee['word_differences']) == (164, 96, 85)
    dependents = {phase: metrics(artifacts['init-' + phase][1], DEPENDENT,
                               rom[0x10FFC:0x111C8], symbols)
                  for phase in ('before', 'proposal')}
    # Do not apply stale frame/register guards from the former callee source.
    with (root / 'conker/retail_word_patches.us.csv').open() as stream:
        guards = list(csv.DictReader(stream))
    callee_guards = [r for r in guards if r['filename'] == 'init_EB00' and r['function'] == CALLEE]
    assert len(callee_guards) == 85
    first = next(r for r in callee_guards if int(r['offset'], 16) == 0)
    assert first['expected'] == '0x27BDFFA0'
    raw, _ = function_payload(after[1], CALLEE)
    assert int.from_bytes(raw[:4], 'big') == 0x27BDFFA8
    census = caller_census(rom, (root / 'conker/retail_layout.us.txt').read_text())
    assert {name: sha((root / name).read_bytes()) for name in FROZEN} == observed
    report = dict(installed=False, credited=False, guard_rows_written=0,
                  consistent_source_proposal=True, functional_validation=False,
                  production_build_run=False, source_inputs_unchanged=True,
                  game=target, game_equal_neighbors=88, init=callee,
                  init_changed_functions=affected, init_equal_neighbors=52,
                  dependent=dependents, stale_callee_guards=85, callers=census,
                  input_sha256=observed,
                  limits='Requires guest/native, all dependent source/ABI/padder audits, actual Make, strict whole-image and production gates before adoption')
    (out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    args = parser.parse_args()
    result = prepare(args.root)
    print(json.dumps({k: result[k] for k in ('installed', 'credited', 'game', 'init',
                                             'init_changed_functions')}, indent=2))
