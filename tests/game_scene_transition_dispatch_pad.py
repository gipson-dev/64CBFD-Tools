import csv, io, json, struct, subprocess, sys
from pathlib import Path
from tools.experiments import game_scene_transition_dispatch_match as p
out=p.out; root=p.root
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.pad_generated_object import parse_object,ELF_HEADER,SECTION_HEADER,read_c_string
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
NAME='func_1501C730'; OWNER='generated_49BE0'; ANCHOR='jtbl_800969A0_game'
def payload(path):
    text,fs,rs=parse_object(path); a,n=fs[NAME]['value'],fs[NAME]['size']
    return text[a:a+n],{i-a:v for i,v in rs.items() if a<=i<a+n}
def assemble(text,label):
    source=out/(label+'.s'); source.write_text(text); obj=source.with_suffix('.o')
    p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(source)],cwd=root/'conker',capture_output=True,text=True)
    assert p.returncode==0 and not p.stderr,(p.stdout,p.stderr)
    return obj
def main():
 asm=root/'conker/asm/49BE0.s'
 # Keep the local branch destination local in this isolated assembly, so GNU
 # resolves PC-relative branches rather than leaving a global PC16 relocation.
 original_source=asm.read_text().replace('jlabel .L1501C848\n','.L1501C848:\n')
 original=assemble(original_source+'\n.size '+NAME+',.-'+NAME+'-8\n','original')
 raw,refs=payload(out/'candidate.o'); truth,truthrefs=payload(original)
 assert len(raw)==len(truth)==296
 normalized={k:[(kind,ANCHOR if sym in ('.rodata','jtbl_800969A0') else sym) for kind,sym in v] for k,v in refs.items()}
 normalized_truth={k:[(kind,ANCHOR if sym=='jtbl_800969A0' else sym) for kind,sym in v] for k,v in truthrefs.items()}
 comparable=bytearray(raw);comparable_refs=dict(normalized)
 for hi,lo in ((0x98,0x9c),(0xc4,0xc8)):
  assert comparable_refs[hi]==[('R_MIPS_HI16','D_800CC2D0')]
  assert comparable_refs[lo]==[('R_MIPS_LO16','D_800CC2D0')]
  assert comparable[lo+2:lo+4]==b'\x00\xb2'
  comparable[lo+2:lo+4]=b'\0\0'
  comparable_refs[hi]=[('R_MIPS_HI16','D_800CC382')]
  comparable_refs[lo]=[('R_MIPS_LO16','D_800CC382')]
 assert bytes(comparable)==truth and comparable_refs==normalized_truth
 elf=(root/'conker/build/conker.us.elf').read_bytes()
 retail=struct.unpack_from('>7I',elf,0x242b20+0x800969a0-0x80082b20)
 def check_table(path):
  pools=sections(path);table=pools['.rodata'][1];rel=pools['.rel.rodata'][1]
  assert len(table)==32 and table[28:]==b'\0'*4 and len(rel)==56
  offsets=struct.unpack_from('>7I',table)
  assert tuple(0x1501C730+x for x in offsets)==retail
  assert [struct.unpack_from('>II',rel,i*8) for i in range(7)]==[(i*4,0x102) for i in range(7)]
  return offsets
 candidate=out/'candidate.o';offsets=check_table(candidate)
 raw_object=candidate.read_bytes();header=ELF_HEADER.unpack_from(raw_object);headers=[SECTION_HEADER.unpack_from(raw_object,header[6]+i*header[11]) for i in range(header[12])];names=headers[header[13]];strings=raw_object[names[4]:names[4]+names[5]]
 pool=next(h for h in headers if read_c_string(strings,h[0])=='.rodata');reloc=next(h for h in headers if read_c_string(strings,h[0])=='.rel.rodata')
 for i in range(7):
  bad=bytearray(raw_object);bad[pool[4]+4*i+3]^=1;path=out/f'corrupt-table-{i}.o';path.write_bytes(bad)
  try:check_table(path)
  except AssertionError:pass
  else:raise AssertionError(('table corruption accepted',i))
 bad=bytearray(raw_object);bad[reloc[4]+7]^=1;path=out/'corrupt-table-relocation.o';path.write_bytes(bad)
 try:check_table(path)
 except AssertionError:pass
 else:raise AssertionError('table relocation corruption accepted')
 fields=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())))
 guard=out/'guards.csv'; stream=io.StringIO(newline=''); csv.DictWriter(stream,fieldnames=fields,lineterminator='\n').writeheader(); guard.write_text(stream.getvalue())
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines()
 entries=[x for x in lines[1:] if x.split(',')[1:3]==[OWNER,NAME]]; assert len(entries)==1
 layout=out/'layout.csv'; layout.write_text(lines[0]+'\n'+entries[0]+'\n')
 generic=assemble(pad_c_object.emit_padded_assembly(out/'candidate.o',layout,OWNER,word_patches_path=guard,rodata_symbol=ANCHOR),'generic')
 generated=assemble(pad_generated_object.emit_padded_assembly(out/'candidate.o',asm,filename=OWNER,word_patches_path=guard,rodata_symbol=ANCHOR),'generated')
 assert payload(generic)==payload(generated)==(raw,normalized)
 lookup={v[1]:v[2][1] for v in symbol_rows(elf)}
 words=bound_blob(truth,normalized_truth,{nm:lookup[nm] for es in normalized_truth.values() for _,nm in es})
 assert struct.pack('>74I',*words)==(root/'conker/conker.us.bin').read_bytes()[0x49BE0:0x49D08]
 assert bound_blob(raw,normalized,{nm:lookup[nm] for es in normalized.values() for _,nm in es})==words
 report=dict(raw_words=74,guard_rows=0,table_entries=7,table_offsets=[hex(x) for x in offsets],table_and_relocation_corruption_controls=8,dual_padder_matches_retail=True,source_installed=False)
 (out/'pad_screen.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report),flush=True)
