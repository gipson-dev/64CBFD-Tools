"""Refresh complete archive/comment/conditional coverage and every retained draft screen.

Original inputs are read-only. Historical successful objects are hash-checked
and re-linked by the existing word screen, not described as fresh compiles.
Failed or unanchored drafts remain explicit queues, not matching credit.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import struct

from tools.experiments import alternative_source_c_inventory as lexical
from tools.experiments import alternative_source_commented_c_audit as comments
from tools.experiments import alternative_source_draft_word_screen as words
from tools.experiments import alternative_source_byte_match_audit as linked
from tools.experiments import game_packed_record_scale as previous
from tools.tests import packed_record_scale_checkpoint as checkpoint
from tools import match_progress as matcher

BUILD = 'conker/build/additional-source-coverage-20261015'
HISTORY = 'conker/build/alternative-source-byte-audit-20261014'
MANIFEST_SHA256 = 'd8a07543bcd17a19096e744a66f67a2bf36ba153b51c81e569ae76b95e6581e1'
SCREENS = {
    'whole': 'whole-c-compile-gate-relative.json',
    'isolated': 'isolated-c-compile-full-v2.json',
    'interface-retry': 'isolated-c-compile-unused-retry.json',
    'commented': 'commented-c-compile-profile-qualified.json',
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_archive(archive, manifest):
    if digest(manifest) != MANIFEST_SHA256:
        raise ValueError('Unknown original archive manifest')
    rows = json.loads(manifest.read_text(encoding='utf-8-sig'))['files']
    if len(rows) != 801:
        raise ValueError('Changed original archive file count')
    for name, expected in rows.items():
        if digest(archive / name).upper() != expected:
            raise ValueError('Changed original archive input: ' + name)
    return rows


def pending_failures(receipts, current_exact):
    """Deduplicate overlapping failed-file, isolated and commented queues."""
    groups = {}
    for origin, receipt in receipts.items():
        names = {row['function'] for row in receipt['draft_compile_gate'] if row['status'] == 'compile_error'}
        groups[origin] = sorted(names - current_exact)
    union = sorted(set().union(*(set(names) for names in groups.values())))
    return dict(by_origin=groups, unique_functions=union, unique_count=len(union),
        queue_counts_must_not_be_added=True, historical_failures_not_fresh_compiles=True)


def verify_receipts(snapshot, receipts):
    counts = Counter()
    for receipt in receipts.values():
        for row in receipt['draft_compile_gate']:
            if digest(snapshot / row['path']) != row['source_sha256']:
                raise ValueError('Changed historical source: ' + row['path'])
            if row.get('generated_input_path') and digest(snapshot / row['generated_input_path']) != row['generated_input_sha256']:
                raise ValueError('Changed historical generated input: ' + row['function'])
            if row.get('isolated_source_sha256') and digest(Path(row['object']).with_suffix('.c')) != row['isolated_source_sha256']:
                raise ValueError('Changed historical isolated input: ' + row['function'])
            if row['status'] == 'object_compiled' and digest(Path(row['object'])) != row['object_sha256']:
                raise ValueError('Changed historical object: ' + row['object'])
            counts[row['status']] += 1
    return dict(counts)


def binding_queue(screens):
    found = {}
    for origin, screen in screens.items():
        for row in screen['function_results']:
            if row['status'] != 'needs_symbol_or_pool_binding':
                continue
            entry = found.setdefault(row['function'], dict(origins=set(), symbols=set()))
            entry['origins'].add(origin)
            entry['symbols'].update(row['unresolved'])
    return {name: {key: sorted(values) for key, values in row.items()} for name, row in sorted(found.items())}


def disabled_regions(source, records):
    result = []
    for row in records:
        if row['conditional_region']:
            directives = [line.strip() for line in source.splitlines()[:row['line']]
                if line.lstrip().startswith(('#if ', '#ifdef ', '#ifndef '))]
            result.append(dict(row, preceding_conditional=directives[-1] if directives else None,
                conditional_is_not_proof_of_active_compilation=True))
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def run(root, out, rescreen=True):
    out.mkdir(exist_ok=True)
    archive = root / '../Another Source/CBFD-Recompiled/conker'
    project, reference = archive / 'conker', root / 'conker'
    history = root / HISTORY
    snapshot = history / 'snapshot/conker'
    before = dict(previous.BASELINE, **checkpoint.AFTER)
    for key, path in previous.PATHS.items():
        if digest(root / path) != before[key]:
            raise ValueError('Changed current audit input: ' + key)
    manifest = verify_archive(archive, history / 'source-before.json')
    anchors = matcher.load_symbol_addrs(str(reference / 'symbol_addrs.us.txt'))
    active = lexical.inventory(reference, project)
    save(out / 'active-inventory.json', active)
    print('Fresh active inventory: %d C files / %d definitions' % (active['source_files'], active['definitions']), flush=True)
    drafts = comments.audit(root, reference, project, out / 'commented-inventory.json')
    save(out / 'commented-inventory.json', drafts)
    print('Fresh commented inventory: %d records' % drafts['commented_definitions'], flush=True)
    header_records, conditional, source_files = [], [], []
    for folder in (project / 'src', project / 'include'):
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or path.suffix.lower() not in ('.c', '.h', '.inc'):
                continue
            relative = path.relative_to(archive).as_posix()
            if relative not in manifest:
                raise ValueError('Uninventoried game source input: ' + relative)
            source_files.append(relative)
            text = path.read_text()
            if path.suffix.lower() == '.c':
                name = path.relative_to(project).as_posix()
                records = [row for row in active['function_definitions'] if row['path'] == name]
                conditional.extend(dict(row, path=name) for row in disabled_regions(text, records))
                if path.read_bytes() != (snapshot / name).read_bytes():
                    raise ValueError('Changed historical C input: ' + name)
            else:
                if path.suffix.lower() == '.h' and path.read_bytes() != (snapshot / path.relative_to(project)).read_bytes():
                    raise ValueError('Changed historical header input: ' + relative)
                header_records.append(dict(path=relative, definitions=lexical.definitions(text),
                    commented_definitions=comments.commented_definitions(text, anchors)))
    old_receipts = {name: json.loads((history / receipt).read_text()) for name, receipt in SCREENS.items()}
    historical_inputs = verify_receipts(snapshot, old_receipts)
    screens = {}
    screen_results = {}
    linked_summary = None
    if rescreen:
        for name, receipt in SCREENS.items():
            result = words.screen(reference, snapshot, history / receipt, out / ('objects-' + name))
            save(out / ('screen-' + name + '.json'), result)
            screen_results[name] = result
            screens[name] = dict(statuses=result['statuses'], objects=result['screened_compiled_draft_files'],
                provisional_candidates=result['provisional_candidates'], receipt_sha256=digest(history / receipt))
            print('Fresh %s word screen: %s' % (name, screens[name]['statuses']), flush=True)
        result = linked.audit(reference, snapshot)
        save(out / 'linked-audit.json', result)
        linked_summary = dict(candidate=result['candidate'], potential_function_donors=result['potential_function_donors'],
            unanchored_C_rows=result['unanchored_C_rows'], diagnostic_not_runnable=True)
    catalogue = [row for row in csv.DictReader((reference / 'progress.csv').open()) if row['version'] == 'us' and linked.code_name(row['function'])]
    segments = matcher.load_segments('us', str(reference / 'progress.csv'))
    matcher.add_retail_lengths(catalogue, 'us', segments, anchors)
    current, current_symbols, addresses = matcher.load_elf_functions(str(reference / 'build/conker.us.elf'), 'mips-linux-gnu-objdump')
    rom = (reference / 'conker.us.bin').read_bytes()
    exact = set()
    for row in catalogue:
        entry = matcher.function_vram(row, anchors)
        base, offset = segments[row['section']]
        truth = list(struct.unpack_from('>%dI' % row['_retail_nwords'], rom, offset + entry - base))
        if row['language'] == 'c' and addresses.get(row['function']) == entry and matcher.classify(
                current.get(row['function'], []), truth, current_symbols, anchors)[0] == 'exact':
            exact.add(row['function'])
    for row in conditional:
        row['already_exact_active_C'] = row['function'] in exact
    summary = dict(original_files_verified=len(manifest), original_extension_counts=dict(Counter(Path(p).suffix or '<no extension>' for p in manifest)),
        game_source_inputs=len(source_files), game_extension_counts=dict(Counter(Path(p).suffix for p in source_files)),
        other_archive_files=len(manifest) - len(source_files), other_files_are_not_implicitly_retail_code=True,
        active_C_files=active['source_files'], active_lexical_definitions=active['definitions'],
        active_trivial_definitions=active['trivial_definitions'], active_unanchored_definitions=[row for row in active['function_definitions'] if not row['canonical_function']],
        commented_definitions=drafts['commented_definitions'], commented_statuses=drafts['statuses'],
        header_and_assembly_support_files=header_records, conditional_definitions=conditional,
        screens=screens, linked_audit=linked_summary,
        verified_historical_inputs=historical_inputs, pending_bindings=binding_queue(screen_results),
        pending_failures=pending_failures({k: old_receipts[k] for k in ('interface-retry', 'commented')}, exact),
        current_exact_executable_C_functions=len(exact), executable_C_catalogue=sum(row['language'] == 'c' for row in catalogue),
        executable_audit_excludes_D_labels_and_NON_MATCHING_bookkeeping=True, baseline_current_inputs=before,
        reference_ELF_sha256=digest(reference / 'build/conker.us.elf'),
        no_source_adoption_or_matching_credit=True, failed_or_unbound_bodies_remain_open=True)
    verify_archive(archive, history / 'source-before.json')
    for key, path in previous.PATHS.items():
        if digest(root / path) != before[key]:
            raise ValueError('Audit changed current input: ' + key)
    save(out / 'coverage.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory-only', action='store_true')
    args = parser.parse_args()
    root = Path.cwd()
    result = run(root, root / BUILD, not args.inventory_only)
    print(json.dumps({k: v for k, v in result.items() if k not in ('header_and_assembly_support_files',
        'active_unanchored_definitions', 'baseline_current_inputs', 'pending_failures')}, indent=2))


if __name__ == '__main__':
    main()
