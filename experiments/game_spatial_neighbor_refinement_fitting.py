"""Retain the spatial node index across helper calls without changing its semantics."""
from pathlib import Path
import json

from tools.experiments import game_spatial_neighbor_refinement_candidates as previous

BUILD=previous.BUILD+'/matching'
SOURCE,OWNER,FUNCTION,ENTRY,ROM,WORDS=previous.SOURCE,previous.OWNER,previous.FUNCTION,previous.ENTRY,previous.ROM,previous.WORDS
INPUTS=previous.INPUTS
DECLARATIONS,HELPER_OLD,HELPER_NEW=previous.DECLARATIONS,previous.HELPER_OLD,previous.HELPER_NEW
SELECTED=dict(previous.candidates())['compact-outer-object']
freeze,compile_profile,link_owner,payload=previous.freeze,previous.compile_profile,previous.link_owner,previous.payload


def recovered_owner(before):return previous.recovered_owner(before,SELECTED)


def compile_candidate(root,out,name='selected',body=None,normal=False,whole=False):
    return previous.compile_candidate(root,out,name,SELECTED if body is None else body,normal,whole)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[2]
    _,_,row=compile_candidate(root,root/BUILD)
    print(json.dumps(row,indent=2))
