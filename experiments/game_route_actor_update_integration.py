"""Private mixed-profile padding and actual Make proof; never installs production."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_route_actor_update_layout as layout
from tools.tests.game_owner_pool import normalized_pools
from tools.pad_generated_object import SYMBOL

source = layout.source
prior = source.source.prior
BUILD = 'conker/build/game-route-actor-update-integration'
OWNER,FUNCTION,ENTRY,ROM = (getattr(source.source,name) for name in ('OWNER','FUNCTION','ENTRY','ROM'))
INPUTS = source.source.INPUTS
checkpoint = source.source.checkpoint
AFTER = {
    'conker/src/game/generated_B3020.c':'463ee96235952f9630273afd743c8995957b06aa3be052de02d15e700663ae78',
    'conker/retail_word_patches.us.csv':'25431b19d3fa915104c9d3882933bfa65db7a1420aaf11a4ad4293a831f9d6e3',
    'conker/build/conker.us.elf':'44ecb171bef3c1e2c5f3afb2345953cf70d15224a51db37a1d4fc62c60105e0c',
}
SUCCESSOR_FILES = {'conker/src/game/generated_B3020.c':'after-owner',
    'conker/retail_word_patches.us.csv':'after-guards','conker/build/conker.us.elf':'after-elf'}
raw_read,raw_text = Path.read_bytes,Path.read_text
SERIALIZATION = (
    (('D_8009D9F8','D_800ABCF8'),(1,0),
     ((0x8009D9F8,0,16,0,65521),(0x800ABCF8,0,16,0,6))),
    (('D_8009D9F0','D_8009D5C0'),(1,0),
     ((0x8009D9F0,0,16,0,65521),(0x8009D5C0,0,16,0,6))),
    (('func_151C2E4C','D_800888CC'),(1,0),
     ((0x151C2E4C,72,18,0,5),(0x800888CC,0,16,0,65521))),
    (('D_8009D9E8','func_1507A7C0'),(1,0),
     ((0x8009D9E8,0,16,0,65521),(0x1507A7C0,28,18,0,5))),
    (('D_8009D9E0','D_8008FE57','D_800A6080','D_8009D5B0'),(1,2,3,0),
     ((0x8009D9E0,0,16,0,65521),(0x8008FE57,0,16,0,65521),
      (0x800A6080,0,16,0,6),(0x8009D5B0,0,16,0,6))),
)


def freeze(root,out):
    return source.source.freeze(root,out)


def recovered_owner(before):
    return source.source.recovered_owner(before,source.selected())


def qualify(root,out):
    values = freeze(root,out)
    primary,_,row = source.qualify(root,out)
    before = values['conker/src/game/generated_B3020.c'].decode()
    normal,nd = prior.compile_profile(root,out,recovered_owner(before),'override-normal',True)
    old_normal,od = prior.compile_profile(root,out,before,'baseline-normal',True)
    if nd or od:
        raise ValueError('Unexpected full-update normal-profile diagnostics')
    prior.candidate.checked(normal)
    same = prior.candidate.source.neighbor.same_functions
    if same(old_normal,normal,(FUNCTION,)) != 72 or normalized_pools(old_normal)!=normalized_pools(normal):
        raise ValueError('Changed full-update normal-profile neighbor or pool')
    raw,bindings = source.checked(primary)
    (out/'primary-no-unroll.o').write_bytes(primary.read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(layout.private_guards(values['conker/retail_word_patches.us.csv'],raw,bindings))
    unchanged = out/'unchanged-guards.csv'
    unchanged.write_bytes(values['conker/retail_word_patches.us.csv'])
    (out/'proposed-owner.c').write_text(recovered_owner(before))
    old = prior.padded(root,out,out/'owner-before.o','baseline-padded',unchanged,old_normal)
    padded = prior.padded(root,out,primary,'qualified-padded',guards,normal)
    a,fa = prior.link_owner(root,out,old,OWNER)
    b,fb = prior.link_owner(root,out,padded,OWNER)
    at = fb[FUNCTION]['value']
    if b[at:at+2416] != values['conker/conker.us.bin'][ROM:ROM+2416] or (
            a[:at],a[at+2416:]) != (b[:at],b[at+2416:]):
        raise ValueError('Private full-update padding changed target or unrelated bytes')
    if set(fa)!=set(fb) or any(fa[name]['value']!=fb[name]['value'] or name!=FUNCTION and fa[name]!=fb[name] for name in fa):
        raise ValueError('Changed unrelated padded update-owner definition')
    if normalized_pools(old)!=normalized_pools(padded):
        raise ValueError('Changed padded full-update pools')
    live = hashlib.sha256(raw_read(root/'conker/build/conker.us.elf')).hexdigest()
    stage = old if live==INPUTS['conker/build/conker.us.elf'] else padded if live==AFTER['conker/build/conker.us.elf'] else None
    if stage is None or same(stage,root/'conker/build/src/game/generated_B3020.c.o',()) != 73:
        raise ValueError('Private baseline differs from production owner')
    result = dict(raw_words=594,normalized_words=604,frame=456,guards=594,inserted_words=10,
        all604_words_equal=True,primary_and_normal_neighbors=72,pools_preserved=True,
        all_other_padded_bytes_and_addresses_fixed=True,baseline_matches_production_owner=True,
        original_four_GLOBAL_ASM_bodies_preserved=True,installed=False,
        raw_SHA256=source.RAW_SHA,normalized_SHA256=layout.NORMALIZED_SHA)
    (out/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def bank_successor(root,out):
    artifacts = {'conker/src/game/generated_B3020.c':'proposed-owner.c',
        'conker/retail_word_patches.us.csv':'qualified-guards.csv','conker/build/conker.us.elf':'first-linked.elf'}
    for name,leaf in artifacts.items():
        data = raw_read(out/leaf)
        if hashlib.sha256(data).hexdigest()!=AFTER[name]:
            raise ValueError('Changed qualified full-update successor: '+name)
        target = out/SUCCESSOR_FILES[name]
        if target.exists() and raw_read(target)!=data:
            raise ValueError('Changed immutable full-update successor artifact')
        if not target.exists():target.write_bytes(data)


def expected_inputs(root,out):
    values = {name:raw_read(out/leaf) for name,leaf in SUCCESSOR_FILES.items()}
    if {name:hashlib.sha256(data).hexdigest() for name,data in values.items()}!=AFTER:
        raise ValueError('Changed immutable full-update successor hashes')
    return values


@contextmanager
def checkpoint_context():
    with patch.multiple(checkpoint,INPUTS=INPUTS,AFTER=AFTER,expected_inputs=expected_inputs):
        yield


@contextmanager
def historical_view(root,out):
    with checkpoint_context(),checkpoint.historical_view(root,out):
        yield


def verify(root,out,installed=False):
    with checkpoint_context():
        return checkpoint.verify(root,out,installed)


def install_guards(root,out):
    expected = expected_inputs(root,out)
    for name in ('conker/build/conker.us.elf','conker/retail_word_patches.us.csv'):
        before = raw_read(out/('before-%02d'%list(INPUTS).index(name)))
        if raw_read(root/name)!=before:
            raise ValueError('Unexpected full-update installation stage: '+name)
    if raw_read(root/'conker/src/game/generated_B3020.c')!=expected['conker/src/game/generated_B3020.c']:
        raise ValueError('Install exact qualified full-update C before its guards')
    before = raw_read(root/'conker/retail_word_patches.us.csv')
    if not expected['conker/retail_word_patches.us.csv'].startswith(before):
        raise ValueError('Changed original full-update guard prefix')
    (root/'conker/retail_word_patches.us.csv').write_bytes(expected['conker/retail_word_patches.us.csv'])


def audit(root,out):
    verify(root,out,True)
    for i,(name,digest) in enumerate(INPUTS.items()):
        if hashlib.sha256(raw_read(out/('before-%02d'%i))).hexdigest()!=digest or (
                hashlib.sha256(raw_read(root/name)).hexdigest()!=AFTER.get(name,digest)):
            raise ValueError('Changed installed full-update input: '+name)
    predecessor = out/('before-%02d'%list(INPUTS).index('conker/build/conker.us.elf'))
    before,actual = raw_read(predecessor),raw_read(root/'conker/build/conker.us.elf')
    rom = raw_read(root/'conker/conker.us.bin')
    if actual!=raw_read(out/'after-elf') or actual!=predicted_image(before,rom[ROM:ROM+2416]):
        raise ValueError('Installed full-update image differs from the qualified first link')
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    old,_,oa = load_elf_functions(str(predecessor),'mips-linux-gnu-objdump')
    new,_,na = load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if oa!=na or old.keys()!=new.keys() or [name for name in old if old[name]!=new[name]]!=[FUNCTION]:
        raise ValueError('Full update changed another linked body or address')
    if prior.candidate.source.neighbor.same_functions(out/'qualified-padded.o',root/'conker/build/src/game/generated_B3020.c.o',())!=73:
        raise ValueError('Installed full-update owner differs from qualified padding')
    data = audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):
        raise ValueError('Full update changed protected Game data')
    result = dict(functions=len(old),all_addresses_fixed=True,other_bodies_fixed=len(old)-1,
        target_words=604,metadata_order_groups=5,changed_ELF_bytes=2067,
        first_link_reproduced=True,installed=True,game_data=data)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def make_shadow(root,out):
    raw,bindings = source.checked(out/'qualified-cursor.o')
    def recovered_guards(before,projection_raw,projection_bindings):
        if (projection_raw,projection_bindings)!=prior.candidate.checked(out/'override-normal.o'):
            raise ValueError('Changed actual Make projection override')
        return layout.private_guards(before,raw,bindings)
    with patch.multiple(prior,freeze=freeze,recovered_owner=recovered_owner,
            recovered_makefile=lambda value:value,recovered_guards=recovered_guards):
        return prior.make_shadow(root,out)


def serialize_symbols(expected):
    rows = prior.symbol_rows(expected)
    for names,order,fields in SERIALIZATION:
        selected = [row for row in rows if row[1] in names]
        if tuple(row[1] for row in selected)!=names or sorted(order)!=list(range(len(names))):
            raise ValueError('Unknown bounded full-update symbol order')
        for i,row in enumerate(selected):
            if row[2][1:]!=fields[i] or row[0]!=selected[0][0]+i*SYMBOL.size:
                raise ValueError('Changed bounded symbol meaning or adjacency')
            wanted = selected[0][3]+sum(len(name)+1 for name in names[:i])
            if row[3]!=wanted or expected[row[3]:row[3]+len(names[i])+1]!=names[i].encode()+b'\0':
                raise ValueError('Changed bounded string serialization')
        start,string_name = selected[0][3],selected[0][2][0]
        payload = b''.join(names[i].encode()+b'\0' for i in order)
        expected[start:start+len(payload)] = payload
        offset = 0
        for row,i in zip(selected,order):
            SYMBOL.pack_into(expected,row[0],string_name+offset,*fields[i])
            offset += len(names[i])+1


def predicted_image(before,span):
    if hashlib.sha256(before).hexdigest()!=source.source.INPUTS['conker/build/conker.us.elf'] or len(span)!=2416:
        raise ValueError('Unknown full-update predecessor or target extent')
    expected = bytearray(before)
    at = prior.elf_slot_offset(before,ENTRY,2416)
    expected[at:at+2416] = span
    rows = [row for row in prior.symbol_rows(before) if row[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):
        raise ValueError('Wrong full-update predecessor symbol extent')
    struct.pack_into('>I',expected,rows[0][0]+8,2416)
    serialize_symbols(expected)
    return bytes(expected)


def predict(root,out):
    values = freeze(root,out)
    expected = predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+2416])
    elf = out/'first-linked.elf'
    reused = elf.exists()
    if not reused:
        script = (root/'conker/build/conker.ld').read_text()
        old = 'build/src/game/'+OWNER+'.c.o'
        if script.count(old)!=1:
            raise ValueError('Unknown full-update linker owner input')
        path = out/'first-predicted.ld'
        path.write_text(script.replace(old,(out/'qualified-padded.o').relative_to(root/'conker').as_posix()))
        subprocess.run(['mips-linux-gnu-ld','-T',str(path.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',check=True,capture_output=True)
    image = elf.read_bytes()
    result = dict(first_link_reused=reused,predicted_SHA256=hashlib.sha256(expected).hexdigest(),
        linked_SHA256=hashlib.sha256(image).hexdigest(),expected_bytes=len(expected),linked_bytes=len(image),
        exact_whole_image_prediction=image==expected,installed=False)
    if image!=expected:
        result['different_common_bytes'] = sum(a!=b for a,b in zip(image,expected))
        (out/'prediction-mismatch.json').write_text(json.dumps(result,indent=2)+'\n')
        raise ValueError('First full-update link changed unrelated bytes or metadata; retained first-linked.elf')
    result.update(changed_ELF_bytes=sum(a!=b for a,b in zip(values['conker/build/conker.us.elf'],image)),
        only_target_code_and_symbol_extent_and_bounded_symbol_order_changed=True,
        metadata_order_groups=len(SERIALIZATION),original_first_link_preserved=True)
    artifact = out/'first-prediction.json'
    if artifact.exists():
        old = json.loads(artifact.read_text())
        if any(old[key]!=result[key] for key in result if key!='first_link_reused'):
            raise ValueError('Changed immutable full-update prediction receipt')
    else:
        artifact.write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--make-shadow',action='store_true')
    parser.add_argument('--predict',action='store_true')
    parser.add_argument('--audit',action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    out = root/BUILD
    if args.audit:
        print(json.dumps(audit(root,out),indent=2))
        raise SystemExit(0)
    print(json.dumps(qualify(root,out),indent=2),flush=True)
    if args.make_shadow or args.predict:
        print(json.dumps(make_shadow(root,out),indent=2))
    if args.predict:
        print(json.dumps(predict(root,out),indent=2))
        bank_successor(root,out)
