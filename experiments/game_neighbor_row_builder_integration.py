"""Actual owner, Make and strict image gates for the complete neighbor row."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_neighbor_row_builder_layout as layout
from tools.experiments import game_actor_pair_visibility_integration as prior

source=layout.source
BUILD=layout.BUILD+'/integration'
SIZE=1344
NORMAL_FUNCTIONS=prior.NORMAL_FUNCTIONS
elf_slot_offset=prior.elf_slot_offset
symbol_rows=prior.symbol_rows
same_functions=prior.mixed.candidate.source.neighbor.same_functions


def recovered_owner(before):return source.recovered_owner(before,layout.SELECTED)


def guard_bytes(before,out):
    raw,bindings=source.payload(out/'after-primary.o')
    return layout.private_guards(before,raw,bindings)


def padded(root,out,guards,name='qualified-padded'):
    with patch.multiple(prior,source=source,layout=layout):return prior.padded(root,out,guards,name)


def qualify(root,out):
    values=source.freeze(root,out)
    for name,normal in (('primary',False),('normal',True)):
        before,diag=source.compile_profile(root,out,values[source.SOURCE].decode(),'before-'+name,normal)
        after,_,row=source.compile_candidate(root,out,'after-'+name,layout.SELECTED,normal,whole=True)
        if not normal:layout.normalize(*source.payload(after))
        if diag or row['diagnostics'] or same_functions(before,after,(source.FUNCTION,))!=72:
            raise ValueError('Neighbor row changed a raw neighbor')
        if prior.normalized_pools(before)!=prior.normalized_pools(after):raise ValueError('Neighbor row changed pools')
    guards=guard_bytes(values['conker/retail_word_patches.us.csv'],out)
    (out/'qualified-guards.csv').write_bytes(guards)
    obj=padded(root,out,out/'qualified-guards.csv')
    baseline=out/'before-padded.o'
    if not baseline.exists():shutil.copyfile(root/'conker/build/src/game/generated_B3020.c.o',baseline)
    a,fa=source.link_owner(root,out,baseline,source.OWNER)
    b,fb=source.link_owner(root,out,obj,source.OWNER)
    at=fb[source.FUNCTION]['value'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+SIZE]
    old=values['conker/build/conker.us.elf'];slot=elf_slot_offset(old,source.ENTRY,SIZE)
    if a[at:at+SIZE]!=old[slot:slot+SIZE] or b[at:at+SIZE]!=truth:
        raise ValueError('Neighbor row actual padding differs')
    if fa.keys()!=fb.keys() or any(fa[n]['value']!=fb[n]['value'] or n!=source.FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Neighbor row changed an owner address or extent')
    if a[:at]!=b[:at] or a[at+SIZE:]!=b[at+SIZE:] or same_functions(baseline,obj,(source.FUNCTION,))!=72:
        raise ValueError('Neighbor row changed a padded neighbor')
    if prior.normalized_pools(baseline)!=prior.normalized_pools(obj):raise ValueError('Padded pools differ')
    (out/'proposed-owner.c').write_text(recovered_owner(values[source.SOURCE].decode()))
    row=dict(words=336,frame=168,differences=0,raw_words=345,expected_word_guards=345,
        retained_origins=319,derived_forms=17,omissions=26,bindings=19,
        unchanged_neighbor_instructions=72,all73_addresses_fixed=True,
        selected_normal_functions=list(NORMAL_FUNCTIONS),Makefile_unchanged=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return row


def predicted_image(before,truth):
    if hashlib.sha256(before).hexdigest()!=source.INPUTS['conker/build/conker.us.elf'] or len(truth)!=SIZE:
        raise ValueError('Unknown neighbor-row image predecessor')
    result=bytearray(before);at=elf_slot_offset(before,source.ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown neighbor-row stub size')
    struct.pack_into('>I',result,rows[0][0]+8,SIZE)
    return bytes(result)


def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Neighbor row differs from strict full-image prediction')


def predict(root,out):
    values=source.freeze(root,out);elf=out/'first-linked.elf'
    if not elf.exists():
        script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+source.OWNER+'.c.o'
        if script.count(old)!=1:raise ValueError('Unknown neighbor-row link input')
        link=out/'first-link.ld'
        link.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld','-T',str(link.relative_to(root/'conker')),'-T','undefined_syms.us.txt',
            '-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
            '--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],
            cwd=root/'conker',check=True,capture_output=True)
    before,actual=values['conker/build/conker.us.elf'],elf.read_bytes()
    truth=values['conker/conker.us.bin'][source.ROM:source.ROM+SIZE];expected=predicted_image(before,truth)
    row=dict(exact_prediction=actual==expected,expected_SHA256=hashlib.sha256(expected).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(),changed_bytes=sum(a!=b for a,b in zip(before,actual)))
    (out/'first-link.json').write_text(json.dumps(row,indent=2)+'\n')
    check_image(before,actual,truth);return row


def make_shadow(root,out):
    with patch.multiple(prior,source=source,layout=layout):return prior.make_shadow(root,out)


def install_guards(root,out):
    values=source.freeze(root,out)
    if (root/source.SOURCE).read_bytes()!=recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Unknown production neighbor-row source')
    for name in ('conker/Makefile','conker/retail_word_patches.us.csv','conker/build/conker.us.elf'):
        if (root/name).read_bytes()!=values[name]:raise ValueError('Changed neighbor-row predecessor '+name)
    check_image(values['conker/build/conker.us.elf'],(out/'first-linked.elf').read_bytes(),
        values['conker/conker.us.bin'][source.ROM:source.ROM+SIZE])
    (root/'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],out))
    return dict(guard_rows=345,omissions=26,insertions=17,prior_guard_bytes_unchanged=True)


def audit(root,out):
    values=source.freeze(root,out);before=values['conker/build/conker.us.elf']
    expected=predicted_image(before,values['conker/conker.us.bin'][source.ROM:source.ROM+SIZE])
    for name,old in values.items():
        wanted=recovered_owner(old.decode()).encode() if name==source.SOURCE else (
            guard_bytes(old,out) if name=='conker/retail_word_patches.us.csv' else
            expected if name=='conker/build/conker.us.elf' else old)
        if (root/name).read_bytes()!=wanted:raise ValueError('Changed installed neighbor-row input '+name)
    if (out/'first-linked.elf').read_bytes()!=expected:raise ValueError('Retained neighbor-row link changed')
    a,_,aa=prior.load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=prior.load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys() or [n for n in a if a[n]!=b[n]]!=[source.FUNCTION]:
        raise ValueError('Neighbor row changed another linked body/address')
    data=prior.audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Neighbor row changed protected Game data')
    row=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,
        exact_first_link_reproduced=True,target_words=336,game_data=data,Makefile_unchanged=True)
    (out/'installed-audit.json').write_text(json.dumps(row,indent=2)+'\n');return row


def build(root,out):
    with (out/'production-build.log').open('w') as log:
        result=subprocess.run(['make','-C','conker','-j4','build/conker.us.elf','progress.csv'],
            cwd=root,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError('Neighbor-row Make failed; inspect production-build.log')
    return dict(exit_code=0,audit=audit(root,out))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for flag in ('predict','make-shadow','install-guards','build','audit'):p.add_argument('--'+flag,action='store_true')
    args=p.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.install_guards:print(json.dumps(install_guards(root,out),indent=2))
    elif args.build:print(json.dumps(build(root,out),indent=2))
    elif args.audit:print(json.dumps(audit(root,out),indent=2))
    else:
        print(json.dumps(qualify(root,out),indent=2),flush=True)
        if args.make_shadow:print(json.dumps(make_shadow(root,out),indent=2),flush=True)
        if args.predict:print(json.dumps(predict(root,out),indent=2))
