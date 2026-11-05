"""Qualify the direct point-interval effect callback and its complete retail slot."""
import hashlib,json,struct,subprocess,re
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_point_interval_effect_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_118400.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/118400.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BUILD='conker/build/game-point-interval-effect-150EB090-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE=WORDS*4,candidate.SLOT_WORDS*4
RAW_SHA256='5a25e25740153faa7b6bb8bc60578768f6c5b63c6d94927bc0bf86f3df1b582e'
RETAIL_SHA256='56dfa682164737f2cddb643c198a161d15896bdcb09ff6b0a2629a12103042fb'
BASELINE_ELF_SHA256='0547aedf1ed72a2ee2dc86c0b28a5f40d33f098984f9b078c5d11ce4f53afcde'
BINDINGS={0x30:[('R_MIPS_26','func_150EAF50')],0x44:[('R_MIPS_HI16','D_800A1470')],
 0x48:[('R_MIPS_LO16','D_800A1470')],0x54:[('R_MIPS_HI16','D_800A1474')],
 0x58:[('R_MIPS_LO16','D_800A1474')],0x10C:[('R_MIPS_26','func_15141F78')]}
def function_blob(obj):
    text,functions,relocs=parse_object(obj);f=functions[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in relocs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
def checked_payload(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Point effect raw body/bindings changed')
    if hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Point effect retail body changed')
    expected=bytearray(truth)
    for at,rows in BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=bytes(expected):raise ValueError('Point effect requires a word correction')
    return raw,bindings
def checked_candidate(root,obj):return checked_payload(*function_blob(obj),original_bytes(root))
def serialize_symbol_pair(expected,before):
    # Referencing D_800A1470 changes one GNU-ld hash-bucket collision order.
    # Predict both complete records and both name strings from the frozen
    # predecessor; values, bindings, sizes and section identities stay fixed.
    rows={name:(off,f,string)for off,name,f,string in symbol_rows(before)}
    names=('D_800A1470','D_8009CF70');a,b=(rows[name]for name in names)
    if(a[0],b[0])!=(0x2D892C,0x2D893C)or a[1][1:]!=(0x800A1470,0,16,0,65521)or b[1][1:]!=(0x8009CF70,0,16,0,6):
        raise ValueError('Point-effect predecessor symbol collision changed')
    for destination,source,name in((a,b,names[1]),(b,a,names[0])):
        off,fields,string=destination
        if before[string:string+11]!=names[0 if destination==a else 1].encode()+b'\0':raise ValueError('Point-effect symbol string changed')
        struct.pack_into('>IIIBBH',expected,off,fields[0],*source[1][1:])
        expected[string:string+11]=name.encode()+b'\0'
def strict_image(before,after,truth):
    if len(truth)!=SIZE:raise ValueError('Wrong point effect body extent')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT_SIZE)
    if before[at+SIZE:at+SLOT_SIZE]!=bytes(SLOT_SIZE-SIZE):raise ValueError('Predecessor alignment changed')
    expected[at:at+SIZE]=truth;rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Predecessor point effect symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    serialize_symbol_pair(expected,before)
    if bytes(expected)!=after:raise ValueError('Point effect literal whole ELF prediction differs')
    return sum(a!=b for a,b in zip(before,after))
def registry_evidence(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w==(0x0C000000|((ENTRY>>2)&0x03FFFFFF))]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    source=(Path(root)/'conker/asm/data/22EB40.rodata.s').read_text()
    entries=re.findall(r'\.word\s+(\w+)',source.split('dlabel D_8008A0B4\n')[1].split('enddlabel D_8008A0B4')[0])
    if calls or pointers!=[0x22EBDC]or entries[26:28]!=[FUNCTION,'0x00000055']or len(entries)!=43:raise ValueError('Point effect callback census changed')
    return dict(direct_jal_calls=[],aligned_pointer_literals=['0x22ebdc'],table='D_8008A0B4',index=13,count=85,
        dispatch='func_15141A7C',abi='u8 *actor, s32 mode, s32 amount; void return; forwarded mode is low unsigned byte')
def assemble_owner(root,out,compact,label):
    path=out/(label+'.s');path.write_text(emit_padded_assembly(compact,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME))
    obj=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(path)],check=True,capture_output=True);return obj
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    before_obj,before_diagnostics=candidate.compile_owner(root,out,before_source,'predecessor-compact')
    after_obj,after_diagnostics=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(before_diagnostics)!=harness.diagnostics(after_diagnostics):raise ValueError('Owner diagnostics changed')
    raw,bindings=checked_candidate(root,after_obj)
    before_owner=assemble_owner(root,out,before_obj,'predecessor-owner');after_owner=assemble_owner(root,out,after_obj,'qualified-owner')
    if(after_owner if installed else before_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Live owner changed')
    if function_blob(after_owner)!=(raw,bindings):raise ValueError('Padder changed direct point effect body')
    raw_neighbors=same_functions(before_obj,after_obj,(FUNCTION,));neighbors=same_functions(before_owner,after_owner,(FUNCTION,))
    for a,b in((before_obj,after_obj),(before_owner,after_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Owner pools changed')
    with patch.object(harness,'OBJECT',OBJECT),patch.object(harness,'LINKER',LINKER):
        before_elf=harness.link_image(root,out,before_owner,'predecessor-image');after_elf=harness.link_image(root,out,after_owner,'qualified-image')
    before,after=before_elf.read_bytes(),after_elf.read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:raise ValueError('Predecessor ELF changed')
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Live image changed')
    delta=strict_image(before,after,original_bytes(root))
    old,_,old_addresses=load_elf_functions(str(before_elf),'mips-linux-gnu-objdump');new,_,new_addresses=load_elf_functions(str(after_elf),'mips-linux-gnu-objdump')
    changed=[name for name in new if old[name]!=new[name]];truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SLOT_SIZE]
    if set(old)!=set(new)or old_addresses!=new_addresses or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>76I',truth)):raise ValueError('Full image function/address/76-word slot closure failed')
    data=audit_layout(after_elf,root/'conker')
    if not data['exact']or(data['bytes'],data['owner_count'],data['different_bytes'])!=(189088,720,0):raise ValueError('Protected Game data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=WORDS,slot_words=76,alignment_words=3,frame=88,
        guards=0,relocations=len(bindings),neighbors=neighbors,raw_neighbors=raw_neighbors,raw_sha256=hashlib.sha256(raw).hexdigest(),
        retail_sha256=RETAIL_SHA256,qualified_owner_sha256=hashlib.sha256(after_owner.read_bytes()).hexdigest(),
        predecessor_elf_sha256=BASELINE_ELF_SHA256,qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),
        changed_bodies=changed,all_addresses_fixed=True,strict_exclusions=0,strict_changed_bytes=delta,registry=registry_evidence(root),game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=before_owner,qualified_owner=after_owner,predecessor_elf=before_elf,qualified_elf=after_elf,qualified_compact=after_obj)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
