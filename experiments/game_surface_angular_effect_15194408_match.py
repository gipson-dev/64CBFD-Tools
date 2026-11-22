"""Direct angular surface effect with explicit compact-pool and whole-image gates."""
from pathlib import Path
import hashlib,json,os,sys,struct
ROOT=Path(os.environ.get('CBFD_CONSUMER_ROOT',Path(__file__).resolve().parents[2])).resolve()
MANIFEST=json.loads(Path(__file__).with_name('game_surface_angular_effect_15194408_manifest.json').read_text())
OUT=ROOT/MANIFEST['build'];root,out=ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
norm=lambda b:b.replace(b'\r\n',b'\n')
def installed():return norm((ROOT/MANIFEST['source']).read_bytes())==MANIFEST['selected_source'].encode()
def prepare():
 for n,d in MANIFEST['inputs'].items():
  if (OUT/'baseline'/n).exists():assert sha(OUT/'baseline'/n)==d,('frozen baseline changed',n)
  permitted={d}
  if n==MANIFEST['source']:permitted.add(MANIFEST['selected_sha256'])
  if n==MANIFEST['object']:permitted.add(MANIFEST['padded_sha256'])
  if n=='conker/build/conker.us.elf':permitted.add(MANIFEST['predicted_ELF_sha256'])
  if n=='conker/retail_word_patches.us.csv':permitted.add(MANIFEST['selected_guards_sha256'])
  assert sha(ROOT/n)in permitted,n
 return installed()
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_selector_table_payload_match import diagnostic_rows
from tools.tests.game_owner_pool import normalized_pools
SOURCE=MANIFEST['source'];FUNCTION=MANIFEST['function'];ENTRY=0x15194408;ROM=0x1C18B8;WORDS=96
TYPES=MANIFEST['types'];BODY=MANIFEST['body']
def proposal(selected=BODY):
    old=(out/'baseline'/SOURCE).read_text();start,end=function_span(old,FUNCTION)
    source=old[:start]+TYPES+'\n/* Submit the surface-aligned angular effect for actor kinds zero through four. */\n'+selected+old[end:]
    # Both real callers pass the second actor in A1. This pointer declaration
    # repairs the wrapper's old integer view without changing its instructions.
    return source.replace('void func_15194588(u8 *arg0, s32 arg1, s32 arg2)',
                          'void func_15194588(u8 *arg0, u8 *arg1, s32 arg2)')

def inspect(selected=BODY,label='first-source'):
    where=out/label;where.mkdir(exist_ok=True)
    before,ad=compile_owner(root,where,(out/'baseline'/SOURCE).read_text(),'before')
    source=proposal(selected);after,bd=compile_owner(root,where,source,'candidate')
    assert diagnostic_rows(ad)==diagnostic_rows(bd),(diagnostic_rows(ad),diagnostic_rows(bd))
    from tools.pad_generated_object import parse_object
    parsed_a,parsed_b=parse_object(before),parse_object(after)
    assert set(parsed_a[1])==set(parsed_b[1])
    moved=[]
    for name in parsed_a[1]:
        if name==FUNCTION:continue
        a,ar=payload(before,name);b,br=payload(after,name)
        if (a,ar)!=(b,br):moved.append(name)
    neighbors=len(parsed_a[1])-1-len(moved)
    blob,refs=payload(after,FUNCTION)
    symbols={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
    # The new table begins after the two already present five-entry tables.
    symbols['.rodata']=symbols['jtbl_800A8258_game']
    words=bound_blob(blob,refs,symbols);original=struct.unpack_from('>96I',(root/'conker/conker.us.bin').read_bytes(),ROM)
    changes=[dict(word=i,C=f'{a:08x}',original=f'{b:08x}')for i,(a,b)in enumerate(zip(words,original))if a!=b]
    frames=[65536-(w&65535)for w in words if w&0xFFFF0000==0x27BD0000 and w&0x8000]
    def pools(p):
        return {n:None if v is None else dict(hex=v[0].hex(),targets=v[1])for n,v in normalized_pools(p).items()}
    r=dict(words=len(words),frame=max(frames,default=0),differences=len(changes)+abs(len(words)-96),changed_words=changes,bindings=refs,unchanged_neighbors=neighbors,raw_changed_neighbors=moved,relocation_sites=len(refs),raw_sha256=hashlib.sha256(blob).hexdigest(),pools_before=pools(before),pools_after=pools(after),source_installed=False,matching_credit=0)
    (where/'selected-owner.c').write_text(source);(out/(label+'.json')).write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in('changed_words','bindings','pools_before','pools_after')}));return r

def qualify():
    prepare()
    """Close the target, compact-pool move, one guard precondition and full image."""
    from pathlib import Path
    from unittest.mock import patch
    import hashlib,json,re,shutil,struct,sys
    root=ROOT;out=OUT
    screen=sys.modules[__name__]
    from tools import pad_generated_object as pg
    from tools.experiments.game_paired_ground_constructor_match import payload
    from tools.experiments.game_path_heading_turn_roles import bound_blob
    from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows,elf_slot_offset
    from tools.experiments import game_embedded_dual_phase_position_update_match as linker
    from tools.experiments import game_list_owner_make as route
    from tools.check_game_data_layout import audit_layout
    from tools.match_progress import load_elf_functions
    base=out/'baseline';where=out/'image-qualification';where.mkdir(exist_ok=True)
    SOURCE=screen.SOURCE;FUNCTION=screen.FUNCTION;OBJECT='conker/build/src/game/generated_1C1150.c.o'
    record=screen.inspect(label='qualified-source');assert record['words']==96 and record['frame']==152 and record['differences']==0
    assert record['raw_changed_neighbors']==['func_15194794']and record['unchanged_neighbors']==27
    a=record['pools_before'];b=record['pools_after'];assert a['.data']==b['.data']is None
    old=a['.rodata'];new=b['.rodata'];assert set(bytes.fromhex(old['hex']))==set(bytes.fromhex(new['hex']))=={0}
    expected=[tuple(v)for v in old['targets'][:10]]+[(40+4*i,FUNCTION,56)for i in range(5)]+[(v[0]+20,*v[1:])for v in old['targets'][10:]]
    assert [tuple(v)for v in new['targets']]==expected
    assert len(bytes.fromhex(old['hex']))==64 and len(bytes.fromhex(new['hex']))==80
    compact=out/'qualified-source/candidate.o';beforecompact=out/'qualified-source/before.o'
    ab,ar=payload(beforecompact,'func_15194794');bb,br=payload(compact,'func_15194794')
    assert ar==br;expected_bytes=bytearray(ab);assert struct.unpack_from('>I',ab,0x54)[0]==0x8C2E0028
    struct.pack_into('>I',expected_bytes,0x54,0x8C2E003C);assert bb==expected_bytes
    oldguards=(base/'conker/retail_word_patches.us.csv').read_bytes()
    token=b'generated_1C1150,func_15194794,0x054,0x8C2E0028,0x8C2E0000,'
    assert oldguards.count(token)==1
    newguards=oldguards.replace(token,token.replace(b'0x8C2E0028',b'0x8C2E003C'),1)
    guards=out/'qualified-guards.csv';guards.write_bytes(newguards)
    assert sum(a!=b for a,b in zip(oldguards,newguards))==2 and len(oldguards)==len(newguards)
    assert root.joinpath('conker/retail_word_patches.us.csv').read_bytes()in(oldguards,newguards)
    assert ',func_15194408,'not in newguards.decode()

    def assemble(name,text):
        import subprocess
        p=where/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
        q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(root/'conker/include'),'-o',str(obj),str(p)],capture_output=True,text=True)
        assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr)
        return obj
    original=(root/'conker/asm/1C1150.s').read_text();body='glabel '+FUNCTION+original.split('glabel '+FUNCTION,1)[1].split('endlabel '+FUNCTION,1)[0]+'endlabel '+FUNCTION
    body=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',body)
    truth=assemble('retail','.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'\n.size '+FUNCTION+',.-'+FUNCTION+'\n')
    lookup={n:r[1]for _,n,r,_ in symbol_rows((base/'conker/build/conker.us.elf').read_bytes())if n};lookup['.rodata']=lookup['jtbl_800A8258_game']
    retail=list(struct.unpack_from('>96I',(root/'conker/conker.us.bin').read_bytes(),screen.ROM))
    assert bound_blob(*payload(truth,FUNCTION),lookup)==bound_blob(*payload(compact,FUNCTION),lookup)==retail
    text=pg.emit_padded_assembly(compact,root/'conker/asm/1C1150.s',filename='generated_1C1150',word_patches_path=guards,rodata_symbol='jtbl_800A8258_game')
    padded=assemble('padded',text)
    assert bound_blob(*payload(padded,FUNCTION),lookup)==retail
    assert same_functions(base/OBJECT,padded,(FUNCTION,))==28
    old=pg.parse_object(base/OBJECT);new=pg.parse_object(padded)
    for n,f in old[1].items():
        expected=dict(f)
        if n==FUNCTION:expected['size']=384
        assert new[1][n]==expected,(n,f,new[1][n])
    selected=(out/'qualified-source/selected-owner.c').read_text()
    (where/'after-diagnostics.txt').write_text((out/'qualified-source/candidate-diagnostics.txt').read_text())
    make=route.actual_Make(root,where,padded,compact,guards,SOURCE,OBJECT,selected,'target',29)
    linked_owner=where/'qualified-owner/generated_1C1150.c.o';linked_owner.parent.mkdir(exist_ok=True);shutil.copyfile(padded,linked_owner)
    with patch.multiple(linker,FILENAME='generated_1C1150',OBJECT=OBJECT,LINKER='conker/build/conker.ld'):
        image=linker.link_image(root,where,linked_owner,'image')
    before=(base/'conker/build/conker.us.elf').read_bytes();predicted=bytearray(before)
    at=elf_slot_offset(predicted,screen.ENTRY,384);predicted[at:at+384]=(root/'conker/conker.us.bin').read_bytes()[screen.ROM:screen.ROM+384]
    matches=[(at,row)for at,n,row,_ in symbol_rows(predicted)if n==FUNCTION];assert len(matches)==1
    at,row=matches[0];assert row[1:3]==(screen.ENTRY,12);struct.pack_into('>I',predicted,at+8,384)
    # GNU ld changed the order of three adjacent absolute-symbol pairs. Predict
    # those closed permutations from the old named records, preserving every field.
    from tools.experiments.game_actor_classifier_candidates import ELF_HEADER,SECTION_HEADER,read_c_string
    permutations=[(['D_800A8298','D_8008FAD0'],['D_8008FAD0','D_800A8298']),
                  (['D_800D2890','D_800E0DA0'],['D_800E0DA0','D_800D2890']),
                  (['D_800A8F9C','D_8009FC9C'],['D_8009FC9C','D_800A8F9C'])]
    header=ELF_HEADER.unpack_from(predicted)
    headers=[SECTION_HEADER.unpack_from(predicted,header[6]+i*header[11])for i in range(header[12])]
    names_header=headers[header[13]];names=predicted[names_header[4]:names_header[4]+names_header[5]]
    strings=[h for h in headers if read_c_string(names,h[0])=='.strtab'];assert len(strings)==1
    rows=symbol_rows(predicted);symbols={n:(at,row)for at,n,row,_ in rows if n};string_bytes=0
    for old_order,new_order in permutations:
     assert set(old_order)==set(new_order)and len(set(old_order))==2
     first_at,first_row=symbols[old_order[0]];start=first_row[0];offset=start
     old_names=b''.join(n.encode()+b'\0'for n in old_order)
     for i,n in enumerate(old_order):
      symbol_at,row=symbols[n];assert symbol_at==first_at+16*i and row[0]==offset;offset+=len(n)+1
     assert {n for _,n,row,_ in rows if start<=row[0]<offset}==set(old_order)
     at=strings[0][4]+start;assert predicted[at:at+len(old_names)]==old_names
     new_names=b''.join(n.encode()+b'\0'for n in new_order);assert len(new_names)==len(old_names)
     predicted[at:at+len(old_names)]=new_names;offset=start
     for i,n in enumerate(new_order):
      row=symbols[n][1];assert row[2:]==(0,16,0,65521)
      struct.pack_into('>IIIBBH',predicted,first_at+16*i,offset,*row[1:]);offset+=len(n)+1
     string_bytes+=len(old_names)
    actual=image.read_bytes();assert len(actual)==len(predicted)
    differences=[(i,a,b)for i,(a,b)in enumerate(zip(predicted,actual))if a!=b]
    (where/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected image bytes',len(differences),differences[:20])
    (where/'predicted.elf').write_bytes(predicted)
    functions,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    r=dict(raw_and_padded_bound_words_equal_original=True,words=96,frame=152,target_guards=0,insertions=0,omissions=0,
        owner_functions=29,unchanged_padded_neighbors=28,unchanged_raw_neighbors=27,
        compact_neighbor_changed='func_15194794',compact_neighbor_only_changed_offset=84,compact_table_addend_before=40,compact_table_addend_after=60,
        guard_replacement_unchanged=True,guard_expected_word_changed_only=True,guard_count_unchanged=True,
        new_table_targets=5,new_table_target_relative=56,old_table_ownership_preserved=True,
        actual_Make=make,strict_predicted_ELF_equal=True,changed_bytes=sum(a!=b for a,b in zip(before,actual)),exclusions=0,
        function_slots=len(functions),ELF_sha256=hashlib.sha256(actual).hexdigest(),previous_symbol_size=12,
        metadata_permutations=permutations,metadata_symbol_records=6,metadata_string_bytes=string_bytes,
        protected_data_audit=audit_layout(image,root/'conker'),source_installed=installed(),matching_credit=0)
    (out/'image-qualification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
    return r
