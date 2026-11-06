"""Closed query scheduling with an explicit dependent stub ABI delta."""
import csv,hashlib,io,json,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_actor_type_query_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_player_status_accessor_match import alloc_pools
from tools.experiments.game_path_heading_turn_match import padded_pools
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools.pad_generated_object import emit_padded_assembly,parse_object
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,FILENAME,SOURCE,ASM=candidate.FUNCTION,candidate.OWNER,candidate.SOURCE,candidate.ASM
ENTRY,ROM,WORDS,BUILD=candidate.ENTRY,candidate.ROM,candidate.WORDS,candidate.BUILD
OBJECT='conker/build/src/game/generated_AE1D0.c.o'
ELF,GUARDS,MAKE,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BASELINE_SHA='7fed3e3d16adc225ed18fce721a8669903cd4a061c01d6c94d9f1c2558b01ecf'
OLD_GUARD_SHA='35c4628409bcf6ed0c1b776c1f886bc144f19ca23ec7f923a4e2fdb614e9b4fa'
RAW_SHA='638351b5f098f3bfee359f8a7da18d4f8b555dc814a1ba7dfe5ea05290407e94'
BINDINGS={64:[('R_MIPS_HI16','D_800CC2D0')],80:[('R_MIPS_LO16','D_800CC2D0')],68:[('R_MIPS_HI16','D_800D121C')],96:[('R_MIPS_LO16','D_800D121C')],76:[('R_MIPS_HI16','D_8009BD30')],84:[('R_MIPS_LO16','D_8009BD30')],140:[('R_MIPS_26','func_1508108C')],180:[('R_MIPS_26','func_15080D20')]}
HELPER='func_15080D20';HELPER_ENTRY=0x15080d20
STUB=bytes.fromhex('00001025 03e00008 00000000')
TYPED_STUB=bytes.fromhex('afa40000 afa50004 afa60008 afa7000c')+STUB
sha=lambda b:hashlib.sha256(b).hexdigest()

def symbols():return dict(D_800CC2D0=0x800cc2d0,D_800D121C=0x800d121c,D_8009BD30=0x8009bd30,func_1508108C=0x1508108c,func_15080D20=HELPER_ENTRY)
def function_blob(obj,name=FUNCTION):
    t,f,r=parse_object(obj);v=f[name];a,n=v['value'],v['size'];return t[a:a+n],{p-a:b for p,b in r.items()if a<=p<a+n}
def checked(raw,b):
    if len(raw)!=272 or sha(raw)!=RAW_SHA or b!=BINDINGS:raise ValueError('Actor query compiler body or bindings changed')
def scheduling(raw,b):
    checked(raw,b);w=list(struct.unpack('>68I',raw));origins=list(range(68));origins[17:26]=[19,18,17,24,22,23,21,20,25];rename={20:21,21:22,22:20};rows=[];ledger=[];new=[];nb={}
    for slot,origin in enumerate(origins):
        value=w[origin]
        if 17<=origin<=53:
            op,rs,rt,rd=value>>26,value>>21&31,value>>16&31,value>>11&31
            if op not in(0,3,4,9,15,17,20,21,35,36,43,49,57):raise ValueError('Unexpected query-cycle instruction')
            if op in(49,57):value=(value&~0x03e00000)|(rename.get(rs,rs)<<21)
            elif op==17:
                if rs not in(0,4):raise ValueError('Unexpected query COP1 transfer')
                value=(value&~0x001f0000)|(rename.get(rt,rt)<<16)
            elif op!=3:
                value=(value&~0x03ff0000)|(rename.get(rs,rs)<<21)|(rename.get(rt,rt)<<16)
                if op==0:value=(value&~0xf800)|(rename.get(rd,rd)<<11)
        oldrel,newrel=b.get(slot*4,[]),b.get(origin*4,[])
        if newrel:nb[slot*4]=newrel
        reason='Schedule the same independent address or argument load in the retail order'if origin!=slot else'Retain the semantic role through the closed s4/s5/s6 allocation cycle'
        if value!=w[slot]or oldrel!=newrel:
            encode=lambda r:';'.join(k+':'+s for k,s in r)or'-'
            rows.append(dict(filename=FILENAME,function=FUNCTION,offset='0x%03X'%(slot*4),expected='0x%08X'%w[slot],replacement='0x%08X'%value,expected_relocations=encode(oldrel),replacement_relocations=encode(newrel),note=reason,insert_after='',insert_after_relocations='',omit='false'))
        ledger.append(dict(output=slot,source=origin,reason=reason if value!=w[slot]or oldrel!=newrel else'Unmodified compiler word'));new.append(value)
    if len(rows)!=11:raise ValueError('Query scheduling closure changed')
    return struct.pack('>68I',*new),nb,rows,ledger
def proposed_guards(before,rows):
    if sha(before)!=OLD_GUARD_SHA:raise ValueError('Query guard predecessor changed')
    fields=csv.DictReader(before.decode().splitlines()).fieldnames;s=io.StringIO(newline='');writer=csv.DictWriter(s,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in before else'\n');writer.writerows(rows);return before+s.getvalue().encode()
def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        values=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Query discovery changed: '+n)
        names=set(values)|{'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'};names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'));values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(p.read_text());allowed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json',GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen query input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected query input changed: '+n)
    return len(values)
def owner_audit(old,new,padded=False):
    a,b=parse_object(old),parse_object(new)
    if a[1].keys()!=b[1].keys():raise ValueError('Query function inventory differs')
    changed=[n for n in a[1]if function_blob(old,n)!=function_blob(new,n)]
    if set(changed)!={FUNCTION,HELPER}or function_blob(old,HELPER)!=(STUB,{})or function_blob(new,HELPER)!=(TYPED_STUB,{}):raise ValueError('Query dependent interface delta differs')
    if padded:
        if padded_pools(old)!=padded_pools(new):raise ValueError('Query padded metadata differs')
    else:
        x,y=alloc_pools(old),alloc_pools(new)
        if x.keys()!=y.keys()or[n for n in x if x[n]!=y[n]]!=['.reginfo']:raise ValueError('Query compact pools differ')
        ax,bx=x['.reginfo'],y['.reginfo'];expected=bytearray(ax[4])
        if ax[:4]!=bx[:4]or ax[5:]!=bx[5:]or struct.unpack_from('>I',expected,8)[0]!=0x00350551:raise ValueError('Query register metadata predecessor differs')
        struct.pack_into('>I',expected,8,0x00f50551)
        if bytes(expected)!=bx[4]:raise ValueError('Query F22/F23 mask differs')
    return len(a[1])-2
def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/(FILENAME+'.c.o');s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],check=True,capture_output=True);return o
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=284:raise ValueError('Query image predecessor differs')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,284);expected[at:at+284]=truth;at=elf_slot_offset(before,HELPER_ENTRY,28)
    if before[at:at+28]!=STUB+bytes(16):raise ValueError('Query helper predecessor differs')
    expected[at:at+28]=TYPED_STUB
    for name,entry,size in((FUNCTION,ENTRY,272),(HELPER,HELPER_ENTRY,28)):
        rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==name]
        if len(rows)!=1 or rows[0][1][1:3]!=(entry,12):raise ValueError('Query predecessor symbol differs')
        struct.pack_into('>I',expected,rows[0][0]+8,size)
    if bytes(expected)!=after:raise ValueError('Query literal whole-image closure failed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out);bs,ns,installed=candidate.source_states((root/SOURCE).read_text())
    if bs!=(out/'match-frozen'/SOURCE).read_text():raise ValueError('Query predecessor source differs')
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if od or nd:raise ValueError('Query owner diagnostics changed')
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+284];raw,b=function_blob(new);normal,nb,rows,ledger=scheduling(raw,b)
    if bound_blob(normal,nb,symbols())!=list(struct.unpack('>68I',truth[:272]))or truth[272:]!=bytes(12):raise ValueError('Query normalized body or alignment differs')
    guards=proposed_guards((out/'match-frozen'/GUARDS).read_bytes(),rows);(out/'proposed-guards.csv').write_bytes(guards)
    if(root/GUARDS).read_bytes()!=(guards if installed else(out/'match-frozen'/GUARDS).read_bytes()):raise ValueError('Query live guard history differs')
    rn=owner_audit(old,new);oo=assemble_owner(root,out,old,'match-predecessor-owner',out/'match-frozen'/GUARDS);no=assemble_owner(root,out,new,'match-qualified-owner',out/'proposed-guards.csv');pn=owner_audit(oo,no,True)
    if function_blob(no)!=(normal,nb)or(no if installed else oo).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Query padded owner identity differs')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'match-predecessor-image');ne=harness.link_image(root,out,no,'match-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Query live ELF differs')
    delta=strict_image(before,after,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or{n for n in b if a[n]!=b[n]}!={FUNCTION,HELPER}:raise ValueError('Query linked body/address closure differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Query protected data differs')
    report=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,raw_words=68,words=68,slot_words=71,alignment_words=3,frame=80,guards=11,omissions=0,raw_word_differences=11,normalized_differences=0,raw_neighbors=rn,neighbors=pn,dependent_helper=HELPER,helper_words_before=3,helper_words_after=7,helper_new_matching_credit=0,raw_FPR_mask_delta='F22/F23 only',padded_pools_and_metadata_unchanged=True,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=sorted([FUNCTION,HELPER]),protected_data=data)
    (out/'proposed-owner.c').write_text(ns);(out/'guard-origin-ledger.json').write_text(json.dumps(dict(rows=rows,origins=ledger),indent=2)+'\n');(out/'match-qualification.json').write_text(json.dumps(report,indent=2)+'\n');return dict(report=report,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
