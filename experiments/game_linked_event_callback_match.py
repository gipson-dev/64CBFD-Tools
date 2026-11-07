"""Derive the closed shared-load/delay-slot split, then audit the complete ELF.

The compiler emits 71 real words. The retail 72-word form executes the same
store followed by one flags load on the second-key match path. Moving that
existing load into the branch delay slot leaves the shared load for all other
paths. No retail instruction is used as an input to the derivation.
"""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_linked_event_callback_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
SIZE=288
OBJECT='conker/build/src/game/generated_15F680.c.o'
ASM='conker/asm/15F680.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='f045bea0e577eb05309cbb9b1d5d41dd750e0f0f0e01c479a94deb9d0888d13b'
GUARD_SHA='10fbf973fdc0c43c675645f651ed61592f4d5e6d8c5613080fecd3a989411af8'
RAW_SHA='99821cf867661beda49a63675411344abec62e8d932f877796425ac4df1029ba'
BINDINGS={0x3C:[('R_MIPS_26','func_151B9660')],0xD8:[('R_MIPS_HI16','D_800899F8')],0xF8:[('R_MIPS_LO16','D_800899F8')]}

def derive(raw,bindings):
    if sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Unqualified complete linked event body')
    words=list(struct.unpack('>71I',raw));oldbranch=0x98;oldload=0xD0
    branch,store,load=(words[p//4]for p in(oldbranch,oldbranch+4,oldload))
    target=oldbranch+4+4*(((branch&65535)^32768)-32768)
    if branch>>16!=0x1000 or target!=oldload or store!=0xA0890080 or load!=0x8C8D0060:raise ValueError('Linked event store/load edge changed')
    def moved(pc):return pc+4 if pc>=0xA0 else pc
    result=[]
    for i,w in enumerate(words):
        pc=4*i
        if pc==oldbranch:
            result.append(store);continue
        if pc==oldbranch+4:
            newpc=pc;newtarget=moved(oldload)+4
            result.extend(((branch&0xFFFF0000)|((newtarget-newpc-4)//4&65535),load));continue
        if w>>26 in(4,5,6,7,20,21,22,23):
            dest=pc+4+4*(((w&65535)^32768)-32768)
            if not 0<=dest<len(raw):raise ValueError('Nonlocal linked event branch')
            w=(w&0xFFFF0000)|((moved(dest)-moved(pc)-4)//4&65535)
        if pc==0x88:
            rs,rt=w>>21&31,w>>16&31
            if w>>26!=21 or {rs,rt}!={3,8}:raise ValueError('Only the closed BNEL operands commute')
            w=(w&~0x03FF0000)|(rt<<21)|(rs<<16)
        result.append(w)
    return struct.pack('>72I',*result),{moved(at):list(v)for at,v in bindings.items()}

def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Linked event predecessor guards changed')
    normalized,_=derive(raw,bindings);a=struct.unpack('>71I',raw);b=struct.unpack('>72I',normalized)
    rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Linked event is already guarded')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');offsets=[]
    for i,w in enumerate(a):
        at=4*i;replacement=b[i+(at>=0xA0)];insert=b[0xA0//4]if at==0x9C else None
        if w==replacement and insert is None:continue
        if at in bindings:raise ValueError('The edge split must not replace a symbol binding')
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected='0x%08X'%w,replacement='0x%08X'%replacement,expected_relocations='-',replacement_relocations='-',note='Split the shared flags-load edge into its retail branch delay slot; preserve access order and local branch targets',insert_after=''if insert is None else'0x%08X'%insert,insert_after_relocations='',omit='false'));offsets.append(at)
    if offsets!=[0x58,0x7C,0x88,0x98,0x9C]:raise ValueError('Linked event guard derivation changed')
    tail=stream.getvalue().encode();return before+(tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail)

def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Linked event discovery changed: '+n)
        names=set(initial)|{'conker/asm/data/22FF40.rodata.s','conker/src/game_1944C0.c','conker/src/game/generated_1E6260.c','conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Linked event protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Linked event include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Linked event predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Linked event predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    # The new table reference swaps two existing absolute symbols in one GNU
    # hash bucket. Reconstruct both serialized records and strings from BEFORE;
    # retain every named definition and byte, with no comparison exclusions.
    named={n:(p,f,loc)for p,n,f,loc in symbol_rows(before)}
    names=('D_800899F8','D_8008A3F8');group=[named[n]for n in names]
    for i,(n,(pos,f,loc))in enumerate(zip(names,group)):
        if f[1:]!=(int(n[2:],16),0,16,0,65521):raise ValueError('Linked event absolute definition changed')
        if pos!=group[0][0]+16*i or loc!=group[0][2]+11*i or before[loc:loc+11]!=n.encode()+b'\0':raise ValueError('Linked event symbol bucket changed')
    for dest,origin,n in zip(group,reversed(group),reversed(names)):
        expected[dest[0]:dest[0]+16]=before[origin[0]:origin[0]+16]
        struct.pack_into('>I',expected,dest[0],dest[1][0]);expected[dest[2]:dest[2]+11]=n.encode()+b'\0'
    if bytes(expected)!=after:raise ValueError('Linked event literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Linked event definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    diagnostics=paired_diagnostics(od,nd,FILENAME)
    if(diagnostics['before'],diagnostics['after'])!=(2,2):raise ValueError('Linked event diagnostic baseline changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,));a,b=alloc_pools(old),alloc_pools(new)
    if a!=b:raise ValueError('Linked event raw loaded pool/register metadata changed')
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized,moved=derive(raw,bindings)
    symbols={n:int(n.split('_')[1],16)for values in bindings.values()for _,n in values}
    if bound_blob(normalized,moved,symbols)!=list(struct.unpack('>72I',truth)):raise ValueError('Linked event normalized body differs')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Linked event source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live linked event owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Padded linked event pools/register metadata changed')
    if function_blob(no)!=(normalized,moved):raise ValueError('Linked event actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'event-predecessor-image');ne=harness.link_image(root,out,no,'event-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Linked event live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Linked event complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Linked event protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,raw_words=71,words=72,frame=48,slot_words=72,alignment_words=0,guards=5,inserted_words=1,bindings=3,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_and_padded_loaded_pools_register_metadata_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
