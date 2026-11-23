"""Closed instruction roles, strict guards, both padders and independent links."""
from collections import Counter
import json,struct,subprocess,sys
from tools.experiments import game_actor_emission_preset_150bffe0_match as packet
from tools.tests import game_actor_emission_preset_150bffe0_guest as g
from tools.experiments.game_actor_emission_preset_150bffe0_objects import assemble
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=packet.ROOT,packet.OUT;NAME='func_150BFFE0'
def assembly(data,refs):
 text='.set noat\n.set noreorder\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,name in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {name}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+NAME+',.-'+NAME+'\n'
def roles(data,refs):
 result=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',data)):
  op=w>>26
  if op in (9,15,0x23,0x28,0x29,0x2B,0x31,0x39):mask=~(31<<16)
  elif op==0x11 and w>>21&31==16:mask=~((31<<16)|(31<<11)|(31<<6))
  elif op==0x11 and w>>21&31==4:mask=~((31<<16)|(31<<11))
  else:mask=0xFFFFFFFF
  result.append((w&mask,tuple(refs.get(i*4,[]))))
 return Counter(result)
def main():
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert len(data)==len(truth[0])==508 and(data,refs)!=truth;assert roles(data,refs)==roles(*truth)
 assert len(packet.MANIFEST['guard_rows'])==45 and all(not v['insert_after']and v['omit']=='false'for v in packet.MANIFEST['guard_rows'])
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[line for line in rows if line.split(',')[1:3]==['generated_EC420',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n');guard=where/'target-guards.csv';guard.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,'generated_EC420',word_patches_path=guard),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename='generated_EC420',word_patches_path=guard)]
 outputs=[]
 for i,emit in enumerate(emitters):
  p=where/f'padded-{i}.o';assemble(emit(target),p);assert payload(p,NAME)==truth;outputs.append(p)
 controls=0
 for label in ('word','binding'):
  bad=bytearray(data);br={i:list(v)for i,v in refs.items()}
  if label=='word':bad[0]^=1
  else:
   at=next(i for i,v in br.items()if('R_MIPS_26','func_15136C3C')in v);br[at]=[('R_MIPS_26','func_15136C40')]
  p=where/(label+'.o');assemble(assembly(bad,br),p)
  for i,emit in enumerate(emitters):
   candidate=where/f'{label}-{i}.o';assemble(emit(p),candidate);assert payload(candidate,NAME)!=truth;controls+=1
 strict=0
 for label in ('guarded-word','guarded-binding'):
  bad=bytearray(data);br={i:list(v)for i,v in refs.items()}
  if label=='guarded-word':bad[int(packet.MANIFEST['guard_rows'][0]['offset'],0)+3]^=1
  else:
   at=next(int(v['offset'],0)for v in packet.MANIFEST['guard_rows']if v['expected_relocations']!='-');kind,_=br[at][0];br[at]=[(kind,'D_800A014C')]
  p=where/(label+'.o');assemble(assembly(bad,br),p)
  for emit in emitters:
   try:emit(p)
   except ValueError:strict+=1
   else:raise AssertionError('Wrong guard input was accepted')
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);rejected=0;oversized_reasons=[]
 for i,emit in enumerate(emitters):
  try:text=emit(oversized)
  except ValueError as error:
   assert NAME in str(error)
   if i==0:assert 'stale overflow word patch'in str(error)
   oversized_reasons.append(dict(padder=i,error=str(error)));rejected+=1;continue
  assert i==0;p=where/f'oversized-padded-{i}.o';assemble(text,p);assert '__retail_overflow_'+NAME in text and payload(p,NAME)!=truth;rejected+=1
 links=runs=0
 bindings=((g.ENTRY,g.PREPARE,g.FACTORY,0),(g.ENTRY+0x10000,0x150016C0,0x150020C0,0x8000),(g.ENTRY-0x10000,0x15FF7000,0x15FF8000,-0x1000),(0x250BFFE0,0x250016C0,0x25008000,0x10000000))
 for number,(entry,prepare,callee,shift)in enumerate(bindings):
  symbols={n:(v+shift)&0xFFFFFFFF for n,v in g.S.items()if n in {n for entries in truth[1].values()for _,n in entries}and not n.startswith('func_')};symbols.update(func_15136C3C=prepare,func_15153634=callee);blobs=[]
  for i,p in enumerate([*outputs,o/'original-target.o']):
   script=where/f'{number}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[508:]);blobs.append(text[:508]);assert list(struct.unpack('>127I',text[:508]))==g.bound_blob(*payload(p,NAME),symbols);defs=[v for _,n,v,_ in symbol_rows(elf.read_bytes())if n==NAME];assert len(defs)==1 and defs[0][1:3]==(entry,508);links+=1
  assert len(set(blobs))==1
  for seed,y in enumerate((0,0x4C000000,0xC28C0000,0x80000001)):
   for phase in (0,8):
    c=g.Case(y=y,seed=seed,mutation=1,phase=phase);initial=g.fixture(c,symbols)
    for blob in blobs:
     m=g.Oracle(struct.unpack('>127I',blob),initial,c,entry=entry,s=symbols).run();g.check(m,initial,c,symbols);runs+=1
 report=dict(both_padders_byte_exact=True,register_erased_instruction_and_binding_multiset_equal=True,guards=45,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,strict_expected_word_and_binding_rejections=strict,oversized_body_rejections=rejected,oversized_reasons=oversized_reasons,GNU_links=links,independent_two_callee_and_data_arrangements=4,guest_rebase_runs=runs,source_installed=packet.installed(),matching_credit=0,limits='Register-erased instruction/binding multiset equality is structural closure. Independent raw C guest/native tests establish value flow; normalization restores exact private ordering.')
 (o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
