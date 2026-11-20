from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools.tests import game_actor_randomized_effect_150f97ec_normalizer as d
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments import game_actor_randomized_effect_150f97ec_recovery as source
ROOT=source.ROOT;OUT=source.OUT;BASE=OUT/'baseline';WHERE=OUT/'qualification'
def permute_metadata(image):
    result=bytearray(image);pairs=[('D_800A48C8','D_800A03C8'),('D_800A1C54','D_800A5F54')]
    for before in pairs:
        entries={n:(at,row,s)for at,n,row,s in symbol_rows(image)if n in before};assert set(entries)==set(before)
        rows=[entries[n]for n in before];start,record,string=rows[0];assert rows[1][0]==start+16
        expected=b''.join(n.encode()+b'\0'for n in before);assert image[string:string+len(expected)]==expected
        cursor=0
        for i,name in enumerate(reversed(before)):
            row=list(entries[name][1]);row[0]=record[0]+cursor;struct.pack_into('>IIIBBH',result,start+i*16,*row)
            data=name.encode()+b'\0';result[string+cursor:string+cursor+len(data)]=data;cursor+=len(data)
        assert cursor==len(expected)
    assert{n:r[1:]for at,n,r,s in symbol_rows(image)}=={n:r[1:]for at,n,r,s in symbol_rows(result)}
    return bytes(result),pairs
def qualify():
    WHERE.mkdir(exist_ok=True);obj=OUT/'qualified-screen/candidate.o';raw,refs=d.payload(obj,'func_150F97EC');blob,bindings,_=d.derive(raw,refs)
    source=struct.unpack('>88I',raw);wanted=struct.unpack('>89I',blob);old=(BASE/'conker/retail_word_patches.us.csv').read_bytes()
    reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames;assert not[r for r in reader if r['function']=='func_150F97EC']
    rows=[];cursor=0
    def reloc(rs):return';'.join(k+':'+n for k,n in rs)or'-'
    for i,w in enumerate(source):
        row={key:''for key in fields};rr=bindings.get(cursor*4,[])
        row.update(filename='generated_124920',function='func_150F97EC',offset='0x%03X'%(i*4),expected='0x%08X'%w,replacement='0x%08X'%wanted[cursor],
            expected_relocations=reloc(refs.get(i*4,[])),replacement_relocations=reloc(rr),
            note='Normalize proved randomized effect actor reload and register scheduling',omit='false')
        changed=w!=wanted[cursor]or refs.get(i*4,[])!=rr;cursor+=1
        if i==12:
            assert cursor==13;row.update(insert_after='0x%08X'%wanted[cursor],insert_after_relocations=reloc(bindings.get(cursor*4,[])));cursor+=1;changed=True
        if changed:rows.append(row)
    assert cursor==89
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode());objects=[]
    for name,text in(('layout',pc.emit_padded_assembly(obj,ROOT/'conker/retail_layout.us.txt','generated_124920',word_patches_path=guards)),
                      ('assembly',pg.emit_padded_assembly(obj,ROOT/'conker/asm/124920.s',filename='generated_124920',word_patches_path=guards))):
        p=WHERE/(name+'.s');p.write_text(text);q=p.with_suffix('.o');subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],check=True,capture_output=True);objects.append(q)
    assert objects[0].read_bytes()==objects[1].read_bytes()
    a=pg.parse_object(BASE/'conker/build/src/game/generated_124920.c.o');b=pg.parse_object(objects[0]);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':356}if name=='func_150F97EC'else{})==h,(name,f,h)
        def contents(p,s):
            lo=s['value'];hi=lo+s['size'];return(p[0][lo:hi],{at-lo:rs for at,rs in p[2].items()if lo<=at<hi})
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert changed==['func_150F97EC'],changed
    (WHERE/'after-diagnostics.txt').write_text('')
    route=actual_Make(ROOT,WHERE,objects[0],obj,guards,'conker/src/game/generated_124920.c','conker/build/src/game/generated_124920.c.o',
        (OUT/'qualified-screen/selected-owner.c').read_text(),'target',17)
    assert route['commands']==5 and route['natural_live_recipe']
    with patch.multiple(linker,FILENAME='generated_124920',OBJECT='conker/build/src/game/generated_124920.c.o',LINKER='conker/build/conker.ld'):
        image=linker.link_image(ROOT,WHERE,objects[0],'image')
    before=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x150F97EC,356);prediction[at:at+356]=(ROOT/'conker/conker.us.bin').read_bytes()[0x126C9C:0x126E00]
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name=='func_150F97EC'];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(0x150F97EC,12);struct.pack_into('>I',prediction,at+8,356)
    (WHERE/'predicted-code-size.elf').write_bytes(prediction)
    prediction,permutations=permute_metadata(prediction)
    actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(prediction,actual))if a!=b]
    (WHERE/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected linked bytes',len(differences))
    (WHERE/'predicted.elf').write_bytes(prediction);fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    report=dict(guard_rows=len(rows),insertions=1,omissions=0,owner_functions=len(a[1]),actual_Make=route,padders_equal=True,strict_predicted_ELF_equal=True,
        changed_bytes=sum(a!=b for a,b in zip(before,prediction)),exclusions=0,function_slots=len(fs),protected_data=audit_layout(image,ROOT/'conker'),
        ELF_sha256=hashlib.sha256(actual).hexdigest(),metadata_swaps=permutations,named_definitions_preserved_by_swaps=True,matching_credit=0)
    (WHERE/'integration.json').write_text(json.dumps(report,indent=2)+'\n');return report
