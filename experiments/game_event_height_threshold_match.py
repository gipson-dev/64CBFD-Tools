"""Guarded scheduling origins, complete owner and literal whole-image proof."""
import csv,hashlib,io,json,re,struct,subprocess,sys
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_event_height_threshold_candidates as candidate
from tools.experiments import game_embedded_dual_phase_position_update_match as harness
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
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
OBJECT='conker/build/src/game/generated_1FA770.c.o'
ELF,GUARDS,MAKE,LINKER='conker/build/conker.us.elf','conker/retail_word_patches.us.csv','conker/Makefile','conker/build/conker.ld'
ROM_IMAGE='conker/conker.us.bin'
BASELINE_SHA='a2f56948a8333d9828998dcfb4a2467ef8afaf32ca7c0bec0a5b259fb30957cd'
OLD_GUARD_SHA='7d469fee131d8adbc169fda991046c614fea90f2704bfcd612c41371e6efa1f0'
GUARD_SHA='d4dffc34fb8b6371d8090bffe66ef9c93b5216cb347facd74e694cb8e15cf833'
RAW_SHA='1f91f64bdc8e97554f3b8643bbbd696b6090c79f0bb9c5f6f59c78ec9e7a6b2d'
RAW_BINDINGS={12:[('R_MIPS_26','func_151CE634')],40:[('R_MIPS_26','func_1515C1A0')],168:[('R_MIPS_26','func_1505D024')],264:[('R_MIPS_26','func_1505D024')]}
BINDINGS={12:RAW_BINDINGS[12],40:RAW_BINDINGS[40],164:RAW_BINDINGS[168],256:RAW_BINDINGS[264]}
sha=lambda b:hashlib.sha256(b).hexdigest()
def symbols():return dict(func_151CE634=0x151ce634,func_1515C1A0=0x1515c1a0,func_1505D024=0x1505d024)
def function_blob(obj):
    t,f,r=parse_object(obj);v=f[FUNCTION];a,n=v['value'],v['size'];return t[a:a+n],{p-a:b for p,b in r.items()if a<=p<a+n}
def checked(raw,bindings,truth,normalized=False):
    if normalized:
        if len(raw)!=280 or bindings!=BINDINGS or bound_blob(raw,bindings,symbols())!=list(struct.unpack('>70I',truth)):raise ValueError('Normalized height body or bindings differ')
    elif len(raw)!=288 or sha(raw)!=RAW_SHA or bindings!=RAW_BINDINGS:raise ValueError('Complete compiler height body or bindings changed')
    return raw,bindings
def scheduling(raw,bindings):
    checked(raw,bindings,b'');w=list(struct.unpack('>72I',raw));origins=list(range(72));origins[36:39]=[38,36,37];origins[59:62]=[61,59,60];origins[63:65]=[64,63]
    omits={39,65};positions={src:i for i,src in enumerate(v for j,v in enumerate(origins)if j not in omits)};rows=[];emitted=[];ledger=[]
    for slot,origin in enumerate(origins):
        value=w[origin];note=''
        if slot in(5,15,20,40,44,49):
            target=slot+1+((w[slot]&65535)^32768)-32768;value=(w[slot]&0xffff0000)|((positions[target]-positions[origin]-1)&65535);note='Retarget the original branch after two closed scheduling omissions'
        if slot==52:
            if value!=0x8c640094:raise ValueError('Upper-table load origin changed')
            value=0x8c620094;note='Keep the upper-table base in the retail dead caller-saved v0 lifetime'
        if slot==57:
            if value!=0x008b6021:raise ValueError('Upper-table address origin changed')
            value=0x004b6021;note='Consume the upper-table base through the same retail v0 lifetime'
        if slot==63:
            if w[origin]!=0x45020004:raise ValueError('Upper false-branch origin changed')
            value=0x45000000|((positions[68]-len(emitted)-1)&65535);note='Use the ordinary false branch into the shared saved-RA epilogue'
        if slot in(36,37,38):note='Schedule the original float compare before the two independent argument reloads'
        if slot in(59,60,61):note='Schedule the original upper float compare before command materialization'
        if slot==64:note='Fill the ordinary false-branch delay with the original argument-zero move'
        if slot==39:note='Omit the compiler-only comparison hazard nop after filling its useful delay work'
        if slot==65:note='Fold the duplicate false-path saved-RA delay load into the existing shared epilogue'
        if value!=w[slot]or slot in omits:
            if bindings.get(slot*4)or bindings.get(origin*4):raise ValueError('Unexpected relocation at a height scheduling guard')
            rows.append(dict(filename=FILENAME,function=FUNCTION,offset='0x%03X'%(slot*4),expected='0x%08X'%w[slot],replacement='0x%08X'%value,expected_relocations='-',replacement_relocations='-',note=note,insert_after='',insert_after_relocations='',omit='true'if slot in omits else'false'))
        if slot not in omits:ledger.append(dict(output=len(emitted),source=origin,source_slot=slot,reason=note or'Unmodified compiler word'));emitted.append(value)
    if len(rows)!=18 or len(emitted)!=70:raise ValueError('Height scheduling closure changed')
    b={positions[p//4]*4:v for p,v in bindings.items()};return struct.pack('>70I',*emitted),b,rows,ledger
def proposed_guards(before,rows):
    if sha(before)!=OLD_GUARD_SHA:raise ValueError('Height guard predecessor changed')
    nl='\r\n'if b'\r\n'in before else'\n';fields=list(csv.DictReader(before.decode().splitlines()).fieldnames);s=io.StringIO(newline='');writer=csv.DictWriter(s,fieldnames=fields,lineterminator=nl);writer.writerows(rows);after=before+s.getvalue().encode()
    if sha(after)!=GUARD_SHA:raise ValueError('Height appended guard rows changed')
    return after
def freeze(root,out):
    p=out/'match-input-sha256.json';dest=out/'match-frozen'
    if not p.exists():
        if sha((root/ELF).read_bytes())!=BASELINE_SHA:raise ValueError('Freeze the height predecessor first')
        values=json.loads((out/'discovery-input-sha256.json').read_text())
        for n,h in values.items():
            if sha((root/n).read_bytes())!=h:raise ValueError('Height discovery input changed: '+n)
        names=set(values)|{'conker/undefined_funcs.us.txt','conker/undefined_syms.us.txt','conker/undefined_funcs_auto.txt','conker/conker.ld'}
        names.update('ido/ido5.3_recomp/'+n for n in('cc','acpp','cfe','uopt','ugen','as1'));values={n:sha((root/n).read_bytes())for n in sorted(names)}
        for n in values:q=dest/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((root/n).read_bytes())
        p.write_text(json.dumps(values,indent=2)+'\n')
    values=json.loads(p.read_text());allowed={SOURCE,OBJECT,ELF,'conker/build/conker.us.bin','graphify-out/graph.json',GUARDS}
    for n,h in values.items():
        if sha((dest/n).read_bytes())!=h:raise ValueError('Frozen height input changed: '+n)
        if n not in allowed and sha((root/n).read_bytes())!=h:raise ValueError('Protected height input changed: '+n)
    return len(values)
def diagnostic(s):return re.sub(r'build/[^,]+\.c, line \d+','<owned source>, line <relocated>',s)
def assemble_owner(root,out,obj,label,guards):
    p=out/label;p.mkdir(parents=True,exist_ok=True);s=p/'owner.s';o=p/'generated_1FA770.c.o';s.write_text(emit_padded_assembly(obj,root/ASM,filename=FILENAME,word_patches_path=guards));subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(o),str(s)],capture_output=True,check=True);return o
def strict_image(before,after,truth):
    if sha(before)!=BASELINE_SHA or len(truth)!=280:raise ValueError('Height image predecessor differs')
    expected=bytearray(before);at=elf_slot_offset(before,ENTRY,280);expected[at:at+280]=truth;rows=[(p,f)for p,n,f,s in symbol_rows(before)if n==FUNCTION]
    if len(rows)!=1 or rows[0][1][1:3]!=(ENTRY,12):raise ValueError('Height predecessor symbol differs')
    struct.pack_into('>I',expected,rows[0][0]+8,280)
    if bytes(expected)!=after:raise ValueError('Height literal whole-image closure failed')
    return sum(a!=b for a,b in zip(before,after))
def prepare(root,output=None):
    root=Path(root).resolve();out=Path(output or root/BUILD).resolve();out.mkdir(parents=True,exist_ok=True);frozen=freeze(root,out);bs,ns,installed=candidate.source_states((root/SOURCE).read_text())
    if bs!=(out/'match-frozen'/SOURCE).read_text():raise ValueError('Height source predecessor differs')
    old,od=candidate.compile_owner(root,out,bs,'match-predecessor-compact');new,nd=candidate.compile_owner(root,out,ns,'match-qualified-compact')
    if diagnostic(od)!=diagnostic(nd)or od.count('Warning 712:')!=8:raise ValueError('Height compiler diagnostics changed: '+od+nd)
    truth=(root/ROM_IMAGE).read_bytes()[ROM:ROM+280];raw,b=function_blob(new);checked(raw,b,truth);normal,nb,rows,ledger=scheduling(raw,b);checked(normal,nb,truth,True)
    guards=proposed_guards((out/'match-frozen'/GUARDS).read_bytes(),rows);(out/'proposed-guards.csv').write_bytes(guards)
    if(root/GUARDS).read_bytes()!=(guards if installed else(out/'match-frozen'/GUARDS).read_bytes()):raise ValueError('Live height guard history differs')
    rn=same_functions(old,new,(FUNCTION,))
    if rn!=51 or alloc_pools(old)!=alloc_pools(new):raise ValueError('Height raw neighbors or compact pools changed')
    oo=assemble_owner(root,out,old,'match-predecessor-owner',out/'match-frozen'/GUARDS);no=assemble_owner(root,out,new,'match-qualified-owner',out/'proposed-guards.csv');checked(*function_blob(no),truth,True)
    if(no if installed else oo).read_bytes()!=(root/OBJECT).read_bytes():raise ValueError('Live height owner differs')
    if same_functions(oo,no,(FUNCTION,))!=51 or padded_pools(oo)!=padded_pools(no):raise ValueError('Height padded neighbors/pools differ')
    with patch.multiple(harness,OBJECT=OBJECT,LINKER=LINKER):oe=harness.link_image(root,out,oo,'match-predecessor-image');ne=harness.link_image(root,out,no,'match-qualified-image')
    before,after=oe.read_bytes(),ne.read_bytes()
    if(after if installed else before)!=(root/ELF).read_bytes():raise ValueError('Height live ELF differs')
    delta=strict_image(before,after,truth);a,_,aa=load_elf_functions(str(oe),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(ne),'mips-linux-gnu-objdump')
    if set(a)!=set(b)or aa!=bb or[n for n in b if a[n]!=b[n]]!=[FUNCTION]or b[FUNCTION]!=list(struct.unpack('>70I',truth)):raise ValueError('Height function/address closure differs')
    data=audit_layout(ne,root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Height protected data differs')
    v=dict(function=FUNCTION,source_installed=installed,frozen_inputs=frozen,raw_words=72,words=70,frame=80,guards=18,omissions=2,raw_word_differences=36,normalized_differences=0,raw_neighbors=rn,neighbors=51,compact_pools_and_metadata_unchanged=True,padded_pools_unchanged=True,qualified_owner_sha256=sha(no.read_bytes()),qualified_elf_sha256=sha(after),guard_sha256=sha(guards),strict_changed_bytes=delta,strict_exclusions=0,all_addresses_fixed=True,functions=len(b),changed_bodies=[FUNCTION],protected_data=data,unchanged_existing_warnings=8)
    (out/'proposed-owner.c').write_text(ns);(out/'guard-origin-ledger.json').write_text(json.dumps(dict(rows=rows,origins=ledger),indent=2)+'\n');(out/'match-qualification.json').write_text(json.dumps(v,indent=2)+'\n');return dict(report=v,predecessor_owner=oo,qualified_owner=no,qualified_compact=new,predecessor_elf=oe,qualified_elf=ne)
if __name__=='__main__':print(json.dumps(prepare(candidate.ROOT)['report'],indent=2))
