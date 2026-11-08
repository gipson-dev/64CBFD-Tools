"""Record subtype recovery and fail-closed, complete-owner/image gates."""
import csv
import hashlib
import io
import json
import shlex
import struct
import subprocess
import sys
from collections import Counter
from pathlib import Path

from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools import pad_generated_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT = Path(__file__).resolve().parents[2]
BUILD = 'conker/build/game-record-subtype-150A25D4-match'
SOURCE = 'conker/src/game/generated_CDE80.c'
OBJECT = 'conker/build/src/game/generated_CDE80.c.o'
OWNER, FUNCTION = 'generated_CDE80', 'func_150A25D4'
ENTRY, ROM, WORDS, FRAME = 0x150A25D4, 0xCFA84, 110, 40
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
BEFORE_SHA = 'e89916b8a4729061901753c9c5127be78c45c553ea5243e003d3d859f48c58aa'
GUARD_SHA = '2458418c897988981b244e7d15fba669c3502d56ad2f3f84a40a32d10af856e2'
RAW_SHA = 'b970ba7d39ee5dd68138189376daddd712080f84d170a7e216ef8e8393af9784'
BINDINGS = {44: [('R_MIPS_HI16', '.rodata')], 52: [('R_MIPS_LO16', '.rodata')], 84: [('R_MIPS_26', 'func_150E7290')], 108: [('R_MIPS_HI16', 'D_800D9EB8')], 128: [('R_MIPS_LO16', 'D_800D9EB8')], 184: [('R_MIPS_26', 'func_150E68B0')], 212: [('R_MIPS_HI16', 'D_800D3090')], 216: [('R_MIPS_LO16', 'D_800D3090')], 248: [('R_MIPS_26', 'func_10010344')], 256: [('R_MIPS_HI16', 'D_800D3090')], 260: [('R_MIPS_LO16', 'D_800D3090')], 264: [('R_MIPS_HI16', 'D_800BE9E4')], 268: [('R_MIPS_LO16', 'D_800BE9E4')], 364: [('R_MIPS_26', 'func_151C8674')], 384: [('R_MIPS_26', 'func_1515F270')], 404: [('R_MIPS_26', 'func_151CE51C')]}
STUB = 's32 func_150A25D4() {\n    return 0;\n}'
DECLARATIONS = 'extern u8 D_800D3090;\nextern s32 D_800BE9E4;\nextern u8 D_800D9EB8[][3];\nvoid func_150E7290(u8, u8, s32);\ns32 func_150E68B0(struct127 *, s32, GeneratedCDE80Record *, u8);\ns32 func_10010344(u16, void *, s32, s16, u16);\nvoid func_151C8674(s32, s32);\nvoid func_1515F270(u8 *, u8 *);\nvoid func_151CE51C(struct127 *, u8 *);'
SELECTED = '/* Dispatch record subtypes and advance the actor timed parameter. */\nvoid func_150A25D4(GeneratedCDE80Record *record, struct127 *actor,\n                  s32 selector, u64 flags) {\n    u8 *output;\n    s32 value;\n    s32 tick;\n    switch (record->field17) {\n    case 0:\n        break;\n    case 1:\n        if (selector != 255) func_150E7290(selector, 255, 0);\n        break;\n    case 2:\n        if (selector != 255) {\n            output = D_800D9EB8[selector];\n            output[0] = record->field18;\n            output[1] = record->field1C;\n            output[2] = record->field20;\n        }\n        break;\n    case 3:\n        if (selector != 255) {\n            func_150E68B0(actor, selector, record, (u8)record->field18);\n        }\n        break;\n    case 6:\n        if ((flags & 1) == 0) {\n            D_800D3090 = 30;\n            func_10010344(0x66F, actor, 24000, 400, 500);\n        }\n        tick = (u8)(D_800D3090 + (u32)D_800BE9E4);\n        D_800D3090 = tick;\n        if (tick >= 31) {\n            value = actor->unkB2;\n            if (value >= 1441) actor->unkB2 = 1200;\n            else if (value <= 240) actor->unkB2 = 90;\n            else actor->unkB2 = value - 240;\n            D_800D3090 = 0;\n        }\n        break;\n    case 8:\n        func_151C8674((s32)actor, (s32)record);\n        break;\n    case 9:\n        func_1515F270((u8 *)actor, (u8 *)record);\n        break;\n    case 10:\n        func_151CE51C(actor, (u8 *)record);\n        break;\n    }\n}'
sha = lambda b: hashlib.sha256(b).hexdigest()
def source_states(live):
    if live.count(STUB)==1 and DECLARATIONS not in live:
        return live,live.replace(STUB,DECLARATIONS+'\n\n'+SELECTED,1),False
    if live.count(DECLARATIONS+'\n\n'+SELECTED)!=1:
        raise ValueError('Record subtype source or declarations changed')
    return live.replace(DECLARATIONS+'\n\n'+SELECTED,STUB,1),live,True


def function_blob(obj):
    text, functions, refs = parse_object(obj)
    f = functions[FUNCTION]
    a, n = f['value'], f['size']
    return text[a:a+n], {p-a: r for p, r in refs.items() if a <= p < a+n}


def normalize(raw,refs):
    if len(raw)!=432 or sha(raw)!=RAW_SHA or refs!=BINDINGS:raise ValueError('Unknown dispatcher C words')
    words=list(struct.unpack('>108I',raw));rows=[]
    def reg(w,mapping):
        op=w>>26;shifts=(21,16,11)if op==0 else(16,)if op==15 else(21,16)if op in(4,5,9,10,11,12,20,21,33,35,36,40,41,43)else()
        result=w
        for shift in shifts:
            r=w>>shift&31
            if r in mapping:result=(result&~(31<<shift))|(mapping[r]<<shift)
        return result
    def emit(origin,mapping=None,binding=None,word=None):
        w=words[origin]if word is None else word
        rows.append([reg(w,mapping or{}),refs.get(origin*4,[])if binding is None else binding,origin])
    for i in range(50):emit(i)
    # The provider consumes a u8. Reuse the already-homed selector word;
    # current real caller supplies a zero-extended byte. Upper bits are padding
    # at the provider boundary, and no write intervenes between the two reads.
    assert words[16]==0x8FAF0030 and words[18]==0x93A40033
    rows[18]=[words[20],[],20]
    rows[20]=[(words[16]&0x001F0000)<<5 | (4<<11) | 0x25,[],18]
    # Retain the low-word mask test. Rematerialize the byte address at each
    # direct access rather than allocating that constant address to S0.
    for i,m in((50,{}),(51,{}),(52,{}),(55,{13:2}),(56,{8:13}),(53,{16:1})):
        emit(i,m)
    emit(57,{16:1,13:2},refs[54*4]);emit(58,{8:13})
    for i in range(59,64):emit(i)
    emit(64,{16:2});emit(66,{10:8});emit(68,{16:2,9:2},refs[65*4]);emit(67,{10:8})
    emit(64,{16:1});emit(69,{9:2,10:8});emit(70,{11:9})
    emit(73,{16:1,11:9},refs[65*4]);emit(71,{11:9})
    emit(72,{},{},(words[72]&0x03FFFFFF)|(21<<26));emit(103)
    for i in range(74,88):emit(i,{12:10,14:11,15:12})
    # Clone the already-emitted address constant and RA reload for retail's
    # two return paths. No new state transition or service logic is introduced.
    emit(64,{16:1});emit(89,{16:1},refs[65*4]);emit(88);emit(103)
    for i in range(90,108):emit(i)
    assert len(rows)==110
    origin_to_new={i:i for i in range(50)}
    origin_to_new.update({50:50,51:51,52:52,64:63,**{i:i for i in range(74,89)},**{i:i+2 for i in range(90,108)}})
    for i,row in enumerate(rows):
        w,bindings,origin=row
        if w>>26 in(1,4,5,6,7,20,21,22,23):
            target=origin+1+((words[origin]&65535)^32768)-32768
            new_target=106 if origin in(72,88) else origin_to_new[target]
            row[0]=(w&0xFFFF0000)|((new_target-(i+1))&65535)
        row[1]=[(kind,'jtbl_8009F648'if name=='.rodata'else name)for kind,name in bindings]
    return struct.pack('>110I',*(r[0]for r in rows)),{i*4:r[1]for i,r in enumerate(rows)if r[1]}


def guard_rows(raw, refs):
    normal,nrefs=normalize(raw,refs);before=struct.unpack('>108I',raw);after=struct.unpack('>110I',normal)
    spec=lambda rows:';'.join(kind+':'+name for kind,name in rows)or'-'
    rows=[]
    for i,a in enumerate(before):
        j=i if i<=88 else i+1 if i==89 else i+2
        b=after[j];old_binding,new_binding=refs.get(i*4,[]),nrefs.get(j*4,[])
        extra=after[j+1]if i in(88,89)else None
        if a==b and old_binding==new_binding and extra is None:continue
        rows.append([OWNER,FUNCTION,hex(i*4),f'0x{a:08X}',f'0x{b:08X}',spec(old_binding),spec(new_binding),
            'Normalize dispatcher address allocation and return scheduling; preserve narrow provider argument padding',
            ''if extra is None else f'0x{extra:08X}',''if extra is None else spec(nrefs.get((j+1)*4,[])),'false'])
    if len(rows)!=41:raise ValueError('Record subtype guard count changed: '+str(len(rows)))
    return rows


def guard_manifest(before, raw, refs):
    if sha(before) != GUARD_SHA or not before.endswith(b'\n'):
        raise ValueError('Record-subtype inherited guard history changed')
    stream = io.StringIO(newline='')
    csv.writer(stream,lineterminator='\n').writerows(guard_rows(raw,refs))
    return before+stream.getvalue().encode()


def freeze(root, out):
    folder = out/'frozen'
    receipt = out/'frozen-inputs.json'
    if not receipt.exists():
        if sha((root/ELF).read_bytes()) != BEFORE_SHA:
            raise ValueError('Freeze the record-state predecessor before installation')
        names = [SOURCE, OBJECT, ELF, GUARDS, 'conker/Makefile', 'conker/build/conker.ld',
                 'conker/retail_layout.us.txt', 'conker/conker.us.bin', 'conker/progress.csv',
                 'conker/asm/CDE80.s','conker/asm/data/244060.rodata.s','conker/asm/nonmatchings/init_EB00/func_10010344.s','conker/src/init_EB00.c','conker/src/game/generated_113D60.c','conker/asm/113D60.s','conker/src/game/generated_1F4650.c','conker/src/game/generated_18A8F0.c','conker/src/game/generated_1FA770.c','conker/symbol_addrs.us.txt',
                 'conker/undefined_syms.us.txt', 'conker/undefined_funcs.us.txt',
                 'conker/undefined_syms_auto.txt', 'conker/undefined_funcs_auto.txt']
        names += [p.relative_to(root).as_posix() for p in (root/'conker/include').rglob('*.h')]
        names += ['ido/ido5.3_recomp/'+n for n in ('cc', 'cfe', 'uopt', 'ugen')]
        for name in names:
            p = folder/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((root/name).read_bytes())
        receipt.write_text(json.dumps({n: sha((folder/n).read_bytes()) for n in names}, indent=2)+'\n')
    hashes = json.loads(receipt.read_text())
    allowed = {SOURCE, OBJECT, ELF, GUARDS}
    for name, digest in hashes.items():
        if sha((folder/name).read_bytes()) != digest or (name not in allowed and sha((root/name).read_bytes()) != digest):
            raise ValueError('Record-subtype frozen input changed: '+name)
    return hashes


def padded(root, out, obj, guards, label, strict=False):
    destination = out/(label+'.o')
    sys.modules.setdefault('pad_generated_object', pad_generated_object)
    if strict:
        from tools import pad_c_object
        assembly = pad_c_object.emit_padded_assembly(obj, root/'conker/retail_layout.us.txt', OWNER, word_patches_path=guards)
    else:
        assembly = pad_generated_object.emit_padded_assembly(obj, root/'conker/asm/CDE80.s', word_patches_path=guards, filename=OWNER)
    p = out/(label+'.s')
    p.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as', '-EB', '-mtune=vr4300', '-march=vr4300', '-mabi=32', '-I', 'include', '-o', str(destination), str(p)], cwd=root/'conker', capture_output=True, check=True)
    return destination


def link(root, out, owner, label):
    script = (out/'frozen/conker/build/conker.ld').read_text()
    name = OBJECT.removeprefix('conker/')
    if script.count(name) != 1:
        raise ValueError('Record-subtype linker owner changed')
    p = out/(label+'.ld')
    p.write_text(script.replace(name, owner.relative_to(root/'conker').as_posix()))
    destination = out/(label+'.elf')
    subprocess.run(['mips-linux-gnu-ld', '-T', str(p.relative_to(root/'conker')),
                    *[v for n in ('undefined_syms.us.txt', 'undefined_funcs.us.txt', 'undefined_syms_auto.txt', 'undefined_funcs_auto.txt') for v in ('-T', n)],
                    '--no-check-sections', '--no-warn-mismatch', '-o', str(destination.relative_to(root/'conker'))], cwd=root/'conker', capture_output=True, check=True)
    return destination


def strict_image(before, actual, truth):
    if sha(before)!=BEFORE_SHA or len(truth)!=440:raise ValueError('Record subtype predecessor image/slot changed')
    wanted=bytearray(before);at=elf_slot_offset(before,ENTRY,440);wanted[at:at+440]=truth
    named={name:(p,f,strings)for p,name,f,strings in symbol_rows(before)}
    target=named[FUNCTION]
    if target[1][1:3]!=(ENTRY,12):raise ValueError('Record subtype predecessor symbol changed')
    struct.pack_into('>I',wanted,target[0]+8,440)
    # Newly referenced globals change three GNU-linker symbol/string orders.
    # Rebuild every affected row and name from the frozen predecessor bytes;
    # never borrow metadata from the candidate or omit a range from comparison.
    groups=[(('D_800CC2D0','D_8009D2B0'),('D_8009D2B0','D_800CC2D0')),
            (('.L1509E5F0_game_data','D_8009D8F0'),('D_8009D8F0','.L1509E5F0_game_data')),
            (('D_800D3090','D_8008B440','D_8008B090'),('D_8008B440','D_8008B090','D_800D3090'))]
    for previous,ordered in groups:
        start,fields,text=named[previous[0]];name_offset=fields[0]
        cursor=0
        for i,name in enumerate(previous):
            row,f,address=named[name];data=name.encode()+b'\0'
            if row!=start+16*i or address!=text+cursor or f[0]!=name_offset+cursor or before[address:address+len(data)]!=data:
                raise ValueError('Record subtype predecessor metadata group changed')
            cursor+=len(data)
        names=b''.join(name.encode()+b'\0'for name in ordered)
        if len(names)!=cursor or set(previous)!=set(ordered):raise ValueError('Record subtype metadata is not a closed permutation')
        wanted[text:text+cursor]=names;cursor=0
        for i,name in enumerate(ordered):
            fields=list(named[name][1]);fields[0]=name_offset+cursor
            struct.pack_into('>IIIBBH',wanted,start+16*i,*fields);cursor+=len(name)+1
    if actual!=wanted:
        diff=[i for i,(a,b)in enumerate(zip(wanted,actual))if a!=b]
        raise ValueError('Literal record subtype entire image differs: '+repr((len(wanted),len(actual),len(diff),diff[:32])))
    expected=Counter((name,f[1],440 if name==FUNCTION else f[2],*f[3:])for _,name,f,_ in symbol_rows(before))
    if expected!=Counter((name,*f[1:])for _,name,f,_ in symbol_rows(actual)):
        raise ValueError('Record subtype named definitions changed')
    return sum(a!=b for a,b in zip(before,actual))



def make_shadow(root, out, proposal, guards, wanted, compact):
    shadow = out/'make-shadow'
    source_path = SOURCE
    conker = root/'conker'
    target = shadow/'src/game/generated_CDE80.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make', '-n', '-B', 'BUILD_DIR='+shadow.relative_to(conker).as_posix(), target.relative_to(conker).as_posix()], cwd=conker, capture_output=True, text=True, check=True)
    (out/'actual-Make-plan.txt').write_text(plan.stdout+plan.stderr)
    commands = []
    for line in plan.stdout.replace('\\\n', '').splitlines():
        args = shlex.split(line)
        if not args or args[0] == 'rm':
            continue
        if args[0] not in ('../ido/ido5.3_recomp/cc', 'python3', 'mips-linux-gnu-as'):
            raise ValueError('Unexpected record-state Make command: '+repr(args))
        args = [proposal.relative_to(conker).as_posix() if a == source_path.removeprefix('conker/') else guards.relative_to(conker).as_posix() if a == 'retail_word_patches.us.csv' else a for a in args]
        redirect = None
        if '>' in args:
            if args.count('>') != 1 or args[-2] != '>':
                raise ValueError('Unknown record-state Make redirect')
            redirect = (conker/args[-1]).resolve()
            redirect.relative_to(shadow.resolve())
            args = args[:-2]
        result = subprocess.run(args, cwd=conker, capture_output=True, text=True)
        allowed_diagnostics = Counter()
        if result.returncode or diagnostic_rows(result.stderr) != allowed_diagnostics or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None:
            redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands) != 5 or len([a for a in commands if a[0] == '../ido/ido5.3_recomp/cc' and '-O2' in a and '-g3' in a]) != 1:
        raise ValueError('Record-subtype actual Make profile changed')
    if target.read_bytes() != wanted.read_bytes():
        raise ValueError('Record-subtype actual Make padded owner differs')
    count = same_functions(compact, Path(str(target)+'.compact'))
    (out/'actual-Make-commands.json').write_text(json.dumps(commands, indent=2)+'\n')
    return dict(commands=len(commands), functions=count, padded_object_equal=True, inherited_Make_warnings=plan.stderr)


def owner_pools(before, after):
    from tools.tests.game_owner_pool import normalized_pools
    a,b=alloc_pools(before),alloc_pools(after)
    if set(b)-set(a)!={'.rodata'} or any(a[n]!=b[n]for n in a):
        raise ValueError('Record subtype pools outside its new table changed')
    raw_offsets=(412,64,100,160,412,412,200,412,360,380,400)
    wanted={'.rodata':(bytes(48),tuple((i*4,FUNCTION,off)for i,off in enumerate(raw_offsets))),'.data':None}
    if normalized_pools(after)!=wanted:raise ValueError('Record subtype raw table ownership changed')
    return raw_offsets





def prepare(root=ROOT):
    root = Path(root).resolve()
    out = root/BUILD
    out.mkdir(parents=True, exist_ok=True)
    frozen = freeze(root, out)
    before, after, installed = source_states((root/SOURCE).read_text())
    if before != (out/'frozen'/SOURCE).read_text():
        raise ValueError('Record-subtype predecessor source changed')
    old, old_diag = compile_owner(root, out, before, 'predecessor-owner')
    new, new_diag = compile_owner(root, out, after, 'qualified-owner')
    if diagnostic_rows(old_diag) != diagnostic_rows(new_diag) or new_diag:
        raise ValueError('Record-subtype owner diagnostics changed')
    neighbors = same_functions(old, new, (FUNCTION,))
    owner_pools(old,new)
    raw, refs = function_blob(new)
    normal, normal_refs = normalize(raw, refs)
    rom = (root/'conker/conker.us.bin').read_bytes()
    truth = rom[ROM:ROM+440]
    if struct.pack('>110I', *bound_blob(normal, normal_refs, {name: (0x8009F648 if name == 'jtbl_8009F648' else int(name.split('_')[1], 16)) for rows in normal_refs.values() for _, name in rows})) != truth:
        raise ValueError('Record-subtype normalized body differs')
    old_guards = out/'predecessor-guards.csv'
    old_guards.write_bytes((out/'frozen'/GUARDS).read_bytes())
    guards = out/'qualified-guards.csv'
    guards.write_bytes(guard_manifest(old_guards.read_bytes(), raw, refs))
    if (root/GUARDS).read_bytes() != (guards if installed else old_guards).read_bytes():
        raise ValueError('Record-subtype live guard scope changed')
    old_padded = padded(root, out, old, old_guards, 'predecessor-padded')
    new_padded = padded(root, out, new, guards, 'qualified-padded')
    strict = padded(root, out, new, guards, 'strict-qualified-padded', strict=True)
    if same_functions(new_padded, strict) != 28 or alloc_pools(new_padded) != alloc_pools(strict):
        raise ValueError('Record-subtype production/strict padded code or pools differ')
    generated_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(new_padded.read_bytes())}
    strict_names = {n: tuple(f[1:]) for _, n, f, _ in symbol_rows(strict.read_bytes())}
    start, _, _, jump_labels = pad_generated_object.parse_retail_slice(root/'conker/asm/CDE80.s')
    labels = {name: (address-start, 0, 16, 0, 1) for address, names in jump_labels.items() for name in names}
    if set(generated_names)-set(strict_names) != set(labels) or generated_names != {**strict_names, **labels}:
        raise ValueError('Record-subtype preserved case-label accounting differs')
    padded_neighbors = same_functions(old_padded, new_padded, (FUNCTION,))
    if alloc_pools(old_padded) != alloc_pools(new_padded) or function_blob(new_padded) != (normal, normal_refs):
        raise ValueError('Record-subtype padded body or owner pools changed')
    if (root/OBJECT).read_bytes() != (new_padded if installed else old_padded).read_bytes():
        raise ValueError('Record-subtype live owner differs')
    proposal = out/'proposed-owner.c'
    proposal.write_text(after)
    make = make_shadow(root, out, proposal, guards, new_padded, new)
    old_image, new_image = link(root, out, old_padded, 'predecessor-image'), link(root, out, new_padded, 'qualified-image')
    if (root/ELF).read_bytes() != (new_image if installed else old_image).read_bytes():
        raise ValueError('Record-subtype live ELF differs')
    changed = strict_image(old_image.read_bytes(), new_image.read_bytes(), truth)
    a, _, aa = load_elf_functions(str(old_image), 'mips-linux-gnu-objdump')
    b, _, bb = load_elf_functions(str(new_image), 'mips-linux-gnu-objdump')
    if a.keys() != b.keys() or aa != bb or [n for n in a if a[n] != b[n]] != [FUNCTION]:
        raise ValueError('Record-subtype linked body/address census changed')
    data = audit_layout(new_image, root/'conker')
    if (data['exact'], data['bytes'], data['owner_count'], data['different_bytes']) != (True, 189088, 720, 0):
        raise ValueError('Record-subtype protected data changed')
    report = dict(source_installed=installed, frozen_inputs=len(frozen), words=110, raw_words=108, frame=40, guards=41, symbol_string_permutations=3, metadata_permutation_bytes=69, raw_CPR1_added_bits="0x00000000", preserved_labels=len(labels),
                  raw_neighbors=neighbors, padded_neighbors=padded_neighbors, diagnostics=0,
                  actual_Make=make, strict_changed_bytes=changed, exclusions=0, functions=len(a),
                  all_addresses_fixed=True, changed_bodies=[FUNCTION], protected_data=data,
                  owner_sha256=sha(new_padded.read_bytes()), ELF_sha256=sha(new_image.read_bytes()), guard_sha256=sha(guards.read_bytes()))
    (out/'qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    return dict(report=report, raw=raw, refs=refs, normal=normal, normal_refs=normal_refs,
                predecessor_elf=old_image, qualified_elf=new_image, qualified_object=new_padded)


if __name__ == '__main__':
    print(json.dumps(prepare()['report'], indent=2))
