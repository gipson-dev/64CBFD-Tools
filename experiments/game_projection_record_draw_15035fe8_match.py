from pathlib import Path
import sys
from tools.experiments import game_projection_record_draw_15035fe8_recovery as source
ROOT=source.ROOT
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess
from tools.tests import game_projection_record_draw_15035fe8_normalizer as d
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
from tools.tests.game_owner_pool import normalized_pools
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
OUT=source.OUT;BASE=OUT/'baseline';WHERE=OUT/'qualification'

def qualify():
    WHERE.mkdir(exist_ok=True);compact=OUT/'qualified-screen/candidate.o';raw,refs=d.payload(compact,'func_15035FE8')
    blob,bindings,proof=d.derive(raw,refs);source=struct.unpack('>90I',raw);wanted=struct.unpack('>88I',blob)
    old=(BASE/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']=='func_15035FE8'];rows=[];cursor=0;omitted=set(range(38,46))|{49};inserted={48,50,51,52,53,54,55}
    def reloc(rs):return';'.join(k+':'+n for k,n in rs)or'-'
    for i,w in enumerate(source):
        row={key:''for key in fields}
        row.update(filename='generated_61D10',function='func_15035FE8',offset='0x%03X'%(i*4),expected='0x%08X'%w,
                   expected_relocations=reloc(refs.get(i*4,[])),omit='false',note='Normalize proved record draw count-bound gate, duplicated limit and register scheduling')
        if i in omitted:
            row.update(replacement='0x%08X'%w,replacement_relocations=row['expected_relocations'],omit='true')
        else:
            rr=bindings.get(cursor*4,[]);replacement=wanted[cursor];row.update(replacement='0x%08X'%replacement,replacement_relocations=reloc(rr));cursor+=1
            if i in inserted:
                row.update(insert_after='0x%08X'%wanted[cursor],insert_after_relocations=reloc(bindings.get(cursor*4,[])));cursor+=1
            elif replacement==w and rr==refs.get(i*4,[]):continue
        rows.append(row)
    assert cursor==88
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode())
    def assemble(name,text):
        p=WHERE/(name+'.s');p.write_text(text);q=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],check=True,capture_output=True)
        return q
    target=assemble('layout',pc.emit_padded_assembly(compact,ROOT/'conker/retail_layout.us.txt','generated_61D10',word_patches_path=guards))
    assembly=assemble('assembly',pg.emit_padded_assembly(compact,ROOT/'conker/asm/61D10.s',filename='generated_61D10',word_patches_path=guards))
    assert target.read_bytes()==assembly.read_bytes()
    a=pg.parse_object(BASE/'conker/build/src/game/generated_61D10.c.o');b=pg.parse_object(target);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':352}if name=='func_15035FE8'else{})==h,(name,f,h)
        def contents(p,s):
            lo=s['value'];hi=lo+s['size'];return(p[0][lo:hi],{at-lo:rs for at,rs in p[2].items()if lo<=at<hi})
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert changed==['func_15035FE8'],changed
    (WHERE/'after-diagnostics.txt').write_text('')
    target_route=actual_Make(ROOT,WHERE,target,compact,guards,'conker/src/game/generated_61D10.c','conker/build/src/game/generated_61D10.c.o',
        (OUT/'qualified-screen/selected-owner.c').read_text(),'target',10)
    caller_source='conker/src/game_45B80.c';before=(BASE/caller_source).read_text()
    selected=before.replace('s32  func_15035FE8(s32 arg0, s32 arg1);','Gfx *func_15035FE8(Gfx *commands, s32 view);')
    selected=selected.replace('commands = (Gfx *)func_15035FE8((s32)commands, view);','commands = func_15035FE8(commands, view);');assert selected!=before
    ca,cd=compile_owner(ROOT,WHERE,before,'caller-before');cb,cbd=compile_owner(ROOT,WHERE,selected,'caller-after')
    assert cd.replace('caller-before','caller-input')==cbd.replace('caller-after','caller-input')and cd.count('Warning 712:')==3
    assert same_functions(ca,cb,())==16 and normalized_pools(ca)==normalized_pools(cb)
    caller=assemble('caller-layout',pc.emit_padded_assembly(cb,ROOT/'conker/retail_layout.us.txt','game_45B80',word_patches_path=guards))
    assert caller.read_bytes()==(BASE/'conker/build/src/game_45B80.c.o').read_bytes()
    (WHERE/'caller-after-diagnostics.txt').write_text(cbd);(WHERE/'selected-caller.c').write_text(selected)
    caller_route=actual_Make(ROOT,WHERE,caller,cb,guards,caller_source,'conker/build/src/game_45B80.c.o',selected,'caller',16)
    with patch.multiple(linker,FILENAME='generated_61D10',OBJECT='conker/build/src/game/generated_61D10.c.o',LINKER='conker/build/conker.ld'):
        image=linker.link_image(ROOT,WHERE,target,'image')
    before=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x15035FE8,352);prediction[at:at+352]=(ROOT/'conker/conker.us.bin').read_bytes()[0x63498:0x635F8]
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name=='func_15035FE8'];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(0x15035FE8,12);struct.pack_into('>I',prediction,at+8,352)
    (WHERE/'predicted-code-size.elf').write_bytes(prediction);actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,x,y)for i,(x,y)in enumerate(zip(prediction,actual))if x!=y]
    (WHERE/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected linked bytes',len(differences))
    (WHERE/'predicted.elf').write_bytes(prediction);fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(guard_rows=len(rows),insertions=len(inserted),omissions=len(omitted),owner_functions=len(a[1]),caller_functions_unchanged=16,
           caller_complete_padded_object_unchanged=True,unchanged_caller_Warning_712_count=3,padders_equal=True,
           actual_Make=dict(target=target_route,caller=caller_route),strict_predicted_ELF_equal=True,
           changed_bytes=sum(x!=y for x,y in zip(before,prediction)),exclusions=0,function_slots=len(fs),
           protected_data=audit_layout(image,ROOT/'conker'),ELF_sha256=hashlib.sha256(actual).hexdigest(),matching_credit=0)
    (WHERE/'integration.json').write_text(json.dumps(r,indent=2)+'\n');return r
