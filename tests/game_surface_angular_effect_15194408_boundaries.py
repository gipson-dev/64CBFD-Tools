"""Both padders, table ownership, independent GNU binding and fail-closed guards."""
from pathlib import Path
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_surface_angular_effect_15194408_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_surface_angular_effect_15194408_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_15194408'
def assemble(text,name):
 path=out/(name+'.s');path.write_text(text);obj=path.with_suffix('.o')
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=root/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj
def main():
 raw,refs=payload(out/'qualified-source/candidate.o',NAME)
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for at,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*at,[]):text+='.reloc ., '+kind+', '+('jtbl_800A8258_game'if name=='.rodata'else name)+'\n'
  text+='.word 0x%08X\n'%w
 target=assemble(text+'.size '+NAME+',.-'+NAME+'\n','target-raw')
 expected_refs={at:[(k,'jtbl_800A8258_game'if n=='.rodata'else n)for k,n in es]for at,es in refs.items()}
 assert payload(target,NAME)==(raw,expected_refs)
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();rows=[line for line in lines[1:]if line.split(',')[1:3]==['generated_1C1150',NAME]];assert len(rows)==1
 layout=out/'target-layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n')
 header=next(csv.reader(io.StringIO((root/'conker/retail_word_patches.us.csv').read_text())))
 buf=io.StringIO(newline='');csv.DictWriter(buf,fieldnames=header).writeheader();guards=out/'empty-guards.csv';guards.write_text(buf.getvalue())
 generic=assemble(pc.emit_padded_assembly(target,layout,'generated_1C1150',word_patches_path=guards),'target-generic')
 source=(root/'conker/asm/1C1150.s').read_text();body='glabel '+NAME+source.split('glabel '+NAME,1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME
 asm=out/'target-original.s';asm.write_text(body+'\n')
 generated=assemble(pg.emit_padded_assembly(target,asm,filename='generated_1C1150',word_patches_path=guards),'target-generated')
 original=out/'image-qualification/retail.o'
 paths=(target,generic,generated,original);links=0
 for low in(0,0x7FE0,0x8000,0xFFC0):
  anchor=0x800B0000+low
  symbols={'jtbl_800A8258_game':anchor,'jtbl_800A8280':anchor+40,
   'D_800A8294':0x800D0000+low,'D_800A8298':0x800E0000+low,'D_800A829C':0x800F0000+low,
   'func_151AE7B0':0x15210000+low,'func_1504715C':0x15230000+low,'func_15153F18':0x15250000+low}
  streams=[]
  for i,p in enumerate(paths):
   expected=bound_blob(*payload(p,NAME),symbols);streams.append(expected)
   script=out/('bind-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x15194408 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(p)],capture_output=True,text=True)
   assert q.returncode==0,q.stderr;assert list(struct.unpack('>96I',sections(elf)['.text'][1]))==expected;links+=1
  assert streams[0]==streams[1]==streams[2]==streams[3]
 stale=False
 try:pg.emit_padded_assembly(out/'qualified-source/candidate.o',root/'conker/asm/1C1150.s',filename='generated_1C1150',word_patches_path=out/'baseline/conker/retail_word_patches.us.csv',rodata_symbol='jtbl_800A8258_game')
 except ValueError as e:assert 'stale word patch for func_15194794+0x54'in str(e);stale=True
 assert stale
 # Original table validity is required only on the accepted kind paths.
 streams=g.programs();controls=[]
 for kind in range(5):
  m=g.Oracle(streams[0],g.Case(kind=kind));g.put(m.memory,g.TABLE+kind*4,0xDEADBEEF)
  try:m.run();raise AssertionError('corrupt table accepted')
  except AssertionError as e:assert 'unowned jump'in str(e),str(e)
  controls.append(kind)
 for kind in range(5,256):
  m=g.Oracle(streams[0],g.Case(kind=kind))
  for i in range(20):del m.memory[g.TABLE+i]
  m.run();assert not m.calls
 r=dict(GNU_rebased_links=links,raw_generic_generated_original_bound_words_equal=True,target_guards=0,
  stale_neighbor_guard_rejected=True,corrupt_table_controls=controls,invalid_kinds_never_read_table=251,
  compact_pool_anchor_and_original_table_alias_checked=True,source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
