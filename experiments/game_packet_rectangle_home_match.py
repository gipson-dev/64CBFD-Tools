"""Qualify and install closed callee-private rectangle temporary homes."""
from contextlib import contextmanager
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_clip_homes as homes
from tools.experiments import game_packet_rectangle_clip_phases as source
from tools.pad_generated_object import emit_padded_assembly, parse_object
from tools.tests.test_game_record_constructor_match import elf_slot_offset

BUILD = 'conker/build/game-packet-rectangle-home-match'
FUNCTION, OWNER, ENTRY, ROM = homes.FUNCTION, homes.OWNER, homes.ENTRY, homes.ROM
PATCHES = {205:(4,12),210:(0,8),211:(2,10),224:(4,12),242:(4,12),254:(0,8)}
AFTER = {'conker/build/conker.us.elf':'9a3f5eeca3804bde42fd9ee5b2dbd2d49c34ae58b7c5a1c47003f6e391a5441b',
    'conker/retail_word_patches.us.csv':'6fbe433672dd2e72c09417034b7127feeba4ea827403c9ccbb55af83c3dd4a5e'}
raw_read = Path.read_bytes
raw_text = Path.read_text
_active = False


def proof(words, normalized):
    if len(words) != 346 or len(normalized) != 346:
        raise ValueError('Changed rectangle home-proof extent')
    if [i for i,(a,b) in enumerate(zip(words,normalized)) if a != b] != list(PATCHES):
        raise ValueError('Home proof requires exactly six displacement changes')
    for i,(old,new) in PATCHES.items():
        if (words[i] & 65535, normalized[i] & 65535) != (old,new) or words[i] >> 16 != normalized[i] >> 16:
            raise ValueError('Changed rectangle home opcode/base/value register')
    if words[0] != 0x27BDFF78 or words[-1] != 0x27BD0088:
        raise ValueError('Changed rectangle frame ownership')
    memory_ops = {32:1,33:2,35:4,36:1,37:2,40:1,41:2,43:4,49:4,53:8,57:4,61:8}
    private = []
    for i,word in enumerate(words):
        op,rs,rt,rd,fn = word>>26,word>>21&31,word>>16&31,word>>11&31,word&63
        if op in memory_ops and rs == 29:
            offset = (word&65535)^32768
            offset -= 32768
            if offset < 136:
                private.append((i,op,offset,memory_ops[op]))
            if rt == 29 and op in (40,41,43):
                raise ValueError('Rectangle leaks a private stack address')
        elif (op == 0 and (rs == 29 or rt == 29 or rd == 29) or
                op in (8,9,10,11,12,13,14) and (rs == 29 or rt == 29) or
                op == 17 and rs in (0,2,4,6) and rt == 29):
            if i not in (0,345):
                raise ValueError('Rectangle stack address escapes or changes phase')
    if private != [(134,43,0,4),(205,43,4,4),(210,43,0,4),(211,33,2,2),
            (224,35,4,4),(242,35,4,4),(254,35,0,4)]:
        raise ValueError('Unclosed rectangle private stack accesses')

    # Nondeterministic branch conditions over-approximate every reachable path.
    # Pending destinations model normal/likely delay slots, including returns.
    todo,seen,exits = [(0,None,0)],set(),0
    while todo:
        state = todo.pop()
        if state in seen:
            continue
        seen.add(state)
        i,pending,defined = state
        if i == -1:
            exits += 1
            continue
        if not 0 <= i < 346:
            raise ValueError('Rectangle home proof escapes its routine')
        word = words[i]
        op,rs,rt,fn = word>>26,word>>21&31,word>>16&31,word&63
        if i == 205:
            defined |= 1
        elif i == 210:
            defined |= 2
        elif i in (224,242) and not defined&1 or i in (211,254) and not defined&2:
            raise ValueError('Rectangle reads a home before its complete definition')
        branch = op in (1,4,5,6,7,20,21,22,23) or op == 17 and rs == 8
        jump = op in (2,3) or op == 0 and fn in (8,9)
        if pending is not None:
            if branch or jump:
                raise ValueError('Rectangle delay slot contains control flow')
            todo.append((pending,None,defined))
        elif op == 0 and fn == 13:
            exits += 1
        elif op == 3 or op == 0 and fn == 9 or op == 1 and rt >= 16:
            raise ValueError('Rectangle private-home proof is leaf-only')
        elif op == 0 and fn == 8:
            if rs != 31 or i != 344:
                raise ValueError('Unexpected rectangle return')
            todo.append((i+1,-1,defined))
        elif op == 2:
            target = (((ENTRY+i*4+4)&0xF0000000)|((word&0x3FFFFFF)<<2))-ENTRY
            if target&3:
                raise ValueError('Unaligned rectangle jump')
            todo.append((i+1,target//4,defined))
        elif branch:
            offset = ((word&65535)^32768)-32768
            target = i+1+offset
            likely = op in (20,21,22,23) or op == 1 and rt in (2,3) or op == 17 and rt&2
            todo.append((i+1,target,defined))
            todo.append((i+2,None,defined) if likely else (i+1,i+2,defined))
        else:
            todo.append((i+1,None,defined))
    if not exits:
        raise ValueError('Rectangle home proof has no terminal path')
    return dict(states=len(seen),exits=exits,private_accesses=private,leaf=True,
        no_stack_address_escape=True,all_role_loads_dominated=True,
        contract='Mapped callee-owned 0x88-byte frame; external objects cannot alias it',
        raw_private_dead_bytes_not_equal=True)


def guards(obj, truth):
    source.checked_object(obj)
    text,functions,_ = parse_object(obj)
    f = functions[FUNCTION]
    words = struct.unpack_from('>346I',text,f['value'])
    rows = []
    for i,(old,new) in PATCHES.items():
        expected = words[i]
        if expected&65535 != old:
            raise ValueError('Unknown rectangle source home')
        if (expected&0xFFFF0000)|new != truth[i]:
            raise ValueError('Rectangle guard is not the corresponding retail home')
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%(i*4),
            expected='0x%08X'%expected,replacement='0x%08X'%((expected&0xFFFF0000)|new),
            expected_relocations='-',replacement_relocations='-',
            note='Normalize closed callee-private rectangle clipping temporary homes',
            insert_after='',insert_after_relocations='',omit='false'))
    return rows


def append_guards(before, rows):
    if not before.endswith(b'\n'):
        raise ValueError('Rectangle guard prefix lacks its final line ending')
    fields = next(csv.reader(io.StringIO(before.decode())))
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output,fieldnames=fields,lineterminator='\n')
    writer.writerows(rows)
    return before+output.getvalue().encode()


def expected_inputs(root, out):
    before = raw_read(out/'before-elf')
    prefix = raw_read(out/'before-guards')
    if hashlib.sha256(before).hexdigest() != homes.INPUTS['conker/build/conker.us.elf'] or (
            hashlib.sha256(prefix).hexdigest() != homes.INPUTS['conker/retail_word_patches.us.csv']):
        raise ValueError('Changed immutable rectangle match predecessor')
    manifest = raw_read(out/'after-guards')
    rows = json.loads(raw_text(out/'guards.json'))
    if manifest != append_guards(prefix,rows):
        raise ValueError('Changed immutable rectangle guard prediction')
    obj = out/'raw.o'
    truth = struct.unpack_from('>346I',raw_read(root/'conker/conker.us.bin'),ROM)
    if rows != guards(obj,truth):
        raise ValueError('Changed closed rectangle guard rows')
    slot = raw_read(out/'matched-slot.bin')
    if slot != struct.pack('>346I',*truth):
        raise ValueError('Changed emitted rectangle matching slot')
    at = elf_slot_offset(before,ENTRY,1384)
    result = {'conker/build/conker.us.elf':before[:at]+slot+before[at+1384:],
        'conker/retail_word_patches.us.csv':manifest}
    if {path:hashlib.sha256(data).hexdigest() for path,data in result.items()} != AFTER:
        raise ValueError('Changed exact rectangle successor fingerprints')
    return result


def verify(root, out, installed=False):
    expected = expected_inputs(root,out)
    stages = set()
    for path,after in expected.items():
        before = raw_read(out/('before-elf' if path.endswith('.elf') else 'before-guards'))
        actual = raw_read(root/path)
        if actual == before:
            stages.add('before')
        elif actual == after:
            stages.add('after')
        else:
            raise ValueError('Unexpected live rectangle match member: '+path)
    if len(stages) != 1 or installed and stages != {'after'}:
        raise ValueError('Mixed or uninstalled rectangle match checkpoint')
    return next(iter(stages))


@contextmanager
def historical_view(root, out):
    global _active
    if _active:
        raise RuntimeError('Rectangle match view cannot nest')
    verify(root,out)
    paths = {str((root/path).resolve()):raw_read(out/('before-elf' if path.endswith('.elf') else 'before-guards'))
        for path in expected_inputs(root,out)}
    def read_bytes(path):
        return paths.get(str(path.resolve()),raw_read(path))
    def read_text(path,encoding=None,errors=None,newline=None):
        if str(path.resolve()) not in paths:
            return raw_text(path,encoding=encoding,errors=errors,newline=newline)
        with io.TextIOWrapper(io.BytesIO(read_bytes(path)),encoding=encoding,errors=errors,newline=newline) as stream:
            return stream.read()
    emit = source.emit_padded_assembly
    def old_source_padder(*args,**kwargs):
        path = kwargs.get('word_patches_path')
        if path is not None and Path(path).resolve() == (root/'conker/retail_word_patches.us.csv').resolve():
            # The CSV parser uses open(), outside the Path reader view.
            kwargs['word_patches_path'] = out/'before-guards'
        return emit(*args,**kwargs)
    _active = True
    try:
        with patch.object(Path,'read_bytes',read_bytes),patch.object(Path,'read_text',read_text),patch.object(
                source,'emit_padded_assembly',old_source_padder):
            yield
    finally:
        _active = False


def qualify(root, out):
    homes.freeze(root,root/homes.BUILD)
    out.mkdir(parents=True,exist_ok=True)
    obj,words,row = homes.measure(root,out,'raw')
    truth = struct.unpack_from('>346I',(root/'conker/conker.us.bin').read_bytes(),ROM)
    lifetime = proof(words,truth)
    rows = guards(obj,truth)
    prefix = (root/'conker/retail_word_patches.us.csv').read_bytes()
    values = {'before-elf':(root/'conker/build/conker.us.elf').read_bytes(),
        'before-guards':prefix,'after-guards':append_guards(prefix,rows),
        'guards.json':(json.dumps(rows,indent=2)+'\n').encode()}
    for name,data in values.items():
        path = out/name
        if path.exists() and path.read_bytes() != data:
            raise ValueError('Changed immutable rectangle match fixture: '+name)
        if not path.exists():
            path.write_bytes(data)
    script = out/'matched-padded.s'
    script.write_text(emit_padded_assembly(obj,root/'conker/asm/C1D70.s',
        filename=OWNER,word_patches_path=out/'after-guards'))
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(script.with_suffix('.o')),str(script)],
        check=True,capture_output=True)
    data,functions = homes.build.link_owner(root,out,script.with_suffix('.o'),OWNER)
    f = functions[FUNCTION]
    slot = data[f['value']:f['value']+f['size']]
    if slot != struct.pack('>346I',*truth):
        raise ValueError('Guarded rectangle does not emit the complete retail routine')
    path = out/'matched-slot.bin'
    if path.exists() and path.read_bytes() != slot:
        raise ValueError('Changed first emitted rectangle match')
    if not path.exists():
        path.write_bytes(slot)
    neighbors = source.same_functions(root/'conker/build/src/game/generated_C1D70.c.o',
        script.with_suffix('.o'),(FUNCTION,))
    expected = expected_inputs(root,out)
    row = dict(words=346,frame=136,raw_differences=6,normalized_differences=0,
        guards=6,neighbors=neighbors,lifetime=lifetime,
        changed_ELF_bytes=sum(a!=b for a,b in zip(values['before-elf'],expected['conker/build/conker.us.elf'])),
        after={path:hashlib.sha256(data).hexdigest() for path,data in expected.items()})
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def audit(root,out):
    verify(root,out,installed=True)
    from tools.match_progress import load_elf_functions
    from tools.check_game_data_layout import audit_layout
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    before = raw_read(out/'before-elf')
    actual = raw_read(root/'conker/build/conker.us.elf')
    old,_,oa = load_elf_functions(str(out/'before-elf'),'mips-linux-gnu-objdump')
    new,_,na = load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if oa != na or set(old) != set(new) or [n for n in old if old[n] != new[n]] != [FUNCTION]:
        raise ValueError('Rectangle match changed unrelated bodies or addresses')
    if sorted((n,f[1:]) for _,n,f,_ in symbol_rows(before)) != sorted((n,f[1:]) for _,n,f,_ in symbol_rows(actual)):
        raise ValueError('Rectangle match changed symbol metadata')
    source.same_functions(out/'matched-padded.o',root/'conker/build/src/game/generated_C1D70.c.o')
    layout = audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if (layout['exact'],layout['bytes'],layout['owner_count'],layout['different_bytes']) != (True,189088,720,0):
        raise ValueError('Rectangle match changed Game data')
    result = dict(functions=len(old),only_target_changed=True,all_addresses_and_metadata_preserved=True,
        actual_padded_owner_identical=True,changed_ELF_bytes=sum(a!=b for a,b in zip(before,actual)),
        game_data=layout)
    (out/'installed-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def install_guard_manifest(root,out):
    """Generate only the six qualified rows, preserving mixed legacy endings."""
    homes.freeze(root,root/homes.BUILD)
    expected = expected_inputs(root,out)
    path = root/'conker/retail_word_patches.us.csv'
    if raw_read(path) != raw_read(out/'before-guards'):
        raise ValueError('Rectangle guard installation requires its exact predecessor')
    path.write_bytes(expected['conker/retail_word_patches.us.csv'])
    return hashlib.sha256(raw_read(path)).hexdigest()


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(qualify(root,root/BUILD),indent=2))
