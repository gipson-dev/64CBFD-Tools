"""Direct C sound-token timer: owner, ABI, independent padding and image gates."""
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
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-sound-timer-15103aa0-private/qualified'
SPEC=json.loads(Path(__file__).with_name('game_sound_timer_15103aa0_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM,SIZE=SPEC['entry'],SPEC['rom'],SPEC['size']
ELF='conker/build/conker.us.elf'
GUARDS='conker/retail_word_patches.us.csv'
SELECTED,HEADER=SPEC['selected'],SPEC['header']
sha=lambda b:hashlib.sha256(b).hexdigest()


def source_states():
    old=SPEC['old_source'];assert old.count(SPEC['stub'])==1
    new=old.replace('s32 func_15103AA0();\n','').replace(SPEC['stub'],SELECTED.rstrip())
    live=(ROOT/SOURCE).read_text()
    if live not in(old,new):raise ValueError('Sound timer owner changed')
    return old,new,live==new


def checked(raw,refs):
    if len(raw)!=SIZE or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:
        raise ValueError('Sound timer words/bindings changed')
    return raw,refs


def freeze():
    before=ROOT/'conker/build/game-sound-timer-15103aa0-private/baseline'
    for name,digest in SPEC['predecessor']['inputs'].items():
        q=before/name if name in(SOURCE,OBJECT,ELF,'conker/progress.csv')else ROOT/name
        if sha(q.read_bytes())!=digest:raise ValueError('Frozen sound timer input changed: '+name)
    return before


def assemble(out,label,assembly):
    folder=out/label;folder.mkdir(exist_ok=True)
    source,obj=folder/'game_130CB0.c.s',folder/'game_130CB0.c.o';source.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
    return obj


def strict_image(before,actual,truth):
    if sha(before)!=SPEC['predecessor']['inputs'][ELF]or sha(truth)!=SPEC['retail_sha256']:raise ValueError('Sound timer strict input changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(pos,v)for pos,n,v,_ in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Sound timer predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=actual:raise ValueError('Sound timer image differs outside the predicted body/extent')
    return sum(a!=b for a,b in zip(before,actual))


def actual_Make(out,proposal,wanted):
    conker=ROOT/'conker';shadow=out/'make';target=shadow/'src/game_130CB0.c.o';target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected sound timer Make command')
        args=[proposal.relative_to(conker).as_posix()if a=='src/game_130CB0.c'else a for a in args]
        assert '>'not in args
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
        if args[0]=='../ido/ido5.3_recomp/cc':assert args.count('-O2')==args.count('-g3')==1 and '-O1'not in args
        commands.append(args)
    if len(commands)!=3 or target.read_bytes()!=wanted.read_bytes():raise ValueError('Actual sound timer Make owner differs')
    (out/'make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=3,padded_object_equal=True,profile='existing O2/g3')


def census(rom):
    calls=[];pointers=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
        if w>>26 in(2,3)and((w&0x3FFFFFF)<<2|0x10000000)==ENTRY:calls.append(i*4)
        if w==ENTRY:pointers.append(i*4)
    if calls or pointers:raise ValueError('Sound timer literal-call census changed')
    return dict(direct_calls=calls,literal_pointers=pointers,computed_calls_not_excluded=True)


def prepare():
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);base=freeze();old,new,installed=source_states()
    (out/'proposed-owner.c').write_text(new)
    before,bd=compile_owner(ROOT,out,old,'before');after,ad=compile_owner(ROOT,out,new,'after');single,sd=compile_owner(ROOT,out,HEADER+SELECTED,'isolated')
    if bd or ad or sd:raise ValueError('Sound timer compiler diagnostics changed')
    raw,refs=checked(*payload(after,FUNCTION));assert payload(single,FUNCTION)==(raw,refs)
    assert same_functions(before,after,(FUNCTION,))==4 and normalized_pools(before)==normalized_pools(after)
    assembly=ROOT/SPEC['assembly'];assert sha(assembly.read_bytes())==SPEC['assembly_sha256']
    original=assemble(out,'retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly.read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    assert payload(original,FUNCTION)==(raw,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+SIZE]
    symbols={n:int(n.split('_')[1],16)for bindings in refs.values()for _,n in bindings}
    assert struct.pack('>93I',*bound_blob(raw,refs,symbols))==truth
    beforepad=assemble(out,'before-pad',pc.emit_padded_assembly(before,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=ROOT/GUARDS))
    afterpad=assemble(out,'after-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=ROOT/GUARDS))
    assert same_functions(beforepad,afterpad,(FUNCTION,))==4 and normalized_pools(beforepad)==normalized_pools(afterpad)
    assert payload(afterpad,FUNCTION)==(raw,refs)
    assert (ROOT/OBJECT).read_bytes()==(afterpad if installed else beforepad).read_bytes()
    text=[]
    for row in csv.DictReader(io.StringIO((ROOT/'conker/retail_layout.us.txt').read_text())):
        if row['filename']!=SPEC['owner']:continue
        text.append('glabel '+row['function'])
        for va in range(int(row['address'],16),int(row['end'],16),4):
            off=va-0x15000000+0x2D4B0;w=struct.unpack_from('>I',rom,off)[0]
            text.append('/* %06X %08X %08X */ .word 0x%08X'%(off,va,w,w))
    asm=out/'retail-owner.s';asm.write_text('\n'.join(text)+'\n')
    independent=assemble(out,'independent-pad',pg.emit_padded_assembly(after,asm,filename=SPEC['owner'],word_patches_path=ROOT/GUARDS))
    assert same_functions(afterpad,independent)==5 and normalized_pools(afterpad)==normalized_pools(independent)
    masks=[struct.unpack('>6I',sections(q)['.reginfo'][1])for q in(before,after,single)]
    assert masks[1]==tuple(masks[0][i]|masks[2][i]if i<5 else masks[0][i]for i in range(6))
    recipe=actual_Make(out,out/'proposed-owner.c',afterpad)
    with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,out,beforepad,'before-image');newelf=linker.link_image(ROOT,out,afterpad,'after-image')
    assert (ROOT/ELF).read_bytes()==(newelf if installed else oldelf).read_bytes()
    delta=strict_image(oldelf.read_bytes(),newelf.read_bytes(),truth)
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump')
    assert af.keys()==bf.keys()and aa==ba and[n for n in bf if af[n]!=bf[n]]==[FUNCTION]and bf[FUNCTION]==list(struct.unpack('>93I',truth))
    data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
    report=dict(words=93,frame=48,guards=0,direct_C=True,neighbors=4,independent_padders=True,frozen_inputs=len(SPEC['predecessor']['inputs']),functions=len(af),diagnostics=0,Make=recipe,strict_changed_bytes=delta,exclusions=0,all_addresses_fixed=True,changed_bodies=[FUNCTION],protected_data=data,census=census(rom),source_installed=installed,ELF_sha256=sha(newelf.read_bytes()),raw_sha256=sha(raw))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=out,after=afterpad,raw=raw,refs=refs,retail=original,elf=newelf,oldelf=oldelf)


if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
