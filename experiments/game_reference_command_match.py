"""Qualify the owner-reference handler without excluding any image bytes."""
import csv,hashlib,io,json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
from tools.experiments import game_reference_command_candidates as candidate
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_selector_table_payload_match import paired_diagnostics
from tools.experiments.game_record_address_relocator_match import dependent_sections
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
sha=lambda b:hashlib.sha256(b).hexdigest()
BUILD=candidate.BUILD
ELF,GUARDS,MAKE='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile'
ROM_IMAGE,LINKER='conker/conker.us.bin','conker/build/conker.ld'
BASELINE_SHA='326836ce96a1eaafa5ca835465c74a783934737c4c608f86d29bf211b1a9057d'
GUARD_SHA='5cef039754c4e0bbc2f63202b3e345c31158277e74f76e062bfe90b48b75a97c'
TU='conker/src/game/translation_units/161520_actor_point_effects.c'
def function_blob(obj,index=0):
    text,fs,rs=parse_object(obj);f=fs[candidate.TARGETS[index]['function']];a,n=f['value'],f['size']
    return text[a:a+n],{p-a:r for p,r in rs.items()if a<=p<a+n}
def derive(raw,bindings,index=0):
    t=candidate.TARGETS[index]
    if len(raw)!=292 or bindings!=t['bindings']:raise ValueError('Reference handler extent/bindings changed')
    words=list(struct.unpack('>73I',raw));old,new=t['patches'][0x100]
    # BNEL compares an unordered pair of GPR values. Preserve opcode, branch
    # displacement and likely-delay behavior; only exchange its two operands.
    rs,rt=old>>21&31,old>>16&31
    if old>>26!=0x15 or ((old&~0x03FF0000)|(rt<<21)|(rs<<16))!=new:raise ValueError('Non-commutative guard')
    if words[64]!=old:raise ValueError('Reference handler expected branch changed')
    words[64]=new
    return struct.pack('>73I',*words),dict(bindings)
def guard_manifest(before):
    if sha(before)!=GUARD_SHA:raise ValueError('Reference handler guard predecessor changed')
    fields=next(csv.reader(io.StringIO(before.decode('utf-8'))))
    if any(r['function']=='func_151347CC'for r in csv.DictReader(io.StringIO(before.decode('utf-8')))):raise ValueError('Handler guard already present')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n')
    writer.writerow(dict(filename='game_161520',function='func_151347CC',offset='0x100',expected='0x54790005',replacement='0x57230005',expected_relocations='-',replacement_relocations='-',note='Normalize commutative reference-handler BNEL operand order',omit='false'))
    return before+stream.getvalue().encode('utf-8')
def freeze(root,out):
    path=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not path.exists():
        initial=json.loads((out/'discovery-input-sha256.json').read_text(encoding='utf-8'))
        for n,h in initial.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Discovery changed: '+n)
        names=set(initial)|{'ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1')}
        names.update(p.relative_to(root).as_posix()for p in(root/'conker/include').rglob('*.h'))
        values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:
            p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/n).read_bytes())
        path.write_text(json.dumps(values,indent=2)+'\n',encoding='utf-8')
    values=json.loads(path.read_text(encoding='utf-8'));allowed={ELF,GUARDS,'conker/build/conker.us.bin','graphify-out/graph.json'}|{t[k]for t in candidate.TARGETS for k in('source','object')}
    override=out/'match-override-sha256.json'
    if not override.exists():
        p=dest/TU;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/TU).read_bytes())
        override.write_text(json.dumps({TU:sha(p.read_bytes())},indent=2)+'\n',encoding='utf-8')
    values.update(json.loads(override.read_text(encoding='utf-8')))
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h or(n not in allowed and sha((root/n).read_bytes())!=h):raise ValueError('Protected input changed: '+n)
    return len(values)
def assemble_owner(root,out,obj,index,label,guards):
    t=candidate.TARGETS[index];p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(t['owner']+'.c.o')
    effects,diag=candidate.compile_owner(root,out,(root/TU).read_text(encoding='utf-8'),label+'-effects')
    if diag:raise ValueError('Point-effects override diagnostics changed')
    s.write_text(pad_c_object.emit_padded_assembly(obj,root/t['assembly'],filename=t['owner'],word_patches_path=guards,rodata_symbol='jtbl_800A4350_game',function_objects={'func_15138BC0':effects}),encoding='utf-8')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True)
    return o
def pools(before,after,padded=False):
    if alloc_pools(before)!=alloc_pools(after):raise ValueError('Whole allocatable pools changed')
    a,b=(dependent_sections(p.read_bytes()).get('.options')for p in(before,after))
    if a is None and b is None:return
    # The section's file offset follows the larger .text; its other header
    # fields and complete payload must remain literal.
    if a is None or b is None or a[0][:4]+a[0][5:]!=b[0][:4]+b[0][5:]or a[1]!=b[1]:raise ValueError('Options section changed')
def link_image(root,out,owners,label):
    linker=(out/'match-frozen'/LINKER).read_text(encoding='utf-8')
    for t,obj in zip(candidate.TARGETS,owners):
        old=t['object'].removeprefix('conker/');new=obj.relative_to(root/'conker').as_posix()
        if linker.count(old)!=1:raise ValueError('Link owner reference changed')
        linker=linker.replace(old,new)
    d=out/label;d.mkdir(exist_ok=True);script=d/'conker.ld';script.write_text(linker,encoding='utf-8');elf=d/'conker.us.elf'
    subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(elf.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    return elf
def strict_image(before,after,rom):
    if sha(before)!=BASELINE_SHA:raise ValueError('Predecessor image changed')
    expected=bytearray(before);t=candidate.TARGETS[0];at=elf_slot_offset(before,t['entry'],292);expected[at:at+292]=rom[t['rom']:t['rom']+292]
    rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==t['function']]
    if len(rows)!=1 or rows[0][1][1:3]!=(t['entry'],12):raise ValueError('Predecessor symbol changed')
    struct.pack_into('>I',expected,rows[0][0]+8,292)
    if bytes(expected)!=after:
        diff=[i for i,(a,b)in enumerate(zip(expected,after))if a!=b]
        raise ValueError('Literal whole image differs: '+repr((len(expected),len(after),len(diff),diff[:32])))
    wanted=Counter((n,f[1],292 if n==t['function']else f[2],*f[3:])for p,n,f,s in symbol_rows(before))
    if wanted!=Counter((n,*f[1:])for p,n,f,s in symbol_rows(after)):raise ValueError('Symbol definitions changed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);inputs=freeze(root,out);rom=(root/ROM_IMAGE).read_bytes();t=candidate.TARGETS[0]
    before,after,installed=candidate.source_states((root/t['source']).read_text(encoding='utf-8'))
    if before!=(out/'match-frozen'/t['source']).read_text(encoding='utf-8'):raise ValueError('Reconstructed predecessor changed')
    bg=(out/'match-frozen'/GUARDS).read_bytes();ag=guard_manifest(bg);gp=[out/'predecessor-guards.csv',out/'proposed-guards.csv'];gp[0].write_bytes(bg);gp[1].write_bytes(ag)
    old,od=candidate.compile_owner(root,out,before,'match-predecessor-0');new,nd=candidate.compile_owner(root,out,after,'match-qualified-0')
    diagnostics=paired_diagnostics(od,nd,t['owner']);raw_neighbors=same_functions(old,new,(t['function'],));pools(old,new)
    raw,refs=function_blob(new);normalized,nrefs=derive(raw,refs)
    if bound_blob(normalized,nrefs,{'func_1516972C':0x1516972C})!=list(struct.unpack_from('>73I',rom,t['rom'])):raise ValueError('Normalized body differs')
    oo=assemble_owner(root,out,old,0,'match-predecessor-owner-0',gp[0]);no=assemble_owner(root,out,new,0,'match-qualified-owner-0',gp[1]);padded_neighbors=same_functions(oo,no,(t['function'],));pools(oo,no,True)
    if function_blob(no)!=(normalized,nrefs):raise ValueError('Padded body differs')
    if(root/t['object']).read_bytes()!=(no if installed else oo).read_bytes():raise ValueError('Live owner differs')
    if(root/GUARDS).read_bytes()!=(ag if installed else bg):raise ValueError('Guard phase differs')
    oe=link_image(root,out,[oo],'reference-predecessor-image');ne=link_image(root,out,[no],'reference-qualified-image');previous,updated=oe.read_bytes(),ne.read_bytes()
    if(root/ELF).read_bytes()!=(updated if installed else previous):raise ValueError('Live ELF differs')
    delta=strict_image(previous,updated,rom);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump');changed=[n for n in b if a[n]!=b[n]]
    if set(a)!=set(b)or aa!=bb or changed!=[t['function']]:raise ValueError('Function/address census differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Protected data differs')
    (out/'proposed-0.c').write_text(after,encoding='utf-8')
    report=dict(source_installed=installed,frozen_inputs=inputs,targets=[dict(function=t['function'],words=73,frame=24,guards=1,bindings=3,raw_neighbors=raw_neighbors,padded_neighbors=padded_neighbors,pools_fixed=True,diagnostics=diagnostics,qualified_owner_sha256=sha(no.read_bytes()))],qualified_elf_sha256=sha(updated),guard_sha256=sha(ag),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=changed,protected_data=data)
    (out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return dict(report=report,predecessor_owners=[oo],qualified_owners=[no],qualified_compacts=[new],predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
