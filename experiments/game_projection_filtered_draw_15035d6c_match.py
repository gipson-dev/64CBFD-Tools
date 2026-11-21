from pathlib import Path
import sys
from tools.experiments import game_projection_filtered_draw_15035d6c_recovery as source
ROOT=source.ROOT
from tools.experiments.game_list_historical_image import historical_dependencies,assert_qualified_makefile
HISTORICAL_SOURCE=source.SOURCE;HISTORICAL_SPEC=source.SPEC
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess
from tools.tests import game_projection_filtered_draw_15035d6c_normalizer as d
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
OUT=source.OUT;BASE=OUT/'baseline';WHERE=OUT/'qualification'

def qualify():
    WHERE.mkdir(exist_ok=True);compact=OUT/'qualified-screen/candidate.o';raw,refs=payload(compact,'func_15035D6C')
    blob,bindings,relation=d.derive(raw,refs);source=struct.unpack('>160I',raw);wanted=struct.unpack('>159I',blob)
    old=(BASE/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']=='func_15035D6C'];rows=[];cursor=0
    def reloc(rs):return';'.join(k+':'+n for k,n in rs)or'-'
    for i,w in enumerate(source):
        row={key:''for key in fields}
        row.update(filename='generated_61D10',function='func_15035D6C',offset='0x%03X'%(i*4),expected='0x%08X'%w,
            expected_relocations=reloc(refs.get(i*4,[])),omit='false',
            note='Normalize proved projection filter saved-role cycle and independent scheduling; remove redundant modulo-32 shift mask and rebase branches')
        if i==relation['omitted_origin']:
            row.update(replacement='0x%08X'%w,replacement_relocations=row['expected_relocations'],omit='true')
        else:
            rr=bindings.get(cursor*4,[]);replacement=wanted[cursor];row.update(replacement='0x%08X'%replacement,replacement_relocations=reloc(rr));cursor+=1
            if replacement==w and rr==refs.get(i*4,[]):continue
        rows.append(row)
    assert cursor==159
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode())
    def assemble(name,text):
        p=WHERE/(name+'.s');p.write_text(text);q=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],check=True,capture_output=True);return q
    target=assemble('layout',pc.emit_padded_assembly(compact,ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=guards))
    assembly=assemble('assembly',pg.emit_padded_assembly(compact,ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=guards))
    assert target.read_bytes()==assembly.read_bytes()
    a=pg.parse_object(BASE/'conker/build/src/game/generated_61D10.c.o');b=pg.parse_object(target);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':636}if name=='func_15035D6C'else{})==h,(name,f,h)
        def contents(p,s):
            lo=s['value'];hi=lo+s['size'];return(p[0][lo:hi],{at-lo:rs for at,rs in p[2].items()if lo<=at<hi})
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert changed==['func_15035D6C'],changed
    assert_qualified_makefile(ROOT,BASE,HISTORICAL_SOURCE,HISTORICAL_SPEC)
    (WHERE/'after-diagnostics.txt').write_text('')
    route=actual_Make(ROOT,WHERE,target,compact,guards,'conker/src/game/generated_61D10.c','conker/build/src/game/generated_61D10.c.o',
        (OUT/'qualified-screen/selected-owner.c').read_text(),'target',10)
    with historical_dependencies(ROOT,WHERE,HISTORICAL_SOURCE,HISTORICAL_SPEC)as script:
        with patch.multiple(linker,FILENAME='generated_61D10',OBJECT='conker/build/src/game/generated_61D10.c.o',LINKER=script):
            image=linker.link_image(ROOT,WHERE,target,'image')
    before=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x15035D6C,636);prediction[at:at+636]=(ROOT/'conker/conker.us.bin').read_bytes()[0x6321C:0x63498]
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name=='func_15035D6C'];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(0x15035D6C,12);struct.pack_into('>I',prediction,at+8,636)
    (WHERE/'predicted-code-size.elf').write_bytes(prediction);actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,x,y)for i,(x,y)in enumerate(zip(prediction,actual))if x!=y]
    (WHERE/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected linked bytes',len(differences))
    (WHERE/'predicted.elf').write_bytes(prediction);fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(guard_rows=len(rows),insertions=0,omissions=1,owner_functions=len(a[1]),unchanged_owner_functions=9,
        record_field_rename_neighbors_unchanged=True,submit_placeholder_unchanged=True,padders_equal=True,
        actual_Make=route,owner_Make_recipe_unchanged=True,strict_predicted_ELF_equal=True,
        changed_bytes=sum(x!=y for x,y in zip(before,prediction)),exclusions=0,function_slots=len(fs),
        protected_data=audit_layout(image,ROOT/'conker'),ELF_sha256=hashlib.sha256(actual).hexdigest(),matching_credit=0)
    (WHERE/'integration.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
