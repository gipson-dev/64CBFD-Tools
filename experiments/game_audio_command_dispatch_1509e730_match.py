"""Qualify both padders, proposed natural Make recipe and a strict full image."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,re,struct,subprocess,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT

from tools.tests.game_audio_command_dispatch_1509e730_normalizer import emit
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_list_owner_make as make_route
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
def qualify():
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE='conker/src/game/generated_CBAF0.c';OBJECT='conker/build/src/game/generated_CBAF0.c.o';FUNCTION='func_1509E730'
    compact=out/'qualified-source-screen/candidate.o';raw,refs=payload(compact,FUNCTION);blob,bindings,_=emit(raw,refs)
    words=struct.unpack('>92I',raw);wanted=struct.unpack('>92I',blob)
    old=(base/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']==FUNCTION];rows=[]
    def reloc(entries):return';'.join(kind+':'+name for kind,name in entries)or'-'
    for i,word in enumerate(words):
        before,after=refs.get(i*4,[]),bindings.get(i*4,[])
        if wanted[i]==word and before==after:continue
        row={key:''for key in fields};row.update(filename='generated_CBAF0',function=FUNCTION,offset='0x%03X'%(i*4),
          expected='0x%08X'%word,replacement='0x%08X'%wanted[i],expected_relocations=reloc(before),replacement_relocations=reloc(after),
          omit='false',note='Move dominated audio-dispatch zero return to its default block and rebase the closed instruction schedule')
        rows.append(row)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=where/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode())
    def assemble(name,text):
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],check=True,capture_output=True)
        return obj
    layout_text=pc.emit_padded_assembly(compact,root/'conker/retail_layout.us.txt','generated_CBAF0',rodata_symbol='jtbl_8009F3D0',word_patches_path=guards)
    assembly_text=pg.emit_padded_assembly(compact,root/'conker/asm/CBAF0.s',filename='generated_CBAF0',rodata_symbol='jtbl_8009F3D0',word_patches_path=guards)
    layout=assemble('layout',layout_text);assembly=assemble('assembly',assembly_text)
    assert pg.parse_object(layout)==pg.parse_object(assembly)
    # The layout-only padder has no original jlabel namespace. Reintroduce only
    # the seven independently qualified original case labels at their exact PCs.
    start,_,_,labels=pg.parse_retail_slice(root/'conker/asm/CBAF0.s')
    expected_labels=json.loads((out/'normalizer-qualification.json').read_text())['new_code_pointer_entries']
    assert set(labels)==set(expected_labels)and len(labels)==7
    position=0;remaining=dict(labels);augmented=[]
    for line in layout_text.splitlines():
        if line.startswith(('.word ','.reloc '))and start+position in remaining:
            for name in remaining.pop(start+position):augmented.extend(('.globl '+name,name+':'))
        augmented.append(line)
        if line.startswith('.word '):position+=4
        elif line.startswith('.space '):
            count=int(line.split()[1].rstrip(','),0)
            assert not any(start+position<=address<start+position+count for address in remaining)
            position+=count
    assert not remaining
    augmented_text='\n'.join(augmented)+'\n'
    augmented_text=augmented_text.replace('/* C-compiled functions re-spaced using retail_layout.us.txt. */','/* C-compiled functions padded to retail layout from CBAF0.s. */')
    assert augmented_text==assembly_text
    labelled_layout=assemble('layout-with-original-labels',augmented_text)
    assert labelled_layout.read_bytes()==assembly.read_bytes()
    a=pg.parse_object(base/OBJECT);b=pg.parse_object(assembly);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':368}if name==FUNCTION else{})==h,(name,f,h)
        def contents(parsed,symbol):
            lo=symbol['value'];hi=lo+symbol['size'];return parsed[0][lo:hi],{at-lo:rs for at,rs in parsed[2].items()if lo<=at<hi}
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert changed==[FUNCTION],changed
    make_before=(base/'conker/Makefile').read_bytes();recovery.validate_inputs()
    addition=b'\n# Audio command dispatch retains its original seven-entry table.\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_CBAF0.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009F3D0\n$(BUILD_DIR)/$(SRC_DIR)/game/generated_CBAF0.c.o: Makefile\n'
    proposed_make=where/'proposed-Makefile';proposed_make.write_bytes(make_before+addition)
    (where/'after-diagnostics.txt').write_text('')
    original_run=subprocess.run
    def run_proposed(command,*args,**kwargs):
        if command[0]=='make':command=[command[0],'-f',proposed_make.relative_to(root/'conker').as_posix(),*command[1:]]
        return original_run(command,*args,**kwargs)
    with patch.object(make_route.subprocess,'run',side_effect=run_proposed):
        route=make_route.actual_Make(root,where,assembly,compact,guards,SOURCE,OBJECT,
            (out/'qualified-source-screen/selected-owner.c').read_text(),'target',4)
    route.update(proposed_Makefile=True,production_Makefile_unchanged=True)
    with patch.multiple(linker,FILENAME='generated_CBAF0',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,assembly,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x1509E730,368);prediction[at:at+368]=(root/'conker/conker.us.bin').read_bytes()[0xcbbe0:0xcbd50]
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name==FUNCTION];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(0x1509E730,a[1][FUNCTION]['size'])
    previous_size=row[2];struct.pack_into('>I',prediction,at+8,368)
    # The newly referenced table changes GNU ld's serialization order for one
    # adjacent ABS/function pair. Preserve each complete definition and model
    # only the closed two-record/two-string permutation, with no exclusions.
    symbol_map={name:(at,row)for at,name,row,_ in symbol_rows(prediction)if name}
    first_name,second_name='D_80099A24','func_151F8960'
    first_at,first_row=symbol_map[first_name];second_at,second_row=symbol_map[second_name]
    assert second_at==first_at+16 and first_row[1:]==(0x80099a24,0,16,0,65521)and second_row[1:]==(0x151f8960,52,18,0,5)
    first_string=first_name.encode()+b'\0';second_string=second_name.encode()+b'\0'
    assert second_row[0]==first_row[0]+len(first_string)
    head=ELF_HEADER.unpack_from(prediction)
    headers=[SECTION_HEADER.unpack_from(prediction,head[6]+i*head[11])for i in range(head[12])]
    name_header=headers[head[13]];section_names=prediction[name_header[4]:name_header[4]+name_header[5]]
    strtab=[row for row in headers if read_c_string(section_names,row[0])=='.strtab'];assert len(strtab)==1
    start_string=strtab[0][4]+first_row[0];string_size=len(first_string)+len(second_string)
    assert prediction[start_string:start_string+string_size]==first_string+second_string
    assert{name for _,name,row,_ in symbol_rows(prediction)if first_row[0]<=row[0]<first_row[0]+string_size}=={first_name,second_name}
    prediction[start_string:start_string+string_size]=second_string+first_string
    struct.pack_into('>IIIBBH',prediction,first_at,first_row[0],*second_row[1:])
    struct.pack_into('>IIIBBH',prediction,second_at,first_row[0]+len(second_string),*first_row[1:])
    actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,x,y)for i,(x,y)in enumerate(zip(prediction,actual))if x!=y]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('Unexpected linked bytes',len(differences),differences[:12])
    (where/'predicted.elf').write_bytes(prediction)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    report=dict(guard_rows=len(rows),insertions=0,omissions=0,owner_functions=len(a[1]),unchanged_owner_functions=3,
     both_padders_text_functions_and_bindings_identical=True,namespace_augmented_layout_object_equal=True,
     original_jump_labels_preserved=7,natural_assembly_padder_used=True,actual_Make=route,strict_predicted_ELF_equal=True,
     changed_bytes=sum(x!=y for x,y in zip(before,actual)),exclusions=0,function_slots=len(functions),
     proposed_ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_size,
     closed_metadata_permutation=[first_name,second_name],metadata_string_bytes=string_size,metadata_symbol_records=2,
     protected_data_audit=audit_layout(image,root/'conker'),source_installed=recovery.installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
