"""Direct identity, independent GNU relocations and effective boundary controls."""
import json,struct,subprocess,sys
from tools.experiments import game_texture_registration_15195dd4_match as p
from tools.tests import game_texture_registration_15195dd4_guest as g
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner,function_span
from tools.experiments.game_actor_classifier_candidates import sections
r,o=p.ROOT,p.OUT;NAME=p.FUNCTION
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def main():
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert len(data)==476 and(data,refs)==truth
 assert p.MANIFEST['guard_count']==0 and(o/'private-guards.csv').read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_1C2C60',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_1C2C60'),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_1C2C60')];outputs=[];controls=0
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 for label in('word','binding'):
  bad=bytearray(data);br={i:list(v)for i,v in refs.items()}
  if label=='word':bad[3]^=4
  else:
   at=next(i for i,v in br.items()if('R_MIPS_26','func_15195868')in v);br[at]=[('R_MIPS_26','func_1519586C')]
  f=where/(label+'.o');assemble(assembly(bad,br),f)
  for i,emit in enumerate(emitters):
   output=where/f'{label}-{i}.o';assemble(emit(f),output);assert payload(output,NAME)!=truth;controls+=1
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);text=emitters[0](oversized);assert '__retail_overflow_'+NAME in text;overflow=where/'generic-overflow.o';assemble(text,overflow);assert payload(overflow,NAME)!=truth
 try:emitters[1](oversized)
 except ValueError as error:assert NAME in str(error)
 else:raise AssertionError('Generated padder accepted an oversized body')
 names={n for v in refs.values()for _,n in v};callees=sorted(n for n in names if n.startswith('func_'));links=runs=0
 for number,(entry,base,shift)in enumerate(((g.ENTRY,0x15001000,0),(g.ENTRY+0x10000,0x15008000,0x8000),(g.ENTRY-0x10000,0x15F07000,-0x1000),(0x25195DD4,0x25001000,0x10000000))):
  symbols={n:(g.S[n]+shift)&0xFFFFFFFF for n in names if n not in callees};symbols.update({n:base+0x1000*i for i,n in enumerate(callees)});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[476:]);words=list(struct.unpack('>119I',text[:476]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(asset=0,mode=-1,hits=3,mutation=3),g.Case(head=0,hits=0),g.Case(head=0,failure=0),g.Case(asset=-1,separate=1),g.Case(index=32768),g.Case(gate=255),g.Case(null=1)):
   initial=g.fixture(c,symbols);models=[]
   for ws in blobs:m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert g.state(models[0])==g.state(models[1])==g.state(models[2])
 # A superficially helpful zero initializer must fail the actual first-miss result.
 source=p.MANIFEST['selected_source'];a,b=function_span(source,NAME);body=source[a:b];assert 'u8 *record;'in body;bad=body.replace('u8 *record;','u8 *record = NULL;');obj,_=compile_owner(r,where,source[:a]+bad+source[b:],'zero-initialized');c=g.Case(hits=0);initial=g.fixture(c);m=g.Oracle(g.bound_blob(*payload(obj,NAME),g.S),initial,c);m.run();assert m.r[2]!=g.reference(initial,c)[2]
 report=dict(raw_is_exact_retail_words_and_bindings=True,both_padders_byte_exact=True,guards=0,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,generated_oversized_rejection=1,generic_overflow_preserved_but_unmatched=1,GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,effective_zero_initializer_guest_control=True,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
