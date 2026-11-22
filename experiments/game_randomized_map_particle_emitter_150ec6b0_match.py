"""Randomized map emitter, guarded instruction scheduling and strict image proof."""
from pathlib import Path
import hashlib,json,os,sys,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_randomized_map_particle_emitter_150ec6b0_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];FUNCTION='func_150EC6B0'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/MANIFEST['source']).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
    permitted={MANIFEST['source']:MANIFEST['selected_sha256'],MANIFEST['object']:MANIFEST['padded_sha256'],
        'conker/build/conker.us.elf':MANIFEST['predicted_ELF_sha256'],
        'conker/retail_word_patches.us.csv':MANIFEST['guards_sha256'],'conker/Makefile':MANIFEST['Makefile_sha256']}
    for name,digest in MANIFEST['inputs'].items():
        frozen=OUT/'baseline'/name
        if frozen.exists():assert sha(frozen)==digest,('Frozen baseline changed',name)
        assert sha(ROOT/name)in {digest,permitted.get(name,digest)},name
    return installed()
def inspect_source():
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_actor_state_tick_integration import same_functions
    from tools.experiments.game_selector_table_payload_match import diagnostic_rows
    root,out=ROOT,OUT;where=out/'early-payload';where.mkdir(exist_ok=True)
    before,bd=compile_owner(root,where,MANIFEST['old_source'],'before')
    after,ad=compile_owner(root,where,MANIFEST['selected_source'],'candidate')
    assert diagnostic_rows(bd)==diagnostic_rows(ad)and same_functions(before,after,(FUNCTION,))==6
    raw,refs=payload(after,FUNCTION)
    assert hashlib.sha256(raw).hexdigest()=='74539b4f1c7cf3d1a9aa4af97ddd5b15bf3c7aeb2385d87295c4b26c88175bed'
    assert len(raw)==948 and int.from_bytes(raw[:4],'big')==0x27BDFEF0
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    from tools.experiments.game_actor_state_tick_integration import symbol_rows
    symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n};symbols['.rodata']=0x800A1578
    (where/'words.json').write_text(json.dumps(bound_blob(raw,refs,symbols))+chr(10))
    (where/'selected-owner.c').write_text(MANIFEST['selected_source'])
    return {'words':237,'frame':272,'unchanged_neighbors':6}
def normalize():
    from pathlib import Path
    import csv,hashlib,json,struct,subprocess,sys
    root,out=ROOT,OUT
    from tools import pad_generated_object as pg
    sys.modules.setdefault('pad_generated_object',pg)
    from tools import pad_c_object as pc
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
    from tools.experiments.game_actor_classifier_candidates import sections
    from tools.tests.game_owner_pool import normalized_pools
    NAME='func_150EC6B0';obj=out/'early-payload/candidate.o'
    raw,refs=payload(obj,NAME);ws=list(struct.unpack('>237I',raw))
    assert hashlib.sha256(raw).hexdigest()=='74539b4f1c7cf3d1a9aa4af97ddd5b15bf3c7aeb2385d87295c4b26c88175bed'
    pool=normalized_pools(obj)['.rodata'];expected_pool=bytes.fromhex('44D4400038D1B7173F7870B93F82B1143DC8B43A3E3020C5')
    assert pool[0][:24]==expected_pool and not any(pool[0][24:])and not pool[1]
    items=[(i,w,refs.get(4*i,[]))for i,w in enumerate(ws)]
    pointer=items.pop(50);assert pointer[1]==0x27B7009C
    zero_index=next(i for i,x in enumerate(items)if x[1]==0x44800000)
    zero=items.pop(zero_index)
    items[57:57]=[zero,(-1,0,[])]
    items.insert(100,pointer)
    assert len(items)==238 and sorted(i for i,w,r in items if i>=0)==list(range(237))
    fixes={55:(0x450200A3,0x450200A5,'Adjust forward branch for the preserved setup schedule'),
           168:(0x8FAF00F4,0x8FAC00F4,'Close the T4 T7 temporary exchange across commutative OR'),
           172:(0x00506025,0x00507825,'Close the T4 T7 temporary exchange across commutative OR'),
           199:(0x461E9080,0x461E9180,'Use the retail caller-volatile extent-result register'),
           200:(0xE7A200C8,0xE7A600C8,'Use the retail caller-volatile extent-result register'),
           201:(0xE7A200C4,0xE7A600C4,'Use the retail caller-volatile extent-result register'),
           212:(0xC626000C,0xC628000C,'Close the final caller-volatile floating temporary sequence'),
           213:(0x46163201,0x46164101,'Close the final caller-volatile floating temporary sequence'),
           214:(0xE628000C,0xE624000C,'Close the final caller-volatile floating temporary sequence'),
           215:(0xC624000C,0xC62A000C,'Close the final caller-volatile floating temporary sequence'),
           216:(0x4604B03C,0x460AB03C,'Close the final caller-volatile floating temporary sequence')}
    for index,(expected,replacement,note)in fixes.items():
        origin,word,relocs=items[index];assert word==expected and not relocs,(index,hex(word))
        items[index]=(origin,replacement,relocs)
    newraw=b''.join(struct.pack('>I',word)for origin,word,rr in items)
    newrefs={4*i:rr for i,(origin,word,rr)in enumerate(items)if rr}
    symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
    symbols['.rodata']=0x800A1578
    truth=list(struct.unpack_from('>238I',(root/'conker/conker.us.bin').read_bytes(),0x119B60))
    assert bound_blob(newraw,newrefs,symbols)==truth
    source=out/'baseline/conker/retail_word_patches.us.csv'
    with source.open(newline='')as f:reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
    assert not any(r['function']==NAME for r in rows)
    spell=lambda rr:';'.join(k+':'+v for k,v in rr)if rr else '-'
    added=[]
    for index,word in enumerate(ws):
        output_index=index if index<=57 else index+1
        origin,replacement,rr=items[output_index];old_rr=refs.get(index*4,[])
        if word==replacement and old_rr==rr and index!=57:continue
        note=fixes[output_index][2]if output_index in fixes else 'Normalize independent emitter packet-address and floating-zero setup schedule'
        if index==57:note='Retain the floating-zero setup and retail coprocessor hazard nop'
        row=dict(filename='generated_1199D0',function=NAME,offset=f'0x{index*4:03X}',
            expected=f'0x{word:08X}',replacement=f'0x{replacement:08X}',
            expected_relocations=spell(old_rr),replacement_relocations=spell(rr),note=note,
            insert_after='0x00000000'if index==57 else '',insert_after_relocations='-'if index==57 else '',omit='false')
        added.append(row)
    guards=out/'private-word-patches.csv'
    import io
    tail=io.StringIO(newline='')
    csv.DictWriter(tail,fieldnames=fields).writerows(added)
    original_guards=source.read_bytes();assert original_guards.endswith(b'\n')
    guards.write_bytes(original_guards+tail.getvalue().encode())
    def assemble(text,name):
        path=out/(name+'.s');path.write_text(text);target=path.with_suffix('.o')
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(target),str(path)],capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return target
    padded=assemble(pg.emit_padded_assembly(obj,root/'conker/asm/1199D0.s',filename='generated_1199D0',word_patches_path=guards,rodata_symbol='D_800A1578'),'private-padded')
    assert same_functions(out/'baseline/conker/build/src/game/generated_1199D0.c.o',padded,(NAME,))==6
    isolated_text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
    for i,word in enumerate(ws):
        for kind,symbol in refs.get(4*i,[]):isolated_text+=f'.reloc ., {kind}, {symbol}\n'
        isolated_text+=f'.word 0x{word:08X}\n'
    isolated_text+='.size '+NAME+',.-'+NAME+'\n'
    isolated=assemble(isolated_text,'isolated-raw')
    layout_lines=(root/'conker/retail_layout.us.txt').read_text().splitlines()
    layout_rows=[line for line in layout_lines[1:]if line.split(',')[1:3]==['generated_1199D0',NAME]];assert len(layout_rows)==1
    layout=out/'target-layout.csv';layout.write_text(layout_lines[0]+'\n'+layout_rows[0]+'\n')
    generic=assemble(pc.emit_padded_assembly(isolated,layout,'generated_1199D0',word_patches_path=guards,rodata_symbol='D_800A1578'),'private-generic')
    assert payload(generic,NAME)==payload(padded,NAME)
    full=(root/'conker/asm/1199D0.s').read_text();body='glabel '+NAME+full.split('glabel '+NAME,1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME
    retail=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+NAME+',.-'+NAME+'\n','original-target')
    links=0
    used={name for rr in payload(retail,NAME)[1].values()for kind,name in rr}|{name for rr in payload(padded,NAME)[1].values()for kind,name in rr}
    for rebase in(0,0x7FFC,0x8000,0xFFFC):
        values={name:symbols[name]+rebase for name in used}
        streams=[]
        for object_path,label in((padded,'normalized'),(retail,'retail')):
            script=out/(f'link-{rebase:X}-{label}.ld');script.write_text('SECTIONS { .text 0x150EC6B0 : SUBALIGN(4) { *(.text) } }\n')
            # The padded owner has other functions and symbols; compare only the target extent.
            if label=='normalized':
                target_raw,target_refs=payload(padded,NAME)
                text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n'+NAME+':\n'
                for i,(word,)in enumerate(struct.iter_unpack('>I',target_raw)):
                    for kind,symbol in target_refs.get(4*i,[]):text+=f'.reloc ., {kind}, {symbol}\n'
                    text+=f'.word 0x{word:08X}\n'
                text+='.size '+NAME+',.-'+NAME+'\n';object_path=assemble(text,'isolated-normalized')
            elf=script.with_suffix('.elf')
            q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in values.items()],'-o',str(elf),str(object_path)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr;streams.append(sections(elf)['.text'][1][:952]);links+=1
        assert streams[0]==streams[1],rebase
    r={'raw_words':237,'normalized_words':238,'frame':272,'guards':len(added),'inserted_hazard_nops':1,
       'omissions':0,'semantic_instruction_origins_preserved_once':237,'closed_register_repair_words':10,
       'constant_pool_bytes':24,'constant_pool_matches_retail':True,'unchanged_neighbors':6,
       'GNU_links':links,'rebases':4,'both_padders_equal':True,'linked_target_equals_retail':True,
       'source_installed':installed(),'matching_credit':0}
    (out/'normalization.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    return r
def qualify():
    from pathlib import Path
    from unittest.mock import patch
    import hashlib,json,shutil,struct,subprocess,sys
    root,out=ROOT,OUT
    from tools.experiments import game_list_owner_make as route
    from tools.experiments import game_embedded_dual_phase_position_update_match as linker
    from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
    from tools.check_game_data_layout import audit_layout
    from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE='conker/src/game/generated_1199D0.c';OBJECT='conker/build/src/game/generated_1199D0.c.o';NAME='func_150EC6B0'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    prepare();inspect_source();normalize()
    normal=json.loads((out/'normalization.json').read_text());assert normal['linked_target_equals_retail']and normal['guards']==19
    selected=(out/'early-payload/selected-owner.c').read_text()
    compact=out/'early-payload/candidate.o';padded=out/'private-padded.o';guards=out/'private-word-patches.csv'
    assert same_functions(base/OBJECT,padded,(NAME,))==6
    (where/'after-diagnostics.txt').write_text((out/'early-payload/candidate-diagnostics.txt').read_text())
    real_run=subprocess.run
    def proposed_make(*args,**kwargs):
        command=args[0]
        if command and command[0]=='make':
            args=([*command[:-1],'RETAIL_RODATA_SYMBOL=D_800A1578',command[-1]],*args[1:])
        return real_run(*args,**kwargs)
    with patch.object(route.subprocess,'run',side_effect=proposed_make):
        make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',7)
    make['proposed_rodata_binding_override']='D_800A1578'
    owner=where/'qualified-owner/generated_1199D0.c.o';owner.parent.mkdir(exist_ok=True);shutil.copyfile(padded,owner)
    with patch.multiple(linker,FILENAME='generated_1199D0',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,0x150EC6B0,952)
    predicted[at:at+952]=(root/'conker/conker.us.bin').read_bytes()[0x119B60:0x119F18]
    entries=[(at,row)for at,name,row,_ in symbol_rows(predicted)if name==NAME];assert len(entries)==1
    at,row=entries[0];assert row[1:3]==(0x150EC6B0,12);struct.pack_into('>I',predicted,at+8,952)
    # The first fail-closed comparison isolated this one adjacent GNU symbol-table
    # permutation. Predict its records and strings explicitly; exclude no bytes.
    old_order=['D_80099F38','D_800E0E08'];new_order=old_order[::-1]
    rows=symbol_rows(predicted);symbols={name:(at,row)for at,name,row,_ in rows if name}
    first_at,first_row=symbols[old_order[0]];start=first_row[0];offset=start
    for i,name in enumerate(old_order):
        symbol_at,symbol_row=symbols[name]
        assert symbol_at==first_at+16*i and symbol_row[0]==offset
        offset+=len(name)+1
    assert {name for _,name,symbol_row,_ in rows if start<=symbol_row[0]<offset}==set(old_order)
    header=ELF_HEADER.unpack_from(predicted)
    headers=[SECTION_HEADER.unpack_from(predicted,header[6]+i*header[11])for i in range(header[12])]
    names_header=headers[header[13]];names=predicted[names_header[4]:names_header[4]+names_header[5]]
    string_headers=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(string_headers)==1
    at=string_headers[0][4]+start
    old_strings=b''.join(name.encode()+b'\0'for name in old_order)
    new_strings=b''.join(name.encode()+b'\0'for name in new_order)
    assert predicted[at:at+len(old_strings)]==old_strings and len(old_strings)==len(new_strings)
    predicted[at:at+len(old_strings)]=new_strings;offset=start
    for i,name in enumerate(new_order):
        symbol_row=symbols[name][1];struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*symbol_row[1:]);offset+=len(name)+1
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences)+'\n')
    assert not differences,('Unexpected complete-image differences',len(differences),differences[:12])
    (where/'predicted.elf').write_bytes(predicted)
    r={'raw_words':237,'normalized_words':238,'frame':272,'guards':19,'inserted_hazard_nops':1,'omissions':0,
       'actual_Make':make,'strict_predicted_ELF_equal':True,'changed_bytes':sum(a!=b for a,b in zip(before,actual)),
       'exclusions':0,'metadata_permutations':[[old_order,new_order]],'metadata_symbol_records':2,
       'metadata_string_bytes':len(old_strings),'ELF_sha256':hashlib.sha256(actual).hexdigest(),
       'protected_data_audit':audit_layout(image,root/'conker'),'unchanged_owner_neighbors':6,
       'production_build_verified':False,'source_installed':installed(),'matching_credit':0}
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
    return r
