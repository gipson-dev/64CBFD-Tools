"""Direct live-mode dispatcher, signed countdown, caller and complete image."""
import hashlib,json,struct,subprocess
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_live_mode_dispatch_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.pad_generated_object import parse_object,emit_padded_assembly
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=288,candidate.BUILD
OBJECT='conker/build/src/game/generated_20AE20.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/20AE20.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin';CALLER='conker/src/game_45B80.c';CALLER_OBJECT='conker/build/src/game_45B80.c.o'
RAW_SHA='f3a8c25768375ee91817dd8ed3251295bb22ca379e3a3f9beb8e13331b122d5e'
TRUTH_SHA='34c234ce0c4fa85689d95088b4eae5315bbb7dcfa4dfc33252d376ab474d256c'
BASELINE_SHA='f393cfbd7602e51e735eb052dcb9d8ab3ddd59afda769203479384fa078b003b'
GUARD_SHA='dbf863c776f06735c271a02c91930c84fd5ce9cf064086653a32d6fb19d24f29'
SYMBOL_GROUPS=((0x2BE69C,('D_800E0BDC','D_800A36AC'),(1,0)),
 (0x2C9DFC,('D_800BE930','D_8009CDE8'),(1,0)),(0x2DDD1C,('func_15187978','D_8009E570'),(1,0)))
BINDINGS={}
for name,pairs in{
 'D_800E0B94':((8,20),(100,104),(168,172),(200,204)),
 'D_8003C8E0':((16,24),(264,268)), 'D_800E0BDC':((28,36),),
 'D_8008FE28':((52,56),),'D_800BE930':((64,68),),'D_800E0B9A':((72,76),),
 'D_8008FDEC':((176,188),),'D_800E0A90':((212,220),),'D_800BE9E4':((224,228),),'D_800E0B95':((240,256),)}.items():
    for hi,lo in pairs:BINDINGS[hi]=[('R_MIPS_HI16',name)];BINDINGS[lo]=[('R_MIPS_LO16',name)]
for at,name in((44,'func_15042D78'),(120,'func_151E6964'),(144,'func_151E6964'),(160,'func_151E6964')):BINDINGS[at]=[('R_MIPS_26',name)]
sha=lambda b:hashlib.sha256(b).hexdigest()
def freeze(root,out):
    manifest=out/'input-sha256.json'
    if not manifest.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze live dispatcher at its predecessor ELF first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,CALLER,CALLER_OBJECT,'conker/build/conker.us.bin','conker/Makefile','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json',
          'conker/asm/data/234830.rodata.s','conker/asm/nonmatchings/game_45B80/func_1501878C.s','conker/src/game_70200.c','conker/build/src/game_70200.c.o']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        values={}
        for path in sorted(set(paths)):
            data=(root/path).read_bytes();dest=out/'frozen'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[path]=sha(data)
        manifest.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(manifest.read_text());changed={SOURCE,OBJECT,ELF,CALLER,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for path,wanted in values.items():
        if sha((out/'frozen'/path).read_bytes())!=wanted:raise ValueError('Live dispatcher frozen input changed: '+path)
        if path not in changed and sha((root/path).read_bytes())!=wanted:raise ValueError('Live dispatcher protected live input changed: '+path)
    return len(values)
def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Live dispatcher raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Live dispatcher original changed')
    expected=bytearray(truth)
    for at,rows in bindings.items():
        mask=0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000
        struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&mask)
    if raw!=expected:raise ValueError('Live dispatcher direct body differs')
    return raw
def assemble_owner(root,out,obj,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/ASM,word_patches_path=root/GUARDS,filename=FILENAME,rodata_symbol='jtbl_800AB9BC'))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Live dispatcher strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(off,fields)for off,name,fields,string in symbol_rows(before)if name==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Live dispatcher predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={name:(off,fields,string)for off,name,fields,string in symbol_rows(before)}
    for start,names,order in SYMBOL_GROUPS:
        group=[symbols[name]for name in names];strings=b''.join((name+'\0').encode()for name in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Live dispatcher symbol serialization baseline changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Live dispatcher original string block changed')
        text=b''
        for i,j in enumerate(order):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=71:raise ValueError('Live dispatcher named serialization extent changed')
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Live dispatcher literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:40])))))
    wanted=Counter((name,fields[1],SIZE if name==FUNCTION else fields[2],*fields[3:])for _,name,fields,_ in symbol_rows(before))
    if wanted!=Counter((name,*fields[1:])for _,name,fields,_ in symbol_rows(after)):raise ValueError('Live dispatcher named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def census(root):
    rom=(root/ROM_IMAGE).read_bytes();direct=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        word=struct.unpack_from('>I',rom,at)[0]
        if word==ENTRY:pointers.append(at)
        if word>>26 in(2,3)and(word&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if word>>26!=3:raise ValueError('Live dispatcher unexpected tail jump')
            direct.append(at)
    if direct!=[0x45D40]or pointers:raise ValueError('Live dispatcher caller census changed')
    return dict(direct_calls=1,call_rom=direct[0],call=0x15018890,parent='func_1501878C',return_window=0x15018898)
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    before_source,after_source,installed=candidate.source_states((root/SOURCE).read_text())
    if sha((root/GUARDS).read_bytes())!=GUARD_SHA:raise ValueError('Live dispatcher guards changed')
    old,od=candidate.compile_owner(root,out,before_source,'predecessor-compact');new,nd=candidate.compile_owner(root,out,after_source,'qualified-compact')
    if od or nd:raise ValueError('Unexpected live dispatcher diagnostics')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized(*function_blob(new),truth);raw_neighbors=same_functions(old,new,(FUNCTION,))
    a,b=alloc_pools(old),alloc_pools(new);(out/'compact-pools.json').write_text(json.dumps({k:repr((a.get(k),b.get(k)))for k in a.keys()|b.keys()if a.get(k)!=b.get(k)},indent=2)+'\n')
    if a!=b:raise ValueError('Live dispatcher compact allocatable sections changed')
    old_owner=assemble_owner(root,out,old,'predecessor-owner');new_owner=assemble_owner(root,out,new,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Live dispatcher live owner differs')
    if function_blob(new_owner)!=function_blob(new):raise ValueError('Live dispatcher padded body differs')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Live dispatcher padded sections changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        old_elf=harness.link_image(root,out,old_owner,'predecessor-image');new_elf=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=old_elf.read_bytes(),new_elf.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Live dispatcher live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(old_elf),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(new_elf),'mips-linux-gnu-objdump')
    changed=[name for name in b if a[name]!=b[name]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Live dispatcher function/address closure failed')
    data=audit_layout(new_elf,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Live dispatcher protected data changed')
    cb,ca,ci=candidate.caller_states((root/CALLER).read_text())
    if ci!=installed:raise ValueError('Partial live dispatcher caller installation')
    co,cd=candidate.compile_owner(root,out,cb,'caller-before');cn,ce=candidate.compile_owner(root,out,ca,'caller-after')
    if harness.diagnostics(cd)!=harness.diagnostics(ce):raise ValueError('Live dispatcher caller diagnostics changed')
    caller_count=same_functions(co,cn)
    if alloc_pools(co)!=alloc_pools(cn):raise ValueError('Live dispatcher caller sections changed')
    table=elf_slot_offset(after,0x8008FDEC,48)
    if after[table:table+48]!=(root/ROM_IMAGE).read_bytes()[0x2348AC:0x2348DC]:raise ValueError('Live dispatcher callback table changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=72,frame=32,guards=0,bindings=len(BINDINGS),raw_neighbors=raw_neighbors,neighbors=neighbors,
      qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,
      protected_data=data,registration=census(root),caller_functions_unchanged=caller_count,unchanged_caller_diagnostics=harness.diagnostics(cd),named_serialization_bytes=71,rodata_symbol='jtbl_800AB9BC')
    (out/'proposed-owner.c').write_text(after_source);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=old_elf,qualified_elf=new_elf)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
