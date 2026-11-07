"""Direct queued command decoder, typed Init count return and exact image."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_channel_command_poller_candidates as candidate
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
OBJECT='conker/build/src/game/generated_AD6B0.c.o'
ASM='conker/asm/AD6B0.s'
ELF,GUARDS,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/build/conker.ld'
ROM_IMAGE,MAKE='conker/conker.us.bin','conker/Makefile'
BASELINE_SHA='a6b0d2c2d2a6067ef4b698a9388277e06ac46071e382d05446afb0c98b17b516'
GUARD_SHA='28d7a491d60ac432579e06040e28e21cd7e074d6a47e5c665d1d466ef42670ee'
RAW_SHA='d91b7be0e4fecba84273e49b9949f801c2413004221580203cfa7b962b846afd'
BINDINGS={40: [('R_MIPS_26', 'func_100126E8')], 56: [('R_MIPS_HI16', 'D_800D18D0')], 68: [('R_MIPS_LO16', 'D_800D18D0')], 60: [('R_MIPS_HI16', 'D_800CC2D0')], 64: [('R_MIPS_LO16', 'D_800CC2D0')], 224: [('R_MIPS_26', 'func_15080430')], 236: [('R_MIPS_26', 'func_100126E8')]}
sha=lambda b:hashlib.sha256(b).hexdigest()

def checked(raw,bindings,truth):
    if sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Packet poller complete raw body/bindings changed')
    if bound_blob(raw,bindings,{n:int(n.split('_')[1],16)for values in BINDINGS.values()for _,n in values})!=list(struct.unpack('>72I',truth)):raise ValueError('Packet poller is not a direct retail match')


def function_blob(obj):
    t,fs,rs=parse_object(obj);f=fs[FUNCTION];a,n=f['value'],f['size']
    return t[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}

def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Packet poller discovery changed: '+n)
        names=set(initial)|{'conker/conker.ld','conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.us.yaml'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(path.read_text());allowed={SOURCE,OBJECT,ELF,GUARDS,candidate.INIT,candidate.HEADER,'conker/build/conker.us.bin','graphify-out/graph.json'}
    scope=out/'header-active-scope.json'
    if scope.exists():allowed.update('conker/build/'+n+'.o'for n in json.loads(scope.read_text())['sources'])
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Packet poller protected input changed: '+n)
    return len(values)

def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o')
    s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o

def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=SIZE:raise ValueError('Packet poller predecessor image changed')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);expected[at:at+SIZE]=truth
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Packet poller predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,SIZE)
    if bytes(expected)!=after:raise ValueError('Packet poller literal full image differs')
    wanted=Counter((n,f[1],SIZE if n==FUNCTION else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Packet poller named definitions changed')
    return sum(a!=b for a,b in zip(before,after))

def init_owner(root,out,source,header,label):
    h=out/(label+'-functions.h');h.write_text(header)
    included='#include "'+h.relative_to(root/'conker').as_posix()+'"'
    obj,diagnostics=candidate.compile_owner(root,out,source.replace('#include "functions.h"',included,1),label)
    from tools.pad_c_object import emit_padded_assembly as plain
    asm=out/(label+'.s');padded=out/(label+'-padded.o');asm.write_text(plain(obj,root/'conker/retail_layout.us.txt','init_12560',word_patches_path=root/GUARDS))
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(padded),str(asm)],capture_output=True,check=True)
    return obj,padded,diagnostics

def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out)
    before,after,installed=candidate.source_states((root/SOURCE).read_text());old,od=candidate.compile_owner(root,out,before,'match-predecessor');new,nd=candidate.compile_owner(root,out,after,'match-qualified')
    if od or nd:raise ValueError('Packet Game owner acquired diagnostics')
    raw_neighbors=same_functions(old,new,(FUNCTION,));a,b=alloc_pools(old),alloc_pools(new)
    if set(a)!=set(b)or[n for n in a if a[n]!=b[n]]!=['.reginfo']:raise ValueError('Packet Game data/metadata changes are not closed')
    x,y=a['.reginfo'],b['.reginfo']
    if x[:4]!=y[:4]or x[5:]!=y[5:]:raise ValueError('Packet register section shape differs')
    x,y=(struct.unpack('>6I',v[4])for v in(x,y))
    if x[1:]!=y[1:]or(x[0],y[0])!=(0xA300CF7E,0xA33FFF7E):raise ValueError('Packet GPR mask delta differs')
    raw,bindings=function_blob(new);truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+SIZE];checked(raw,bindings,truth)
    guards=(out/'match-frozen'/GUARDS).read_bytes()
    if sha(guards)!=GUARD_SHA or(root/GUARDS).read_bytes()!=guards:raise ValueError('Direct packet match changed inherited guards')
    old_guard=out/'predecessor-guards.csv';old_guard.write_bytes(guards)
    oo=assemble_owner(root,out,old,'match-predecessor-owner',old_guard);no=assemble_owner(root,out,new,'match-qualified-owner',old_guard)
    if(root/OBJECT).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live packet owner differs')
    padded_neighbors=same_functions(oo,no,(FUNCTION,))
    if alloc_pools(oo)!=alloc_pools(no):raise ValueError('Padded packet pools/register metadata changed')
    checked(*function_blob(no),truth)
    header=(out/'match-frozen'/candidate.HEADER).read_text();init=(out/'match-frozen'/candidate.INIT).read_text();new_header=candidate.repaired_header(header);new_init=candidate.repaired_init(init)
    if(root/candidate.HEADER).read_text()!=(new_header if installed else header)or(root/candidate.INIT).read_text()!=(new_init if installed else init):raise ValueError('Reader ABI installation phases disagree')
    ia,pa,da=init_owner(root,out,init,header,'match-init-before');ib,pb,db=init_owner(root,out,new_init,new_header,'match-init-after')
    init_neighbors=same_functions(ia,ib,())
    if diagnostic_rows(da)!=diagnostic_rows(db)or sum(diagnostic_rows(da).values())!=1:raise ValueError('Init reader baseline warning changed')
    if alloc_pools(ia)!=alloc_pools(ib)or pa.read_bytes()!=pb.read_bytes()or pb.read_bytes()!=(root/'conker/build/src/init_12560.c.o').read_bytes():raise ValueError('Reader ABI repair changed production Init bytes')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'packet-predecessor-image');ne=harness.link_image(root,out,no,'packet-qualified-image')
    previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Packet live ELF differs')
    delta=strict_image(previous,updated,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>72I',truth)):raise ValueError('Packet complete body/address audit failed')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Packet protected data differs')
    for name,text in(('proposed-owner.c',after),('qualified-functions.h',new_header),('qualified-init_12560.c',new_init)):(out/name).write_text(text)
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=inputs,words=72,frame=312,slot_words=72,alignment_words=0,guards=0,raw_word_differences=0,bindings=7,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,raw_GPR_before='0xa300cf7e',raw_GPR_after='0xa33fff7e',all_other_raw_and_padded_pools_metadata_fixed=True,Game_compiler_diagnostics=0,Init_unchanged_baseline_warning=1,Init_raw_functions_fixed=init_neighbors,Init_complete_padded_owner_fixed=True,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(updated),guard_sha256=sha(guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
