"""Proposed exact-word guards, both owner routes and zero-exclusion image gate."""
from pathlib import Path
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_list_draw_1517e4a8_recovery as s
from tools.experiments.game_list_owner_make import actual_Make
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
from tools.experiments.game_list_historical_image import historical_dependencies
from tools.tests.game_list_draw_1517e4a8_normalizer import derive,OUT
BASE=OUT/'baseline'

def metadata_permutations(image):
    """Predict only two measured contiguous GNU symbol/string permutations."""
    result=bytearray(image)
    permutations=[(('func_15005C80','func_151F6970'),('func_151F6970','func_15005C80')),
                  (('D_800A131C','D_800AA7CC','D_800AEB7C'),('D_800AEB7C','D_800A131C','D_800AA7CC'))]
    for before,after in permutations:
        entries={name:(at,row,string)for at,name,row,string in symbol_rows(image)if name in before}
        assert set(entries)==set(before)
        rows=[entries[n]for n in before];start,_,string_start=rows[0]
        assert [r[0]for r in rows]==[start+16*i for i in range(len(before))]
        expected=b''.join(n.encode()+b'\0'for n in before)
        assert image[string_start:string_start+len(expected)]==expected
        first_name=rows[0][1][0];cursor=0
        for i,name in enumerate(after):
            record=list(entries[name][1]);record[0]=first_name+cursor
            struct.pack_into('>IIIBBH',result,start+16*i,*record)
            value=name.encode()+b'\0';result[string_start+cursor:string_start+cursor+len(value)]=value;cursor+=len(value)
        assert cursor==len(expected)
    def canonical(blob):return{n:r[1:]for at,n,r,string in symbol_rows(blob)}
    assert canonical(image)==canonical(bytes(result))
    return bytes(result),permutations

def qualify():
    root=s.ROOT;where=OUT/'qualification';where.mkdir(exist_ok=True)
    obj=s.WHERE/'candidate.o';raw,refs=s.payload(obj,s.FUNCTION);derived,bindings,proof=derive(raw,refs)
    original=list(struct.unpack('>361I',raw));wanted=list(struct.unpack('>361I',derived))
    old=(BASE/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']==s.FUNCTION]
    def reloc(r):return';'.join(kind+':'+name for kind,name in r)or'-'
    rows=[]
    for i,(value,replacement)in enumerate(zip(original,wanted)):
        expected_refs=refs.get(i*4,[]);replacement_refs=bindings.get(i*4,[])
        if value==replacement and expected_refs==replacement_refs:continue
        row={key:''for key in fields}
        row.update(filename='generated_1AB530',function=s.FUNCTION,offset='0x%03X'%(i*4),expected='0x%08X'%value,
            replacement='0x%08X'%replacement,expected_relocations=reloc(expected_refs),replacement_relocations=reloc(replacement_refs),
            note='Normalize proved flare draw register roles, conditional scheduling and private counter home',omit='false')
        rows.append(row)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    proposed=old+stream.getvalue().encode();guards=where/'proposed-guards.csv';guards.write_bytes(proposed)
    def assemble(label,text):
        p=where/(label+'.s');p.write_text(text);q=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(q),str(p)],capture_output=True,check=True)
        return q
    results={};padded=[]
    for label,source,owner,asm,compact,count in(('target',s.SOURCE,'generated_1AB530','1AB530','candidate.o',8),('helper',s.HELPER,'generated_C1D70','C1D70','helper-after.o',19)):
        compact=s.WHERE/compact
        a=assemble(label+'-layout',pc.emit_padded_assembly(compact,root/'conker/retail_layout.us.txt',owner,word_patches_path=guards))
        b=assemble(label+'-asm',pg.emit_padded_assembly(compact,root/('conker/asm/'+asm+'.s'),filename=owner,word_patches_path=guards))
        assert a.read_bytes()==b.read_bytes();padded.append(a)
        object_path='conker/build/src/game/'+owner+'.c.o'
        if label=='helper':assert a.read_bytes()==(BASE/object_path).read_bytes()
        selected=(s.WHERE/'selected-owner.c').read_text()if label=='target'else s.SPEC['selected_helper']
        (where/('after-diagnostics.txt'if label=='target'else label+'-after-diagnostics.txt')).write_text('')
        results[label]=actual_Make(root,where,a,compact,guards,source,object_path,selected,label,count)
        assert results[label]['commands']==3 and results[label]['natural_live_recipe']
    a=pg.parse_object(BASE/'conker/build/src/game/generated_1AB530.c.o');b=pg.parse_object(padded[0]);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];assert f|({'size':1444}if name==s.FUNCTION else{})==h,(name,f,h)
        def content(parsed,info):
            lo=info['value'];hi=lo+info['size'];return(parsed[0][lo:hi],{at-lo:rs for at,rs in parsed[2].items()if lo<=at<hi})
        if content(a,f)!=content(b,h):changed.append(name)
    assert changed==[s.FUNCTION],changed
    with historical_dependencies(root,where,s.SOURCE,s.SPEC)as script:
        with patch.multiple(linker,FILENAME='generated_1AB530',OBJECT='conker/build/src/game/generated_1AB530.c.o',LINKER=script):
            image=linker.link_image(root,where,padded[0],'image')
    previous=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(previous)
    at=elf_slot_offset(prediction,s.ENTRY,1444);retail=(root/'conker/conker.us.bin').read_bytes()[s.ROM:s.ROM+1444]
    prediction[at:at+1444]=retail
    matches=[(at,row)for at,name,row,_ in symbol_rows(prediction)if name==s.FUNCTION];assert len(matches)==1
    at,row=matches[0];assert(row[1],row[2])==(s.ENTRY,12);struct.pack_into('>I',prediction,at+8,1444)
    (where/'predicted-code-size.elf').write_bytes(prediction)
    prediction,permutations=metadata_permutations(prediction)
    (where/'predicted.elf').write_bytes(prediction)
    actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(prediction,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected linked bytes',len(differences),'see unpredicted-differences.json')
    fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    report=dict(guard_rows=len(rows),actual_Make=results,padders_equal=True,helper_complete_padded_object_unchanged=True,
        strict_predicted_ELF_equal=True,exclusions=0,function_slots=len(fs),protected_data_audit=audit_layout(image,root/'conker'),
        ELF_sha256=hashlib.sha256(actual).hexdigest(),source_installed=False,matching_credit=0,
        changed_bytes=sum(a!=b for a,b in zip(previous,prediction)),metadata_permutations=permutations,metadata_named_definitions_unchanged=True)
    (where/'integration.json').write_text(json.dumps(report,indent=2)+'\n');return report

from copy import deepcopy

def guard_controls():
    path=OUT/'qualification/proposed-guards.csv';counts={}
    for label,module in(('layout',pc),('assembly',pg)):
        guards=module.load_word_patches(path,'generated_1AB530')
        targets={key:row for key,row in guards.items()if key[0]==s.FUNCTION};assert len(targets)==162
        words=bindings=0
        def reject(changed,phrase):
            with patch.object(module,'load_word_patches',return_value=changed):
                try:
                    if label=='layout':module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/retail_layout.us.txt','generated_1AB530',word_patches_path=path)
                    else:module.emit_padded_assembly(s.WHERE/'candidate.o',s.ROOT/'conker/asm/1AB530.s',filename='generated_1AB530',word_patches_path=path)
                except ValueError as error:assert phrase in str(error),(label,str(error))
                else:raise AssertionError('Changed guard accepted')
        for key,row in targets.items():
            changed=deepcopy(guards);changed[key]['expected']^=1;reject(changed,'stale word patch');words+=1
            if row['expected_relocations']:
                changed=deepcopy(guards);changed[key]['expected_relocations']=[('R_MIPS_26','func_1517E4A8')]
                reject(changed,'stale relocations');bindings+=1
        counts[label]=dict(expected_word_controls=words,expected_binding_controls=bindings)
    report=dict(padders=counts,all_controls_rejected=True,matching_credit=0)
    (OUT/'guard-controls.json').write_text(json.dumps(report,indent=2)+'\n');return report
