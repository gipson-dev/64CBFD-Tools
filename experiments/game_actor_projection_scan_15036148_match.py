from pathlib import Path
import sys
from tools.experiments import game_actor_projection_scan_15036148_recovery as source
ROOT=source.ROOT
from unittest.mock import patch
import csv,hashlib,io,json,struct,subprocess
from tools.tests import game_actor_projection_scan_15036148_normalizer as d
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments import game_list_owner_make as owner_make,game_actor_state_tick_integration as integration
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments import game_embedded_dual_phase_position_update_match as linker
from tools.check_game_data_layout import audit_layout
from tools.match_progress import load_elf_functions
OUT=source.OUT;BASE=OUT/'baseline';WHERE=OUT/'qualification'
def qualify():
    WHERE.mkdir(exist_ok=True);compact=OUT/'qualified-screen/candidate.o';raw,refs=payload(compact,'func_15036148')
    derived,bindings=d.derive(raw,refs);source=struct.unpack('>112I',raw);wanted=struct.unpack('>112I',derived)
    old=(BASE/'conker/retail_word_patches.us.csv').read_bytes();reader=csv.DictReader(io.StringIO(old.decode()));fields=reader.fieldnames
    assert not[r for r in reader if r['function']=='func_15036148'];rows=[]
    for i,(a,b)in enumerate(zip(source,wanted)):
        if a==b and refs.get(i*4,[])==bindings.get(i*4,[]):continue
        reloc=lambda rs:';'.join(k+':'+n for k,n in rs)or'-'
        row={key:''for key in fields};row.update(filename='generated_61D10',function='func_15036148',offset='0x%03X'%(i*4),expected='0x%08X'%a,replacement='0x%08X'%b,
            expected_relocations=reloc(refs.get(i*4,[])),replacement_relocations=reloc(bindings.get(i*4,[])),omit='false',note='Bind verified projection sentinel pool and normalize proved independent submit argument scheduling');rows.append(row)
    assert len(rows)==8
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\r\n'if b'\r\n'in old else'\n');writer.writerows(rows)
    guards=WHERE/'proposed-guards.csv';guards.write_bytes(old+stream.getvalue().encode())
    def assemble(name,text):
        p=WHERE/(name+'.s');p.write_text(text);q=p.with_suffix('.o')
        subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(ROOT/'conker/include'),'-o',str(q),str(p)],check=True,capture_output=True);return q
    kwargs=dict(word_patches_path=guards)
    target=assemble('layout',pc.emit_padded_assembly(compact,ROOT/'conker/retail_layout.us.txt','generated_61D10',**kwargs))
    assembly=assemble('assembly',pg.emit_padded_assembly(compact,ROOT/'conker/asm/61D10.s',filename='generated_61D10',**kwargs))
    assert target.read_bytes()==assembly.read_bytes()
    a,b=pg.parse_object(BASE/'conker/build/src/game/generated_61D10.c.o'),pg.parse_object(target);assert set(a[1])==set(b[1]);changed=[]
    for name,f in a[1].items():
        h=b[1][name];size={'func_15036148':448,'func_15035808':28}.get(name,f['size']);assert f|{'size':size}==h,(name,f,h)
        def contents(p,s):
            lo=s['value'];hi=lo+s['size'];return p[0][lo:hi],{at-lo:rs for at,rs in p[2].items()if lo<=at<hi}
        if contents(a,f)!=contents(b,h):changed.append(name)
    assert set(changed)=={'func_15036148','func_15035808'},changed
    # The two exact relocation guards consume only this function's verified
    # literal pool. The installed production Makefile/profile stay unchanged.
    assert(ROOT/'conker/Makefile').read_bytes()==(BASE/'conker/Makefile').read_bytes()
    (WHERE/'after-diagnostics.txt').write_text('');(WHERE/'caller-after-diagnostics.txt').write_text((OUT/'qualified-screen/caller-after-diagnostics.txt').read_text())
    caller_compact=OUT/'qualified-screen/caller-after.o'
    caller=assemble('caller-layout',pc.emit_padded_assembly(caller_compact,ROOT/'conker/retail_layout.us.txt','game_45B80',word_patches_path=guards))
    assert caller.read_bytes()==(BASE/'conker/build/src/game_45B80.c.o').read_bytes()
    target_route=owner_make.actual_Make(ROOT,WHERE,target,compact,guards,'conker/src/game/generated_61D10.c','conker/build/src/game/generated_61D10.c.o',
        (OUT/'qualified-screen/selected-owner.c').read_text(),'target',10)
    caller_route=owner_make.actual_Make(ROOT,WHERE,caller,caller_compact,guards,'conker/src/game_45B80.c','conker/build/src/game_45B80.c.o',
        (OUT/'qualified-screen/selected-caller.c').read_text(),'caller',16)
    with patch.multiple(linker,FILENAME='generated_61D10',OBJECT='conker/build/src/game/generated_61D10.c.o',LINKER='conker/build/conker.ld'):
        image=linker.link_image(ROOT,WHERE,target,'image')
    before=(BASE/'conker/build/conker.us.elf').read_bytes();prediction=bytearray(before)
    at=elf_slot_offset(prediction,0x15036148,448);prediction[at:at+448]=(ROOT/'conker/conker.us.bin').read_bytes()[0x635F8:0x637B8]
    at=elf_slot_offset(prediction,0x15035808,28);old_helper=bytes(prediction[at:at+12]);prediction[at:at+28]=bytes.fromhex('afa40000afa50004afa60008afa7000c')+old_helper
    for name,entry,size in(('func_15036148',0x15036148,448),('func_15035808',0x15035808,28)):
        matches=[(at,row)for at,n,row,_ in symbol_rows(prediction)if n==name];assert len(matches)==1;at,row=matches[0];assert(row[1],row[2])==(entry,12);struct.pack_into('>I',prediction,at+8,size)
    (WHERE/'predicted-code-size.elf').write_bytes(prediction)
    groups=(('D_800A130C','D_800AEB6C'),('D_80097D74','D_800A5FA4'))
    with patch.object(integration,'SYMBOL_ORDER',groups):prediction=integration.reorder_symbols(prediction)
    actual=image.read_bytes();assert len(actual)==len(prediction)
    differences=[(i,x,y)for i,(x,y)in enumerate(zip(prediction,actual))if x!=y]
    (WHERE/'unpredicted-differences.json').write_text(json.dumps(differences,indent=2)+'\n')
    assert not differences,('unexpected linked bytes',len(differences))
    (WHERE/'predicted.elf').write_bytes(prediction);fs,_,_=load_elf_functions(image,'mips-linux-gnu-objdump')
    report=dict(guards=8,scheduling_guards=6,verified_pool_relocation_guards=2,Makefile_unchanged=True,insertions=0,omissions=0,padders_equal=True,owner_functions=10,unchanged_owner_functions=8,
        typed_submit_placeholder_four_incoming_stores=True,caller_complete_padded_object_unchanged=True,
        actual_Make=dict(target=target_route,caller=caller_route),strict_predicted_ELF_equal=True,
        changed_bytes=sum(x!=y for x,y in zip(before,prediction)),exclusions=0,function_slots=len(fs),
        protected_data=audit_layout(image,ROOT/'conker'),metadata_adjacent_pair_permutations=groups,named_definitions_preserved=True,
        metadata_permutation_bytes=28,ELF_sha256=hashlib.sha256(actual).hexdigest(),matching_credit=0)
    (WHERE/'integration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));return report
