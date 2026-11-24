"""Private-table provenance, corruption visibility and real GNU HI/LO rebases."""
import json,struct,subprocess,sys
from tools.experiments import game_base_color_output_1513137c_match as p
from tools.tests import game_base_color_output_1513137c_guest as g
from tools.tests.game_base_color_output_1513137c_normalizer import normalize
from tools.tests.game_base_color_output_1513137c_tables import audit
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_paired_ground_constructor_match import payload
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def main():
 raw=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert normalize(*raw)==truth;proof=audit(o/'selected-final/before.o',o/'selected-final/candidate.o',o/'original-target.o');where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(*raw),target)
 guard=where/'target-guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes());rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_15D730',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_bytes((rows[0]+'\n'+selected[0]+'\n').encode());emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_15D730',word_patches_path=guard),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_15D730',word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 failclosed=visible=pins=0
 for at in range(0,408,4):
  data=bytearray(raw[0]);data[at+3]^=4
  try:normalize(bytes(data),raw[1])
  except AssertionError:pins+=1
  else:raise AssertionError('Whole-source pin accepted a changed word')
  f=where/'corrupt-word.o';assemble(assembly(data,raw[1]),f)
  for i,emit in enumerate(emitters):
   if at in(32,40):
    try:emit(f)
    except ValueError as error:assert NAME in str(error);failclosed+=1
    else:raise AssertionError('Address guard accepted changed word')
   else:
    out=where/f'visible-{i}.o';assemble(emit(f),out);assert payload(out,NAME)!=truth;visible+=1
 for at in raw[1]:
  refs={i:list(v)for i,v in raw[1].items()};kind,n=refs[at][0];refs[at]=[(kind,n+'_wrong')]
  try:normalize(raw[0],refs)
  except AssertionError:pins+=1
  else:raise AssertionError('Whole-source pin accepted a changed binding')
  f=where/'corrupt-binding.o';assemble(assembly(raw[0],refs),f)
  for emit in emitters:
   try:emit(f)
   except ValueError as error:assert NAME in str(error);failclosed+=1
   else:raise AssertionError('Address guard accepted changed binding')
 oversized=where/'oversized.o';assemble(assembly(raw[0]+struct.pack('>I',0),raw[1]),oversized);generic_rejection=0
 try:text=emitters[0](oversized)
 except ValueError as error:assert NAME in str(error);generic_rejection=1
 else:
  assert '__retail_overflow_'+NAME in text;out=where/'generic-overflow.o';assemble(text,out);assert payload(out,NAME)!=truth
 try:emitters[1](oversized)
 except ValueError as error:assert NAME in str(error)
 else:raise AssertionError('Generated padder accepted oversized target')
 links=runs=0;arrangements=[]
 for number,(entry,protected,private)in enumerate(((g.ENTRY,0x800a3800,0x800a1000),(g.ENTRY+0x10000,0x80029000,0x80027ff0),(g.ENTRY-0x10000,0x90018000,0x9001a000),(0x2513137c,0xa0043800,0xa0041000))):
  s={'jtbl_800A3800':protected,'.rodata':private};assert(private+36+0x8000)>>16==(protected+0x8000)>>16;blobs=[]
  for i,f in enumerate([target,*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{a:X}'for n,a in s.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;data=sections(elf)['.text'][1];assert not any(data[408:]);words=list(struct.unpack('>102I',data[:408]));assert words==g.bound_blob(*payload(f,NAME),s);blobs.append(words);links+=1
  assert blobs[1]==blobs[2]==blobs[3]
  for c in(g.Case(mode=0),g.Case(mode=1),g.Case(mode=3,layout=5),g.Case(mode=6),g.Case(mode=7,alias=3),g.Case(mode=8,layout=9)):
   initial=g.fixture(c,entry,s);models=[]
   for i,words in enumerate(blobs):m=g.Oracle(words,initial,c,entry=entry,s=s);m.run();g.verify(m,initial,c);models.append(m);runs+=1
   assert all(g.state(m,c,i==0,s)==g.state(models[-1],c,s=s)for i,m in enumerate(models))
  arrangements.append(dict(code=hex(entry),protected_table=hex(protected),private_pool=hex(private),raw_table=hex(private+36)))
 report=dict(table_provenance=proof,guards=2,insertions=0,omissions=0,source_words_covered=102,source_binding_sites_covered=2,whole_source_pin_controls=pins,failclosed_address_word_or_binding_controls=failclosed,non_address_word_corruption_visibility_controls=visible,total_effective_word_or_binding_controls=failclosed+visible,generated_oversize_rejection=1,generic_oversize_rejection=generic_rejection,generic_overflow_visible_unmatched=1-generic_rejection,GNU_target_links=links,guest_rebase_runs=runs,arrangements=arrangements,HI_carry_and_negative_LO_exercised=True,adjusted_HI_shared_to_compare_dead_AT_literally=True,source_installed=p.installed(),matching_credit=0);(o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in report.items()if k not in('table_provenance','arrangements')}),flush=True);return report
if __name__=='__main__':main()
