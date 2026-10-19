"""Qualify both mode-code paths, retained tables and a literal image prediction."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_mode_code_candidates as source
from tools.experiments import game_route_limit_switch_integration as previous
from tools.experiments import game_route_projection_integration as mixed
from tools.experiments.game_remaining_donor_candidates import link_owner
from tools.tests.game_owner_pool import normalized_pools
from tools.tests.test_game_record_constructor_match import elf_slot_offset
from tools.tests.test_game_one_shot_timer_match import symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

BUILD=source.BUILD
ISOLATED_SHA='cf055a9004c6ed7bf1c00be92145c8630235266ad970e093bcec29a930794d37'
OWNER_SHA='4cad5feeb7d92dbee82d9194ab7bad8689b0830184c9d9c8ffd138d2487f74ce'
BINDINGS={0:[('R_MIPS_HI16','D_800D23B0')],4:[('R_MIPS_LO16','D_800D23B0')],
          36:[('R_MIPS_HI16','.rodata')],44:[('R_MIPS_LO16','.rodata')]}
SERIALIZATION=((('func_151D77C8','D_80088874'),(1,0),
    ((0x151D77C8,104,18,0,5),(0x80088874,0,16,0,65521))),)


def checked(obj,whole=False):
    raw,bindings=source.payload(obj)
    if hashlib.sha256(raw).hexdigest()!=(OWNER_SHA if whole else ISOLATED_SHA) or bindings!=BINDINGS:
        raise ValueError('Changed mode-code instructions or relocation ownership')
    return raw,bindings


def guard_bytes(before,obj):
    raw,_=checked(obj,True);reader=csv.DictReader(io.StringIO(before.decode()))
    if any(r['filename']==source.OWNER and r['function']==source.FUNCTION for r in reader):
        raise ValueError('Existing mode-code table binding')
    if not before.endswith(b'\n'):raise ValueError('Unterminated guard prefix')
    tail=io.StringIO();writer=csv.DictWriter(tail,fieldnames=reader.fieldnames,lineterminator='\n')
    for at,kind,word in ((36,'R_MIPS_HI16',0x3C010000),(44,'R_MIPS_LO16',0x8C380000)):
        writer.writerow(dict(filename=source.OWNER,function=source.FUNCTION,offset='0x%X'%at,
            expected='0x%08X'%struct.unpack_from('>I',raw,at)[0],replacement='0x%08X'%word,
            expected_relocations=kind+':.rodata',replacement_relocations=kind+':jtbl_8009DB90_game',
            note='Bind semantic mode-dependent type code to its verified retained retail table',
            insert_after='',insert_after_relocations='',omit='false'))
    return before+tail.getvalue().encode()


def qualify(root,out):
    values=source.freeze(root,out);same=mixed.candidate.source.neighbor.same_functions;objects={}
    rom=values['conker/conker.us.bin']
    first=tuple((8+i*4,previous.source.FUNCTION,v-previous.source.ENTRY) for i,v in
        enumerate(struct.unpack_from('>63I',rom,previous.source.TABLE_ROM)))
    second=tuple((260+i*4,source.FUNCTION,v-source.ENTRY) for i,v in
        enumerate(struct.unpack_from('>57I',rom,source.TABLE_ROM)))
    for label,normal in (('primary',False),('normal',True)):
        old,diag=source.compile_profile(root,out,values[source.SOURCE].decode(),'before-'+label,normal)
        new,row=source.compile_candidate(root,out,'after-'+label,whole=True,normal=normal);checked(new,True)
        if diag or row['diagnostics'] or same(old,new,(source.FUNCTION,))!=72:
            raise ValueError('Changed mode-code profile or neighbor')
        a,b=normalized_pools(old),normalized_pools(new);constant=bytes.fromhex('3f91de69ad42c3ca')
        if a['.rodata']!=(constant+bytes(264),first) or b['.rodata']!=(constant+bytes(488),first+second) or a['.data']!=b['.data']:
            raise ValueError('Changed first switch, constants or second table targets/layout')
        objects[label]=new
    isolated,row=source.compile_candidate(root,out,'isolated');checked(isolated)
    if row['word_differences'] or not row['table_equal'] or row['diagnostics']:
        raise ValueError('Isolated mode code/table does not match directly')
    guards=guard_bytes(values['conker/retail_word_patches.us.csv'],objects['primary'])
    (out/'qualified-guards.csv').write_bytes(guards)
    obj=mixed.padded(root,out,objects['primary'],'qualified-padded',out/'qualified-guards.csv',objects['normal'])
    baseline=root/'conker/build/src/game/generated_B3020.c.o';a,fa=link_owner(root,out,baseline,source.OWNER);b,fb=link_owner(root,out,obj,source.OWNER)
    at=fb[source.FUNCTION]['value']
    if fb[source.FUNCTION]['size']!=284 or b[at:at+284]!=rom[source.ROM:source.ROM+284]:
        raise ValueError('Actual padded mode-code body does not match retail')
    if fa.keys()!=fb.keys() or any(fa[n]['value']!=fb[n]['value'] or n!=source.FUNCTION and fa[n]!=fb[n] for n in fa):
        raise ValueError('Changed another padded address/extent')
    if a[:at]!=b[:at] or a[at+284:]!=b[at+284:] or same(baseline,obj,(source.FUNCTION,))!=72:
        raise ValueError('Changed another padded instruction')
    if normalized_pools(baseline)!=normalized_pools(obj):raise ValueError('Changed retained production pools')
    (out/'proposed-owner.c').write_text(source.recovered_owner(values[source.SOURCE].decode()))
    result=dict(words=71,frame=0,word_differences=0,table_entries=57,prior63_table_targets_preserved=True,
        neighbors_in_each_profile=72,other_padded_functions_fixed=72,new_relocation_bindings=2,scheduling_guards=0)
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n');return result


def predicted_image(before,truth):
    if hashlib.sha256(before).hexdigest()!=source.INPUTS['conker/build/conker.us.elf'] or len(truth)!=284:
        raise ValueError('Unknown mode-code predecessor')
    result=bytearray(before);at=elf_slot_offset(before,source.ENTRY,284);result[at:at+284]=truth
    rows=[r for r in symbol_rows(before) if r[1]==source.FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(source.ENTRY,12):raise ValueError('Unknown mode-code stub extent')
    struct.pack_into('>I',result,rows[0][0]+8,284)
    with patch.object(previous.symbol_layout,'SERIALIZATION',SERIALIZATION):previous.symbol_layout.serialize_symbols(result)
    return bytes(result)


def check_image(before,actual,truth):
    expected=predicted_image(before,truth)
    if actual!=expected:raise ValueError('Mode-code image differs from exact target-only prediction')
    return expected


def predict(root,out):
    values=source.freeze(root,out);elf=out/'first-linked.elf'
    if not elf.exists():
        script=(root/'conker/build/conker.ld').read_text();old='build/src/game/'+source.OWNER+'.c.o'
        if script.count(old)!=1:raise ValueError('Unknown mode-code linker input')
        link=out/'first-link.ld';link.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld','-T',str(link.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    before=values['conker/build/conker.us.elf'];actual=elf.read_bytes();truth=values['conker/conker.us.bin'][source.ROM:source.ROM+284]
    expected=predicted_image(before,truth);result=dict(expected_SHA256=hashlib.sha256(expected).hexdigest(),
        actual_SHA256=hashlib.sha256(actual).hexdigest(),exact_prediction=actual==expected,image_bytes=len(actual),
        changed_bytes=sum(a!=b for a,b in zip(before,actual)))
    receipt=out/'first-link.json';initial=out/'initial-first-link-diagnosis.json'
    if receipt.exists() and not json.loads(receipt.read_text())['exact_prediction'] and not initial.exists():initial.write_bytes(receipt.read_bytes())
    receipt.write_text(json.dumps(result,indent=2)+'\n');check_image(before,actual,truth);return result


def make_shadow(root,out):
    with patch.multiple(previous,source=source,guard_bytes=guard_bytes):return previous.make_shadow(root,out)


def audit(root,out):
    values=source.freeze(root,out);expected=predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][source.ROM:source.ROM+284])
    for name,old in values.items():
        want=source.recovered_owner(old.decode()).encode() if name==source.SOURCE else (
            guard_bytes(old,out/'after-primary.o') if name=='conker/retail_word_patches.us.csv' else
            expected if name=='conker/build/conker.us.elf' else old)
        if (root/name).read_bytes()!=want:raise ValueError('Changed installed mode-code input: '+name)
    if (out/'first-linked.elf').read_bytes()!=expected:raise ValueError('Changed retained first mode-code link')
    a,_,aa=load_elf_functions(str(out/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump')
    b,_,ba=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if aa!=ba or a.keys()!=b.keys() or [n for n in a if a[n]!=b[n]]!=[source.FUNCTION]:raise ValueError('Mode code changed another body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Mode code changed Game data')
    result=dict(functions=len(b),other_bodies_fixed=len(b)-1,all_addresses_fixed=True,
        exact_first_link_reproduced=True,target_words=71,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n');return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--predict',action='store_true')
    parser.add_argument('--audit',action='store_true');parser.add_argument('--make-shadow',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[2];out=root/BUILD
    if args.audit:print(json.dumps(audit(root,out),indent=2))
    else:
        print(json.dumps(qualify(root,out),indent=2),flush=True)
        if args.make_shadow:print(json.dumps(make_shadow(root,out),indent=2),flush=True)
        if args.predict:print(json.dumps(predict(root,out),indent=2))
