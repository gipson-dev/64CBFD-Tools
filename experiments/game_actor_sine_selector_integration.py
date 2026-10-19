"""Qualify actual selector padding and strictly predict the complete linked image."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_actor_sine_selector_candidates as source
from tools.experiments import game_actor_sine_selector_layout as layout
from tools.experiments import game_route_limit_switch_integration as previous
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments import game_category_boundaries_integration as symbol_layout
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

BUILD=source.BUILD+'/integration'
SYMBOL_RUNS=(
    (('D_8009DA4C','func_150B73F0'),('func_150B73F0','D_8009DA4C')),
    (('D_8009DA58','D_80098628','D_800A6028'),('D_80098628','D_800A6028','D_8009DA58')),
    (('D_8009DA50','func_10004DB0','D_800C3510'),('func_10004DB0','D_800C3510','D_8009DA50')),
    (('D_8009DA44','func_1512E5F0','func_15086098','func_150DDF88','D_800A6014'),
     ('func_1512E5F0','func_15086098','func_150DDF88','D_800A6014','D_8009DA44')))


def guard_bytes(before,obj):
    raw,bindings=source.payload(obj);return layout.private_guards(before,raw,bindings)


def qualify(root,out):
    values=source.freeze(root,out);same=mixed.candidate.source.neighbor.same_functions;objects={}
    for label,normal in (('primary',False),('normal',True)):
        old,diag=source.compile_profile(root,out,values[source.SOURCE].decode(),'before-'+label,normal)
        new,_,row=source.compile_candidate(root,out,'after-'+label,whole=True,normal=normal)
        raw,bindings=source.payload(new);layout.normalize(raw,bindings)
        if diag or row['diagnostics'] or same(old,new,(source.FUNCTION,))!=72 or normalized_pools(old)!=normalized_pools(new):
            raise ValueError('Changed selector profile, neighbor or pool')
        objects[label]=new
    (out/'qualified-guards.csv').write_bytes(guard_bytes(values['conker/retail_word_patches.us.csv'],objects['primary']))
    obj=mixed.padded(root,out,objects['primary'],'qualified-padded',out/'qualified-guards.csv',objects['normal'])
    baseline=root/'conker/build/src/game/generated_B3020.c.o'
    a,fa=source.link_owner(root,out,baseline,source.OWNER);b,fb=source.link_owner(root,out,obj,source.OWNER)
    at=fb[source.FUNCTION]['value'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+544]
    if fb[source.FUNCTION]['size']!=544 or b[at:at+544]!=truth:raise ValueError('Padded selector is not exact')
    if fa.keys()!=fb.keys() or any(fa[n]['value']!=fb[n]['value'] or n!=source.FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Changed another selector owner address/extent')
    if a[:at]!=b[:at] or a[at+544:]!=b[at+544:] or same(baseline,obj,(source.FUNCTION,))!=72:
        raise ValueError('Changed another padded selector owner instruction')
    if normalized_pools(baseline)!=normalized_pools(obj):raise ValueError('Changed selector owner pools')
    (out/'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
    row=dict(words=136,frame=112,differences=0,guards=138,neighbors_each_profile=72,all73_addresses_fixed=True,
        source_unique_origins=135,omitted_dead_words=3,inserted_cursor_move=1,all19_bindings_retained=True)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n');return row


def predicted_image(before,truth):
    if hashlib.sha256(before).hexdigest()!=source.INPUTS['conker/build/conker.us.elf'] or len(truth)!=544:
        raise ValueError('Unknown selector image predecessor')
    result=bytearray(before);at=elf_slot_offset(before,source.ENTRY,544);result[at:at+544]=truth
    rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown selector stub extent')
    struct.pack_into('>I',result,rows[0][0]+8,544)
    with patch.object(symbol_layout,'SYMBOL_RUNS',SYMBOL_RUNS):symbol_layout.predict_symbol_runs(result)
    return bytes(result)


def check_image(before,actual,truth):
    expected=predicted_image(before,truth)
    if actual!=expected:raise ValueError('Selector image differs from exact prediction')
    return expected


def predict(root,out):
    values=source.freeze(root,out);elf=out/'first-linked.elf'
    if not elf.exists():
        script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+source.OWNER+'.c.o'
        if script.count(old)!=1:raise ValueError('Unknown selector linker input')
        link=out/'first-link.ld';link.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld','-T',str(link.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
            '--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+544]
    expected=predicted_image(before,truth)
    row=dict(expected_SHA256=hashlib.sha256(expected).hexdigest(),actual_SHA256=hashlib.sha256(actual).hexdigest(),
        exact_prediction=actual==expected,image_bytes=len(actual),changed_bytes=sum(a!=b for a,b in zip(before,actual)))
    receipt=out/'first-link.json';initial=out/'initial-first-link-diagnosis.json'
    if receipt.exists() and not json.loads(receipt.read_text())['exact_prediction'] and not initial.exists():initial.write_bytes(receipt.read_bytes())
    receipt.write_text(json.dumps(row,indent=2)+'\n');check_image(before,actual,truth);return row


def make_shadow(root,out):
    with patch.multiple(previous,source=source,guard_bytes=guard_bytes):return previous.make_shadow(root,out)


def install_guards(root,out):
    values=source.freeze(root,out);before=values['conker/retail_word_patches.us.csv']
    if (root/source.SOURCE).read_bytes()!=source.recovered_owner(values[source.SOURCE].decode()).encode():raise ValueError('Unknown selector source before guard installation')
    if (root/'conker/retail_word_patches.us.csv').read_bytes()!=before:raise ValueError('Changed selector guard predecessor')
    if (root/'conker/build/conker.us.elf').read_bytes()!=values['conker/build/conker.us.elf']:raise ValueError('Changed selector image before guard installation')
    check_image(values['conker/build/conker.us.elf'],(out/'first-linked.elf').read_bytes(),values['conker/conker.us.bin'][source.ROM:source.ROM+544])
    (root/'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(before,out/'after-primary.o'))
    return dict(generated_guard_rows=138,historical_prefix_preserved=True)


def audit(root,out):
    values=source.freeze(root,out);before=values['conker/build/conker.us.elf']
    expected=predicted_image(before,values['conker/conker.us.bin'][source.ROM:source.ROM+544])
    for name,old in values.items():
        wanted=source.recovered_owner(old.decode()).encode() if name==source.SOURCE else (
            guard_bytes(old,out/'after-primary.o') if name=='conker/retail_word_patches.us.csv' else expected if name=='conker/build/conker.us.elf' else old)
        if (root/name).read_bytes()!=wanted:raise ValueError('Changed installed selector input: '+name)
    if (out/'first-linked.elf').read_bytes()!=expected:raise ValueError('Changed retained selector first link')
    a,_,aa=load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys() or [n for n in a if a[n]!=b[n]]!=[source.FUNCTION]:raise ValueError('Selector changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Selector changed protected Game data')
    row=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,exact_first_link_reproduced=True,target_words=136,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(row,indent=2)+'\n');return row


def build(root,out):
    values=source.freeze(root,out);log=out/'production-build.log'
    if (root/source.SOURCE).read_bytes()!=source.recovered_owner(values[source.SOURCE].decode()).encode():raise ValueError('Unknown selector production source')
    if (root/'conker/retail_word_patches.us.csv').read_bytes()!=guard_bytes(values['conker/retail_word_patches.us.csv'],out/'after-primary.o'):raise ValueError('Unknown selector production guards')
    with log.open('w') as stream:result=subprocess.run(['make','-C','conker','-j4','build/conker.us.elf','progress.csv'],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError('Selector production Make failed; inspect '+str(log))
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
