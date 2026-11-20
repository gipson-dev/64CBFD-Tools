"""Private padder/actual Make and linked image gate; no installation."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_list_render_1517e28c_recovery as s
from tools.experiments import game_map_trail_constructor_15105ce0_match as driver
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.tests.game_list_render_1517e28c_normalizer import derive,OUT

def rotate(image):
    result=bytearray(image);names=('D_8008D008','func_1503FB40','D_8002BBE0')
    entries={name:(at,row,string)for at,name,row,string in symbol_rows(image)if name in names}
    assert set(entries)==set(names)
    rows=[entries[n]for n in names];start,_,string_start=rows[0]
    assert [r[0]for r in rows]==[start+16*i for i in range(3)]
    expected=b''.join(n.encode()+b'\0'for n in names)
    assert image[string_start:string_start+len(expected)]==expected
    first_name=rows[0][1][0];cursor=0
    for i,name in enumerate(names[1:]+names[:1]):
        record=list(entries[name][1]);record[0]=first_name+cursor
        struct.pack_into('>IIIBBH',result,start+16*i,*record)
        value=name.encode()+b'\0';result[string_start+cursor:string_start+cursor+len(value)]=value;cursor+=len(value)
    assert cursor==len(expected)==36
    return bytes(result)


def qualify():
    root=s.ROOT;base=s.OUT/'committed-baseline';where=OUT/'qualification';where.mkdir(exist_ok=True)
    obj=s.OUT/'banked-screen/candidate.o';raw,refs=s.payload(obj,s.FUNCTION);derived,bindings,proof=derive(raw,refs)
    original=list(struct.unpack('>132I',raw));wanted=list(struct.unpack('>135I',derived))
    old=(base/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']==s.FUNCTION]
    rows=[];cursor=0;inserted=[];omitted=[]
    def reloc(r):return';'.join(kind+':'+name for kind,name in r)or'-'
    for i,value in enumerate(original):
        row={key:''for key in fields}
        row.update(filename='generated_1AB530',function=s.FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%value,
            expected_relocations=reloc(refs.get(i*4,[])),note='Normalize proved list-flare conditional paths and helper-boundary scheduling',omit='false')
        if i in(67,76):
            row.update(replacement='0x%08X'%value,replacement_relocations=row['expected_relocations'],omit='true');omitted.append(i)
        else:
            replacement=wanted[cursor];replacement_refs=bindings.get(cursor*4,[])
            row.update(replacement='0x%08X'%replacement,replacement_relocations=reloc(replacement_refs));cursor+=1
            if cursor in(45,71,73,89,91):
                row.update(insert_after='0x%08X'%wanted[cursor],insert_after_relocations=reloc(bindings.get(cursor*4,[])))
                inserted.append(cursor);cursor+=1
            elif replacement==value and replacement_refs==refs.get(i*4,[]):continue
        rows.append(row)
    assert cursor==135 and inserted==[45,71,73,89,91]and omitted==[67,76]
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    proposed=old+stream.getvalue().encode();guards=where/'proposed-guards.csv';guards.write_bytes(proposed)
    padded=[]
    for label,text in(('layout',pc.emit_padded_assembly(obj,root/'conker/retail_layout.us.txt','generated_1AB530',word_patches_path=guards)),
        ('asm',pg.emit_padded_assembly(obj,root/'conker/asm/1AB530.s',filename='generated_1AB530',word_patches_path=guards))):
        p=where/(label+'.s');p.write_text(text);q=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(q),str(p)],capture_output=True,check=True)
        padded.append(q)
    assert padded[0].read_bytes()==padded[1].read_bytes()
    a=pg.parse_object(base/'conker/build/src/game/generated_1AB530.c.o');b=pg.parse_object(padded[0]);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':540}if name==s.FUNCTION else{})==h,(name,f,h)
        def content(parsed,info):
            lo=info['value'];hi=lo+info['size'];return(parsed[0][lo:hi],{at-lo:rs for at,rs in parsed[2].items()if lo<=at<hi})
        if content(a,f)!=content(b,h):changed.append(name)
    assert changed==[s.FUNCTION],changed
    selected=s.source()[1];(where/'after-diagnostics.txt').write_text('')
    object_path='conker/build/src/game/generated_1AB530.c.o'
    with patch.multiple(driver,ROOT=root,OUT=where,SOURCE=s.SOURCE,OBJECT=object_path,SPEC=dict(selected=selected)):
        route=driver.actual_Make(padded[0],obj,guards,source=s.SOURCE,object_path=object_path,selected=selected,functions=8)
        caller=(root/s.CALLER).read_text().replace('s32  func_1517E28C(s32 arg0, s32 arg1);','Gfx *func_1517E28C(Gfx *commands, s32 category);').replace('commands = (Gfx *)func_1517E28C((s32)commands, D_800BE9F0);','commands = func_1517E28C(commands, D_800BE9F0);')
        (where/'caller-after-diagnostics.txt').write_text((s.OUT/'banked-screen/caller-typed-diagnostics.txt').read_text())
        caller_route=driver.actual_Make(base/'conker/build/src/game_45B80.c.o',s.OUT/'banked-screen/caller-typed.o',guards,source=s.CALLER,object_path='conker/build/src/game_45B80.c.o',selected=caller,label='caller',functions=16)
    with patch.multiple(linker,FILENAME='generated_1AB530',OBJECT=object_path,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,padded[0],'image')
    previous=(base/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(previous)
    at=elf_slot_offset(prediction,s.ENTRY,540);retail=(root/'conker/conker.us.bin').read_bytes()[s.ROM:s.ROM+540]
    prediction[at:at+540]=retail
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name==s.FUNCTION];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(s.ENTRY,12);struct.pack_into('>I',prediction,at+8,540)
    prediction=rotate(prediction)
    assert image.read_bytes()==prediction,'More than the declared code/size/metadata changed'
    same=True
    (where/'predicted.elf').write_bytes(prediction)
    fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump');assert len(fs)==6051
    report=dict(guard_rows=len(rows),inserted_output_indices=inserted,omitted_source_rows=omitted,actual_Make=route,caller_actual_Make=caller_route,
        strict_predicted_ELF_equal=same,exclusions=0,function_slots=len(fs),protected_data_audit=audit_layout(image,root/'conker'),
        ELF_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),source_installed=s.BODY in(root/s.SOURCE).read_text(),credit=0)
    report.update(metadata_rotation=['D_8008D008','func_1503FB40','D_8002BBE0'],metadata_named_definitions_unchanged=True,changed_bytes=sum(a!=b for a,b in zip(previous,prediction)))
    (where/'integration.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
