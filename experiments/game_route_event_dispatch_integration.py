"""Direct route dispatcher: owner isolation, unchanged ELF and installed audit."""
import argparse
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from tools.experiments import game_route_event_dispatch_candidates as source
from tools.experiments import game_route_actor_event_integration as previous
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

BUILD = source.BUILD
RAW_SHA = 'a222a2eac943e70a0f266df106590d9b45dcbd5d88de6eeebfc736d50120ba92'
EXPECTED_BINDINGS = {
    16:[('R_MIPS_HI16','D_800872A0')],20:[('R_MIPS_LO16','D_800872A0')],
    64:[('R_MIPS_HI16','D_800CC2D0')],104:[('R_MIPS_LO16','D_800CC2D0')],
    120:[('R_MIPS_26','func_1508802C')],164:[('R_MIPS_HI16','D_800D239A')],
    168:[('R_MIPS_LO16','D_800D239A')],
}


def checked(obj):
    raw,bindings=source.payload(obj)
    if hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=EXPECTED_BINDINGS:
        raise ValueError('Changed direct dispatch instructions or bindings')
    return raw,bindings


def qualify(root,out):
    values=source.freeze(root,out)
    same=mixed.candidate.source.neighbor.same_functions
    bodies={}
    for label,normal in (('primary',False),('normal',True)):
        old,diag=source.compile_profile(root,out,values[source.SOURCE].decode(),'before-'+label,normal)
        new,words,row=source.compile_candidate(root,out,'after-'+label,whole=True,normal=normal)
        checked(new)
        if diag or row['diagnostics'] or (row['words'],row['frame'],row['differences'])!=(53,32,0):
            raise ValueError('Dispatch profile is not directly exact')
        if same(old,new,(source.FUNCTION,))!=72 or normalized_pools(old)!=normalized_pools(new):
            raise ValueError('Changed dispatch owner neighbor or data pool')
        bodies[label]=new
    isolated,_,_=source.compile_candidate(root,out,'isolated')
    if checked(isolated)!=checked(bodies['primary']) or checked(bodies['normal'])!=checked(isolated):
        raise ValueError('Isolated/full/profile dispatch mismatch')
    obj=mixed.padded(root,out,bodies['primary'],'qualified-padded',
        out/'before-conker_retail_word_patches.us.csv',bodies['normal'])
    baseline=root/'conker/build/src/game/generated_B3020.c.o'
    if link_owner(root,out,baseline,source.OWNER)!=link_owner(root,out,obj,source.OWNER) or (
            normalized_pools(baseline)!=normalized_pools(obj)) or same(baseline,obj,())!=73:
        raise ValueError('Changed padded dispatch owner body/metadata/pool')
    (out/'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
    result=dict(words=53,frame=32,word_differences=0,new_guards=0,bindings=7,
        isolated_and_both_profiles_equal=True,neighbors_in_each_profile=72,padded_functions_fixed=73)
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def predict(root,out):
    with patch.object(previous,'source',source):
        return previous.predict(root,out)


def audit(root,out):
    values=source.freeze(root,out)
    for name,before in values.items():
        want=source.recovered_owner(before.decode()).encode() if name==source.SOURCE else before
        if (root/name).read_bytes()!=want:
            raise ValueError('Changed installed dispatch input: '+name)
    old,_,oa=load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    new,_,na=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if old!=new or oa!=na:
        raise ValueError('Dispatch changed a linked function or address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Dispatch changed protected Game data')
    result=dict(functions=len(new),all_bodies_and_addresses_fixed=True,whole_ELF_unchanged=True,
        guards_and_Makefile_unchanged=True,target_words=53,new_guards=0,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    out=root/BUILD
    if args.audit:
        print(json.dumps(audit(root,out),indent=2))
    else:
        print(json.dumps(qualify(root,out),indent=2),flush=True)
        if args.predict:print(json.dumps(predict(root,out),indent=2))
