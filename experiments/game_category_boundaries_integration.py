"""Qualify category-boundary lifetime guards, actual padding and exact first image."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_category_boundaries_lifetime_fit as source
from tools.experiments import game_category_boundaries_layout as layout
from tools.experiments import game_route_limit_switch_integration as previous
from tools.experiments import game_route_projection_integration as mixed
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.pad_generated_object import SYMBOL

BUILD=source.BUILD+'/integration'
SYMBOL_RUNS=(
    (('D_8009D9C0','D_8009D1E0','D_800A6060'),('D_8009D1E0','D_800A6060','D_8009D9C0')),
    (('D_8009D9C4','D_8008A450'),('D_8008A450','D_8009D9C4')),
    (('func_15044964','D_800A0500'),('D_800A0500','func_15044964')))


def predict_symbol_runs(result):
    rows=symbol_rows(result)
    for before,after in SYMBOL_RUNS:
        selected=[r for r in rows if r[1] in before]
        if tuple(r[1] for r in selected)!=before or sorted(before)!=sorted(after):raise ValueError('Unknown category-boundary symbol run')
        at=selected[0][0];string_at=selected[0][3];entries={r[1]:r for r in selected}
        strings_base=string_at-selected[0][2][0]
        if any(r[0]!=at+i*SYMBOL.size for i,r in enumerate(selected)):raise ValueError('Noncontiguous category-boundary symbol rows')
        literal=b''.join(n.encode()+b'\0' for n in before)
        if result[string_at:string_at+len(literal)]!=literal or any(r[3]-r[2][0]!=strings_base for r in selected):
            raise ValueError('Unknown category-boundary symbol strings')
        for i,name in enumerate(after):
            fields=list(entries[name][2]);fields[0]=string_at-strings_base
            SYMBOL.pack_into(result,at+i*SYMBOL.size,*fields)
            literal=name.encode()+b'\0';result[string_at:string_at+len(literal)]=literal;string_at+=len(literal)


def guard_bytes(before,obj):
    raw,bindings=source.payload(obj);return layout.private_guards(before,raw,bindings)


def qualify(root,out):
    values=source.freeze(root,out);same=mixed.candidate.source.neighbor.same_functions;objects={}
    for label,normal in (('primary',False),('normal',True)):
        old,diag=source.compile_profile(root,out,values[source.SOURCE].decode(),'before-'+label,normal)
        new,_,row=source.compile_candidate(root,out,'after-'+label,whole=True,normal=normal)
        raw,bindings=source.payload(new);layout.normalize(raw,bindings)
        if diag or row['diagnostics'] or same(old,new,(source.FUNCTION,))!=72 or normalized_pools(old)!=normalized_pools(new):
            raise ValueError('Changed category-boundary profile, neighbor or pool')
        objects[label]=new
    guards=guard_bytes(values['conker/retail_word_patches.us.csv'],objects['primary']);(out/'qualified-guards.csv').write_bytes(guards)
    obj=mixed.padded(root,out,objects['primary'],'qualified-padded',out/'qualified-guards.csv',objects['normal'])
    baseline=root/'conker/build/src/game/generated_B3020.c.o'
    a,fa=source.link_owner(root,out,baseline,source.OWNER);b,fb=source.link_owner(root,out,obj,source.OWNER)
    at=fb[source.FUNCTION]['value'];truth=values['conker/conker.us.bin'][source.ROM:source.ROM+448]
    if fb[source.FUNCTION]['size']!=448 or b[at:at+448]!=truth:raise ValueError('Actual padded category boundaries do not match retail')
    if fa.keys()!=fb.keys() or any(fa[n]['value']!=fb[n]['value'] or n!=source.FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Changed another category-boundary owner address/extent')
    if a[:at]!=b[:at] or a[at+448:]!=b[at+448:] or same(baseline,obj,(source.FUNCTION,))!=72:
        raise ValueError('Changed another padded category-boundary owner instruction')
    if normalized_pools(baseline)!=normalized_pools(obj):raise ValueError('Changed retained category-boundary owner pools')
    (out/'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
    result=dict(words=112,frame=96,word_differences=0,neighbors_in_each_profile=72,other_padded_functions_fixed=72,
        guarded_layout_words=35,source_words_retained=112,inserted_words=0,omitted_words=0,moved_binding_positions=0)
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');return result


def predicted_image(before,truth):
    if hashlib.sha256(before).hexdigest()!=source.INPUTS['conker/build/conker.us.elf'] or len(truth)!=448:
        raise ValueError('Unknown category-boundary predecessor')
    result=bytearray(before);at=elf_slot_offset(before,source.ENTRY,448);result[at:at+448]=truth
    rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown category-boundary stub extent')
    struct.pack_into('>I',result,rows[0][0]+8,448);predict_symbol_runs(result);return bytes(result)


def check_image(before,actual,truth):
    expected=predicted_image(before,truth)
    if actual!=expected:raise ValueError('Category-boundary image differs from exact prediction')
    return expected


def predict(root,out):
    values=source.freeze(root,out);elf=out/'first-linked.elf'
    if not elf.exists():
        script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+source.OWNER+'.c.o'
        if script.count(old)!=1:raise ValueError('Unknown category-boundary linker input')
        link=out/'first-link.ld';link.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld','-T',str(link.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt',
            '--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+448]
    expected=predicted_image(before,truth);result=dict(expected_SHA256=hashlib.sha256(expected).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(),exact_prediction=actual==expected,image_bytes=len(actual),
        changed_bytes=sum(a!=b for a,b in zip(before,actual)))
    receipt=out/'first-link.json';initial=out/'initial-first-link.json'
    if receipt.exists() and not json.loads(receipt.read_text())['exact_prediction'] and not initial.exists():initial.write_bytes(receipt.read_bytes())
    receipt.write_text(json.dumps(result,indent=2)+'\n');check_image(before,actual,truth);return result


def make_shadow(root,out):
    with patch.multiple(previous,source=source,guard_bytes=guard_bytes):return previous.make_shadow(root,out)


def build(root,out):
    values=source.freeze(root,out)
    if (root/source.SOURCE).read_bytes()!=source.recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Unknown category-boundary source before production build')
    if (root/'conker/retail_word_patches.us.csv').read_bytes()!=guard_bytes(values['conker/retail_word_patches.us.csv'],out/'after-primary.o'):
        raise ValueError('Unknown category-boundary guards before production build')
    log=out/'production-build.log'
    with log.open('w') as stream:
        result=subprocess.run(['make','-C','conker','-j4','build/conker.us.elf','progress.csv'],cwd=root,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:raise ValueError('Production Make failed; inspect '+str(log))
    return dict(exit_code=0,log=log.relative_to(root).as_posix(),audit=audit(root,out))


def install_guards(root,out):
    values=source.freeze(root,out);before=values['conker/retail_word_patches.us.csv']
    if (root/source.SOURCE).read_bytes()!=source.recovered_owner(values[source.SOURCE].decode()).encode():
        raise ValueError('Install the exact qualified C owner before generating category-boundary guards')
    if (root/'conker/retail_word_patches.us.csv').read_bytes()!=before:raise ValueError('Changed category-boundary guard predecessor')
    if (root/'conker/build/conker.us.elf').read_bytes()!=values['conker/build/conker.us.elf']:raise ValueError('Changed category-boundary image before guard generation')
    check_image(values['conker/build/conker.us.elf'],(out/'first-linked.elf').read_bytes(),values['conker/conker.us.bin'][source.ROM:source.ROM+448])
    (root/'conker/retail_word_patches.us.csv').write_bytes(guard_bytes(before,out/'after-primary.o'))
    return dict(generated_guard_rows=35,historical_prefix_preserved=True)


def audit(root,out):
    values=source.freeze(root,out);before=values['conker/build/conker.us.elf']
    expected=predicted_image(before,values['conker/conker.us.bin'][source.ROM:source.ROM+448])
    for name,old in values.items():
        want=source.recovered_owner(old.decode()).encode() if name==source.SOURCE else (
            guard_bytes(old,out/'after-primary.o') if name=='conker/retail_word_patches.us.csv' else expected if name=='conker/build/conker.us.elf' else old)
        if (root/name).read_bytes()!=want:raise ValueError('Changed installed category-boundary input: '+name)
    if (out/'first-linked.elf').read_bytes()!=expected:raise ValueError('Changed retained first category-boundary link')
    a,_,aa=load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys() or [n for n in a if a[n]!=b[n]]!=[source.FUNCTION]:raise ValueError('Category boundaries changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Category boundaries changed Game data')
    result=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,exact_first_link_reproduced=True,target_words=112,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for flag in ('predict','audit','make-shadow','install-guards','build'):parser.add_argument('--'+flag,action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.build:print(json.dumps(build(root,out),indent=2))
    elif args.install_guards:print(json.dumps(install_guards(root,out),indent=2))
    elif args.audit:print(json.dumps(audit(root,out),indent=2))
    else:
        print(json.dumps(qualify(root,out),indent=2),flush=True)
        if args.make_shadow:print(json.dumps(make_shadow(root,out),indent=2),flush=True)
        if args.predict:print(json.dumps(predict(root,out),indent=2))
