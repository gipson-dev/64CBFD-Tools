"""Ground explosion: semantic C, closed sample-cell guards and whole-image gates."""
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
BUILD='conker/build/game-ground-explosion-15103e40-private/qualified'
SPEC=json.loads(Path(__file__).with_name('game_ground_explosion_15103e40_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM,SIZE,BODY_SIZE=SPEC['entry'],SPEC['rom'],SPEC['size'],SPEC['body_size']
ELF='conker/build/conker.us.elf';GUARDS='conker/retail_word_patches.us.csv';PROGRESS='conker/progress.csv'
SELECTED=SPEC['selected'];sha=lambda b:hashlib.sha256(b).hexdigest()

def source_states():
    old,new=SPEC['old_source'],SELECTED;live=(ROOT/SOURCE).read_text()
    if live not in(old,new):raise ValueError('Explosion source changed')
    return old,new,live==new

def checked(raw,refs):
    if len(raw)!=BODY_SIZE or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Explosion words/bindings changed')
    return raw,refs

def frame_proof(raw):
    if sha(raw)!=SPEC['raw_sha256']:raise ValueError('Unqualified explosion body')
    fields=SPEC['frame_cell'];seen=[];exports=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
        op,rs,rt=w>>26,w>>21&31,w>>16&31;off=((w&65535)^32768)-32768
        if op in(0x20,0x21,0x23,0x24,0x25,0x28,0x29,0x2B,0x31,0x39)and rs==29:
            width=1 if op in(0x20,0x24,0x28)else 2 if op in(0x21,0x25,0x29)else 4
            if any(off<=cell+3 and off+width>cell for cell in(0x44,0x54)):
                if op not in(0x31,0x39)or off!=0x54 or rt not in(0,18):raise ValueError('Frame cell is not closed')
                seen.append(i*4)
        if op==9 and rs==29 and rt!=29 and 0<=off<152:
            if off<0x58:raise ValueError('Private sample address escapes')
            exports.append(off)
    if seen!=fields['access_offsets']or set(exports)!={0x58,0x5C,0x7C,0x8C}:raise ValueError('Frame-cell access/export census changed')
    return dict(raw_offset=0x54,retail_offset=0x44,width=4,access_offsets=seen,exports=sorted(set(exports)),
                outgoing_bytes=48,saved_offsets=[0x38,0x3C],frame=152,unexposed_cells=True)

def normalize(raw):
    frame_proof(raw);changed=bytearray(raw)
    for at in SPEC['frame_cell']['access_offsets']:
        w=struct.unpack_from('>I',raw,at)[0];struct.pack_into('>I',changed,at,w-16)
    if sha(changed)!=SPEC['original_raw_sha256']:raise ValueError('Explosion frame guards differ from retail')
    return bytes(changed)

def base_dir():return ROOT/'conker/build/game-ground-explosion-15103e40-private/baseline'
def guard_states():
    old=(base_dir()/GUARDS).read_bytes()
    if sha(old)!=SPEC['predecessor']['inputs'][GUARDS]:raise ValueError('Guard history changed')
    eol='\r\n'if b'\r\n'in old else'\n';new=old+SPEC['append_guards'].replace('\n',eol).encode()
    if sha(new)!=SPEC['new_guards_sha256']or(ROOT/GUARDS).read_bytes()not in(old,new):raise ValueError('Explosion guards changed')
    return old,new

def progress_states():
    old=(base_dir()/PROGRESS).read_bytes();rows=old.splitlines(keepends=True);changed=[]
    for i,line in enumerate(rows):
        if line.startswith(b'us,game,generated_1312F0,func_15103E40,'):
            if b',816,asm'not in line:raise ValueError('Unexpected explosion conversion row')
            rows[i]=line.replace(b',816,asm',b',816,c');changed.append(i)
    if len(changed)!=1:raise ValueError('No unique explosion conversion row')
    new=b''.join(rows)
    if(ROOT/PROGRESS).read_bytes()not in(old,new):raise ValueError('Unexpected progress CSV changes')
    return old,new

def freeze():
    before=base_dir()
    for name,digest in SPEC['predecessor']['inputs'].items():
        q=before/name if name in(SOURCE,OBJECT,ELF,GUARDS,PROGRESS,'README.md')or name.startswith('DOCS/')else ROOT/name
        if sha(q.read_bytes())!=digest:raise ValueError('Frozen explosion input changed: '+name)
    return before

def assemble(out,label,assembly):
    folder=out/label;folder.mkdir(exist_ok=True);source,obj=folder/'generated_1312F0.c.s',folder/'generated_1312F0.c.o';source.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
    return obj

def strict_image(before,actual,truth):
    if sha(before)!=SPEC['predecessor']['inputs'][ELF]or sha(truth)!=SPEC['retail_sha256']:raise ValueError('Strict explosion image input changed')
    at=elf_slot_offset(actual,ENTRY,SIZE)
    if actual[at:at+SIZE]!=truth or actual!=before:raise ValueError('ASM-to-C explosion image is not byte-identical')
    return 0

def actual_Make(out,wanted):
    conker=ROOT/'conker';fixture=out/'make-source';source=fixture/'game/generated_1312F0.c';source.parent.mkdir(parents=True,exist_ok=True);source.write_text(SELECTED)
    shadow=out/'make';target=shadow/fixture.relative_to(conker)/'game/generated_1312F0.c.o';target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),'SRC_DIR='+fixture.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unexpected generated-C Make command')
        args=[str((out/'proposed-guards.csv').relative_to(conker))if a=='retail_word_patches.us.csv'else a for a in args]
        if '>'in args or 'asm_processor.py'in' '.join(args):raise ValueError('Proposed generated source did not select the C recipe')
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
        if args[0]=='../ido/ido5.3_recomp/cc':assert args.count('-O2')==args.count('-g3')==1 and '-O1'not in args
        commands.append(args)
    if len(commands)!=3 or target.read_bytes()!=wanted.read_bytes():raise ValueError('Generated-C Make object differs')
    (out/'make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=3,padded_object_equal=True,profile='existing O2/g3',source_fixture_has_no_GLOBAL_ASM=True)

def census(rom):
    calls=[];pointers=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
        if w>>26 in(2,3)and((w&0x3FFFFFF)<<2|0x10000000)==ENTRY:calls.append(i*4)
        if w==ENTRY:pointers.append(i*4)
    if calls!=[0x9805C,0x980A4,0x9E174]or pointers:raise ValueError('Explosion caller census changed')
    return dict(direct_calls=calls,literal_pointers=pointers,computed_calls_not_excluded=True)

def prepare():
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);base=freeze();old,new,installed=source_states();oldguards,newguards=guard_states();oldcsv,newcsv=progress_states()
    if(ROOT/GUARDS).read_bytes()!=(newguards if installed else oldguards)or(ROOT/PROGRESS).read_bytes()!=(newcsv if installed else oldcsv):raise ValueError('Explosion source/guards/conversion row disagree')
    for name,digest in SPEC['context'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Explosion caller/callee context changed')
    (out/'proposed-guards.csv').write_bytes(newguards);(out/'proposed-source.c').write_text(new)
    before,bd=compile_owner(ROOT,out,old,'before');after,ad=compile_owner(ROOT,out,new,'after')
    if bd or ad:raise ValueError('Explosion compiler diagnostics changed')
    raw,refs=checked(*payload(after,FUNCTION));proof=frame_proof(raw)
    original=assemble(out,'retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+(ROOT/SPEC['assembly']).read_text()+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    if sha((ROOT/SPEC['assembly']).read_bytes())!=SPEC['assembly_sha256']:raise ValueError('Original explosion assembly changed')
    assert payload(original,FUNCTION)==payload(before,FUNCTION)==(normalize(raw),refs)
    assert same_functions(before,after,(FUNCTION,))==0 and normalized_pools(before)==normalized_pools(after)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+SIZE];symbols={n:int(n.split('_')[1],16)for pairs in refs.values()for _,n in pairs}
    assert struct.pack('>202I',*bound_blob(normalize(raw),refs,symbols))+b'\0'*8==truth
    fullasm=ROOT/SPEC['full_assembly']
    beforepad=assemble(out,'before-pad',pg.emit_padded_assembly(before,fullasm,filename=SPEC['owner'],word_patches_path=base/GUARDS))
    afterpad=assemble(out,'after-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=out/'proposed-guards.csv'))
    assert same_functions(beforepad,afterpad)==1 and normalized_pools(beforepad)==normalized_pools(afterpad)
    assert payload(afterpad,FUNCTION)==(normalize(raw),refs)
    assert(ROOT/OBJECT).read_bytes()==(afterpad if installed else beforepad).read_bytes()
    independent=assemble(out,'independent-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=out/'proposed-guards.csv'))
    assert same_functions(afterpad,independent)==1 and normalized_pools(afterpad)==normalized_pools(independent)
    recipe=actual_Make(out,afterpad)
    with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,out,beforepad,'before-image');newelf=linker.link_image(ROOT,out,afterpad,'after-image')
    assert(ROOT/ELF).read_bytes()==(newelf if installed else oldelf).read_bytes()
    strict_image(oldelf.read_bytes(),newelf.read_bytes(),truth)
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump');assert af==bf and aa==ba
    assert bf[FUNCTION]==list(struct.unpack('>204I',truth));data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
    report=dict(body_words=202,slot_words=204,frame=152,guards=4,frame_cell_proof=proof,independent_padders=True,
                frozen_inputs=len(SPEC['predecessor']['inputs']),functions=len(af),diagnostics=0,Make=recipe,ELF_identical=True,
                strict_changed_bytes=0,exclusions=0,all_addresses_fixed=True,changed_bodies=[],conversion_rows=1,
                protected_data=data,census=census(rom),source_installed=installed,ELF_sha256=sha(newelf.read_bytes()),raw_sha256=sha(raw),
                reginfo_before=list(struct.unpack('>6I',sections(before)['.reginfo'][1])),reginfo_after=list(struct.unpack('>6I',sections(after)['.reginfo'][1])))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=out,after=afterpad,raw=raw,refs=refs,retail=original,elf=newelf,oldelf=oldelf)

if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
