"""Normalizer pins, padder corruption visibility and real GNU symbol rebases."""
import json,struct,subprocess
from tools.experiments import game_opening_spray_150c1f60_match as p
from tools.tests import game_opening_spray_150c1f60_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
r,o=p.ROOT,p.OUT
def main():
 raw=payload(o/'selected-final/owner-candidate.o',p.FUNCTION);truth=payload(o/'original-target.o',p.FUNCTION);assert p.normalize(*raw)==truth;relation=p.proof(raw,truth);w=o/'boundaries';w.mkdir(exist_ok=True);target=w/'raw.o';p.assemble(p.assembly(*raw),target)
 layout=w/'layout.csv';lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[s for s in lines if s.split(',')[1:3]==['game_EF410',p.FUNCTION]];assert len(rows)==1;layout.write_bytes((lines[0]+'\n'+rows[0]+'\n').encode());guards=w/'guards.csv';guards.write_bytes((o/'private-guards.csv').read_bytes().splitlines(keepends=True)[0]+(o/'guard-suffix.csv').read_bytes())
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,'game_EF410',word_patches_path=guards),lambda f:p.pg.emit_padded_assembly(f,o/'original-target.s',filename='game_EF410',word_patches_path=guards)];outputs=[]
 for i,emit in enumerate(emitters):
  f=w/f'padded-{i}.o';p.assemble(emit(target),f);assert payload(f,p.FUNCTION)==truth;outputs.append(f)
 pins=rejects=visible=0
 for at in range(0,816,4):
  data=bytearray(raw[0]);data[at+3]^=4
  try:p.normalize(bytes(data),raw[1])
  except AssertionError:pins+=1
  else:raise AssertionError('word pin failed')
  f=w/'corrupt.o';p.assemble(p.assembly(data,raw[1]),f)
  for i,emit in enumerate(emitters):
   if at//4 in p.MANIFEST['guard_indices']:
    try:emit(f)
    except ValueError as error:assert p.FUNCTION in str(error);rejects+=1
    else:raise AssertionError('guard did not reject')
   else:
    out=w/f'visible-{i}.o';p.assemble(emit(f),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 for at in raw[1]:
  refs={k:list(v)for k,v in raw[1].items()};kind,n=refs[at][0];refs[at]=[(kind,n+'_wrong')]
  try:p.normalize(raw[0],refs)
  except AssertionError:pins+=1
  else:raise AssertionError('binding pin failed')
  f=w/'binding.o';p.assemble(p.assembly(raw[0],refs),f)
  for i,emit in enumerate(emitters):
   if at//4 in p.MANIFEST['guard_indices']:
    try:emit(f)
    except ValueError as error:assert p.FUNCTION in str(error);rejects+=1
    else:raise AssertionError('binding guard did not reject')
   else:
    out=w/f'binding-{i}.o';p.assemble(emit(f),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 oversized=w/'oversized.o';p.assemble(p.assembly(raw[0]+b'\0\0\0\0',raw[1]),oversized);oversize=[]
 for emit in emitters:
  try:text=emit(oversized)
  except ValueError as error:assert p.FUNCTION in str(error);oversize.append('rejected')
  else:assert '__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 arrangements=[(0x150c1f60,0x800a0230),(0x250c1f60,0x80017ff8),(0x350c1f60,0x90019000),(0x450c1f60,0xa002fffc)];links=runs=0
 for k,(entry,base)in enumerate(arrangements):
  syms=dict(g.S);syms.update({n:base+4*i for i,n in enumerate(g.GLOBALS)});syms['func_15151A38']=entry+0x18000;syms['func_15150178']=entry+0x1a000;programs=[]
  for i,f in enumerate([target,*outputs,o/'original-target.o']):
   script=w/f'{k}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');defs={n:syms[n]for a in raw[1].values()for _,n in a};q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,*[f'--defsym={n}=0x{a:X}'for n,a in defs.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;data=sections(elf)['.text'][1];words=list(struct.unpack('>204I',data[:816]));assert not any(data[816:]);assert words==g.bound_blob(*payload(f,p.FUNCTION),syms);programs.append(words);links+=1
  for c in[g.Case(),g.Case(0xabcdef81,9,8,3,1)]:
   initial=g.fixture(c,syms);models=[]
   for words in programs:
    m=g.Oracle(words,initial,c,entry=entry,s=syms);m.run();g.check(m,initial,c,syms);models.append(m);runs+=1
   assert all(g.state(m)==g.state(models[0])for m in models[1:])
 q=dict(relation=relation,whole_source_and_binding_pins=pins,guarded_word_rejections=rejects,non_guard_word_or_binding_corruption_visible=visible,oversized=oversize,GNU_links=links,guest_rebase_runs=runs,HI_carry_negative_LO_and_JAL_regions_verified=True,source_installed=p.installed(),matching_credit=0);(o/'qualification.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
