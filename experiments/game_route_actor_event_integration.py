"""Direct event conversion: mixed-owner isolation and immutable first-link audit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from tools.experiments import game_route_actor_event_candidates as source
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

BUILD = source.BUILD
SOURCE = source.SOURCE
FUNCTION = source.FUNCTION
RAW_SHA = 'fd2091bf2ad369fea38cc4cf25a6cec536659ccb69a8c121e0ea51a9aff98acd'
EXPECTED_BINDINGS = {
    20:[('R_MIPS_HI16','D_800CC2D0')],24:[('R_MIPS_LO16','D_800CC2D0')],
    36:[('R_MIPS_HI16','D_800D18A0')],60:[('R_MIPS_LO16','D_800D18A0')],
    116:[('R_MIPS_HI16','D_800D154C')],120:[('R_MIPS_LO16','D_800D154C')],
    128:[('R_MIPS_HI16','D_800C3E78')],144:[('R_MIPS_26','func_1507BB28')],
    148:[('R_MIPS_LO16','D_800C3E78')],
}


def checked(obj):
    raw, bindings = source.payload(obj)
    if hashlib.sha256(raw).hexdigest()!=RAW_SHA or bindings!=EXPECTED_BINDINGS:
        raise ValueError('Changed direct event instructions or relocation bindings')
    return raw, bindings


def qualify(root, out):
    values = source.freeze(root, out)
    before = values[SOURCE].decode()
    same = source.previous.prior.candidate.source.neighbor.same_functions
    bodies = {}
    for label, normal in (('primary',False),('normal',True)):
        old, diag = source.compile_profile(root,out,before,'before-'+label,normal)
        new, words, row = source.compile_candidate(root,out,'after-'+label,whole=True,normal=normal)
        checked(new)
        if diag or row['diagnostics'] or (row['words'],row['frame'],row['differences'])!=(51,24,0):
            raise ValueError('Event profile is not directly exact')
        if same(old,new,(FUNCTION,))!=72 or normalized_pools(old)!=normalized_pools(new):
            raise ValueError('Changed event-owner neighbor or data pool')
        bodies[label] = new
    isolated, _, _ = source.compile_candidate(root,out,'isolated')
    if checked(isolated)!=checked(bodies['primary']) or checked(bodies['normal'])!=checked(isolated):
        raise ValueError('Isolated/full/profile event mismatch')
    guard = out/'before-conker_retail_word_patches.us.csv'
    padded = source.previous.prior.padded(root,out,bodies['primary'],'qualified-padded',guard,bodies['normal'])
    baseline = root/'conker/build/src/game/generated_B3020.c.o'
    a,fa = link_owner(root,out,baseline,source.OWNER)
    b,fb = link_owner(root,out,padded,source.OWNER)
    if (a,fa)!=(b,fb) or normalized_pools(baseline)!=normalized_pools(padded):
        raise ValueError('Direct conversion changed padded code or metadata')
    if same(baseline,padded,())!=73:
        raise ValueError('Direct conversion changed an installed owner function')
    (out/'proposed-owner.c').write_text(source.recovered_owner(before))
    result = dict(words=51,frame=24,word_differences=0,new_guards=0,bindings=9,
        isolated_and_both_profiles_equal=True,neighbors_in_each_profile=72,
        padded_functions_fixed=73,padded_code_metadata_and_pools_fixed=True)
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def predict(root, out):
    values = source.freeze(root,out)
    script = (root/'conker/build/conker.ld').read_text()
    old = 'build/src/game/'+source.OWNER+'.c.o'
    if script.count(old)!=1:
        raise ValueError('Unknown event owner link input')
    path = out/'first-link.ld'
    path.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
    elf = out/'first-linked.elf'
    if not elf.exists():
        subprocess.run(['mips-linux-gnu-ld','-T',str(path.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    before, actual = values['conker/build/conker.us.elf'], elf.read_bytes()
    result = dict(whole_ELF_unchanged=actual==before,before_SHA256=hashlib.sha256(before).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(),before_bytes=len(before),actual_bytes=len(actual),
        changed_bytes=sum(a!=b for a,b in zip(before,actual)))
    (out/'first-link.json').write_text(json.dumps(result,indent=2)+'\n')
    if actual!=before:
        raise ValueError('First direct event link changed image/metadata; retained for diagnosis')
    return result


def audit(root, out):
    values = source.freeze(root,out)
    expected = source.recovered_owner(values[SOURCE].decode()).encode()
    for name, before in values.items():
        want = expected if name==SOURCE else before
        if (root/name).read_bytes()!=want:
            raise ValueError('Changed installed event input: '+name)
    old,_,oa = load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    new,_,na = load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if old!=new or oa!=na:
        raise ValueError('Direct event conversion changed linked bodies or addresses')
    data = audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Direct event conversion changed Game data')
    result = dict(functions=len(new),all_bodies_and_addresses_fixed=True,whole_ELF_unchanged=True,
        guards_and_Makefile_unchanged=True,target_words=51,new_guards=0,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predict',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/BUILD
    if args.audit:
        print(json.dumps(audit(root,out),indent=2))
    else:
        print(json.dumps(qualify(root,out),indent=2),flush=True)
        if args.predict:
            print(json.dumps(predict(root,out),indent=2))
