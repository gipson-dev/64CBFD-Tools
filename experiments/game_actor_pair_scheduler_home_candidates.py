"""Recover scheduler scalar lifetimes and ranking-buffer homes from real C."""
import argparse
import json
from pathlib import Path
import re

from tools.experiments import game_actor_pair_scheduler_candidates as source

BUILD = source.BUILD + '/homes'


def candidates():
    body = source.SELECTED
    yield 'baseline', body
    single_copy = body.replace('    f32 sameZ;\n', '').replace('                sameZ = x;\n', '').replace(
        'dz = sameZ -', 'dz = x -')
    yield 'one-coordinate-copy', single_copy
    reused = single_copy.replace('    f32 displacedCost;\n', '').replace('displacedCost', 'dz')
    yield 'reuse-Z-after-ranking', reused
    reuse_rank = re.sub(r'\brank\b', 'i', reused.replace('    s32 rank;\n', ''))
    yield 'reuse-ranking-cursor', reuse_rank
    late_actor = reuse_rank.replace('        actor = D_800CC2D0;\n', '').replace(
        '        if (primaryCount > 0) {', '        if (primaryCount > 0) {\n            actor = D_800CC2D0;')
    yield 'primary-actor-positive-scope', late_actor
    arrays = '    f32 costs[4];\n    s8 choices[4];\n'
    for label, current in (('baseline', body), ('compact', late_actor)):
        moved = current.replace(arrays, '')
        yield label + '-arrays-last', moved.replace('\n\n    first =', '\n    s8 choices[4];\n    f32 costs[4];\n\n    first =', 1)
        moved = moved.replace('    s32 *groups;\n', '')
        yield label + '-arrays-before-groups', moved.replace('    f32 x;\n',
            '    s8 choices[4];\n    f32 costs[4];\n    s32 *groups;\n    f32 x;\n', 1)
    for label, current in (('reused', reused), ('compact', late_actor)):
        moved = current.replace(arrays, '').replace('    s32 *groups;\n', '').replace(
            '    f32 x;\n', '    s8 choices[4];\n    f32 costs[4];\n    s32 *groups;\n    f32 x;\n', 1)
        for name in ('x', 'dx', 'cost'):
            declaration = '    f32 %s;\n' % name
            arranged = moved.replace(declaration, '').replace('    s8 choices[4];\n', declaration + '    s8 choices[4];\n')
            yield label + '-homes-' + name, arranged
            if name == 'dx':
                yield label + '-homes-actor-hint', arranged.replace('    u8 *actor;', '    register u8 *actor;')
                if label == 'compact':
                    ranked = arranged.replace('if (i < 0)', 'if ((u32)choices + (u32)i < (u32)choices)')
                    yield 'choice-induction-bound', ranked
                    initialized = arranged.replace('for (i = 0; i < 3; i++) {\n                    choices[i]',
                        'for (i = 0; (u32)(costs + i) < (u32)(costs + 3); i++) {\n                    choices[i]')
                    yield 'unsigned-initializer-bound', initialized
                    both = initialized.replace('if (i < 0)', 'if ((u32)choices + (u32)i < (u32)choices)')
                    yield 'both-induction-bounds', both
                    yield 'signed-candidate-width', both.replace('    s32 candidate;', '    s8 candidate;')


SELECTED = dict(candidates())['compact-homes-dx']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--filter')
    p.add_argument('--normal', action='store_true')
    p.add_argument('--whole', action='store_true')
    args = p.parse_args()
    root = Path(__file__).resolve().parents[2]
    for name, body in candidates():
        if args.filter and args.filter not in name:
            continue
        _, _, row = source.compile_candidate(root, root / BUILD, name + ('-normal' if args.normal else ''),
            body, normal=args.normal, whole=args.whole)
        print(json.dumps(dict(candidate=name, **{k: v for k, v in row.items() if k != 'bindings'})), flush=True)
