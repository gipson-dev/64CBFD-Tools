"""Reproduce interpolation source-layout screens without installing a candidate.

Similarity counts are an investigation aid, not semantic or match evidence.
In particular retail evaluates the numerator before its zero-duration branch.
"""
import difflib
import hashlib
import itertools
import json
import os
import subprocess
from pathlib import Path

from tools import pad_generated_object
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_sequence_direction_1501fe68_match import compile_selected
from tools.experiments.game_sequence_open_candidates import CANDIDATES, payload
from tools.tests.game_owner_pool import normalized_pools

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
OUT = ROOT / 'conker/build/game-interpolation-layout-screen'
NAME = 'func_1501FC8C'
OWNER = 'generated_49D30'
SOURCE = ROOT / 'conker/src/game/generated_49D30.c'
ASM = ROOT / 'conker/asm/49D30.s'
GUARDS = ROOT / 'conker/retail_word_patches.us.csv'


def assemble(source, label):
    asm = OUT / (label + '.s')
    obj = asm.with_suffix('.o')
    asm.write_text(source)
    command = ['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300',
               '-mabi=32', '-I', 'include', '-o', str(obj), str(asm)]
    subprocess.run(command, cwd=ROOT / 'conker', check=True, capture_output=True)
    return obj


def raw_words(path):
    raw, refs = payload(path, NAME)
    return [(raw[i:i + 4], tuple(refs.get(i, ()))) for i in range(0, len(raw), 4)]


def screen():
    OUT.mkdir(parents=True, exist_ok=True)
    original = SOURCE.read_text()
    if body(original, NAME) != 's32 ' + NAME + '() {\n    return 0;\n}':
        raise ValueError('Unexpected production predecessor; screen requires the original stub')
    candidate = next(item['candidate'] for item in CANDIDATES if item['function'] == NAME)
    decls = ['    f32 time;', '    s32 frame;', '    f32 points[2][3];', '    f32 *times;']
    block = '\n'.join(decls)
    if candidate.count(block) != 1:
        raise ValueError('Candidate declarations changed')
    asm = ASM.read_text()
    marker = 'glabel ' + NAME + '\n'
    end = 'endlabel ' + NAME
    snippet = marker + asm.split(marker, 1)[1].split(end, 1)[0] + end
    retail = assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n' +
                      snippet + '\n.size ' + NAME + ',.-' + NAME + '\n', 'retail')
    expected = raw_words(retail)
    baseline, baseline_diag = compile_selected(ROOT, OUT, original, 'baseline')
    results = []
    best = None
    for number, order in enumerate(itertools.permutations(decls)):
        proposal = candidate.replace(block, '\n'.join(order))
        source = original.replace(body(original, NAME), proposal, 1)
        obj, diag = compile_selected(ROOT, OUT, source, 'variant-%02d' % number)
        actual = raw_words(obj)
        first = int.from_bytes(actual[0][0], 'big')
        if first >> 16 != 0x27BD:
            raise ValueError('Unexpected function prologue')
        frame_size = -(first & 0xffff if first & 0x8000 == 0 else (first & 0xffff) - 0x10000)
        score = sum(block.size for block in difflib.SequenceMatcher(
            a=actual, b=expected, autojunk=False).get_matching_blocks())
        result = {'declarations': [line.strip() for line in order],
                  'words': len(actual), 'frame_bytes': frame_size, 'ordered_equal_words': score,
                  'aligned_equal_words': sum(a == b for a, b in zip(actual, expected)),
                  'compact_reginfo_unchanged': sections(obj)['.reginfo'][1] == sections(baseline)['.reginfo'][1],
                  'neighbors_unchanged': same_functions(baseline, obj, (NAME,)),
                  'pools_unchanged': normalized_pools(baseline) == normalized_pools(obj),
                  'diagnostics_unchanged': diagnostic_rows(baseline_diag) == diagnostic_rows(diag)}
        if result['neighbors_unchanged'] != 56 or not result['pools_unchanged'] or not result['diagnostics_unchanged']:
            raise ValueError('Candidate changed unrelated owner state or compiler diagnostics')
        results.append(result)
        if best is None or score > best[0]:
            best = (score, number, proposal, obj)
    (OUT / 'best-candidate.c').write_text(best[2])
    padded = []
    for label, obj in [('baseline', baseline), ('candidate', best[3])]:
        assembly = pad_generated_object.emit_padded_assembly(obj, ASM, filename=OWNER,
                                                             word_patches_path=GUARDS)
        output = assemble(assembly, 'padded-' + label)
        padded.append(sections(output)['.reginfo'][1].hex())
    report = {'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'assembly_sha256': hashlib.sha256(ASM.read_bytes()).hexdigest(),
              'guard_sha256': hashlib.sha256(GUARDS.read_bytes()).hexdigest(),
              'production_elf_sha256': hashlib.sha256((ROOT / 'conker/build/conker.us.elf').read_bytes()).hexdigest(),
              'function': NAME, 'retail_words': len(expected), 'variants': results,
              'best_variant': best[1], 'best_ordered_equal_words': best[0],
              'padded_reginfo_hex': padded, 'padded_reginfo_unchanged': padded[0] == padded[1],
              'installed': False, 'qualified': False}
    (OUT / 'screen.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(screen(), indent=2))
