"""Tank camera callback: direct C, independent padding, Make and strict image."""
import hashlib,json,os,shlex,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout

ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
BUILD='conker/build/game-tank-camera-15104520-private/qualified'
SPEC=json.loads(Path(__file__).with_name('game_tank_camera_15104520_manifest.json').read_text())
FUNCTION,SOURCE,OBJECT=SPEC['function'],SPEC['source'],SPEC['object']
ENTRY,ROM,SIZE,BODY_SIZE=SPEC['entry'],SPEC['rom'],SPEC['size'],SPEC['body_size']
ELF='conker/build/conker.us.elf';GUARDS='conker/retail_word_patches.us.csv';PROGRESS='conker/progress.csv'
SELECTED=SPEC['selected'];sha=lambda b:hashlib.sha256(b).hexdigest()
def base_dir():return ROOT/'conker/build/game-tank-camera-15104520-private/baseline'
def source_states():
    old,new=SPEC['old_source'],SELECTED;live=(ROOT/SOURCE).read_text()
    if live not in(old,new):raise ValueError('Tank camera source changed')
    return old,new,live==new
def checked(raw,refs):
    if len(raw)!=BODY_SIZE or sha(raw)!=SPEC['raw_sha256']or json.loads(json.dumps(refs))!=SPEC['refs']:raise ValueError('Tank camera words/bindings changed')
    return raw,refs
def normalize(raw):
    if sha(raw)!=SPEC['raw_sha256']:raise ValueError('Tank camera source words changed')
    return raw
def progress_states():
    old=(base_dir()/PROGRESS).read_bytes();rows=old.splitlines(keepends=True);changed=[]
    for i,line in enumerate(rows):
        if line.startswith(b'us,game,generated_1319D0,func_15104520,'):
            if b',192,asm'not in line:raise ValueError('Unexpected tank conversion row')
            rows[i]=line.replace(b',192,asm',b',192,c');changed.append(i)
    if len(changed)!=1:raise ValueError('No unique tank conversion row')
    new=b''.join(rows)
    if(ROOT/PROGRESS).read_bytes()not in(old,new):raise ValueError('Unexpected conversion CSV changes')
    return old,new
def freeze():
    base=base_dir()
    for n,h in SPEC['predecessor']['inputs'].items():
        q=base/n if n in(SOURCE,OBJECT,ELF,PROGRESS,'README.md')or n.startswith('DOCS/')else ROOT/n
        if sha(q.read_bytes())!=h:raise ValueError('Frozen tank input changed: '+n)
    return base
def assemble(out,label,assembly):
    folder=out/label;folder.mkdir(exist_ok=True);source,obj=folder/'generated_1319D0.c.s',folder/'generated_1319D0.c.o';source.write_text(assembly)
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(source)],check=True,capture_output=True)
    return obj
def expected_image(before):
    if sha(before)!=SPEC['predecessor']['inputs'][ELF]:raise ValueError('Tank predecessor ELF changed')
    matches=[at for at,n,v,_ in symbol_rows(before)if n==FUNCTION and dict(value=v[1],size=v[2],info=v[3],other=v[4])==SPEC['old_symbol']]
    if len(matches)!=1:raise ValueError('Tank predecessor extent changed')
    result=bytearray(before);struct.pack_into('>I',result,matches[0]+8,BODY_SIZE);return bytes(result)
def strict_image(before,actual,truth):
    if sha(truth)!=SPEC['retail_sha256']:raise ValueError('Tank retail slot changed')
    at=elf_slot_offset(actual,ENTRY,SIZE)
    if actual!=expected_image(before)or actual[at:at+SIZE]!=truth:raise ValueError('Tank image differs outside declared symbol extent')
    return sum(a!=b for a,b in zip(before,actual))
def actual_Make(out,wanted):
    conker=ROOT/'conker';fixture=out/'make-source';source=fixture/'game/generated_1319D0.c';source.parent.mkdir(parents=True,exist_ok=True);source.write_text(SELECTED)
    shadow=out/'make';target=shadow/fixture.relative_to(conker)/'game/generated_1319D0.c.o';target.parent.mkdir(parents=True,exist_ok=True)
    plan=subprocess.run(['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix(),'SRC_DIR='+fixture.relative_to(conker).as_posix(),target.relative_to(conker).as_posix()],cwd=conker,capture_output=True,text=True,check=True)
    (out/'make-plan.txt').write_text(plan.stdout+plan.stderr);commands=[]
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as')or '>'in args or 'asm_processor.py'in' '.join(args):raise ValueError('Unexpected pure-C Make recipe')
        result=subprocess.run(args,cwd=conker,capture_output=True,text=True)
        if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
        if args[0]=='../ido/ido5.3_recomp/cc':assert args.count('-O2')==args.count('-g3')==1 and '-O1'not in args
        commands.append(args)
    if len(commands)!=3 or target.read_bytes()!=wanted.read_bytes():raise ValueError('Tank actual Make object differs')
    (out/'make-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=3,padded_object_equal=True,profile='existing O2/g3',source_fixture_has_no_GLOBAL_ASM=True)
def census(rom):
    calls=[];pointers=[]
    for i,(w,)in enumerate(struct.iter_unpack('>I',rom)):
        if w>>26 in(2,3)and((w&0x3FFFFFF)<<2|0x10000000)==ENTRY:calls.append(i*4)
        if w==ENTRY:pointers.append(i*4)
    if calls or pointers!=[0x22E15C]or struct.unpack_from('>I',rom,0x22E130+11*4)[0]!=ENTRY:raise ValueError('Tank callback census changed')
    return dict(direct_calls=calls,literal_pointers=pointers,table_index=11,computed_calls_not_excluded=True)
def prepare():
    out=ROOT/BUILD;out.mkdir(parents=True,exist_ok=True);base=freeze();old,new,installed=source_states();oldcsv,newcsv=progress_states()
    if(ROOT/PROGRESS).read_bytes()!=(newcsv if installed else oldcsv):raise ValueError('Tank source/conversion row disagree')
    for n,h in SPEC['context'].items():
        if sha((ROOT/n).read_bytes())!=h:raise ValueError('Tank caller/callee context changed')
    (out/'proposed-source.c').write_text(new)
    before,bd=compile_owner(ROOT,out,old,'before');after,ad=compile_owner(ROOT,out,new,'after')
    if bd or ad:raise ValueError('Tank compiler diagnostics changed')
    raw,refs=checked(*payload(after,FUNCTION));beforebody,beforerefs=payload(before,FUNCTION)
    assert beforebody==raw+b'\0'*12 and beforerefs==refs and same_functions(before,after,(FUNCTION,))==0
    assert normalized_pools(before)==normalized_pools(after)
    assembly=(ROOT/SPEC['assembly']).read_text();assert sha((ROOT/SPEC['assembly']).read_bytes())==SPEC['assembly_sha256']
    original=assemble(out,'retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+assembly.split('endlabel '+FUNCTION)[0]+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    assert payload(original,FUNCTION)==(raw,refs)
    rom=(ROOT/'conker/conker.us.bin').read_bytes();truth=rom[ROM:ROM+SIZE];assert struct.pack('>45I',*bound_blob(raw,refs,{'func_15128774':0x15128774}))+b'\0'*12==truth
    fullasm=ROOT/SPEC['full_assembly']
    beforepad=assemble(out,'before-pad',pg.emit_padded_assembly(before,fullasm,filename=SPEC['owner'],word_patches_path=ROOT/GUARDS))
    afterpad=assemble(out,'after-pad',pg.emit_padded_assembly(after,fullasm,filename=SPEC['owner'],word_patches_path=ROOT/GUARDS))
    assert sections(beforepad)['.text'][1]==sections(afterpad)['.text'][1]and normalized_pools(beforepad)==normalized_pools(afterpad)
    assert payload(afterpad,FUNCTION)==(raw,refs)and(ROOT/OBJECT).read_bytes()==(afterpad if installed else beforepad).read_bytes()
    independent=assemble(out,'independent-pad',pc.emit_padded_assembly(after,ROOT/'conker/retail_layout.us.txt',SPEC['owner'],word_patches_path=ROOT/GUARDS))
    assert same_functions(afterpad,independent)==1 and normalized_pools(afterpad)==normalized_pools(independent)
    recipe=actual_Make(out,afterpad)
    with patch.multiple(linker,FILENAME=SPEC['owner'],OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        oldelf=linker.link_image(ROOT,out,beforepad,'before-image');newelf=linker.link_image(ROOT,out,afterpad,'after-image')
    assert(ROOT/ELF).read_bytes()==(newelf if installed else oldelf).read_bytes();delta=strict_image(oldelf.read_bytes(),newelf.read_bytes(),truth)
    af,_,aa=load_elf_functions(str(oldelf),'mips-linux-gnu-objdump');bf,_,ba=load_elf_functions(str(newelf),'mips-linux-gnu-objdump');assert af==bf and aa==ba and bf[FUNCTION]==list(struct.unpack('>48I',truth))
    data=audit_layout(newelf,ROOT/'conker');assert data['exact']and not data['different_bytes']
    report=dict(body_words=45,slot_words=48,frame=24,guards=0,independent_padders=True,frozen_inputs=len(SPEC['predecessor']['inputs']),functions=len(af),diagnostics=0,Make=recipe,
        strict_changed_bytes=delta,exclusions=0,all_addresses_fixed=True,all_instruction_vectors_identical=True,changed_bodies=[],symbol_extent=[192,180],conversion_rows=1,guards_unchanged=True,
        protected_data=data,census=census(rom),source_installed=installed,ELF_sha256=sha(newelf.read_bytes()),raw_sha256=sha(raw))
    assert delta==1
    (out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,out=out,after=afterpad,raw=raw,refs=refs,retail=original,elf=newelf,oldelf=oldelf)
if __name__=='__main__':print(json.dumps(prepare()['report'],indent=2))
