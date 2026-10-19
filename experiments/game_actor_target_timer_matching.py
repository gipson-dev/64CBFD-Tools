"""Qualified partial-return C; preserve its literal handwritten-consumer ABI."""
from unittest.mock import patch

from tools.experiments import game_actor_target_timer_candidates as source

BUILD=source.BUILD+'/matching'
SOURCE,OWNER,FUNCTION,ENTRY,ROM,WORDS=source.SOURCE,source.OWNER,source.FUNCTION,source.ENTRY,source.ROM,source.WORDS
INPUTS=dict(source.INPUTS)
INPUTS.update({
    'conker/asm/DAFA0.s':'c5428427a06160a918eacdd2b2f0fa8dbcaea5459f1c71e5ce5acd3d9a8d5d29',
    'conker/asm/data/22BEF0.rodata.s':'7ce9790a5ce8b759dec089d2b3d1d42d24e3573b52613377ed0fde5b5a7a28ae',
    'conker/asm/data/22D070.rodata.s':'b03cd22a8bb334900c11b52a82d8d1e3cfd17ad581349a09700fed8f5889c4c5',
    'conker/asm/data/243DC0.rodata.s':'d880517c956cb5bedc6ec5af0abe578f7246661a353d99964907188509231f43'})
SELECTED=source.RESEARCH_PARTIAL.replace(
    '/* Publish the target and update its distance timer and probability flag. */',
    '/* Publish the target and update its distance timer and probability flag.\n'
    ' * Only the negative-target path defines a C result; preserve retail fallthrough. */')
RESEARCH_PARTIAL=SELECTED
compile_profile,payload,link_owner=source.compile_profile,source.payload,source.link_owner


def freeze(root,out):
    with patch.object(source,'INPUTS',INPUTS):return source.freeze(root,out)


def recovered_owner(before,body=None):return source.recovered_owner(before,SELECTED if body is None else body)


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    with patch.object(source,'INPUTS',INPUTS):
        return source.compile_candidate(root,out,name,SELECTED if body is None else body,normal,whole)
