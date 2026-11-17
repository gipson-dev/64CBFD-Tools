"""Anchor-checked private homes/spills and likely-delay division normalization."""
def derive(words):
    assert len(words) == 491
    result = list(words)
    sites = {}
    def unique(word, name):
        indices = [i for i, value in enumerate(words) if value == word]
        assert len(indices) == 1, (name, hex(word), indices)
        sites[name] = indices[0]
        return indices[0]
    store = unique(0xE7AA00A0, 'gravity-square-store')
    load = unique(0xC7AA00A0, 'gravity-square-load')
    dy = unique(0x46045401, 'first-Y-difference')
    dz = unique(0x46083481, 'first-Z-difference')
    ratio = unique(0x460C1303, 'vertical-ratio')
    force_x = unique(0x460C7382, 'first-force-product')
    assert words[force_x + 1] == 0
    sequence = [0x45000003, 0, 0x44816000, 0, 0x460C0083]
    patterns = [i for i in range(len(words) - len(sequence) + 1) if words[i:i + len(sequence)] == sequence]
    assert len(patterns) == 1
    norm_branch = patterns[0]
    sites['norm-branch'] = norm_branch
    result[store] = 0xE7AA0084
    result[load] = 0xC7AA0084
    result[force_x + 1] = 0xC7B200AC
    result[norm_branch] = 0x45020000
    result[norm_branch + 1] = sequence[-1]
    inserts = {dy: [0xE7B000B0], dz: [0xE7B200AC], ratio: [0xC7B000B0]}
    mapping = {}
    output = []
    for index, word in enumerate(result):
        mapping[index] = len(output)
        output.append(word)
        output.extend(inserts.get(index, []))
    mapping[len(words)] = len(output)
    branches = []
    for index, original in enumerate(words):
        op, rs = original >> 26, original >> 21 & 31
        if op in (1, 4, 5, 6, 7, 20, 21, 22, 23) or op == 17 and rs == 8:
            assert index not in inserts and index + 1 not in inserts
            old_target = index + 1 + (((original & 65535) ^ 32768) - 32768)
            if index == norm_branch:
                old_target = norm_branch + len(sequence)
            assert old_target in mapping, ('escaped branch', index, old_target)
            at = mapping[index]
            displacement = mapping[old_target] - at - 1
            assert -32768 <= displacement <= 32767
            output[at] = output[at] & ~65535 | displacement & 65535
            branches.append(dict(old_word=index, new_word=at, old_target=old_target, new_target=mapping[old_target]))
    assert len(output) == 494
    report = dict(input_words=491, output_words=494, sites=sites, old_to_new=mapping,
                  insertions={str(key): [hex(v) for v in values] for key, values in inserts.items()},
                  changed_existing=[dict(old_word=i, expected=hex(words[i]), replacement=hex(result[i]))
                                    for i in range(len(words)) if words[i] != result[i]],
                  rebuilt_branches=branches, source_installed=False, c_match_credit=0)
    return output, report
