"""Object initializer: nine FPR fields and the complete literal linked image."""
import csv,hashlib,io,json,re,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_object_defaults_candidates as candidate
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
SIZE,BUILD=272,candidate.BUILD
OBJECT='conker/build/src/game_83300.c.o'
ASM='conker/asm/nonmatchings/game_83300/func_1505F188.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='3a9e879e9e2a27a2d73b27b77f012deba9017904b101b9487d4ca7b0c4a57d83'
GUARD_SHA='b784d5e46c4114cc4a67864835237bd0f85e4c49c451709ada41df8289314ee4'
RAW_SHA='fca1d82f9f69139b5f3a2b741a5b1e3f070f502dc730995ec69cff72a52a863a'
TRUTH_SHA='f40509518bd60c31bd037ae4b24a8f20b4869676ea8541108c6b5f0d10134c65'
BINDINGS={48:[('R_MIPS_HI16','D_8009962C')],52:[('R_MIPS_LO16','D_8009962C')],72:[('R_MIPS_HI16','D_80099630')],92:[('R_MIPS_LO16','D_80099630')],160:[('R_MIPS_26','func_150ADA20')],188:[('R_MIPS_26','func_150615DC')]}
FPR_ROLES={12:0,0:2,2:4}
GUARD_OFFSETS=(44,52,76,80,84,88,92,152,156)
SYMBOL_GROUPS=((0x2C1A6C,('D_8009962C','D_8009927C','D_800A357C','D_8009EC7C','D_800E0A8C'),(1,2,3,4,0)),
 (0x2DED4C,('D_80099630','D_80099280','D_800A71C4','D_800A3580','D_80082F28'),(1,2,3,4,0)))
sha=lambda b:hashlib.sha256(b).hexdigest()

def freeze(root,out):
    path=out/'input-sha256.json'
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze object defaults at its predecessor first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt','conker/src/game_DAE50.c','conker/build/src/game_DAE50.c.o','conker/asm/nonmatchings/game_DAE50/func_150ADA20.s','conker/src/game_981E0.c','conker/build/src/game_981E0.c.o','conker/src/game/generated_AEB40.c','conker/build/src/game/generated_AEB40.c.o','conker/asm/AEB40.s','conker/asm/nonmatchings/game_981E0/func_15072420.s']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/asm/nonmatchings/game_83300').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Defaults frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Defaults protected input changed: '+name)
    return len(values)

def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}

def rename_fprs(raw):
    result=bytearray(raw);changed=[]
    for at in range(0,len(raw),4):
        w=struct.unpack_from('>I',raw,at)[0];op=w>>26
        if op in(49,57):shift=16
        elif op==17:
            if w>>21&31!=4:raise ValueError('Defaults unexpected COP1 instruction')
            shift=11
        else:continue
        role=w>>shift&31
        if role not in FPR_ROLES:raise ValueError('Defaults floating register changed')
        struct.pack_into('>I',result,at,(w&~(31<<shift))|(FPR_ROLES[role]<<shift));changed.append(at)
    if tuple(changed)!=GUARD_OFFSETS:raise ValueError('Defaults floating register lifetime changed')
    return bytes(result)

def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Defaults raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Defaults original changed')
    expected=bytearray(truth)
    for at,rows in bindings.items():
        w=struct.unpack_from('>I',expected,at)[0];struct.pack_into('>I',expected,at,w&(0xFC000000 if rows[0][0]=='R_MIPS_26'else 0xFFFF0000))
    result=rename_fprs(raw)
    if result!=expected:raise ValueError('Defaults FPR-only mapping differs')
    return result

def guard_manifest(before,raw):
    if sha(before)!=GUARD_SHA or sha(raw)!=RAW_SHA:raise ValueError('Defaults guard inputs changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(r['function']==FUNCTION for r in reader):raise ValueError('Defaults already guarded')
    fitted=rename_fprs(raw);rows=[]
    for at in GUARD_OFFSETS:
        bindings=BINDINGS.get(at,[]);relocs=';'.join(k+':'+n for k,n in bindings)or'-'
        rows.append(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(struct.unpack_from('>I',raw,at)[0]),replacement=hex(struct.unpack_from('>I',fitted,at)[0]),expected_relocations=relocs,replacement_relocations=relocs,note='Normalize initializer unit/base/gravity floating register allocation',insert_after='',insert_after_relocations='',omit='false'))
    result=io.StringIO(newline='');csv.DictWriter(result,fields,lineterminator='\r\n').writerows(rows);return before+result.getvalue().encode()

def assemble_owner(root,out,obj,manifest,label):
    p=out/label;p.mkdir(parents=True,exist_ok=True);guards=p/'patches.csv';guards.write_bytes(manifest);asm=p/'owner.s';result=p/'owner.o'
    asm.write_text(emit_padded_assembly(obj,root/'conker/retail_layout.us.txt',FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(result),str(asm)],capture_output=True,check=True)
    return result

def census(root):
    rom=(root/ROM_IMAGE).read_bytes();calls=[];pointers=[]
    for at in range(0,len(rom)-3,4):
        w=struct.unpack_from('>I',rom,at)[0]
        if w==ENTRY:pointers.append(at)
        if w>>26 in(2,3)and(w&0x3FFFFFF)*4==ENTRY&0xFFFFFFF:
            if w>>26!=3:raise ValueError('Defaults tail call changed')
            calls.append(at)
    if pointers or calls!=[0x8A69C,0x8C344,0x8E67C,0x9F958,0xAFF84,0xAFFDC]:raise ValueError('Defaults caller census changed: '+repr((calls,pointers)))
    return calls

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Defaults literal inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,16):raise ValueError('Defaults predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    target_only=bytes(expected);symbols={n:(p,f,s)for p,n,f,s in symbol_rows(before)}
    for start,names,order in SYMBOL_GROUPS:
        group=[symbols[n]for n in names];strings=b''.join((n+'\0').encode()for n in names)
        base_name=group[0][1][0];base_string=group[0][2];cursor=0
        for i,(name,(off,fields,string))in enumerate(zip(names,group)):
            if off!=start+16*i or string!=base_string+cursor or fields[0]!=base_name+cursor:raise ValueError('Defaults symbol serialization baseline changed')
            cursor+=len(name)+1
        if before[base_string:base_string+len(strings)]!=strings:raise ValueError('Defaults original string block changed')
        text=b''
        for i,j in enumerate(order):
            struct.pack_into('>IIIBBH',expected,start+16*i,base_name+len(text),*group[j][1][1:]);text+=(names[j]+'\0').encode()
        expected[base_string:base_string+len(strings)]=text
    if sum(a!=b for a,b in zip(target_only,expected))!=66:raise ValueError('Defaults named serialization extent changed')
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Defaults literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Defaults named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text());old_guards=(out/'frozen'/GUARDS).read_bytes()
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    clean=lambda t:re.sub(r'build/[^\n]+?\.c, line \d+:','<owner>:',t)
    if re.findall(r'Warning (\d+)',od)!=['712']*8 or clean(od)!=clean(nd):raise ValueError('Defaults owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=function_blob(new);fitted=normalized(raw,bindings,truth);new_guards=guard_manifest(old_guards,raw)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial defaults guards installed')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Defaults compact pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Defaults live owner differs')
    if function_blob(new_owner)!=(fitted,bindings):raise ValueError('Defaults padded body/bindings differ')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Defaults padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'predecessor-image');ne=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Defaults live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>68I',truth)):raise ValueError('Defaults function/address closure failed')
    rom=(root/ROM_IMAGE).read_bytes()
    for name,start,off,n in(('func_1505D1C4',0x1505D1C4,0x8A674,61),('func_150615DC',0x150615DC,0x8EA8C,12),('func_150ADA20',0x150ADA20,0xDAED0,18)):
        if b[name]!=list(struct.unpack_from('>%dI'%n,rom,off)):raise ValueError('Defaults caller/helper no longer exact: '+name)
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Defaults protected data changed')
    table=elf_slot_offset(after,0x8009962C,8)
    if after[table:table+8]!=rom[0x23E0EC:0x23E0F4]:raise ValueError('Defaults constants changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=68,frame=24,guards=9,bindings=len(BINDINGS),raw_neighbors=raw_neighbors,neighbors=neighbors,compact_and_padded_pools_unchanged=True,unchanged_warning_712=8,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,named_serialization_bytes=66,closed_symbol_groups=2,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=census(root),constant_words=list(struct.unpack('>2I',after[table:table+8])),caller_words=61,component_words=12,RNG_words=18)
    (out/'proposed-owner.c').write_text(ns);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
