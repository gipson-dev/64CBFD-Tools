"""Both guard-aware padders, GNU rebindings and fail-closed guard controls."""
from pathlib import Path
import csv,io,json,struct,subprocess,sys
from tools.experiments import game_paired_actor_initializer_151951e0_match as packet
root,out=packet.ROOT,packet.OUT
from tools.tests import game_paired_actor_initializer_151951e0_guest as g
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_151951E0'
def assemble(text,name):
 p=out/(name+'.s');p.write_text(text);obj=p.with_suffix('.o')
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(p)],cwd=root/'conker',capture_output=True,text=True)
 assert q.returncode==0 and not q.stdout and not q.stderr,(q.stdout,q.stderr);return obj
def main():
 raw,refs=payload(out/'qualified-source/candidate.o',NAME)
 text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 text+='.size '+NAME+',.-'+NAME+'\n';target=assemble(text,'target-raw');assert payload(target,NAME)==(raw,refs)
 lines=(root/'conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines[1:]if v.split(',')[1:3]==['generated_1C1150',NAME]];assert len(rows)==1
 layout=out/'target-layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n')
 fields=next(csv.reader(io.StringIO((out/'private-guards.csv').read_text())))
 guard_rows=json.loads((out/'guard-rows.json').read_text());assert len(guard_rows)==15
 def guard_file(rows,name):
  p=out/(name+'.csv');s=io.StringIO(newline='');w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows);p.write_text(s.getvalue());return p
 guards=guard_file(guard_rows,'target-guards')
 full=(root/'conker/asm/1C1150.s').read_text();body='glabel '+NAME+full.split('glabel '+NAME,1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME
 asm=out/'original-target.s';asm.write_text(body+'\n')
 generic=assemble(pc.emit_padded_assembly(target,layout,'generated_1C1150',word_patches_path=guards),'target-generic')
 generated=assemble(pg.emit_padded_assembly(target,asm,filename='generated_1C1150',word_patches_path=guards),'target-generated')
 original=out/'image-qualification/retail.o';assert payload(generic,NAME)==payload(generated,NAME)==payload(original,NAME)
 paths=(target,generic,generated,original);links=0
 names={n for p in paths for values in payload(p,NAME)[1].values()for _,n in values};calls={n for values in refs.values()for k,n in values if k=='R_MIPS_26'}
 for low in(0,0x7FF8,0x8000,0xFFF8):
  symbols={n:(0x15210000+0x20000*i+low)for i,n in enumerate(sorted(calls))}
  symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))})
  streams=[]
  for i,p in enumerate(paths):
   expected=bound_blob(*payload(p,NAME),symbols);streams.append(expected)
   script=out/('bind-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x151951E0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%v for v in symbols.items()],'-o',str(elf),str(p)],capture_output=True,text=True)
   assert q.returncode==0,q.stderr
   linked_text=sections(elf)['.text'][1];assert len(linked_text)in(840,848)and not any(linked_text[840:])
   assert list(struct.unpack_from('>210I',linked_text))==expected;links+=1
  assert streams[1]==streams[2]==streams[3]and sum(a!=b for a,b in zip(streams[0],streams[1]))==15
 controls=[]
 assert text.count('.word 0x240300FF\n')>=1
 corrupted=assemble(text.replace('.word 0x240300FF\n','.word 0x240300FE\n',1),'stale-source')
 stale_reloc=assemble(text.replace('.word 0x240300FF\n','.reloc ., R_MIPS_26, func_1507CD64\n.word 0x240300FF\n',1),'stale-source-relocation')
 wrong_reloc=[dict(row)for row in guard_rows];wrong_reloc[0]['expected_relocations']='R_MIPS_26:func_1507CD64'
 duplicate=guard_file(guard_rows+[guard_rows[0]],'duplicate-guard')
 for label,obj,manifest,needle in [('stale-word',corrupted,guards,'stale word patch'),('stale-source-relocation',stale_reloc,guards,'stale relocations'),('stale-expected-relocation',target,guard_file(wrong_reloc,'wrong-relocation'),'stale relocations'),('duplicate-offset',target,duplicate,'duplicate')]:
  try:pg.emit_padded_assembly(obj,asm,filename='generated_1C1150',word_patches_path=manifest);raise AssertionError('control accepted '+label)
  except ValueError as e:assert needle in str(e).lower(),(label,str(e))
  controls.append(label)
 wrong_replacement=[dict(row)for row in guard_rows];wrong_replacement[0]['replacement']='0x00000000'
 changed=assemble(pg.emit_padded_assembly(target,asm,filename='generated_1C1150',word_patches_path=guard_file(wrong_replacement,'wrong-replacement')),'wrong-replacement')
 assert payload(changed,NAME)!=payload(original,NAME);controls.append('wrong-replacement')
 lookup={n:r[1]for _,n,r,_ in symbol_rows((out/'baseline/conker/build/conker.us.elf').read_bytes())if n}
 streams=[bound_blob(*payload(p,NAME),lookup)for p in(generic,generated,original)];assert streams[0]==streams[1]==streams[2]
 faults=0
 for c in(g.Case(),g.Case(angle=0),g.Case(alias=1),g.Case(mode=15,phase=8)):
  full=g.check(streams[0],c)
  for cut in range(full.all_accesses):
   states=[]
   for ws in streams:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run();raise AssertionError('missing access cut')
    except AccessBoundary:pass
    states.append(g.state(m))
   assert states[0]==states[1]==states[2];faults+=1
 r=dict(GNU_rebased_links=links,guards=15,raw_expected_differences=15,normalized_generic_generated_original_payloads_equal=True,
  effective_guard_controls=controls,normalized_fault_triples=faults,all_relocation_bindings_covered=13,
  source_installed=packet.installed(),matching_credit=0)
 (out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return r
if __name__=='__main__':main()
