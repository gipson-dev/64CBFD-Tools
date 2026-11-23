"""Direct C identity, independent GNU bindings and honest overflow controls."""
import json,struct,subprocess,sys
from tools.experiments import game_owner_phase_update_150bf760_match as packet
from tools.tests import game_owner_phase_update_150bf760_guest as g
from tools.experiments.game_owner_phase_update_150bf760_objects import assemble
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools.experiments.game_actor_state_tick_integration import symbol_rows
r,o=packet.ROOT,packet.OUT;NAME='func_150BF760'
def assembly(data,refs,name=NAME):
 text='.set noat\n.set noreorder\n.text\n.globl '+name+'\n.type '+name+',@function\n'+name+':\n'
 for i,(word,)in enumerate(struct.iter_unpack('>I',data)):
  for kind,n in refs.get(i*4,[]):text+=f'.reloc ., {kind}, {n}\n'
  text+=f'.word 0x{word:08X}\n'
 return text+'.size '+name+',.-'+name+'\n'
def main():
 data,refs=payload(o/'selected-final/candidate.o',NAME);truth=payload(o/'original-target.o',NAME);assert len(data)==796 and(data,refs)==truth
 assert packet.MANIFEST['guard_count']==0 and not packet.MANIFEST['guard_rows'];assert(o/'private-guards.csv').read_bytes()==(o/'baseline/conker/retail_word_patches.us.csv').read_bytes()
 where=o/'boundaries';where.mkdir(exist_ok=True);target=where/'raw.o';assemble(assembly(data,refs),target)
 rows=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();selected=[line for line in rows if line.split(',')[1:3]==['generated_EC420',NAME]];assert len(selected)==1;layout=where/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n')
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,'generated_EC420'),lambda p:pg.emit_padded_assembly(p,o/'original-target.s',filename='generated_EC420')];outputs=[]
 for i,emit in enumerate(emitters):
  p=where/f'padded-{i}.o';assemble(emit(target),p);assert payload(p,NAME)==truth;outputs.append(p)
 controls=0
 for label in('word','binding'):
  bad=bytearray(data);br={i:list(v)for i,v in refs.items()}
  if label=='word':bad[3]^=4
  else:
   at=next(i for i,v in br.items()if('R_MIPS_26','func_1511B51C')in v);br[at]=[('R_MIPS_26','func_1511B520')]
  p=where/(label+'.o');assemble(assembly(bad,br),p)
  for i,emit in enumerate(emitters):
   candidate=where/f'{label}-{i}.o';assemble(emit(p),candidate);assert payload(candidate,NAME)!=truth;controls+=1
 oversized=where/'oversized.o';assemble(assembly(data+struct.pack('>I',0x24420001),refs),oversized);text=emitters[0](oversized);assert '__retail_overflow_'+NAME in text;p=where/'generic-overflow.o';assemble(text,p);assert payload(p,NAME)!=truth
 try:emitters[1](oversized)
 except ValueError as error:assert NAME in str(error)
 else:raise AssertionError('Generated padder accepted an oversized body')
 provider='func_15195FB0';relay=payload(o/'provider/candidate.o',provider);assert relay==payload(o/'original-provider.o',provider);relay_raw=where/'relay-raw.o';assemble(assembly(*relay,name=provider),relay_raw)
 names={n for entries in refs.values()for _,n in entries};callees=sorted(n for n in names if n.startswith('func_')or n=='sinf');links=runs=relay_links=0
 for number,(entry,base,shift)in enumerate(((g.ENTRY,0x15001000,0),(g.ENTRY+0x10000,0x15008000,0x8000),(g.ENTRY-0x10000,0x15F07000,-0x1000),(0x250BF760,0x25001000,0x10000000))):
  symbols={n:(g.S[n]+shift)&0xFFFFFFFF for n in names if n not in callees};symbols.update({n:base+0x1000*i for i,n in enumerate(callees)});symbols['func_15195DD4']=base+0x1000*len(callees);blobs=[]
  def link(p,name,address,label,size):
   script=where/(label+'.ld');script.write_text(f'SECTIONS {{ .text 0x{address:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*[f'--defsym={n}=0x{v:X}'for n,v in symbols.items()if n!=name],'-o',str(elf),str(p)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   text=sections(elf)['.text'][1];assert not any(text[size:]);assert list(struct.unpack('>'+str(size//4)+'I',text[:size]))==g.bound_blob(*payload(p,name),symbols);defs=[v for _,n,v,_ in symbol_rows(elf.read_bytes())if n==name];assert len(defs)==1 and defs[0][1:3]==(address,size);return text[:size]
  for i,p in enumerate([*outputs,o/'original-target.o']):blobs.append(link(p,NAME,entry,f'{number}-target-{i}',796));links+=1
  relay_blobs=[link(p,provider,symbols[provider],f'{number}-relay-{i}',64)for i,p in enumerate((relay_raw,o/'original-provider.o'))];relay_links+=2;assert len(set(relay_blobs))==len(set(blobs))==1
  for seed,numerator in enumerate((0,0x40000000,0x41000000,0x7FC12345)):
   for stack_phase in(0,8):
    c=g.Case(phase=seed,numerator=numerator,seed=seed,mutation=1,stack_phase=stack_phase);initial=g.fixture(c,symbols)
    extra=dict(zip(range(symbols[provider],symbols[provider]+64,4),struct.unpack('>16I',relay_blobs[seed%2])))
    for blob in blobs:
     m=g.run(g.Oracle(struct.unpack('>199I',blob),initial,c,entry=entry,s=symbols,extra=extra));g.check(m,initial,c,symbols);runs+=1
 report=dict(raw_is_exact_retail_words_and_bindings=True,both_padders_byte_exact=True,guards=0,insertions=0,omissions=0,effective_wrong_word_or_binding_controls=controls,generated_oversized_rejection=1,generic_overflow_preserved_but_unmatched=1,GNU_target_links=links,GNU_relay_links=relay_links,independent_code_callee_and_data_arrangements=4,guest_rebase_runs=runs,complete_relay_payload_unchanged=True,source_installed=packet.installed(),matching_credit=0,limits='Exact direct target and actual 16-word relay. Other service and sine internals remain bounded providers; generic overflow support is not called a matching body.')
 (o/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
