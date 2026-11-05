"""Qualify the position configuration wrapper, including its special owner recipe."""
import csv,hashlib,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_point_configuration_packet_candidates as candidate
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
OBJECT='conker/build/src/game_161520.c.o'
ASM='conker/asm/nonmatchings/game_161520/func_1513A48C.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
TU='conker/src/game/translation_units/161520_actor_point_effects.c'
BUILD='conker/build/game-point-configuration-1513A48C-match'
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE=264
RAW_SHA256='18262aef893cab06c15b31b0935825ddd158ed6574993b752b66456b7c9df73b'
RETAIL_SHA256='c4afdd83fa086c8d6bc121a3f216001a33f5b70399683c0471e7d5859bb2db3d'
BASELINE_ELF_SHA256='426d61d5a54e30dffc620cd594ba46e49d11042889663ef9fb24295bc0ada0fc'
BINDINGS={0x18:[('R_MIPS_HI16','D_800A4950')],0x24:[('R_MIPS_LO16','D_800A4950')],
0x70:[('R_MIPS_HI16','D_800A4954')],0x74:[('R_MIPS_LO16','D_800A4954')],
0x78:[('R_MIPS_HI16','D_800A4958')],0x7C:[('R_MIPS_LO16','D_800A4958')],
0x80:[('R_MIPS_HI16','D_800A495C')],0x84:[('R_MIPS_LO16','D_800A495C')],
0x94:[('R_MIPS_HI16','D_800A4260')],0x98:[('R_MIPS_HI16','D_800A4264')],
0xBC:[('R_MIPS_LO16','D_800A4264')],0xC0:[('R_MIPS_LO16','D_800A4260')],
0xF0:[('R_MIPS_26','func_15152190')]}
PERMUTATION={**dict(zip(range(1,10),(6,9,1,2,3,4,5,7,8))),**dict(zip(range(46,53),(51,52,46,47,48,49,50)))}
RETAIL_BINDINGS={next((dst*4 for dst,src in PERMUTATION.items()if src*4==at),at):rows for at,rows in BINDINGS.items()}
PREIMAGES={1:0xAFBF0024,2:0xAFA40068,3:0xAFA5006C,4:0xAFA60070,5:0x8FB90068,
6:0x3C010000,7:0x240E0008,8:0x240F0004,9:0xC4200000,
46:0xAFA90014,47:0x24C60000,48:0x24A50000,49:0x27A4002C,50:0x24070001,51:0xE7A0005C,52:0xE7A00060}
GUARD_WORDS=tuple((dst*4,PREIMAGES[dst],PREIMAGES[src])for dst,src in PERMUTATION.items())
PATCH_ROWS=tuple(dict(offset='0x%03X'%at,expected='0x%08X'%a,replacement='0x%08X'%b)for at,a,b in GUARD_WORDS)

def complete_row(row):
    at=int(row['offset'],0)
    binding=lambda rows:'|'.join(k+':'+s for k,s in rows)or '-'
    return dict(filename=FILENAME,function=FUNCTION,**row,expected_relocations=binding(BINDINGS.get(at,[])),
        replacement_relocations=binding(RETAIL_BINDINGS.get(at,[])),
        note='Derive initial scale snapshot and independent packet store schedules',insert_after='',insert_after_relocations='',omit='false')

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=BINDINGS:raise ValueError('Point configuration natural body or bindings changed')
    if len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:raise ValueError('Point configuration retail body changed')
    words=struct.unpack('>66I',raw)
    if any(words[i]!=w for i,w in PREIMAGES.items()):raise ValueError('Point configuration scheduling preimage changed')
    result=struct.pack('>66I',*(words[PERMUTATION.get(i,i)]for i in range(66)))
    expected=bytearray(truth)
    for at,rows in RETAIL_BINDINGS.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if result!=bytes(expected):raise ValueError('Point configuration complete fitted body differs')
    return result

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def census(root):
    image=(Path(root)/ROM_IMAGE).read_bytes();words=struct.unpack('>%dI'%(len(image)//4),image[:len(image)&~3])
    calls=[i*4 for i,w in enumerate(words)if w>>26 in(2,3)and(w&0x3FFFFFF)*4==(ENTRY&0xFFFFFFF)]
    pointers=[i*4 for i,w in enumerate(words)if w==ENTRY]
    if calls!=[0x1643E8,0x164EA0]or pointers:raise ValueError('Point configuration caller census changed')
    return dict(direct_calls=calls,pointers=pointers,abi='void(position *, u8 channel, s32 context)',callee='func_15152190')

def strict_image(before,after,truth):
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256 or len(truth)!=SIZE or hashlib.sha256(truth).hexdigest()!=RETAIL_SHA256:
        raise ValueError('Point configuration strict predecessor or retail input changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,f)for off,name,f,_ in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Point configuration predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # Seven closed GNU-ld hash-bucket pair permutations, reconstructed only
    # from the pinned predecessor. One pair has unequal string lengths, so
    # its second st_name moves inside the same complete string interval.
    symbols={name:(off,fields,string)for off,name,fields,string in symbol_rows(before)}
    pairs=(('D_800A495C','D_800A045C',0x29D50C),('D_800A4260','D_8009F0B0',0x2A357C),
        ('.L1514CC14_game_data','D_8009E5B0',0x2A39CC),('D_800990B0','D_8009E5E0',0x2CA10C),
        ('D_800A4958','D_800A0458',0x2D1A7C),('D_800A4950','D_800A0450',0x2D56DC),
        ('D_800A4954','D_800A0454',0x2D5E9C))
    for left,right,offset in pairs:
        a,b=symbols[left],symbols[right]
        if a[0]!=offset or b[0]!=offset+16 or b[2]!=a[2]+len(left)+1:raise ValueError('Point configuration symbol pair changed')
        old_names=(left+'\0'+right+'\0').encode();new_names=(right+'\0'+left+'\0').encode()
        if before[a[2]:a[2]+len(old_names)]!=old_names:raise ValueError('Point configuration predecessor strings changed')
        struct.pack_into('>IIIBBH',expected,a[0],a[1][0],*b[1][1:])
        struct.pack_into('>IIIBBH',expected,b[0],a[1][0]+len(right)+1,*a[1][1:])
        expected[a[2]:a[2]+len(old_names)]=new_names
    if bytes(expected)!=after:raise ValueError('Point configuration literal whole ELF prediction differs')
    return sum(a!=b for a,b in zip(before,after))

def assemble(root,out,obj,effects,guards,label):
    path=out/(label+'.s');path.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,
        rodata_symbol='jtbl_800A4350_game',word_patches_path=guards,function_objects={'func_15138BC0':effects}))
    output=path.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(output),str(path)],check=True,capture_output=True)
    return output

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    before_obj,before_diag=candidate.compile_owner(root,out,before_source,'predecessor-compact')
    after_obj,after_diag=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if harness.diagnostics(before_diag)!=harness.diagnostics(after_diag):raise ValueError('Point configuration owner diagnostics changed')
    effects,effects_diag=candidate.compile_owner(root,out,(root/TU).read_text(),'effects-compact')
    if effects_diag:raise ValueError('Point configuration override diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=function_blob(after_obj);fitted=normalized(raw,bindings,truth)
    with(root/GUARDS).open(newline='')as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    old_rows=[r for r in rows if r['function']!=FUNCTION];new_rows=old_rows+[complete_row(r)for r in PATCH_ROWS]
    if rows!=(new_rows if installed else old_rows):raise ValueError('Point configuration live guard rows changed')
    old_guard,new_guard=out/'predecessor-patches.csv',out/'qualified-patches.csv'
    harness.write_patches(old_guard,fields,old_rows);harness.write_patches(new_guard,fields,new_rows)
    old_owner=assemble(root,out,before_obj,effects,old_guard,'predecessor-owner')
    new_owner=assemble(root,out,after_obj,effects,new_guard,'qualified-owner')
    if(new_owner if installed else old_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Point configuration live owner changed')
    if function_blob(new_owner)!=(fitted,RETAIL_BINDINGS):raise ValueError('Point configuration padded body changed')
    raw_neighbors=same_functions(before_obj,after_obj,(FUNCTION,));neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    for a,b in((before_obj,after_obj),(old_owner,new_owner)):
        if normalized_pools(a)!=normalized_pools(b):raise ValueError('Point configuration owner pool changed')
    with patch.object(harness,'OBJECT',OBJECT),patch.object(harness,'LINKER',LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if hashlib.sha256(before).hexdigest()!=BASELINE_ELF_SHA256:raise ValueError('Point configuration predecessor ELF changed')
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Point configuration live image changed')
    delta=strict_image(before,after,truth)
    old,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');new,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[n for n in new if old[n]!=new[n]]
    if set(old)!=set(new)or aa!=bb or changed!=[FUNCTION]or new[FUNCTION]!=list(struct.unpack('>66I',truth)):raise ValueError('Point configuration complete function closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Point configuration protected Game data changed')
    report=dict(function=FUNCTION,source_installed=installed,words=WORDS,frame=104,guards=len(PATCH_ROWS),relocations=len(bindings),
        raw_neighbors=raw_neighbors,neighbors=neighbors,raw_sha256=RAW_SHA256,retail_sha256=RETAIL_SHA256,
        qualified_owner_sha256=hashlib.sha256(new_owner.read_bytes()).hexdigest(),predecessor_elf_sha256=BASELINE_ELF_SHA256,
        qualified_elf_sha256=hashlib.sha256(after).hexdigest(),functions=len(new),changed_bodies=changed,all_addresses_fixed=True,
        strict_exclusions=0,strict_changed_bytes=delta,registry=census(root),game_data=data)
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,predecessor_elf=old_elf,qualified_elf=new_elf,qualified_compact=after_obj)

if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
