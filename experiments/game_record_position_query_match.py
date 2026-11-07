"""Two derived commutative address additions and complete record-query audit."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_record_position_query_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
SIZE=288
OBJECT='conker/build/src/game/generated_CDE80.c.o'
ASM='conker/asm/CDE80.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='e3dc92f6db0e71f6440868e6c095456dba668b22b07458067e6940c4ffc1d13b'
GUARD_SHA='28d7a491d60ac432579e06040e28e21cd7e074d6a47e5c665d1d466ef42670ee'
RAW_SHA='e72c41f73179a2cf46de872ed703edb1342f2db58d1e2fd73a282f26a95c52f8'
BINDINGS={8: [('R_MIPS_HI16', 'D_800D3094')], 28: [('R_MIPS_LO16', 'D_800D3094')], 76: [('R_MIPS_HI16', 'D_800D3098')], 80: [('R_MIPS_LO16', 'D_800D3098')], 192: [('R_MIPS_26', 'func_150A1DA0')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def derive(raw,bindings):
    if sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Unqualified complete record query')
    words=list(struct.unpack('>72I',raw))
    for at,registers in((0xB4,{3,16}),(0xD8,{10,16})):
        w=words[at//4];rs,rt=w>>21&31,w>>16&31
        if w>>26!=0 or w&63!=33 or{rs,rt}!=registers or at in bindings:raise ValueError('Only the two closed ADDU operand pairs may change')
        words[at//4]=(w&~0x03FF0000)|(rt<<21)|(rs<<16)
    return struct.pack('>72I',*words),dict(bindings)

def guard_manifest(before,raw,bindings):
    if sha(before)!=GUARD_SHA:raise ValueError('Record query predecessor guards changed')
    normalized,_=derive(raw,bindings);rows=list(csv.DictReader(io.StringIO(before.decode())))
    if any(r['function']==FUNCTION for r in rows):raise ValueError('Record query is already guarded')
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');count=0
    for i,(a,b)in enumerate(zip(struct.unpack('>72I',raw),struct.unpack('>72I',normalized))):
        if a==b:continue
        writer.writerow(dict(filename=FILENAME,function=FUNCTION,offset=hex(4*i),expected='0x%08X'%a,replacement='0x%08X'%b,expected_relocations='-',replacement_relocations='-',note='Preserve commutative record-query address addition operand order',insert_after='',insert_after_relocations='',omit='false'));count+=1
    if count!=2:raise ValueError('Record query guard derivation changed')
    tail=stream.getvalue().encode();return before+(tail.replace(b'\n',b'\r\n')if b'\r\n'in before else tail)

def checked(raw,bindings,truth):
    normalized,moved=derive(raw,bindings)
    if bound_blob(normalized,moved,{n:int(n.split('_')[1],16)for values in BINDINGS.values()for _,n in values})!=list(struct.unpack('>72I',truth)):raise ValueError('Record query normalized body differs')


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Record position query discovery changed: '+n)
        names=set(initial)|{'conker/asm/AC030.s','conker/asm/B3020.s','conker/asm/C4DC0.s','conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Record position query protected input changed: '+n)
    headers=out/'match-include-sha256.json'
    if not headers.exists():
        rows={p.relative_to(root).as_posix():sha(p.read_bytes())for p in sorted((root/'conker/include').rglob('*.h'))}
        for n in rows:p=out/'match-includes'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        headers.write_text(json.dumps(rows,indent=2)+'\n')
    rows=json.loads(headers.read_text())
    for n,h in rows.items():
        if sha((root/n).read_bytes())!=h or sha((out/'match-includes'/n).read_bytes())!=h:raise ValueError('Record query include changed: '+n)
    return len(values)+len(rows)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Record position query predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Record position query predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Record position query literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Record position query named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    if od or nd:raise ValueError('Record query owner acquired diagnostics')
    raw_neighbors=same_functions(old,new,(FUNCTION,))
    a,b=alloc_pools(old),alloc_pools(new)
    if set(a)!=set(b)or[n for n in a if a[n]!=b[n]]!=['.reginfo']:raise ValueError('Record query raw loaded pool delta is not closed')
    x,y=a['.reginfo'],b['.reginfo']
    if x[:4]!=y[:4]or x[5:]!=y[5:]:raise ValueError('Record query register section shape changed')
    x,y=(struct.unpack('>6I',v[4])for v in(x,y))
    if x[1:]!=y[1:]or(x[0],y[0])!=(0xA33FFFFE,0xA37FFFFE):raise ValueError('Only recovered S6 use may enter the raw register mask')
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];checked(raw,bindings,truth)
    guards=(out/'match-frozen'/GUARDS).read_bytes();proposed=guard_manifest(guards,raw,bindings)
    if(root/GUARDS).read_bytes()!=(proposed if installed else guards):raise ValueError('Record query source/guard phases disagree')
    old_guard=out/'predecessor-guards.csv';new_guard=out/'proposed-guards.csv';old_guard.write_bytes(guards);new_guard.write_bytes(proposed)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',new_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live query owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Padded query pools/register metadata changed')
    padded,padded_bindings=function_blob(no)
    if(padded,padded_bindings)!=derive(raw,bindings):raise ValueError('Record query actual padder differs from derivation')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'query-predecessor-image');ne=harness.link_image(root,out,no,'query-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Record query live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Record query complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Record query protected data differs')
    (out/'proposed-owner.c').write_text(after)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,words=72,frame=888,slot_words=72,alignment_words=0,guards=2,raw_word_differences=2,bindings=5,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_GPR_before="0xa33ffffe",raw_GPR_after="0xa37ffffe",other_raw_and_padded_loaded_pools_register_metadata_fixed=True,Game_compiler_diagnostics=0,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(proposed),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
