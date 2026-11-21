"""Direct camera query recovery, natural Make and strict image gates."""
from pathlib import Path
import hashlib,json,os
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_camera_query_1509759c_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];SOURCE=MANIFEST['source'];FUNCTION=MANIFEST['function']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/SOURCE).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
    from tools.experiments.game_remaining_donor_candidates import compile_owner
    from tools.experiments.game_actor_state_tick_integration import same_functions
    from tools.experiments.game_selector_table_payload_match import diagnostic_rows
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.tests.game_owner_pool import normalized_pools
    for n in (SOURCE,MANIFEST['object'],'conker/build/conker.us.elf','conker/Makefile','conker/retail_word_patches.us.csv'):
        assert sha(OUT/'baseline'/n)==MANIFEST['inputs'][n],('frozen baseline changed',n)
    assert norm((ROOT/SOURCE).read_bytes())in(MANIFEST['old_source'].encode(),MANIFEST['selected_source'].encode())
    for n,d in MANIFEST['inputs'].items():
        if n==SOURCE:continue
        permitted={d}
        if n==MANIFEST['object']:permitted.add(MANIFEST['padded_sha256'])
        if n=='conker/Makefile':permitted.add(MANIFEST['make_sha256'])
        if n=='conker/retail_word_patches.us.csv':permitted.add(MANIFEST['guards_sha256'])
        if n=='conker/build/conker.us.elf':permitted.add(MANIFEST['predicted_ELF_sha256'])
        assert sha(ROOT/n)in permitted,n
    old_dir=OUT/'qualified-source';new_dir=OUT/'qualified-source'
    old_dir.mkdir(exist_ok=True);new_dir.mkdir(exist_ok=True)
    a,ad=compile_owner(ROOT,old_dir,MANIFEST['old_source'],'before')
    b,bd=compile_owner(ROOT,new_dir,MANIFEST['selected_source'],'candidate')
    assert diagnostic_rows(ad)==diagnostic_rows(bd)
    assert same_functions(a,b,(FUNCTION,))==6
    old_pools,new_pools=normalized_pools(a),normalized_pools(b)
    assert old_pools['.data']==new_pools['.data']
    assert old_pools['.rodata'] in (None,(b'',()))
    assert new_pools['.rodata']==(bytes(32),tuple((i,FUNCTION,o)for i,o in zip(range(0,20,4),(0xAC,0x8C,0x6C,0xCC,0x138))))
    assert hashlib.sha256(payload(b,FUNCTION)[0]).hexdigest()==MANIFEST['raw_sha256']
    (new_dir/'selected-owner.c').write_text(MANIFEST['selected_source'])
    return dict(installed=installed(),unchanged_neighbors=6,guards=0,words=127,frame=80)



def census():
    from pathlib import Path
    import json,struct,sys
    root=ROOT;out=OUT
    from tools.experiments.game_actor_classifier_candidates import sections
    from tools.experiments.game_actor_state_tick_integration import symbol_rows,elf_slot_offset
    rom=(root/'conker/conker.us.bin').read_bytes();entry=0x1509759C;calls=[];pointers=[];elf=(out/'baseline/conker/build/conker.us.elf').read_bytes()
    for i,w in enumerate(struct.unpack_from('>%dI'%(len(rom)//4),rom)):
     if w>>26 in(2,3)and(w&0x3FFFFFF)<<2==entry&0xFFFFFFF:
      offset=4*i;calls.append({'entry':0x15000000+offset-0x2D4B0,'ROM':offset,'kind':'JAL'if w>>26==3 else'J'})
    for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
     if not address or name.startswith(('.mdebug','.symtab','.strtab')):continue
     for at in range(0,len(data)-3,4):
      if struct.unpack_from('>I',data,at)[0]==entry:pointers.append({'section':name,'address':address+at,'surrounding_words':[hex(n)for n in struct.unpack_from('>%dI'%(min(48,len(data)-max(0,at-16))//4),data,max(0,at-16))]})
    values={}
    for name,(address,data)in sections(out/'baseline/conker/build/conker.us.elf').items():
     if address<=0x8009DF38 and address+len(data)>=0x8009DF50:
      values['jump_table']=[hex(v)for v in struct.unpack_from('>5I',data,0x8009DF38-address)]
      values['angle_constant_bits']=hex(struct.unpack_from('>I',data,0x8009DF4C-address)[0]);values['angle_constant']=struct.unpack_from('>f',data,0x8009DF4C-address)[0]
    r={'function':'func_1509759C','direct_original_calls':calls,'aligned_loaded_pointer_literals':pointers,'data':values,'scope':'Original direct-instruction and current frozen loaded aligned-pointer census; computed references are not excluded.','matching_credit':0,'source_installed':installed()}
    (out/'caller-census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r

def qualify():
    prepare()
    census()
    """Direct emitted-body, natural Make and complete linked-image prediction."""
    from pathlib import Path
    from unittest.mock import patch
    import csv,hashlib,json,re,shutil,struct,subprocess,sys
    root=ROOT;out=OUT
    from tools import pad_generated_object as pg
    sys.modules.setdefault('pad_generated_object',pg)
    from tools import pad_c_object as pc
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows,same_functions
    from tools.experiments import game_embedded_dual_phase_position_update_match as linker
    from tools.experiments import game_list_owner_make as route
    from tools.check_game_data_layout import audit_layout
    from tools.match_progress import load_elf_functions
    from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string,sections
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE='conker/src/game/generated_C3E20.c';OBJECT='conker/build/src/game/generated_C3E20.c.o';FUNCTION='func_1509759C'
    compact=out/'qualified-source/candidate.o';selected=(out/'qualified-source/selected-owner.c').read_text()
    original_guards=(base/'conker/retail_word_patches.us.csv').read_bytes()
    removed=[line for line in original_guards.splitlines(keepends=True)if b',func_1509759C,'in line]
    assert len(removed)==3
    rows=list(csv.DictReader(original_guards.decode().splitlines()))
    old_rows=[r for r in rows if r['function']==FUNCTION]
    assert [(int(r['offset'],0),int(r['expected'],0),r['omit'])for r in old_rows]==[(0,0xAFA40000,'true'),(4,0xAFA50004,'true'),(8,0xAFA60008,'true')]
    guard_bytes=b''.join(line for line in original_guards.splitlines(keepends=True)if b',func_1509759C,'not in line)
    guards=out/'selected-guards.csv';guards.write_bytes(guard_bytes)
    assert (root/'conker/retail_word_patches.us.csv').read_bytes()in(original_guards,guard_bytes)
    def assemble(name,text):
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,check=True)
        return obj
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+('glabel func_1509759C'+(root/'conker/asm/C3E20.s').read_text().split('glabel func_1509759C',1)[1].split('endlabel func_1509759C',1)[0]+'endlabel func_1509759C')+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    def canonical(path):
     blob,refs=payload(path,FUNCTION)
     return blob,{i:[(kind,'jtbl_8009DF38_game' if name in('.rodata','jtbl_8009DF38') else name)for kind,name in rows]for i,rows in refs.items()}
    assert canonical(truth)==canonical(compact)
    raw_text,raw_functions,_=pg.parse_object(compact);pool=sections(compact)['.rodata'][1];assert len(pool)==32 and pool[20:]==bytes(12)
    raw_table=struct.unpack_from('>5I',pool);table_words=[v-raw_functions[FUNCTION]['value']+0x1509759C for v in raw_table]
    assert table_words==[0x15097648,0x15097628,0x15097608,0x15097668,0x150976D4],table_words
    reloc_text=subprocess.check_output(['mips-linux-gnu-objdump','-r','-j','.rodata',str(compact)],text=True)
    rodata_relocs=re.findall(r'^([0-9a-f]{8})\s+(R_MIPS_\w+)\s+(\.\w+)',reloc_text,re.M)
    assert rodata_relocs==[(f'{i:08x}','R_MIPS_32','.text')for i in range(0,20,4)],rodata_relocs
    text=pg.emit_padded_assembly(compact,root/'conker/asm/C3E20.s',filename='generated_C3E20',word_patches_path=guards,rodata_symbol='jtbl_8009DF38_game')
    padded=assemble('padded',text)
    assert canonical(padded)==canonical(truth)
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==6
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
        expected=dict(f)
        if n==FUNCTION:expected['size']=508
        assert new[1][n]==expected,(n,f,new[1][n])
    (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
    make_before=(base/'conker/Makefile').read_text()
    binding='$(BUILD_DIR)/$(SRC_DIR)/game/generated_C3E20.c.o: RETAIL_RODATA_SYMBOL := jtbl_8009DF38_game'
    assert binding not in make_before
    make_selected=make_before.rstrip()+'\n'+binding+'\n'
    make_path=out/'selected-Makefile.txt';make_path.write_text(make_selected)
    assert (root/'conker/Makefile').read_text()in(make_before,make_selected)
    real_run=subprocess.run
    def make_run(args,*a,**kw):
     if args[0]=='make':args=[args[0],'-f',str(make_path.relative_to(root/'conker')),*args[1:]]
     return real_run(args,*a,**kw)
    with patch.object(route.subprocess,'run',make_run):
     make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',7)
    make.update(private_proposed_Makefile=True,natural_live_recipe=(root/'conker/Makefile').read_text()==make_selected)
    linked_owner=where/'qualified-owner/generated_C3E20.c.o';linked_owner.parent.mkdir(exist_ok=True)
    shutil.copyfile(padded,linked_owner);assert linked_owner.read_bytes()==padded.read_bytes()
    with patch.multiple(linker,FILENAME='generated_C3E20',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,linked_owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,0x1509759C,508);predicted[at:at+508]=(root/'conker/conker.us.bin').read_bytes()[0xc4a4c:0xc4c48]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];previous_size=old[1][FUNCTION]['size'];assert row[1:3]==(0x1509759C,previous_size)
    struct.pack_into('>I',predicted,at+8,508)
    # Only independently audited closed metadata changes are allowed.
    permutations=[
     (['jtbl_8009DF38_game','func_15071A34'],['func_15071A34','jtbl_8009DF38_game']),
     (['D_8009DF4C','D_800CC2B0','D_800C3600','D_800A694C'],['D_800CC2B0','D_800C3600','D_800A694C','D_8009DF4C']),
     (['func_1511F92C','D_800E0D88'],['D_800E0D88','func_1511F92C'])]
    head=ELF_HEADER.unpack_from(predicted);headers=[SECTION_HEADER.unpack_from(predicted,head[6]+i*head[11])for i in range(head[12])]
    names_header=headers[head[13]];names=predicted[names_header[4]:names_header[4]+names_header[5]]
    strings=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(strings)==1
    rows=symbol_rows(predicted);symbols={n:(at,row)for at,n,row,_ in rows if n};string_bytes=0
    for original_order,new_order in permutations:
     assert set(original_order)==set(new_order)and len(set(original_order))==len(original_order)
     first_at,first_row=symbols[original_order[0]];string_start=first_row[0]
     old_names=b''.join(n.encode()+b'\0'for n in original_order);offset=string_start
     for i,n in enumerate(original_order):
      symbol_at,row=symbols[n];assert symbol_at==first_at+16*i and row[0]==offset;offset+=len(n)+1
     assert{n for _,n,row,_ in rows if string_start<=row[0]<offset}==set(original_order)
     where_string=strings[0][4]+string_start;assert predicted[where_string:where_string+len(old_names)]==old_names
     new_names=b''.join(n.encode()+b'\0'for n in new_order);assert len(new_names)==len(old_names)
     predicted[where_string:where_string+len(old_names)]=new_names;offset=string_start
     for i,n in enumerate(new_order):
      row=symbols[n][1];struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*row[1:]);offset+=len(n)+1
     string_bytes+=len(old_names)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    (where/'pre-audit-predicted.elf').write_bytes(predicted)
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(direct_raw_and_padded_equal_original=True,words=127,frame=80,guards=0,insertions=0,omissions=0,
     owner_functions=7,unchanged_owner_functions=6,retail_slot_words=127,alignment_words=0,actual_Make=make,strict_predicted_ELF_equal=True,
     changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,function_slots=len(functions),
     ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=previous_size,closed_metadata_permutations=permutations,
     metadata_symbol_records=sum(len(a) for a,b in permutations),metadata_string_bytes=string_bytes,symbol_definitions_preserved_except_target_size=True,
    raw_table_words=table_words,raw_table_relocations=len(rodata_relocs),jump_table_reused=True,obsolete_omission_rows_removed=3,protected_data_audit=audit_layout(image,root/'conker'),
     source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
