"""Closed queue draw schedule, typed helper dependency and complete ELF audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_position_queue_drain_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments import game_actor_height_effect_match as metadata
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_record_address_relocator_match import dependent_sections
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
OBJECT='conker/build/src/game/generated_1A89B0.c.o'
ASM='conker/asm/1A89B0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='ce3fbf40414bdeaebc52658f1f2d421439c7f5e0a8cb33f98240953b42ee01a6'
GUARD_SHA='9892912f5423eb5e518da147fb0bf7e358de56260cb3d59e6b2e6d1bcff0c4ab'
RAW_SHA='77feee82531376ab94ae5f8acce121bf299b5e028176011a65ff93a2f8e722a5'
METADATA_GROUPS=()
BINDINGS={12:[('R_MIPS_HI16','D_800DDD1C')],16:[('R_MIPS_LO16','D_800DDD1C')],48:[('R_MIPS_HI16','D_800DDD58')],52:[('R_MIPS_LO16','D_800DDD58')],88:[('R_MIPS_HI16','D_8008CEB0')],92:[('R_MIPS_LO16','D_8008CEB0')],100:[('R_MIPS_HI16','D_800DDD28')],104:[('R_MIPS_LO16','D_800DDD28')],216:[('R_MIPS_26','func_1517D074')],244:[('R_MIPS_HI16','D_800DDD58')],252:[('R_MIPS_LO16','D_800DDD58')]}
HELPER,HELPER_ENTRY='func_1517D074',0x1517D074
HELPER_BEFORE=struct.pack('>3I',0x00001025,0x03E00008,0)
HELPER_AFTER=struct.pack('>7I',0xAFA40000,0xAFA50004,0xAFA60008,0xAFA7000C,0x00001025,0x03E00008,0)
ORDER=(0xC0,0x8C,0xA0,0xC8,0xB0,0xA4,0xA8,0xB4,0xB8,0x90,0x94,0x98,0xC4,0xCC,0xD0,0xD4,0xDC,0x9C,0xAC,0xD8,0xBC)

def registers(w):
    op,fn,rs,rt,rd=w>>26,w&63,w>>21&31,w>>16&31,w>>11&31
    r=lambda x:set()if x==0 else{('r',x)}
    if op in(0x24,0x21,0x25):return r(rs),r(rt)
    if op==0x31:return r(rs),{('f',rt)}
    if op==0x2B:return r(rs)|r(rt),set()
    if op==0x39:return r(rs)|{('f',rt)},set()
    if op==9:return r(rs),r(rt)
    if op==3:return set(),{('r',31)}
    if op==0:
        if fn==0:return r(rt),r(rd)
        if fn in(0x21,0x25):return r(rs)|r(rt),r(rd)
        if fn==0x19:return r(rs)|r(rt),{('hi',0),('lo',0)}
        if fn==0x12:return{('lo',0)},r(rd)
    raise ValueError('Foreign instruction in argument schedule')

def schedule_dependencies(words):
    origin=list(range(0x8C,0xE0,4))
    if sorted(ORDER)!=origin or ORDER[0xD8//4-0x8C//4]!=0xD8:raise ValueError('Argument schedule or JAL moved')
    positions={p:i for i,p in enumerate(ORDER)};edges=0
    for i,a in enumerate(origin):
        ar,aw=registers(words[a//4])
        for b in origin[i+1:]:
            br,bw=registers(words[b//4])
            if aw&(br|bw)or ar&bw:
                if positions[a]>=positions[b]:raise ValueError('Argument register/HI/LO dependency crossed')
                edges+=1
    return edges

def derive(raw,bindings):
    if len(raw)!=SIZE or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Complete queue body/bindings changed')
    words=list(struct.unpack('>72I',raw));schedule_dependencies(words);changed=words[:];changed[0x8C//4:0xE0//4]=[words[p//4]for p in ORDER]
    if Counter(changed)!=Counter(words):raise ValueError('Queue schedule introduced an instruction')
    return struct.pack('>72I',*changed),dict(bindings)

def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Queue predecessor guards changed')
    normalized,_=derive(raw,bindings);a=struct.unpack('>72I',raw);b=struct.unpack('>72I',normalized);rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Queue is already guarded')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');count=0
    for i,(w,v)in enumerate(zip(a,b)):
        if w==v:continue
        at=4*i
        if at in bindings:raise ValueError('Argument schedule must preserve all bindings')
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(at),expected='0x%08X'%w,replacement='0x%08X'%v,expected_relocations='-',replacement_relocations='-',note='Reschedule the closed queue draw argument block; preserve register and HI/LO dependencies and all complete call arguments',insert_after='',insert_after_relocations='',omit='false'));count+=1
    if count!=20:raise ValueError('Queue guard count changed')
    tail=stream.getvalue().encode();return before+(tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail)

def function_blob(obj,name=FUNCTION):
    t,fs,rs=parse_object(obj);f=fs[name];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def dependent_stub(before,after):
    if function_blob(before,HELPER)!=(HELPER_BEFORE,{})or function_blob(after,HELPER)!=(HELPER_AFTER,{}):raise ValueError('Typed helper stub changed beyond four argument homes')
    return dict(function=HELPER,before_words=3,after_words=7,argument_home_stores=4,relocations=0,additional_matching_credit=0)

def audit_pools(before,after):
    a,b=alloc_pools(before),alloc_pools(after);changed=[]
    if a!=b:
        x,y=a['.reginfo'],b['.reginfo'];raw=bytearray(y[4])
        if struct.unpack_from('>I',x[4],8)[0]!=0x1000 or struct.unpack_from('>I',raw,8)[0]!=0x1010:raise ValueError('Foreign queue FPR mask change')
        struct.pack_into('>I',raw,8,0x1000);b['.reginfo']=(*y[:4],bytes(raw),*y[5:]);changed.append('F4 mask 0x1000 to 0x1010')
        if a!=b:raise ValueError('Queue allocatable pools changed beyond the F4 mask')
    x,y=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if x is not None or y is not None:
        if x is None or y is None or x[0][:4]+x[0][5:]!=y[0][:4]+y[0][5:]:raise ValueError('Queue options section shape changed')
        raw=bytearray(y[1])
        if x[1]!=y[1]:
            if struct.unpack_from('>I',x[1],16)[0]!=0x1000 or struct.unpack_from('>I',raw,16)[0]!=0x1010:raise ValueError('Queue options FPR mask changed')
            struct.pack_into('>I',raw,16,0x1000)
        if x[1]!=bytes(raw):raise ValueError('Queue options changed beyond F4')
    return changed


def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Queue drain discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Queue drain protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Queue drain include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Queue predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    helper_at=elf_slot_offset(before,HELPER_ENTRY,len(HELPER_AFTER))
    if before[helper_at:helper_at+len(HELPER_BEFORE)]!=HELPER_BEFORE or before[helper_at+len(HELPER_BEFORE):helper_at+len(HELPER_AFTER)]!=bytes(16):raise ValueError('Queue predecessor helper footprint changed')
    expected[helper_at:helper_at+len(HELPER_AFTER)]=HELPER_AFTER
    sizes={FUNCTION:SIZE,HELPER:len(HELPER_AFTER)}
    for name,size in sizes.items():
        rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==name]
        if len(rows)!=1 or rows[0][1][1:3]!=((ENTRY if name==FUNCTION else HELPER_ENTRY),12):raise ValueError('Queue predecessor symbol changed')
        struct.pack_into('>I',expected,rows[0][0]+8,size)
    named={n:p for p,n,f,loc in symbol_rows(before)};groups=tuple((named[names[0]],names,order)for names,order in METADATA_GROUPS)
    with patch.object(metadata,'METADATA_GROUPS',groups):metadata.reorder_metadata(before,expected)
    if bytes(expected)!=after:raise ValueError('Queue literal full image differs')
    wanted=Counter((n,f[1],sizes.get(n,f[2]),*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Queue named definitions changed')
    return sum(a!=b for a,b in zip(before,after))


def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    diagnostics=paired_diagnostics(od,nd,FILENAME)
    if(diagnostics['before'],diagnostics['after'])!=(0,0):raise ValueError('Queue drain diagnostic baseline changed')
    raw_neighbors=same_functions(old,new,(FUNCTION,HELPER));dependency=dependent_stub(old,new);raw_metadata=audit_pools(old,new)
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];normalized,moved=derive(raw,bindings)
    symbols={n:int(n.split('_')[1],16)for values in bindings.values()for _,n in values}
    if bound_blob(normalized,moved,symbols)!=list(struct.unpack('>72I',truth)):raise ValueError('Queue drain normalized body differs')
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Queue drain source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live queue drain owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,HELPER));dependent_stub(oo,no)
    padded_metadata=audit_pools(oo,no)
    if function_blob(no)!=(normalized,moved):raise ValueError('Queue drain actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'queue-predecessor-image');ne=harness.link_image(root,out,no,'queue-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Queue drain live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or set(changed)!={FUNCTION,HELPER}or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Queue drain complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Queue drain protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,raw_words=72,words=72,frame=80,slot_words=72,alignment_words=0,guards=20,inserted_words=0,bindings=11,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_metadata_changes=raw_metadata,padded_metadata_changes=padded_metadata,all_other_pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,dependent_helper=dependency,register_dependency_edges=schedule_dependencies(list(struct.unpack('>72I',raw))),protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
