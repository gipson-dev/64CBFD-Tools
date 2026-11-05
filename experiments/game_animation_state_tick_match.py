"""Qualify the direct animation tick through the ordinary C-owner padder."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_animation_state_tick_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
import tools
sys.path.insert(0,tools.__path__[0])
from tools.pad_c_object import emit_padded_assembly
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game_1944C0.c.o'
ASM='conker/asm/nonmatchings/game_1944C0/func_15167B44.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,REGISTRY='conker/conker.us.bin','conker/asm/data/22FF90.rodata.s'
BUILD='conker/build/game-animation-state-tick-15167B44-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE=276,276
RAW_SHA256='b3ee4d4860755a3629384d55d5c8febd44a8509d0ec6bf9215e01892a52e5123'
RETAIL_SHA256='92b6457e9e90d582e1779373bc4080ed6ed747f3cd32fe35b52ab6732efe100f'
BASELINE_ELF_SHA256='6f1eb8121a4c21b123b88b0dc068ae30fd930ba3a03d112117fdf40a7510f71b'
BINDINGS={0xC:[('R_MIPS_HI16','D_8008CA20')],0x1C:[('R_MIPS_LO16','D_8008CA20')],0xFC:[('R_MIPS_26','func_1516972C')]}
PATCH_ROWS=()
source_states=candidate.source_states

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
def checked_payload(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Animation tick natural body/bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Animation tick retail body changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=bytes(expected):raise ValueError('Animation tick requires a correction')
    return raw,bindings

def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls or pointers!=[0x230004]or struct.unpack_from('>I',image,0x22FF68+3*52)[0]!=ENTRY:raise ValueError('Animation tick catalog registration changed')
    if(Path(root)/REGISTRY).read_text().count('.word '+FUNCTION)!=1:raise ValueError('Animation tick registry assembly changed')
    return dict(direct_jump_calls=[],pointer_literals=['0x230004'],catalog='D_8008B4A8',row=3,stride=52,field=0,caller='func_151670C0',abi='void(u8 *state)')

def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Animation tick strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Animation tick predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Animation tick literal complete image prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def assemble(root,out,obj,label):
    path=out/(label+'.s');path.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,word_patches_path=root/GUARDS))
    output=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(output),str(path)],check=True,capture_output=True)
    return output

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    old_obj,old_diag=candidate.compile_owner(root,out,before_source,'predecessor-compact');new_obj,new_diag=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(old_diag)!=harness.diagnostics(new_diag):raise ValueError('Animation tick owner diagnostics changed')
    raw,bindings=checked_payload(*function_blob(new_obj),original_bytes(root));old_owner=assemble(root,out,old_obj,'predecessor-owner');new_owner=assemble(root,out,new_obj,'qualified-owner')
    if(new_owner if installed else old_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Animation tick live owner changed')
    if function_blob(new_owner)!=(raw,bindings):raise ValueError('Animation tick padding changed the direct body')
    raw_neighbors=same_functions(old_obj,new_obj,(FUNCTION,));neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    for a,b in((old_obj,new_obj),(old_owner,new_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Animation tick owner pools changed')
    with patch.object(harness,'OBJECT',OBJECT),patch.object(harness,'LINKER',LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Animation tick live full image changed')
    delta=strict_image(before,after,original_bytes(root))
    old,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');new,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump');changed=[n for n in new if old[n]!=new[n]]
    if set(old)!=set(new)or aa!=bb or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>69I',original_bytes(root))):raise ValueError('Animation tick complete function closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Animation tick protected Game data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=69,slot_words=69,alignment_words=0,frame=24,guards=0,relocations=len(bindings),
        raw_neighbors=raw_neighbors,neighbors=neighbors,raw_sha256=RAW_SHA256,retail_sha256=RETAIL_SHA256,
        qualified_owner_sha256=hashlib.sha256(new_owner.read_bytes()).hexdigest(),predecessor_elf_sha256=BASELINE_ELF_SHA256,
        qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),changed_bodies=changed,all_addresses_fixed=True,strict_exclusions=0,
        strict_changed_bytes=delta,literal_full_image_prediction=True,registry=registry_evidence(root),game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,predecessor_elf=old_elf,qualified_elf=new_elf,qualified_compact=new_obj)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
