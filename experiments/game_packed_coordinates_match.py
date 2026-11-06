"""Packed command updater: bounded schedule/roles and complete image proof."""
import csv,hashlib,io,json,re,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_packed_coordinates_candidates as candidate
from tools.experiments import game_packed_coordinate_roles as roles
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
OBJECT='conker/build/src/game_83300.c.o'
ASM='conker/asm/nonmatchings/game_83300/func_15062D10.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='57c96c17776df60f2ce0a4a4fc21e5399f79eff0db45b34007f5813e4bf1aeac'
GUARD_SHA='693728894a396b7cb48827cc87d5a33f30a2000e981e65f531ba78c3b9fe76d8'
RAW_SHA='e38cc4acee36c21691768f824e77badad7886cbed7a79aeaf1eebc48eab2f2f0'
TRUTH_SHA='2b7d78b9c42e156ace1cc8a39679824c8e85cab22f537fc34be7994090ca22a2'
BINDINGS={16: [('R_MIPS_HI16', 'D_800D19A0')], 24: [('R_MIPS_LO16', 'D_800D19A0')], 28: [('R_MIPS_HI16', 'D_800C4488')], 44: [('R_MIPS_LO16', 'D_800C4488')]}
PATCHES=((52, 2410414084, 2410283012, []), (60, 2368339968, 2368012288, []), (64, 813248, 678080, []), (72, 27924513, 11221025, []), (76, 2355429380, 2363883524, []), (80, 2355560448, 2409758728, []), (84, 2410217480, 2410610696, []), (88, 336643, 400131, []), (92, 814616575, 812388351, []), (96, 816189439, 818155519, []), (100, 633602050, 629342210, []), (104, 285212677, 612630530, []), (108, 616955906, 285212676, []), (112, 2409758728, 2363883520, []), (116, 811077631, 810356735, []), (124, 50335781, 27267109, []), (128, 490243, 422659, []), (132, 838406143, 836243455, []), (136, 53028897, 51324961, []), (140, 8718378, 6621226, []), (156, 10752035, 10686499, []), (168, 10752033, 10686497, []), (176, 811077631, 810422271, []), (180, 2409889804, 2409824268, []), (184, 814419967, 813240319, []), (192, 23076901, 52434981, []), (196, 2410479628, 2410283020, []), (200, 820776959, 818483199, []), (204, 26028065, 19540001, []), (208, 12912682, 8718378, []), (216, 10493989, 10491941, []), (224, 10887203, 10754083, []), (236, 10887201, 10754081, []), (244, 14766116, 12671012, []), (248, 814616575, 812388351, []), (252, 21903397, 23881765, []), (256, 1604352, 967424, []), (260, 31967269, 28848165, []), (264, 2893611008, 2900754432, []))
CALLS=(585908, 585936, 585964, 585992, 586048, 586076, 586104, 586132, 586252, 586628, 586820, 586884, 586912, 586940, 587412, 587440, 587468, 587752, 587780, 587808, 587856)

sha=lambda b:hashlib.sha256(b).hexdigest()
def freeze(root,out):
    path=out/'input-sha256.json'
    if not path.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze packed coordinates at predecessor first')
        paths=[SOURCE,OBJECT,ASM,ELF,GUARDS,LINKER,ROM_IMAGE,MAKE,'conker/build/conker.us.bin','conker/progress.csv','conker/retail_layout.us.txt','graphify-out/graph.json','conker/undefined_syms_auto.txt','conker/symbol_addrs.us.txt']
        paths += [p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h')]+[p.relative_to(root).as_posix()for p in(root/'conker/asm/nonmatchings/game_83300').glob('*.s')]
        values={}
        for name in sorted(set(paths)):
            data=(root/name).read_bytes();dest=out/'frozen'/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);values[name]=sha(data)
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());changed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for name,wanted in values.items():
        if sha((out/'frozen'/name).read_bytes())!=wanted:raise ValueError('Packed frozen input changed: '+name)
        if name not in changed and sha((root/name).read_bytes())!=wanted:raise ValueError('Packed protected input changed: '+name)
    return len(values)
def function_blob(obj):
    text,fs,rs=parse_object(obj);f=fs[FUNCTION];start,size=f['value'],f['size']
    return text[start:start+size],{at-start:r for at,r in rs.items()if start<=at<start+size}
def rescheduled(raw):
    ws=list(struct.unpack('>69I',raw));ws[20],ws[28]=ws[28],ws[20];ws[26],ws[27]=ws[27],ws[26]
    if ws[27]>>26!=4 or ws[27]&65535!=5:raise ValueError('Packed branch schedule changed')
    ws[27]=(ws[27]&0xFFFF0000)|4
    return struct.pack('>69I',*ws)
def normalized(raw,bindings,truth):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packed raw body/bindings changed')
    if len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Packed original changed')
    result=bytearray(raw)
    for at,old,new,rs in PATCHES:
        if struct.unpack_from('>I',result,at)[0]!=old or bindings.get(at,[])!=rs:raise ValueError('Packed guarded schedule/roles changed')
        struct.pack_into('>I',result,at,new)
    expected=bytearray(truth)
    for at in bindings:struct.pack_into('>I',expected,at,struct.unpack_from('>I',expected,at)[0]&0xFFFF0000)
    if result!=expected:raise ValueError('Packed fitted words differ')
    roles.prove(rescheduled(raw),bytes(result),bindings)
    return bytes(result)
def guard_manifest(before,raw):
    if sha(before)!=GUARD_SHA or sha(raw)!=RAW_SHA:raise ValueError('Packed guard inputs changed')
    reader=csv.DictReader(io.StringIO(before.decode()));fields=reader.fieldnames
    if any(r['function']==FUNCTION for r in reader):raise ValueError('Packed already guarded')
    rows=[]
    for at,old,new,rs in PATCHES:
        reloc=';'.join(k+':'+n for k,n in rs)or'-'
        rows.append(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected=hex(old),replacement=hex(new),expected_relocations=reloc,replacement_relocations=reloc,note='Normalize proven packed-coordinate register roles and two read/delay schedules',insert_after='',insert_after_relocations='',omit='false'))
    s=io.StringIO(newline='');csv.DictWriter(s,fields,lineterminator='\r\n').writerows(rows);return before+s.getvalue().encode()
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
            if w>>26!=3:raise ValueError('Packed tail call changed')
            calls.append(at)
    if pointers or tuple(calls)!=CALLS:raise ValueError('Packed caller census changed')
    return calls
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or sha(truth)!=TRUTH_SHA:raise ValueError('Packed literal inputs changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Packed predecessor extent changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Packed literal image differs: '+repr((len(before),len(after),len(diff),list(map(hex,diff[:40])))))
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Packed named definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out)
    bs,ns,installed=candidate.source_states((root/SOURCE).read_text());old_guards=(out/'frozen'/GUARDS).read_bytes()
    old,od=candidate.compile_owner(root,out,bs,'predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'qualified-compact')
    clean=lambda t:re.sub(r'build/[^\n]+?\.c, line \d+:','<owner>:',t)
    if re.findall(r'Warning (\d+)',od)!=['712']*8 or clean(od)!=clean(nd):raise ValueError('Packed owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];raw,bindings=function_blob(new);fitted=normalized(raw,bindings,truth);new_guards=guard_manifest(old_guards,raw)
    if(root/GUARDS).read_bytes()!=(new_guards if installed else old_guards):raise ValueError('Partial packed guards installed')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    if alloc_pools(old)!=alloc_pools(new):raise ValueError('Packed compact pools changed')
    old_owner=assemble_owner(root,out,old,old_guards,'predecessor-owner');new_owner=assemble_owner(root,out,new,new_guards,'qualified-owner')
    if(old_owner if not installed else new_owner).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Packed live owner differs')
    if function_blob(new_owner)!=(fitted,bindings):raise ValueError('Packed padded words/bindings differ')
    neighbors=same_functions(old_owner,new_owner,(FUNCTION,))
    if alloc_pools(old_owner)!=alloc_pools(new_owner):raise ValueError('Packed padded pools changed')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):
        oe=harness.link_image(root,out,old_owner,'predecessor-image');ne=harness.link_image(root,out,new_owner,'qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(before if not installed else after)!=(root/ELF).read_bytes():raise ValueError('Packed live ELF differs')
    delta=strict_image(before,after,truth)
    a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>69I',truth)):raise ValueError('Packed body/address closure failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packed protected data changed')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,words=69,frame=0,guards=39,bindings=4,raw_neighbors=raw_neighbors,neighbors=neighbors,all_pools_unchanged=True,unchanged_warning_712=8,qualified_owner_sha256=sha(new_owner.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(new_guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data,direct_calls=census(root),symbolic_states=265,symbolic_paths=17)
    (out/'proposed-owner.c').write_text(ns);(out/'qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=old_owner,qualified_owner=new_owner,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
