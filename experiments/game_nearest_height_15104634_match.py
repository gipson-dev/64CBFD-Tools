"""Nearest terrain height: proven register guards and complete image prediction."""
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
BUILD='conker/build/game-nearest-height-15104634-match-private/qualified'
SPEC=json.loads(Path(__file__).with_name('game_nearest_height_15104634_match_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM,SIZE,BODY_SIZE=SPEC['entry'],SPEC['rom'],SPEC['size'],SPEC['body_size']
ELF='conker/build/conker.us.elf';GUARDS='conker/retail_word_patches.us.csv';PROGRESS='conker/progress.csv'
SELECTED=SPEC['selected'];sha=lambda b:hashlib.sha256(b).hexdigest()

def base_dir():return ROOT/'conker/build/game-nearest-height-15104634-match-private/baseline'
def source_states():
    old,new=SPEC['old_source'],SELECTED;live=(ROOT/SOURCE).read_text()
    if live not in(old,new):raise ValueError('Nearest-height source changed')
    return old,new,live==new
def checked(raw,refs):
    if len(raw)!=BODY_SIZE or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Nearest-height words/bindings changed')
    return raw,refs
def normalize(raw):
    checked(raw,{int(k):v for k,v in SPEC['refs'].items()});changed=bytearray(raw)
    for row in SPEC['register_guards']:
        at=row['offset'];a=struct.unpack_from('>I',raw,at)[0];b=row['replacement']
        if a!=row['expected']or(a^b)&~row['register_mask']:raise ValueError('Nearest-height guard exceeds proven register fields')
        struct.pack_into('>I',changed,at,b)
    if sha(changed)!=SPEC['original_raw_sha256']:raise ValueError('Nearest-height normalized words differ from original')
    return bytes(changed)
def guard_states():
    old=(base_dir()/GUARDS).read_bytes()
    if sha(old)!=SPEC['predecessor']['inputs'][GUARDS]:raise ValueError('Nearest-height guard history changed')
    eol='\r\n'if b'\r\n'in old else'\n';new=old+SPEC['append_guards'].replace('\n',eol).encode()
    if sha(new)!=SPEC['new_guards_sha256']or(ROOT/GUARDS).read_bytes()not in(old,new):raise ValueError('Nearest-height guard append changed')
    return old,new
def freeze():
    base=base_dir();mutable={SOURCE,OBJECT,ELF,GUARDS,'README.md'}
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n in mutable or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Frozen nearest-height input changed: '+n)
    return base
def assemble(out,label,assembly):
    folder=out/label;folder.mkdir(exist_ok=True);source,obj=folder/'generated_131A90.c.s',folder/'generated_131A90.c.o';source.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
    return obj
def expected_image(before,truth):
    if sha(before)!=SPEC['predecessor']['inputs'][ELF]or sha(truth)!=SPEC['retail_sha256']:raise ValueError('Nearest-height predicted-image inputs changed')
    rows=[at for at,n,v,_ in symbol_rows(before)if n==FUNCTION and dict(value=v[1],size=v[2],info=v[3],other=v[4])==SPEC['old_symbol']]
    if len(rows)!=1:raise ValueError('Nearest-height predecessor symbol changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth;struct.pack_into('>I',result,rows[0]+8,BODY_SIZE)
    return bytes(result)
def strict_image(before,actual,truth):
    if actual!=expected_image(before,truth):raise ValueError('Nearest-height image differs outside predicted slot and symbol extent')
    return sum(a!=b for a,b in zip(before,actual))
def census(rom):
    calls=[];pointers=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
        if w>>26 in(2,3)and((w&0x3FFFFFF)<<2|0x10000000)==ENTRY:calls.append(i*4)
        if w==ENTRY:pointers.append(i*4)
    if calls!=[0x811A0]or pointers:raise ValueError('Nearest-height caller census changed')
    return dict(direct_calls=calls,literal_pointers=pointers,computed_calls_not_excluded=True)

def actual_Make(out,wanted):
    conker=ROOT/'conker';fixture=out/'make-source';source=fixture/'game/generated_131A90.c';source.parent.mkdir(parents=True,exist_ok=True);source.write_text(SELECTED)
    shadow=out/'make';target=shadow/fixture.relative_to(conker)/'game/generated_131A90.c.o';target.parent.mkdir(parents=True,exist_ok=True)
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

def prepare():
    from tools.tests.game_nearest_height_15104634_relation import qualify as relation
    from tools.experiments.game_nearest_height_15104634_recovery import SYMS
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);base=freeze();old,new,installed=source_states();oldguards,newguards=guard_states()
    if(ROOT/GUARDS).read_bytes()!=(newguards if installed else oldguards):raise ValueError('Nearest-height source/guards disagree')
    if(ROOT/PROGRESS).read_bytes()!=(base/PROGRESS).read_bytes():raise ValueError('Nearest-height conversion CSV changed')
    (out/'proposed-guards.csv').write_bytes(newguards);(out/'proposed-source.c').write_text(new)
    before,bd=compile_owner(ROOT,out,old,'before');after,ad=compile_owner(ROOT,out,new,'after');assert not bd and not ad
    raw,refs=checked(*payload(after,FUNCTION));assert same_functions(before,after,(FUNCTION,))==4 and normalized_pools(before)==normalized_pools(after)
    asm=(ROOT/SPEC['full_assembly']).read_text();body='glabel '+FUNCTION+asm.split('glabel '+FUNCTION,1)[1].split('endlabel '+FUNCTION,1)[0]
    original=assemble(out,'retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    normalized=normalize(raw);assert payload(original,FUNCTION)==(normalized,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();slot=rom[ROM:ROM+SIZE];truth=bound_blob(normalized,refs,SYMS);words=bound_blob(raw,refs,SYMS)
    assert struct.pack('>272I',*truth)+b'\0'*12==slot
    proof=relation(dict(truth=truth,words=words));(out/'register-relation.json').write_text(json.dumps(proof,indent=2)+'\n')
    fullasm=ROOT/SPEC['full_assembly']
    beforepad=assemble(out,'before-pad',pg.emit_padded_assembly(before,fullasm,filename=SPEC['owner'],word_patches_path=base/GUARDS))
    afterpad=assemble(out,'after-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=out/'proposed-guards.csv'))
    assert same_functions(beforepad,afterpad,(FUNCTION,))==4 and normalized_pools(beforepad)==normalized_pools(afterpad)
    assert payload(afterpad,FUNCTION)==(normalized,refs)and(ROOT/OBJECT).read_bytes()==(afterpad if installed else beforepad).read_bytes()
    independent=assemble(out,'independent-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=out/'proposed-guards.csv'))
    assert same_functions(afterpad,independent)==5 and normalized_pools(afterpad)==normalized_pools(independent)
    recipe=actual_Make(out,afterpad)
    with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,out,beforepad,'before-image');newelf=linker.link_image(ROOT,out,afterpad,'after-image')
    assert(ROOT/ELF).read_bytes()==(newelf if installed else oldelf).read_bytes()
    delta=strict_image(oldelf.read_bytes(),newelf.read_bytes(),slot)
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump')
    assert set(af)==set(bf)and aa==ba
    different=[n for n in af if af[n]!=bf[n]];assert different==[FUNCTION],different
    assert bf[FUNCTION]==list(struct.unpack('>275I',slot));data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
    report=dict(body_words=272,slot_words=275,frame=224,guards=121,real_word_differences=121,unchanged_raw_neighbors=4,independent_padders=True,
        frozen_inputs=len(SPEC['predecessor']['inputs']),functions=len(af),diagnostics=0,Make=recipe,strict_changed_bytes=delta,exclusions=0,
        all_addresses_fixed=True,changed_bodies=different,symbol_extent=[12,1088],conversion_rows=0,protected_data=data,census=census(rom),
        source_installed=installed,matching_credit=int(installed),ELF_sha256=sha(newelf.read_bytes()),raw_sha256=sha(raw))
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=out,after=afterpad,raw=raw,refs=refs,truth=truth,words=words,retail=original,elf=newelf,oldelf=oldelf)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
