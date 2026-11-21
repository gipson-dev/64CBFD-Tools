"""Private both-padder, actual-Make and strict whole-image prediction gate."""
from pathlib import Path
import sys
from tools.experiments import game_projection_submit_15035808_recovery as recovery
ROOT=recovery.ROOT
from tools.experiments.game_list_historical_image import historical_dependencies,assert_qualified_makefile
HISTORICAL_SOURCE=recovery.SOURCE;HISTORICAL_SPEC=recovery.SPEC
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess
from tools.tests import game_projection_submit_15035808_normalizer as d
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
OUT=recovery.OUT;BASE=OUT/'baseline';WHERE=OUT/'image-qualification';WHERE.mkdir(exist_ok=True)
SOURCE='conker/src/game/generated_61D10.c';OBJECT='conker/build/src/game/generated_61D10.c.o';FUNCTION='func_15035808'

def assemble(name,text):
    p=WHERE/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(obj),str(p)],check=True,capture_output=True)
    return obj

def qualify():
    compact=recovery.WHERE/'candidate.o';raw,refs=payload(compact,FUNCTION)
    blob,bindings=d.derive(raw,refs,recovery.SPEC['schedule_plan'])
    source=struct.unpack('>345I',raw);wanted=struct.unpack('>345I',blob)
    old=(BASE/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']==FUNCTION];rows=[]
    def reloc(rs):return';'.join(k+':'+n for k,n in rs)or'-'
    for i,w in enumerate(source):
        before,after=refs.get(i*4,[]),bindings.get(i*4,[])
        if wanted[i]==w and before==after:continue
        row={key:''for key in fields};row.update(filename='generated_61D10',function=FUNCTION,offset='0x%03X'%(i*4),
            expected='0x%08X'%w,replacement='0x%08X'%wanted[i],expected_relocations=reloc(before),replacement_relocations=reloc(after),
            omit='false',note='Normalize proved projection submission register lifetimes, index/alpha homes, independent packet schedules and boolean continuation')
        rows.append(row)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode())
    target=assemble('layout',pc.emit_padded_assembly(compact,ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=guards))
    assembly=assemble('assembly',pg.emit_padded_assembly(compact,ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=guards))
    assert target.read_bytes()==assembly.read_bytes()
    a=pg.parse_object(BASE/OBJECT);b=pg.parse_object(target);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':1380}if name==FUNCTION else{})==h,(name,f,h)
        def contents(p,s):
            lo=s['value'];hi=lo+s['size'];return p[0][lo:hi],{at-lo:rs for at,rs in p[2].items()if lo<=at<hi}
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert changed==[FUNCTION],changed
    assert_qualified_makefile(ROOT,BASE,HISTORICAL_SOURCE,HISTORICAL_SPEC)
    (WHERE/'after-diagnostics.txt').write_text('')
    route=actual_Make(ROOT,WHERE,target,compact,guards,SOURCE,OBJECT,
        (recovery.WHERE/'selected-owner.c').read_text(),'target',10)
    caller_compact=recovery.WHERE/'caller-after.o'
    caller_object=assemble('caller-assembly',pg.emit_padded_assembly(caller_compact,ROOT/'conker/asm/CDE80.s',filename='generated_CDE80',word_patches_path=guards))
    assert caller_object.read_bytes()==(BASE/'conker/build/src/game/generated_CDE80.c.o').read_bytes()
    (WHERE/'caller-after-diagnostics.txt').write_text('')
    caller_route=actual_Make(ROOT,WHERE,caller_object,caller_compact,guards,'conker/src/game/generated_CDE80.c',
        'conker/build/src/game/generated_CDE80.c.o',(recovery.WHERE/'selected-caller.c').read_text(),'caller',28)
    with historical_dependencies(ROOT,WHERE,HISTORICAL_SOURCE,HISTORICAL_SPEC)as script:
        with patch.multiple(linker,FILENAME='generated_61D10',OBJECT=OBJECT,LINKER=script):
            image=linker.link_image(ROOT,WHERE,target,'image')
    before=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x15035808,1380);prediction[at:at+1380]=(ROOT/'conker/conker.us.bin').read_bytes()[0x62cb8:0x6321c]
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name==FUNCTION];assert len(matches)==1
    at,row=matches[0]
    assert(row[1],row[2])==(0x15035808,a[1][FUNCTION]['size']),(row,a[1][FUNCTION])
    previous_symbol_size=row[2];struct.pack_into('>I',prediction,at+8,1380)
    actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,x,y)for i,(x,y)in enumerate(zip(prediction,actual))if x!=y]
    (WHERE/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('Unexpected linked bytes',len(differences),differences[:12])
    (WHERE/'predicted.elf').write_bytes(prediction)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    report=dict(guard_rows=len(rows),insertions=0,omissions=0,owner_functions=len(a[1]),unchanged_owner_functions=9,
        both_full_owner_padders_identical=True,actual_Make=route,strict_predicted_ELF_equal=True,
        changed_bytes=sum(x!=y for x,y in zip(before,actual)),exclusions=0,function_slots=len(functions),
        proposed_ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_symbol_size,
        caller_actual_Make=caller_route,complete_padded_caller_object_unchanged=True,matching_credit=0)
    protected=audit_layout(image,ROOT/'conker');report['protected_data_audit']=protected
    (OUT/'image-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
