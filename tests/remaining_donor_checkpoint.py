"""Closed post-donor checkpoint for historical literal-image audits.

Old inputs are never recaptured. The new fixture is accepted only at its pinned
digest; the independent transition test also verifies every executable/data
section, the three removed overflow bodies, and all symbol-definition changes.
"""
import hashlib
import json
from pathlib import Path

from tools.experiments import game_remaining_donor_candidates as source
from tools.tests import unlinked_donor_checkpoint

AFTER = {
    'elf': '65a9c8e783574fbff76c11d3ab000af8015c604a17061f138f5d354e2a2e3968',
    'makefile': 'a7e4fcee0cc3a4dd785e786f1a9f94fd4dedb3656fa4f2210d976b144ee5ec4d',
    'game_35D20': '6659eae27c3cedc49ed7d19b3f80bfc41740e1e923b2947e321959f7654ec227',
    'game_476D0': '05a16ebd87fee7a6894d5a4fc1231a6322ae7ccd4aac7ffa9eb7a55616e486b1',
    'game_70200': '1b6c11aa53cc96e351f51671daae61669726ff89f45806bc47082d56414dca6b',
    'game_83300': '98aa48a292ca9949b0d1a8e0d45b5e7294ef6e1ac40c72bd0c11ec420c06be63',
    'game_981E0': 'e83baa9f46721ba0cdfae136976b6f4d36c1945b75a33998d212250dc7e2b9bb',
    'game_A28B0': 'ed2c59e1ce18d6d3aca652e654847240e4fa20f6db0b96ef357f16ed6dcda78e',
    'game_C8950': '9323f9108a4910237a56fdbbccc12300f51673b0b883217c52071134c49c800b',
    'game_EF410': '2b8db262d35a347d83adbb3cdf39d2844bc2691b186c2c0803129eac404dc177',
    'game_1944C0': '328877b17dd2d16b88ec270bea2c09f900bceaa584cb904fa75b0e3e8029084b',
    'libultra/audio/game_21FC90': 'f967e897506b329bbc9c57d75aba01fb3c97d87367932e44d69748f49e36bbe6',
    'game_221290': '6902258a64fae5f49c0759102b1ce2d452a8e6d27b9b80efcaeaeb31377e27f8',
}


def fixture(root, stage, key):
    out = root / source.BUILD
    data = (out / (stage + '-' + key.replace('/', '_'))).read_bytes()
    expected = AFTER[key] if stage == 'after' else json.loads((out / 'baseline.json').read_text())[key]
    assert hashlib.sha256(data).hexdigest() == expected, 'Modified checkpoint fixture: ' + key
    return data


def previous_owner(current, owner, root):
    current = unlinked_donor_checkpoint.previous_input(current.encode(), 'conker/src/' + owner + '.c', root).decode()
    if hashlib.sha256(current.encode()).hexdigest() == AFTER[owner]:
        return fixture(root, 'before', owner).decode()
    return current


def previous_input(current, path, root):
    current = unlinked_donor_checkpoint.previous_input(current, path, root)
    relative = str(path).replace('\\', '/')
    if relative.startswith(str(root).replace('\\', '/') + '/'):
        relative = relative[len(str(root)) + 1:]
    key = {'conker/build/conker.us.elf': 'elf', 'conker/Makefile': 'makefile'}.get(relative)
    if relative.startswith('conker/src/') and relative.endswith('.c'):
        key = relative[len('conker/src/'):-2]
    if key in AFTER and hashlib.sha256(current).hexdigest() == AFTER[key]:
        return fixture(root, 'before', key)
    return current
