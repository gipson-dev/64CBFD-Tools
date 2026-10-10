"""Measure complete renderer flag phases and physical homes without installing candidates."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_actor_renderer_candidates as recovery
from tools.tests import test_game_actor_renderer_recovery as proof

GATE = '    if (func_1503DA9C(actor, identity, tier, mode != 3) != 0)'
COLORS = '''    s32 primitiveR, primitiveG, primitiveB;
    s32 environmentR, environmentG, environmentB;
    s32 fogR, fogG, fogB, fogA;'''


def candidates():
    base = recovery.SELECTED.replace('    s32 identity, tier;', '    s32 identity, tier, allowed;').replace(
        GATE, '    if (mode == 3) { allowed = 0; } else { allowed = 1; }\n'
        '    if (func_1503DA9C(actor, identity, tier, allowed) != 0)')
    yield 'separate-gate', base
    for label, source in (('plain', base), ('volatile', base.replace('s32 mode, s32 extra)',
            'volatile s32 mode, s32 extra)'))):
        cached = source.replace('s32 identity, tier, allowed;',
            's32 identity, tier, allowed, selectedMode;').replace(
            '    actor = D_800CC2D0', '    selectedMode = mode;\n    actor = D_800CC2D0').replace(
            'if (mode == 3 || mode == 4 || mode == 5)',
            'if (selectedMode == 3 || selectedMode == 4 || selectedMode == 5)').replace(
            'identity = func_150849CC(actor, &tier);',
            'identity = func_150849CC(actor, &tier);\n        selectedMode = mode;').replace(
            'if (mode == 3) { allowed', 'if (selectedMode == 3) { allowed')
        for mask_name, masked in (('masked', True), ('guest-shift', False)):
            shaped = cached if masked else cached.replace('(part & 31)', 'part')
            yield label + '-' + mask_name, shaped
            declarations = shaped.split('    u8 *actor;\n', 1)[1].split('\n\n', 1)[0]
            orders = (
                ('phase-order', '    s32 tier, identity, colorState, flags, enabled;\n'
                    '    s32 selectedMode, allowed, lighting, part, page;\n' + COLORS),
                ('gate-before-colors', '    s32 tier, identity, colorState, allowed, flags, enabled;\n'
                    + COLORS + '\n    s32 selectedMode, lighting, part, page;'),
                ('gate-after-colors', '    s32 tier, identity, colorState, flags, enabled;\n'
                    + COLORS + '\n    s32 allowed, selectedMode, lighting, part, page;'),
                ('gate-between-phases', '    s32 tier, identity, colorState, selectedMode, allowed, enabled;\n'
                    + COLORS + '\n    s32 flags, lighting, part, page;'))
            for order_name, order in orders:
                yield label + '-' + mask_name + '-' + order_name, shaped.replace(declarations, order)
            retail_order = ('    s32 selectedMode, tier, identity, colorState, flags, allowed, enabled, lighting;\n'
                + COLORS + '\n    s32 part, page;')
            ordered = shaped.replace(declarations, retail_order)
            yield label + '-' + mask_name + '-retail-homes', ordered
            history = '''        flags = 2;
        if (actor[0x2FE] == 0) {
            flags = 10;
        }'''
            for history_name, history_body in (
                    ('ternary-history', '        flags = actor[0x2FE] == 0 ? 10 : 2;'),
                    ('explicit-history', '        if (actor[0x2FE] == 0) { flags = 10; } else { flags = 2; }')):
                yield label + '-' + mask_name + '-retail-homes-' + history_name, ordered.replace(history, history_body)
            special = '''        if (mode == 3) {
            if (D_800C48F0[identity] != NULL) {
                gSPDisplayList(commands++, D_800C48F0[identity][part]);
            }
        } else {'''
            null_continue = '''        if (mode == 3) {
            if (D_800C48F0[identity] == NULL) {
                continue;
            }
            gSPDisplayList(commands++, D_800C48F0[identity][part]);
        } else {'''
            yield label + '-' + mask_name + '-retail-homes-null-continue', ordered.replace(special, null_continue)
            history_ordered = ordered.replace(history, '        flags = actor[0x2FE] == 0 ? 10 : 2;')
            for exit_name, exit_body in (
                    ('two-continues', '''        if (mode == 3) {
            if (D_800C48F0[identity] != NULL) {
                gSPDisplayList(commands++, D_800C48F0[identity][part]);
                continue;
            } else {
                continue;
            }
        } else {'''),
                    ('two-gotos', '''        if (mode == 3) {
            if (D_800C48F0[identity] != NULL) {
                gSPDisplayList(commands++, D_800C48F0[identity][part]);
                goto nextPart;
            } else {
                goto nextPart;
            }
        } else {''')):
                body = history_ordered.replace(special, exit_body)
                if exit_name == 'two-gotos':
                    body = body.replace('    }\n    func_1502FD70(actor);',
                        'nextPart:\n        ;\n    }\n    func_1502FD70(actor);')
                yield label + '-' + mask_name + '-retail-homes-' + exit_name, body
    for label, body in list(recovery.candidates()):
        if label not in ('selected', 'volatile-mode', 'cached-early-mode', 'private-order'):
            continue
        yield 'old-' + label, body


SELECTED_NAME = 'plain-masked-retail-homes-ternary-history'
SELECTED = dict(candidates())[SELECTED_NAME]


class HomesOracle(proof.RendererOracle):
    def record_call(self, target):
        if target == proof.S['func_1502CC34']:
            self.color_homes = tuple(self.arguments(14)[4:])
        return super().record_call(target)


def physical_metadata(words, meta):
    args = (proof.OUTPUT, 0, 0, 0x27000, 255, proof.PARAMETERS, 0, 0)
    model = HomesOracle(words, proof.fixture(), args).run()
    sp = model.before[29] - meta['frame']
    saves = {str(word >> 16 & 31): word & 65535 for word in words[:40]
        if word >> 26 == 43 and word >> 21 & 31 == 29
        and word >> 16 & 31 in (*range(16, 24), 31)}
    return dict(color_offsets=[address - sp for address in model.color_homes],
        color_deltas=[address - (model.before[29] - 0x150 + 0x128 - i * 4)
            for i, address in enumerate(model.color_homes)], saved_registers=saves)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', nargs='+')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root / 'conker/build/game-actor-renderer-layout'
    out.mkdir(exist_ok=True)
    records = []
    for name, body in candidates():
        if args.only and name not in args.only:
            continue
        meta, words = recovery.compile_candidate(root, out, name, body)
        meta.update(physical_metadata(words, meta))
        records.append(meta)
        print(name, meta['body_words'], hex(meta['frame']), meta['color_deltas'][0],
            meta['differences'], flush=True)
    (out / 'measurements.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
