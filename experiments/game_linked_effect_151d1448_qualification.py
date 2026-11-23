"""Direct identity, effective corruption controls and independent GNU relocation."""
import json,struct,subprocess,sys
from tools.experiments import game_linked_effect_151d1448_match as p
from tools.tests import game_linked_effect_151d1448_guest as g
from tools.experiments.game_texture_registration_15195dd4_objects import assemble
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_remaining_donor_candidates import compile_owner
from tools.experiments.game_actor_classifier_candidates import sections
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
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME)
 assert len(data)==392 and (data,refs)==truth and len(refs)==4
 assert p.MANIFEST['guard_count']==0 and (o/'private-guards.csv').read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==['generated_1FA770',NAME]];assert len(selected)==1
 layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 emitters=[lambda f:pc.emit_padded_assembly(f,layout,'generated_1FA770'),lambda f:pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_1FA770')];outputs=[];controls=0
 for i,emit in enumerate(emitters):
  f=where/f'padded-{i}.o';assemble(emit(target),f);assert payload(f,NAME)==truth;outputs.append(f)
 # Direct code has no normalizing guards. Corruption must stay visible rather
 # than being silently repaired; it is not a fail-closed padder rejection.
 for at in range(0,len(data),4):
  bad=bytearray(data);bad[at+3]^=4;f=where/'corrupt-word.o';assemble(assembly(bad,refs),f)
  for i,emit in enumerate(emitters):
   out=where/f'corrupt-word-{i}.o';assemble(emit(f),out);assert payload(out,NAME)!=truth;controls+=1
 for at in refs:
  br={i:list(v)for i,v in refs.items()};kind,n=br[at][0];br[at]=[(kind,n+'_wrong')]+br[at][1:];f=where/'corrupt-binding.o';assemble(assembly(data,br),f)
  for i,emit in enumerate(emitters):
   out=where/f'corrupt-binding-{i}.o';assemble(emit(f),out);assert payload(out,NAME)!=truth;controls+=1
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);text=emitters[0](oversized);assert '__retail_overflow_'+NAME in text
 out=where/'generic-overflow.o';assemble(text,out);assert payload(out,NAME)!=truth
 try:emitters[1](oversized)
 except ValueError as error:assert NAME in str(error)
 else:raise AssertionError('Generated padder accepted an oversized body')
 names={n for v in refs.values()for _,n in v};callees=sorted({n for v in refs.values()for kind,n in v if kind=='R_MIPS_26'});links=runs=0
 for number,(entry,base,shift)in enumerate(((g.ENTRY,0x15001000,0),(g.ENTRY+0x10000,0x15008000,0x8000),(g.ENTRY-0x10000,0x15f07000,-0x1000),(0x251d1448,0x25001000,0x10000000))):
  symbols={n:(g.S[n]+shift)&0xffffffff for n in names if n not in callees};symbols.update({n:base+0x1000*i for i,n in enumerate(callees)});blobs=[]
  for i,f in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[392:]);words=list(struct.unpack('>98I',text[:392]));assert words==g.bound_blob(*payload(f,NAME),symbols);blobs.append(words);links+=1
  assert len({tuple(ws)for ws in blobs})==1
  for c in(g.Case(),g.Case(kind=1,views=-1),g.Case(kind=1,views=1,mutation=7),g.Case(outcome=0),g.Case(alias=1,mutation=3),g.Case(context=255,channel=128,phase=8)):
   initial=g.fixture(c,symbols);models=[]
   for ws in[g.bound_blob(data,refs,symbols),*blobs]:
    m=g.Oracle(ws,initial,c,entry=entry,s=symbols);m.run();g.check(m,initial,c,symbols);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[0])for m in models[1:])
 # Retail publishes untouched private padding. Native C does not define its
 # bit values, so this is explicitly a guest-binary observation control.
 source=p.MANIFEST['selected_source'];old='LinkedEffectConfig151D1448 config;';assert source.count(old)==1
 bad=source.replace(old,'LinkedEffectConfig151D1448 config = {0};');obj,_=compile_owner(r,where,bad,'zero-config')
 c=g.Case();initial=g.fixture(c);symbols=g.S.copy();symbols['.data']=0xa0000
 for i,b in enumerate(sections(obj)['.data'][1]):initial[symbols['.data']+i]=b
 m=g.Oracle(g.bound_blob(*payload(obj,NAME),symbols),initial,c,s=symbols);m.run()
 observed=m.observed[-1][2];assert observed[9:12]==b'\0\0\0' and observed[9:12]!=g.reference(initial,c)[2][-1][2][9:12]
 report=dict(raw_is_exact_retail_words_and_bindings=True,both_padders_byte_exact=True,guards=0,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,source_words_covered=98,source_binding_sites_covered=4,generated_oversized_rejection=1,generic_overflow_preserved_but_unmatched=1,GNU_target_links=links,independent_code_callee_and_global_arrangements=4,guest_rebase_runs=runs,effective_zero_padding_guest_control=True,native_padding_bits_claimed=False,source_installed=p.installed(),matching_credit=0)
 (o/'qualification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
