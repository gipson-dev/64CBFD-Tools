"""Qualify the camera preset selector, derived guards, Make recipe and image."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
from unittest.mock import patch

from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object', pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions, elf_slot_offset, symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments import game_actor_state_tick_integration as metadata
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT = Path(os.environ.get('CBFD_CONSUMER_ROOT', Path(__file__).resolve().parents[2])).resolve()
BUILD = 'conker/build/game-camera-preset-15123568-private/qualified'
SPEC = json.loads(Path(__file__).with_name('game_camera_preset_15123568_manifest.json').read_text())
FUNCTION, SOURCE, OBJECT = SPEC['function'], SPEC['source'], SPEC['object']
ENTRY, ROM, SIZE = SPEC['entry'], SPEC['rom'], SPEC['size']
ELF, GUARDS = 'conker/build/conker.us.elf', 'conker/retail_word_patches.us.csv'
SELECTED = SPEC['selected']
HEADER = '#include <ultra64.h>\n#include "functions.h"\n#include "variables.h"\nextern f32 D_800A34D8;\n'
sha = lambda b: hashlib.sha256(b).hexdigest()


def source_states():
    old = SPEC['old_source']
    assert old.count(SPEC['stub']) == 1
    new = old.replace('s32 func_15123568(s32 arg0);', 'void func_15123568(struct108 *camera);').replace(SPEC['stub'], SELECTED.rstrip())
    live = (ROOT/SOURCE).read_text()
    if live not in (old, new):
        raise ValueError('Camera preset owner changed')
    return old, new, live == new


def derive_guards(raw, refs):
    """Rename the two constant-one live ranges, then schedule independent LI."""
    if len(raw) != SIZE or sha(raw) != SPEC['raw_sha256'] or json.loads(json.dumps(refs)) != SPEC['refs']:
        raise ValueError('Camera preset raw words or bindings changed')
    words = list(struct.unpack('>90I', raw)); result = words[:]
    for at in (0x40, 0xE0):
        if words[at//4] != 0x24030001: raise ValueError('Constant-one definition changed')
        result[at//4] = words[at//4] & ~(31 << 16) | 5 << 16
    if words[0x44//4] != 0xA48301B4: raise ValueError('Preset halfword use changed')
    result[0x44//4] = words[0x44//4] & ~(31 << 16) | 5 << 16
    for at, expected in ((0xE8, 0x54690005), (0xF4, 0x506A0019)):
        if words[at//4] != expected: raise ValueError('Constant-one branch use changed')
        result[at//4] = words[at//4] & ~(31 << 21) | 5 << 21
    branch, define = words[0x100//4:0x108//4]
    if (branch, define) != (0x10620015, 0x24030003): raise ValueError('Loop entry schedule changed')
    # Preserve the branch destination while moving it by one instruction.
    result[0x100//4] = define
    result[0x104//4] = (branch & ~((31 << 21) | 65535)) | 5 << 21 | ((branch & 65535)-1)
    offsets = [i*4 for i, (a, b) in enumerate(zip(words, result)) if a != b]
    if offsets != [0x40, 0x44, 0xE0, 0xE8, 0xF4, 0x100, 0x104]: raise ValueError('Guard set changed')
    return [dict(filename='game_14FF90', function=FUNCTION, offset='0x%X'%at,
                 expected='0x%08X'%words[at//4], replacement='0x%08X'%result[at//4],
                 expected_relocations='-', replacement_relocations='-',
                 note='Normalize camera preset constant register lifetimes and independent loop-entry schedule',
                 insert_after='', insert_after_relocations='', omit='false') for at in offsets]


def freeze(out):
    pins = SPEC['predecessor']['inputs']
    allowed = {SOURCE, OBJECT, ELF, GUARDS, 'conker/progress.csv'}
    before = ROOT/'conker/build/game-camera-preset-15123568-private/baseline'
    for name, digest in pins.items():
        live = ROOT/name
        saved = before/name
        if name in allowed:
            if sha(saved.read_bytes()) != digest: raise ValueError('Frozen camera input changed: '+name)
        elif sha(live.read_bytes()) != digest:
            raise ValueError('Protected camera input changed: '+name)
    return before


def assemble(out, label, assembly):
    folder = out/label; folder.mkdir(exist_ok=True)
    source, obj = folder/'game_14FF90.c.s', folder/'game_14FF90.c.o'
    source.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32',
                    '-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)], check=True, capture_output=True)
    return obj


def strict_image(before, after, truth):
    if sha(before) != SPEC['predecessor']['inputs'][ELF] or sha(truth) != SPEC['retail_sha256']:
        raise ValueError('Camera preset strict input changed')
    wanted = bytearray(before); at = elf_slot_offset(before, ENTRY, SIZE)
    wanted[at:at+SIZE] = truth
    rows = [(pos, values) for pos, name, values, _ in symbol_rows(before) if name == FUNCTION]
    if len(rows) != 1 or rows[0][1][1:3] != (ENTRY, 16): raise ValueError('Camera preset predecessor extent changed')
    struct.pack_into('>I', wanted, rows[0][0]+8, SIZE)
    # GNU ld moves this adjacent pair when the new body first references D_800A34D8.
    # The existing helper verifies contiguous rows/strings and exact named definitions.
    with patch.object(metadata, 'SYMBOL_ORDER', (('D_800A34D8', 'D_800991D8'),)):
        wanted = metadata.reorder_symbols(bytes(wanted))
    if bytes(wanted) != after: raise ValueError('Camera preset image differs outside the predicted body/extent')
    return sum(a != b for a, b in zip(before, after))


def make_owner(out, proposal, guards, wanted, compact, diagnostics):
    conker = ROOT/'conker'; shadow = out/'make'; target = shadow/'src/game_14FF90.c.o'
    target.parent.mkdir(parents=True, exist_ok=True)
    plan = subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],
                          cwd=conker, check=True, capture_output=True, text=True)
    (out/'make-plan.txt').write_text(plan.stdout+plan.stderr); commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm': continue
        if args[0] not in ('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'): raise ValueError('Unexpected Make command')
        args=[proposal.relative_to(conker).as_posix() if a=='src/game_14FF90.c' else
              guards.relative_to(conker).as_posix() if a=='retail_word_patches.us.csv' else a for a in args]
        redirect=None
        if '>' in args:
            assert args[-2]=='>' and args.count('>')==1
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow);args=args[:-2]
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        expected=diagnostic_rows(diagnostics) if args[0]=='../ido/ido5.3_recomp/cc' else {}
        if result.returncode or diagnostic_rows(result.stderr)!=expected or (redirect is None and result.stdout):
            raise ValueError(result.stdout+result.stderr)
        if redirect is not None: redirect.write_text(result.stdout)
        commands.append(args)
    if len(commands)!=5 or target.read_bytes()!=wanted.read_bytes(): raise ValueError('Actual Make owner differs')
    same_functions(compact,Path(str(target)+'.compact'))
    (out/'make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=len(commands),padded_object_equal=True)


def prepare():
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);base=freeze(out)
    old,new,installed=source_states();(out/'proposed-owner.c').write_text(new)
    before,bd=compile_owner(ROOT,out,old,'before');after,ad=compile_owner(ROOT,out,new,'after')
    single,sd=compile_owner(ROOT,out,HEADER+SELECTED,'isolated')
    if diagnostic_rows(bd)!=diagnostic_rows(ad) or sd: raise ValueError('Camera preset diagnostics changed')
    raw,refs=payload(after,FUNCTION)
    if payload(single,FUNCTION)!=(raw,refs): raise ValueError('Isolated camera body changed')
    rows=derive_guards(raw,refs)
    assembly=ROOT/'conker/asm/nonmatchings/game_14FF90/func_15123568.s'
    if sha(assembly.read_bytes())!='c43a967aa2e2922c2aea3821f53033ed0b786a86a1ab7118b543c88bbd9d6ce1':
        raise ValueError('Original camera preset assembly changed')
    retailobj=assemble(out,'retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly.read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    original,originalrefs=payload(retailobj,FUNCTION)
    if sha(original)!=SPEC['retail_object_sha256'] or originalrefs!=refs:
        raise ValueError('Original camera words/bindings changed')
    raw_neighbors=same_functions(before,after,(FUNCTION,));assert raw_neighbors==44
    assert normalized_pools(before)==normalized_pools(after)
    oldguard=(base/GUARDS).read_bytes();fields=oldguard.decode().splitlines()[0].split(',')
    extra=io.StringIO();writer=csv.DictWriter(extra,fieldnames=fields,lineterminator='\n');writer.writerows(rows)
    expected_guards=oldguard+extra.getvalue().encode()
    if (ROOT/GUARDS).read_bytes()!=(expected_guards if installed else oldguard): raise ValueError('Camera guard history changed')
    patchfile=out/'guards.csv';patchfile.write_bytes(expected_guards)
    beforepad=assemble(out,'before-pad',pc.emit_padded_assembly(before,ROOT/'conker/retail_layout.us.txt','game_14FF90',word_patches_path=base/GUARDS))
    afterpad=assemble(out,'after-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt','game_14FF90',word_patches_path=patchfile))
    neighbors=same_functions(beforepad,afterpad,(FUNCTION,));assert neighbors==44
    assert normalized_pools(beforepad)==normalized_pools(afterpad)
    assert (ROOT/OBJECT).read_bytes()==(afterpad if installed else beforepad).read_bytes()
    retail=(ROOT/'conker/conker.us.bin').read_bytes()[ROM:ROM+SIZE]
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    syms={n:int(n.split('_')[1],16) for values in refs.values() for _,n in values}
    padded,pr=payload(afterpad,FUNCTION)
    assert struct.pack('>90I',*bound_blob(padded,pr,syms))==retail
    registers=[struct.unpack('>6I',sections(obj)['.reginfo'][1])for obj in (before,after,single)]
    assert registers[1]==tuple(registers[0][i]|registers[2][i] if i<5 else registers[0][i] for i in range(6))
    recipe=make_owner(out,out/'proposed-owner.c',patchfile,afterpad,after,ad)
    with patch.multiple(linker,FILENAME='game_14FF90',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,out,beforepad,'before-image')
        newelf=linker.link_image(ROOT,out,afterpad,'after-image')
    assert (ROOT/ELF).read_bytes()==(newelf if installed else oldelf).read_bytes()
    delta=strict_image(oldelf.read_bytes(),newelf.read_bytes(),retail)
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump')
    assert aa==ba and af.keys()==bf.keys() and [n for n in bf if af[n]!=bf[n]]==[FUNCTION]
    assert bf[FUNCTION]==list(struct.unpack('>90I',retail))
    data=audit_layout(newelf,ROOT/'conker');assert data['exact'] and data['different_bytes']==0
    report=dict(words=90,frame=24,guards=7,raw_neighbors=raw_neighbors,padded_neighbors=neighbors,
                frozen_inputs=len(SPEC['predecessor']['inputs']),functions=len(af),diagnostics=sum(diagnostic_rows(ad).values()),
                Make=recipe,all_addresses_fixed=True,changed_bodies=[FUNCTION],strict_changed_bytes=delta,exclusions=0,
                protected_data=data,source_installed=installed,ELF_sha256=sha(newelf.read_bytes()),raw_sha256=sha(raw))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=out,after=afterpad,raw=raw,refs=refs,retail=retailobj,elf=newelf,oldelf=oldelf,guards=patchfile)


if __name__=='__main__': print(json.dumps(prepare()['report'],indent=2))
