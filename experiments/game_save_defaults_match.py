"""Two opening-address guards, original switch table, root owner and full image."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_save_defaults_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_c_object import emit_padded_assembly
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS=candidate.ENTRY,candidate.ROM,candidate.WORDS
SIZE,BUILD=276,candidate.BUILD
OBJECT='conker/build/src/game_33990.c.o'
ASM,ELF,GUARDS,LINKER='conker/asm/nonmatchings/game_33990/func_15007168.s','conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
RAW_SHA='422469e5692b36a2a789d3cdc3755ca9d1b73bfe578ca365185b9bb9bbe36b83'
TRUTH_SHA='78e4ccbc59d52731909318a8fbb8b5c18c592e021910e431d37bdb47eb94f354'
BASELINE_SHA='acf4fa64d83e59624bf21d9f9da35e85d2f32c78b391e8cf873f5ef697223e17'
GUARD_SHA='dbf863c776f06735c271a02c91930c84fd5ce9cf064086653a32d6fb19d24f29'
TABLE,TABLE_ROM=0x80095A00,0x23A4C0
TARGET_OFFSETS=(156,172,172,244,244,204,244,188,232,232)
RODATA_SYMBOL='jtbl_80095A00_game'
BINDINGS={0:[('R_MIPS_HI16','D_800BE358')],8:[('R_MIPS_LO16','D_800BE358')],4:[('R_MIPS_HI16','D_800BE2F0')],12:[('R_MIPS_LO16','D_800BE2F0')],32:[('R_MIPS_HI16','D_80082BBC')],36:[('R_MIPS_LO16','D_80082BBC')],136:[('R_MIPS_HI16','.rodata')],144:[('R_MIPS_LO16','.rodata')]}
PATCHES=((0,0x3C020000,0x3C030000,'D_800BE358','D_800BE2F0'),(4,0x3C030000,0x3C020000,'D_800BE2F0','D_800BE358'))
MAKE_RULE='$(BUILD_DIR)/$(SRC_DIR)/game_33990.c.o: RETAIL_RODATA_SYMBOL := jtbl_80095A00_game\n'
sha=lambda b:hashlib.sha256(b).hexdigest()
def make_states(live):
    if live.count(MAKE_RULE)==1:return live.replace(MAKE_RULE,''),live,True
    anchor='$(BUILD_DIR)/$(SRC_DIR)/game/generated_20AE20.c.o: RETAIL_RODATA_SYMBOL := jtbl_800AB9BC\n'
    if live.count(anchor)!=1:raise ValueError('Save defaults rodata profile anchor changed')
    return live,live.replace(anchor,anchor+MAKE_RULE,1),False
def census(root):
    rom=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        w=struct.unpack_from('>I',rom,at)[0]
        if w==ENTRY:pointers.append(at)
        if w>>26 in(2,3)and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if w>>26!=3:raise ValueError('Save defaults tail jump changed')
            calls.append(at)
    if pointers or calls!=[0x347F8,0x49AF0]:raise ValueError('Save defaults caller census changed')
    return calls
def freeze(root,out):
    manifest=out/'input-sha256.json'
    if not manifest.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze save defaults at predecessor ELF first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game/generated_48FD0.c','conker/asm/48FD0.s','conker/build/src/game/generated_48FD0.c.o']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/asm/nonmatchings/game_33990').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        manifest.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(manifest.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,MAKE,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Save defaults frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Save defaults protected input changed: '+name)
    return len(values)
def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Save defaults raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Save defaults original body changed')
    result=bytearray(raw);expected=bytearray(truth)
    for at,a,b,old,new in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=a:raise ValueError('Save defaults scheduling guard changed')
        struct.pack_into('>I',result,at,b)
    for at,rows in bindings.items():struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if result!=expected:raise ValueError('Save defaults normalized words differ')
    return bytes(result)
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Save defaults inherited guards changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(row['function']==FUNCTION for row in reader):raise ValueError('Save defaults already guarded')
    rows=[dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(a),replacement=hex(b),expected_relocations='R_MIPS_HI16:'+old,replacement_relocations='R_MIPS_HI16:'+new,note='Normalize independent save-default address load scheduling',insert_after='',insert_after_relocations='',omit='false')for at,a,b,old,new in PATCHES]
    out=io.StringIO(newline='');csv.DictWriter(out,fields,lineterminator='\r\n').writerows(rows);return before+out.getvalue().encode()
def assemble_owner(root,out,obj,manifest,label,rodata=True):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/(FILENAME+'.c.s');result=p/(FILENAME+'.c.o')
    asm.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,rodata_symbol=RODATA_SYMBOL if rodata else None,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Save defaults strict inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Save defaults predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diffs=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Save defaults literal image differs: '+repr((len(before),len(after),len(diffs),list(map(hex,diffs[:35])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Save defaults named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text());bm,nm,mi=make_states((root/MAKE).read_text())
    if mi!=installed:raise ValueError('Partial save defaults rodata profile installation')
    old_guards=(out/'frozen'/GUARDS).read_bytes();new_guards=guard_manifest(old_guards)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial save defaults guard installation')
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    if od or nd:raise ValueError('Save defaults compiler diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];fitted=normalized(*function_blob(new),truth);raw_neighbors=same_functions(old,new,(FUNCTION,))
    a,b=alloc_pools(old),alloc_pools(new);(out/'compact-pools.json').write_text(json.dumps({k:repr((a.get(k),b.get(k)))for k in a.keys()|b.keys()if a.get(k)!=b.get(k)},indent=2)+'\n')
    expected_pool=(1,2,0,16,bytes(48),tuple((i*4,2,('text',FUNCTION,v))for i,v in enumerate(TARGET_OFFSETS)))
    if '.rodata'in a or b.get('.rodata')!=expected_pool:raise ValueError('Save defaults compiler switch table changed')
    if a!={k:v for k,v in b.items()if k!='.rodata'}:raise ValueError('Save defaults unrelated compact pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner',False);new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Save defaults live owner differs')
    expected_bindings={at:rows[:]for at,rows in BINDINGS.items()}
    for at,a,b,oldname,newname in PATCHES:expected_bindings[at]=[('R_MIPS_HI16',newname)]
    for at in(136,144):expected_bindings[at]=[(BINDINGS[at][0][0],RODATA_SYMBOL)]
    if function_blob(new_owner)!=(fitted,expected_bindings):raise ValueError('Save defaults padded body/bindings differ')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Save defaults padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'predecessor-image');ne=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Save defaults live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>69I',truth)):raise ValueError('Save defaults function/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Save defaults protected data changed')
    table=after[elf_slot_offset(after,TABLE,40):elf_slot_offset(after,TABLE,40)+40]
    if table!=(root/ROM_IMAGE).read_bytes()[TABLE_ROM:TABLE_ROM+40]or struct.unpack('>10I',table)!=tuple(ENTRY+i for i in TARGET_OFFSETS):raise ValueError('Save defaults original table changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=69,frame=0,guards=2,bindings=8,raw_neighbors=raw_neighbors,neighbors=neighbors,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=census(root),rodata_symbol=RODATA_SYMBOL)
    (out/'proposed-owner.c').write_text(ns);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
