"""Qualify the live sequence catch-up loop and closed prologue scheduling."""
import csv,hashlib,json,struct,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_sequence_catchup_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_owner_pool import normalized_pools
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
OBJECT='conker/build/src/game/generated_49D30.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/49D30.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BUILD='conker/build/game-sequence-catchup-1501E2F8-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,SLOT_SIZE,NATURAL_FRAME,RETAIL_FRAME=264,264,56,56
RAW_SHA256='30cb1ad4e92e7bf5d44b9abc59fd6ea1799ea95ee187eb91c28d262ae1c462c5'
RETAIL_SHA256='285bb3184d53468f915148446118bf0c9b799a8610842d9b44a51c6c3c8bd2fc'
BASELINE_ELF_SHA256='efd54ec9785d8510c55ccd84cde8d252ccd096f554733cef46b0d34f35de9ee7'
BINDINGS={40: [('R_MIPS_HI16', 'D_800C3640')], 68: [('R_MIPS_LO16', 'D_800C3640')], 44: [('R_MIPS_HI16', 'D_800C35B0')], 64: [('R_MIPS_LO16', 'D_800C35B0')], 48: [('R_MIPS_HI16', 'D_800C35EA')], 60: [('R_MIPS_LO16', 'D_800C35EA')], 52: [('R_MIPS_HI16', 'D_800C3C8C')], 56: [('R_MIPS_LO16', 'D_800C3C8C')], 136: [('R_MIPS_26', 'func_1501E81C')], 160: [('R_MIPS_26', 'func_1501E400')], 172: [('R_MIPS_26', 'func_150242F8')], 180: [('R_MIPS_26', 'func_1501EC38')], 192: [('R_MIPS_26', 'func_150242F8')], 200: [('R_MIPS_26', 'func_15020EC4')]}
PERMUTATION={1: 4, 2: 5, 3: 6, 4: 7, 5: 13, 6: 12, 7: 11, 8: 10, 9: 8, 10: 1, 11: 2, 12: 18, 13: 17, 14: 16, 16: 14, 17: 3, 18: 9}
RETAIL_BINDINGS={next((dst*4 for dst,src in PERMUTATION.items()if src*4==at),at):rows for at,rows in BINDINGS.items()}
PREIMAGES={1: 2947612700, 2: 8423461, 3: 2948530228, 4: 2947940400, 5: 2947874860, 6: 2947809320, 7: 2947743780, 8: 2947678240, 9: 2947547160, 10: 1008074752, 11: 1008009216, 12: 1007943680, 13: 1007878144, 14: 645070848, 16: 649396224, 17: 651558912, 18: 605159425}
GUARD_WORDS=tuple((dst*4,PREIMAGES[dst],PREIMAGES[src])for dst,src in PERMUTATION.items())
PATCH_ROWS=tuple(dict(offset='0x%03X'%at,expected='0x%08X'%a,replacement='0x%08X'%b)for at,a,b in GUARD_WORDS)
source_states=candidate.source_states
CALLER_SOURCE='conker/src/game_45B80.c'
CALLER_OBJECT='conker/build/src/game_45B80.c.o'
def complete_row(row):
    at=int(row['offset'],0);binding=lambda rows:'|'.join(k+':'+s for k,s in rows)or'-'
    return dict(filename=FILENAME,function=FUNCTION,**row,expected_relocations=binding(BINDINGS.get(at,[])),replacement_relocations=binding(RETAIL_BINDINGS.get(at,[])),
        note='Derive the closed sequence catch-up prologue scheduling permutation',insert_after='',insert_after_relocations='',omit='false')
def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def original_bytes(root):return(Path(root)/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE]
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Sequence catch-up raw body or bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Sequence catch-up retail body changed')
    words=struct.unpack('>66I',raw)
    if any(words[i]!=w for i,w in PREIMAGES.items()):raise ValueError('Sequence catch-up scheduling preimage changed')
    result=struct.pack('>66I',*(words[PERMUTATION.get(i,i)]for i in range(66)));expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26' else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if result!=bytes(expected):raise ValueError('Sequence catch-up fitted body differs')
    return result
def census(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)];pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0x466A0]or pointers:raise ValueError('Sequence catch-up caller census changed')
    return dict(direct_calls=['0x466A0'],pointers=[],caller='func_15019130',abi='void(s32 slot)',callees=['func_1501E81C','func_1501E400','func_150242F8','func_1501EC38','func_15020EC4'])
def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Sequence catch-up strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SLOT_SIZE)
    if before[at+SIZE:at+SLOT_SIZE]!=bytes(SLOT_SIZE-SIZE):raise ValueError('Sequence catch-up alignment changed')
    expected[at:at+SIZE]=truth;rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Sequence catch-up predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        offsets=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Sequence catch-up literal image differs: '+repr((len(offsets),list(map(hex,offsets[:40])))))
    return sum(a!=b for a,b in zip(before,after))

def caller_states(live):
    old,new='s32 func_1501E2F8(s32);','void func_1501E2F8(s32);'
    if live.count(old)==1 and new not in live:return live,live.replace(old,new,1),False
    if live.count(new)==1 and old not in live:return live.replace(new,old,1),live,True
    raise ValueError('Sequence catch-up caller declaration changed')

def qualify_caller(root,out,installed):
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    before,after,live=caller_states((root/CALLER_SOURCE).read_text())
    if live!=installed:raise ValueError('Sequence catch-up caller/source installation differs')
    old,od=compile_owner(root,out,before,'caller-before');new,nd=compile_owner(root,out,after,'caller-after')
    if harness.diagnostics(od)!=harness.diagnostics(nd):raise ValueError('Sequence catch-up caller diagnostics changed')
    count=same_functions(old,new)
    if normalized_pools(old)!=normalized_pools(new):raise ValueError('Sequence catch-up caller pools changed')
    owners=[]
    for label,obj in(('caller-before',old),('caller-after',new)):
        assembly=out/(label+'-padded.s');owner=out/(label+'-padded.o')
        subprocess.run(['python3',str(root/'tools/pad_c_object.py'),str(obj),str(root/'conker/retail_layout.us.txt'),'game_45B80',str(assembly),'--word-patches',str(root/GUARDS)],check=True,capture_output=True)
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(owner),str(assembly)],check=True,capture_output=True)
        owners.append(owner)
    if owners[0].read_bytes()!=owners[1].read_bytes()or owners[0].read_bytes()!=(root/CALLER_OBJECT).read_bytes():raise ValueError('Sequence catch-up caller complete object changed')
    return dict(typed_void_interface=True,unchanged_functions=count,unchanged_padded_object=True,sha256=hashlib.sha256(owners[1].read_bytes()).hexdigest())

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=source_states((root/SOURCE).read_text())
    with(root/GUARDS).open(newline='')as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;live=list(reader)
    expected=[complete_row(r)for r in PATCH_ROWS];target=[r for r in live if r['filename']==FILENAME and r['function']==FUNCTION]
    if target!=(expected if installed else[]):raise ValueError('Sequence catch-up installed guards changed')
    old_rows=[r for r in live if not(r['filename']==FILENAME and r['function']==FUNCTION)];new_rows=old_rows+expected
    old_obj,old_diag=candidate.compile_owner(root,out,before_source,'predecessor-compact');new_obj,new_diag=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(old_diag)!=harness.diagnostics(new_diag):raise ValueError('Sequence catch-up owner diagnostics changed')
    fitted=normalized(*function_blob(new_obj),original_bytes(root))
    caller_report=qualify_caller(root,out,installed)
    with patch.multiple(harness,FILENAME=FILENAME,ASM=ASM,OBJECT=OBJECT,LINKER=LINKER):
        old_owner=harness.assemble_owner(root,out,old_obj,old_rows,fields,'predecessor-owner');new_owner=harness.assemble_owner(root,out,new_obj,new_rows,fields,'qualified-owner')
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    if(new_owner if installed else old_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Sequence catch-up live owner differs')
    if function_blob(new_owner)!=(fitted,RETAIL_BINDINGS):raise ValueError('Sequence catch-up padded body differs')
    raw_neighbors=same_functions(old_obj,new_obj,(FUNCTION,));neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    for a,b in((old_obj,new_obj),(old_owner,new_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Sequence catch-up owner pools changed')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Sequence catch-up live image differs')
    delta=strict_image(before,after,original_bytes(root))
    old,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');new,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump');changed=[n for n in new if old[n]!=new[n]]
    slot=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SLOT_SIZE]
    if set(old)!=set(new)or aa!=bb or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>66I',slot)):raise ValueError('Sequence catch-up complete slot/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Sequence catch-up protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=66,slot_words=66,alignment_words=0,frame=56,guards=17,relocations=14,
        raw_neighbors=raw_neighbors,neighbors=neighbors,raw_sha256=RAW_SHA256,retail_sha256=RETAIL_SHA256,
        qualified_owner_sha256=hashlib.sha256(new_owner.read_bytes()).hexdigest(),predecessor_elf_sha256=BASELINE_ELF_SHA256,
        qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),changed_bodies=changed,all_addresses_fixed=True,
        strict_exclusions=0,strict_changed_bytes=delta,named_symbol_serialization_bytes=0,literal_full_image_prediction=True,registry=census(root),caller=caller_report,game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,predecessor_elf=old_elf,qualified_elf=new_elf,
        fields=fields,predecessor_rows=old_rows,qualified_rows=new_rows,qualified_compact=new_obj)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
