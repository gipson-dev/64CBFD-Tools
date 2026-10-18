"""Predict, qualify and audit the same complete spline payload installation."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_spline_payload_layout as layout
from tools.experiments import game_route_spline_payload_native as native
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,SYMBOL,read_c_string

source=layout.source.source
prior=source.prior.prior
BUILD=native.BUILD
OWNER,FUNCTION,ENTRY,ROM=source.OWNER,source.FUNCTION,source.ENTRY,source.ROM
INPUTS=source.INPUTS
AFTER={'conker/build/conker.us.elf':'15138e12aba5c25923d3438ff1db199d550accd18ad4596918a4b2ecd71ec8fd',
    'conker/src/game/generated_B3020.c':'a98ad9f3b781a4f93f39e45cbbe9646054c60c7b1d329bb5b2d21fb1499f7573',
    'conker/retail_word_patches.us.csv':'d9a994d78370af27db71af35f5639096bb0afc56e63b197b7bc6b19bffb7f902'}
SUCCESSOR_FILES={'conker/build/conker.us.elf':'after-elf','conker/src/game/generated_B3020.c':'after-owner',
    'conker/retail_word_patches.us.csv':'after-guards'}
raw_read,raw_text=Path.read_bytes,Path.read_text
# Account only for these observed linker symbol/string order changes.
SYMBOL_ORDERS=((('func_1500B3B0','D_8008D680','D_80088910'),('D_80088910','func_1500B3B0','D_8008D680')),
    (('D_8009979C','D_800888E0'),('D_800888E0','D_8009979C')),
    (('func_150A7A14','D_8008891C'),('D_8008891C','func_150A7A14')))


def freeze(root,out):return source.freeze(root,out)


def recovered_owner(before):return source.recovered_owner(before,layout.source.joint_selected())


def qualify(root,out):
    values=freeze(root,out);before=values['conker/src/game/generated_B3020.c'].decode();body=recovered_owner(before)
    primary,diag=prior.compile_profile(root,out,body,'primary-no-unroll')
    raw,bindings=layout.source.checked(primary,True);normalized,moved=layout.normalize(raw,bindings)
    normal,nd=prior.compile_profile(root,out,body,'override-normal',True);prior.candidate.checked(normal)
    original,od=prior.compile_profile(root,out,before,'baseline-primary')
    old_normal,ond=prior.compile_profile(root,out,before,'baseline-normal',True)
    if any((diag,nd,od,ond)):raise ValueError('Spline payload profile diagnostics')
    for a,b in ((original,primary),(old_normal,normal)):
        if source.prior.same_functions(a,b,(FUNCTION,))!=72:raise ValueError('Changed spline owner neighbor')
    guards=layout.private_guards(values['conker/retail_word_patches.us.csv'],raw,bindings)
    (out/'qualified-guards.csv').write_bytes(guards);(out/'proposed-owner.c').write_text(body)
    (out/'unchanged-guards.csv').write_bytes(values['conker/retail_word_patches.us.csv'])
    old=prior.padded(root,out,original,'baseline-padded',out/'unchanged-guards.csv',old_normal)
    padded=prior.padded(root,out,primary,'qualified-padded',out/'qualified-guards.csv',normal)
    a,fa=prior.link_owner(root,out,old,OWNER);b,fb=prior.link_owner(root,out,padded,OWNER);at=fb[FUNCTION]['value']
    expected=values['conker/conker.us.bin'][ROM:ROM+1220]
    if b[at:at+1220]!=expected or a[:at]!=b[:at] or a[at+1220:]!=b[at+1220:]:
        raise ValueError('Private padding changes target or other owner bytes')
    if set(fa)!=set(fb) or any(fa[n]['value']!=fb[n]['value'] or n!=FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Private padding changes definitions')
    if normalized_pools(old)!=normalized_pools(padded):raise ValueError('Padded pools changed')
    live=hashlib.sha256(raw_read(root/'conker/build/conker.us.elf')).hexdigest()
    stage=old if live==INPUTS['conker/build/conker.us.elf'] else padded if live==AFTER['conker/build/conker.us.elf'] else None
    if stage is None:raise ValueError('Unknown spline image stage')
    source.prior.same_functions(stage,root/'conker/build/src/game/generated_B3020.c.o')
    row=dict(words=305,frame=248,normalized_differences=0,raw_differences=140,guards=305,
        primary_and_normal_neighbors_unchanged=72,all_other_padded_bytes_fixed=True,production_installed=False)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return primary,padded,row


def make_shadow(root,out):
    raw,bindings=layout.source.checked(out/'primary-no-unroll.o',True)
    def recovered_guards(before,projection_raw,projection_bindings):
        if (projection_raw,projection_bindings)!=prior.candidate.checked(out/'override-normal.o'):
            raise ValueError('Changed projection override')
        return layout.private_guards(before,raw,bindings)
    with patch.multiple(prior,freeze=freeze,recovered_owner=recovered_owner,recovered_makefile=lambda x:x,
            recovered_guards=recovered_guards):
        return prior.make_shadow(root,out)


def metadata_order(image):
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols
    result=bytearray(image);rows=prior.symbol_rows(image);header=ELF_HEADER.unpack_from(image)
    headers=[SECTION_HEADER.unpack_from(image,header[6]+i*header[11]) for i in range(header[12])]
    names=headers[header[13]];strings=image[names[4]:names[4]+names[5]]
    section=next(h for h in headers if read_c_string(strings,h[0])=='.strtab')
    for old,new in SYMBOL_ORDERS:
        indices=[i for i in range(len(rows)-len(old)+1) if tuple(r[1] for r in rows[i:i+len(old)])==old]
        if len(indices)!=1:raise ValueError('Unknown spline symbol ordering')
        group=rows[indices[0]:indices[0]+len(old)];lookup={r[1]:r[2] for r in group}
        start=group[0][2][0];old_strings=b''.join(n.encode()+b'\0' for n in old);new_strings=b''.join(n.encode()+b'\0' for n in new)
        if len(old_strings)!=len(new_strings) or image[section[4]+start:section[4]+start+len(old_strings)]!=old_strings:
            raise ValueError('Unknown spline symbol strings')
        result[section[4]+start:section[4]+start+len(old_strings)]=new_strings;offset=start
        for destination,name in zip(group,new):
            SYMBOL.pack_into(result,destination[0],offset,*lookup[name][1:]);offset+=len(name)+1
    if canonical_symbols(image)!=canonical_symbols(bytes(result)):raise ValueError('Spline metadata definitions changed')
    return bytes(result)


def predicted_image(before,span):
    if len(span)!=1220:raise ValueError('Wrong spline target extent')
    image=bytearray(before);at=prior.elf_slot_offset(before,ENTRY,1220);image[at:at+1220]=span
    rows=[r for r in prior.symbol_rows(before) if r[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Wrong spline predecessor extent')
    struct.pack_into('>I',image,rows[0][0]+8,1220);result=metadata_order(bytes(image))
    if hashlib.sha256(result).hexdigest()!=AFTER['conker/build/conker.us.elf']:raise ValueError('Changed first spline prediction')
    return result


def predict(root,out):
    values=freeze(root,out);_,padded,row=qualify(root,out);make_shadow(root,out)
    script=raw_text(root/'conker/build/conker.ld');old='build/src/game/'+OWNER+'.c.o'
    if script.count(old)!=1:raise ValueError('Unexpected spline linker input')
    ld=out/'predicted.ld';ld.write_text(script.replace(old,padded.relative_to(root/'conker').as_posix()))
    elf=out/'trial-predicted.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(ld.relative_to(root/'conker')),
        '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
        '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],
        cwd=root/'conker',capture_output=True,check=True)
    image=raw_read(elf);expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+1220])
    if image!=expected:raise ValueError('First spline ELF prediction changes unrelated bytes')
    after={'conker/build/conker.us.elf':image,'conker/src/game/generated_B3020.c':recovered_owner(values['conker/src/game/generated_B3020.c'].decode()).encode(),
        'conker/retail_word_patches.us.csv':raw_read(out/'qualified-guards.csv')}
    for path,data in after.items():
        target=out/SUCCESSOR_FILES[path]
        if target.exists() and raw_read(target)!=data:raise ValueError('Changed first spline successor '+path)
        if not target.exists():target.write_bytes(data)
    result=dict(after={p:hashlib.sha256(v).hexdigest() for p,v in after.items()},
        changed_ELF_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],image)),
        only_target_code_size_and_closed_symbol_order_changed=True,metadata_named_groups=3,metadata_definitions_unchanged=True)
    (out/'prediction.json').write_text(json.dumps(result,indent=2)+'\n');return result


def expected_inputs(root,out):
    values={p:raw_read(out/n) for p,n in SUCCESSOR_FILES.items()}
    if not AFTER or {p:hashlib.sha256(v).hexdigest() for p,v in values.items()}!=AFTER:
        raise ValueError('Changed first spline successor')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(prior.candidate.source.checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):yield


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),prior.candidate.source.checkpoint.historical_view(root,out):yield


def verify(root,out,installed=False):
    with checkpoint_context():return prior.candidate.source.checkpoint.verify(root,out,installed)


def install_guards(root,out):
    expected=expected_inputs(root,out)
    for path in ('conker/build/conker.us.elf','conker/retail_word_patches.us.csv'):
        before=raw_read(out/('before-%02d'%list(INPUTS).index(path)))
        if raw_read(root/path)!=before:raise ValueError('Unexpected spline installation stage '+path)
    if raw_read(root/'conker/src/game/generated_B3020.c')!=expected['conker/src/game/generated_B3020.c']:
        raise ValueError('Install qualified spline source first')
    prefix=raw_read(root/'conker/retail_word_patches.us.csv')
    if not expected['conker/retail_word_patches.us.csv'].startswith(prefix):raise ValueError('Guard prefix changed')
    (root/'conker/retail_word_patches.us.csv').write_bytes(expected['conker/retail_word_patches.us.csv'])


def audit(root,out):
    verify(root,out,True)
    for index,(path,digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out/('before-%02d'%index))).hexdigest()!=digest or \
                hashlib.sha256(raw_read(root/path)).hexdigest()!=AFTER.get(path,digest):raise ValueError('Changed installed spline input '+path)
    before=raw_read(out/('before-%02d'%list(INPUTS).index('conker/build/conker.us.elf')))
    actual=raw_read(root/'conker/build/conker.us.elf');rom=raw_read(root/'conker/conker.us.bin')
    if actual!=raw_read(out/'after-elf') or actual!=predicted_image(before,rom[ROM:ROM+1220]):
        raise ValueError('Installed spline image differs from first prediction')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    old,_,oa=load_elf_functions(str(out/('before-%02d'%list(INPUTS).index('conker/build/conker.us.elf'))),'mips-linux-gnu-objdump')
    new,_,na=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if oa!=na or old.keys()!=new.keys() or [n for n in old if old[n]!=new[n]]!=[FUNCTION]:
        raise ValueError('Spline changed another linked body/address')
    source.prior.same_functions(out/'qualified-padded.o',root/'conker/build/src/game/generated_B3020.c.o')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Spline changed protected Game data')
    result=dict(functions=len(old),all_addresses_fixed=True,only_target_body_size_and_closed_symbol_order_changed=True,
        metadata_named_groups=3,metadata_definitions_unchanged=True,
        first_prediction_reproduced=True,changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--audit',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];print(json.dumps(audit(root,root/BUILD) if args.audit else predict(root,root/BUILD),indent=2))
