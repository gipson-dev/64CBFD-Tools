"""Closed frame correction, complete owner, original callbacks and literal ELF."""
import csv,hashlib,io,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_threshold_random_effect_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game/generated_197120.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/197120.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
RAW_SHA='f91852acca330bbedea7d2cb186d94fd4eebb7d422e13361e7099d46f813049e'
TRUTH_SHA='32a5796924aa96d4c9d38dd0c52e0c4918ca922793f1ed401ab6d050cffa7cf9'
BASELINE_SHA='31e41dff4d451e29a3def37e867fd07c44dd5a1a85e2f66dc311cfcd40756006'
GUARD_SHA='892dcc21c80c8cc41c6970ed89c7f218e072b5a5487946d406a0d133e7f6d6d6'
BINDINGS={24:[('R_MIPS_26','func_150ADA20')],56:[('R_MIPS_26','func_150ADA20')],248:[('R_MIPS_26','func_15171D4C')]}
PATCHES=((0,0x27BDFFB8,0x27BDFFB0),(28,0xAFA40048,0xAFA40050),(40,0x8FA40048,0x8FA40050),
 (48,0xAFAF0044,0xAFAF0048),(60,0xAFB80040,0xAFB80044),(72,0x8FA40048,0x8FA40050),
 (76,0x8FAB0044,0x8FAB0048),(172,0x8FAE0040,0x8FAE0044),(260,0x27BD0048,0x27BD0050))
sha=lambda b:hashlib.sha256(b).hexdigest()

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();direct=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        word=struct.unpack_from('>I',rom,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:direct.append(at)
    if direct or pointers!=[0x2314EC]:raise ValueError('Threshold effect callback census changed')
    return dict(direct_calls=0,pointer_rom=pointers[0],table=0x8008CA20,index=3,
      original_windows=[0x15167B44,0x151680CC,0x15168BAC,0x15169988])

def freeze(root,out):
    manifest=out/'input-sha256.json'
    if not manifest.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze threshold effect inputs at its predecessor ELF first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,'conker/build/conker.us.bin','conker/Makefile','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json',
          'conker/asm/19F150.s','conker/asm/nonmatchings/game_DAE50/func_150ADA20.s','conker/asm/196DB0.s','conker/asm/data/22FF90.rodata.s',
          'conker/src/game/generated_19F150.c','conker/src/game/generated_196DB0.c','conker/src/game_1944C0.c',
          'conker/build/src/game/generated_19F150.c.o','conker/build/src/game/generated_196DB0.c.o','conker/build/src/game_1944C0.c.o',
          *['conker/asm/nonmatchings/game_1944C0/'+n+'.s'for n in('func_15167B44','func_15167E0C','func_15168BAC')]]
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        values={}
        for path in sorted(set(paths)):
            data=(root/path).read_bytes();dest=out/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[path]=sha(data)
        manifest.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(manifest.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for path,wanted in values.items():
        if sha((out/'frozen'/path).read_bytes())!=wanted:raise ValueError('Threshold effect frozen input changed: '+path)
        if path not in changed and sha((root/path).read_bytes())!=wanted:raise ValueError('Threshold effect protected live input changed: '+path)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Threshold effect raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Threshold effect original changed')
    result=bytearray(raw)
    for at,old,new in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=old:raise ValueError('Threshold effect frame guard changed')
        struct.pack_into('>I',result,at,new)
    expected=bytearray(truth)
    for at in bindings:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFC000000)
    if result!=expected:raise ValueError('Threshold effect normalized body differs')
    return bytes(result)
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Threshold effect inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Threshold effect predecessor already guarded')
    rows=[dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations='-',replacement_relocations='-',
        note='Normalize randomized effect frame and two spill slots',insert_after='',insert_after_relocations='',omit='false')for at,old,new in PATCHES]
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(rows);return before+out.getvalue().encode()
def assemble_owner(root,out,obj,manifest,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=guards,filename=FILENAME))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Threshold effect strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Threshold effect predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Threshold effect literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:40])))))
    wanted=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if wanted!=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(after)):raise ValueError('Threshold effect named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    old_guards=(out/'frozen'/GUARDS).read_bytes();new_guards=guard_manifest(old_guards)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial threshold effect installation')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if od or nd:raise ValueError('Unexpected threshold effect diagnostics')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];fitted=normalized(*function_blob(new),truth);raw_neighbors=same_functions(old,new,(FUNCTION,))
    a,b=alloc_pools(old),alloc_pools(new)
    (out/'compact-pools.json').write_text(json.dumps({k:repr((a.get(k),b.get(k)))for k in a.keys()|b.keys()if a.get(k)!=b.get(k)},indent=2)+'\n')
    ai=bytes.fromhex('800000040000000000000000000000000000000000007ff0')
    bi=bytes.fromhex('a300ffd6000000000007f750000000000000000000007ff0')
    if a.get('.reginfo')!=(1879048198,2,0,4,ai,())or b.get('.reginfo')!=(1879048198,2,0,4,bi,()):raise ValueError('Threshold effect compact register masks changed')
    if {k:v for k,v in a.items()if k!='.reginfo'}!={k:v for k,v in b.items()if k!='.reginfo'}:raise ValueError('Threshold effect compact pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Threshold effect live owner differs')
    if function_blob(new_owner)!=(fitted,BINDINGS):raise ValueError('Threshold effect padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Threshold effect padded sections changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Threshold effect live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Threshold effect function/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Threshold effect protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=68,raw_frame=72,frame=80,guards=9,bindings=3,raw_neighbors=raw_neighbors,neighbors=neighbors,
       qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,registration=census(root),guard_sha256=sha(new_guards))
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
