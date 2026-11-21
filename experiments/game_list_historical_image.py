"""Exact qualified dependency overrides for immutable historical list fixtures.

The live linker/source/objects are never edited. A manifest entry is selected
only by an exact owner-source/guard pair, then every live source/object and
frozen object fingerprint is checked before constructing the private script.
"""
from contextlib import contextmanager
from pathlib import Path
import hashlib

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def qualified_input_context(root,source,manifest):
    """Accept supplemental inputs only with their exact source/guard context."""
    selector=dict(source_sha256=digest(root/source),
                  guards_sha256=digest(root/'conker/retail_word_patches.us.csv'))
    matches=[entry for entry in manifest.get('qualified_input_contexts',[])
             if entry['selector']==selector]
    if not matches:return {}
    if len(matches)!=1:raise ValueError('Duplicate qualified input context')
    for name,expected in matches[0]['inputs'].items():
        if digest(root/name)!=expected:
            raise ValueError('Qualified context fingerprint changed: '+name)
    return dict(matches[0]['overrides'])


def assert_qualified_makefile(root,baseline,source,manifest):
    expected=digest(baseline/'conker/Makefile')
    if expected!=manifest['inputs']['conker/Makefile']:
        raise ValueError('Historical Makefile fixture changed')
    overrides=qualified_input_context(root,source,manifest)
    if digest(root/'conker/Makefile')!=overrides.get('conker/Makefile',expected):
        raise ValueError('Unqualified Makefile input')

@contextmanager
def historical_dependencies(root,output,source,manifest):
    pair=dict(source_sha256=digest(root/source),guards_sha256=digest(root/'conker/retail_word_patches.us.csv'))
    matches=[r for r in manifest.get('historical_image_dependencies',[])if{key:r[key]for key in pair}==pair]
    if not matches:
        yield 'conker/build/conker.ld';return
    if len(matches)!=1:raise ValueError('Duplicate historical dependency snapshot')
    text=(root/'conker/build/conker.ld').read_text()
    for entry in matches[0]['overrides']:
        for key,sha_key in(('source','source_sha256'),('object','live_sha256'),('frozen','frozen_sha256')):
            if digest(root/entry[key])!=entry[sha_key]:raise ValueError('Historical dependency fingerprint changed: '+entry[key])
        old=entry['object'].removeprefix('conker/');new=entry['frozen'].removeprefix('conker/')
        if text.count(old)!=1:raise ValueError('Historical linker dependency reference changed: '+old)
        text=text.replace(old,new)
    script=output/'historical-dependencies.ld';script.write_text(text)
    yield script.relative_to(root).as_posix()
