"""Pool/body fail-closed controls, unchanged padders and independent GNU links."""
from pathlib import Path
from unittest.mock import patch
import json,struct,subprocess
from tools.experiments import game_point_spray_150c71c0_match as p
from tools.tests import game_point_spray_150c71c0_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
r,o=p.ROOT,p.OUT
def main():
 raw=payload(o/'selected-final/owner-candidate.o',p.FUNCTION);data,refs=p.normalize(*raw);truth=payload(o/'original-target.o',p.FUNCTION);assert(data,refs)==truth;w=o/'boundaries';w.mkdir(exist_ok=True);standalone=w/'raw.o';p.assemble(p.assembly(data,refs),standalone)
 lines=(o/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines if v.split(',')[1:3]==['generated_F44D0',p.FUNCTION]];assert len(rows)==1;layout=w/'layout.csv';layout.write_bytes((lines[0]+'\n'+rows[0]+'\n').encode());guard=o/'baseline/conker/retail_word_patches.us.csv'
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,'generated_F44D0',word_patches_path=guard),lambda f:p.pg.emit_padded_assembly(f,o/'original-target.s',filename='generated_F44D0',word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  path=w/f'padded-{i}.o';p.assemble(emit(standalone),path);assert payload(path,p.FUNCTION)==truth;outputs.append(path)
 def carrier(blob,bindings,pool=bytes.fromhex('3ed0624e')+bytes(12),other=''):
  # GNU encodes bare section-symbol names as empty strings; IDO uses the
  # named .rodata symbol. Give this independent carrier a named alias, then
  # shorten only its symbol-string spelling without changing ELF geometry.
  refs={at:[(k,'__test_pool'if n=='.rodata'else n)for k,n in a]for at,a in bindings.items()}
  text=p.assembly(blob,refs)+other.replace(',.rodata',',__test_pool')+'\n.section .rodata,"a"\n.globl __test_pool\n__test_pool:\n'+''.join('.byte %d\n'%v for v in pool);path=w/'pool-control.o';p.assemble(text,path);content=path.read_bytes();assert content.count(b'__test_pool\0')==1;path.write_bytes(content.replace(b'__test_pool\0',b'.rodata\0'+bytes(4)));return path
 def rejected(path):
  try:p.verify(path)
  except ValueError:return
  raise AssertionError('Pool validation accepted corruption')
 assert p.verify(carrier(*raw))['verified'];word_pins=binding_pins=visible=0
 for at in range(0,396,4):
  changed=bytearray(raw[0]);changed[at+3]^=4;rejected(carrier(changed,raw[1]));word_pins+=1
  path=w/'changed.o';p.assemble(p.assembly(changed,refs),path)
  for i,emit in enumerate(emitters):
   out=w/f'visible-{i}.o';p.assemble(emit(path),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 for at in raw[1]:
  changed={k:list(v)for k,v in raw[1].items()};kind,n=changed[at][0];changed[at]=[(kind,n+'_wrong')];rejected(carrier(raw[0],changed));binding_pins+=1
 pool_controls=0
 for at in range(16):
  pool=bytearray(bytes.fromhex('3ed0624e')+bytes(12));pool[at]^=1;rejected(carrier(*raw,pool=pool));pool_controls+=1
 rejected(carrier(*raw,other='\n.globl other_pool_user\n.type other_pool_user,@function\nother_pool_user:\n.reloc .,R_MIPS_HI16,.rodata\n.word 0x3c010000\n.size other_pool_user,.-other_pool_user\n'));pool_controls+=1
 rejected(carrier(raw[0]+bytes(4),raw[1]));pool_controls+=1
 over=w/'oversize.o';p.assemble(p.assembly(data+bytes(8),refs),over);oversize=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:oversize.append('rejected')
  else:assert '__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 names={n for a in refs.values()for _,n in a};calls={n for a in refs.values()for k,n in a if k=='R_MIPS_26'};links=runs=0
 for group,(entry,low)in enumerate([(0x150c71c0,0),(0x250c71c0,0x7ff8),(0x350c71c0,0x8000),(0x450c71c0,0xfff8)]):
  symbols={n:(entry&0xf0000000)+0x00210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});programs=[]
  for i,path in enumerate([standalone,*outputs,o/'original-target.o']):
   script=w/f'{group}-{i}.ld';script.write_bytes((f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n').encode());elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert q.returncode==0,q.stderr;body=sections(elf)['.text'][1];assert not any(body[396:]);words=list(struct.unpack_from('>99I',body));assert words==g.bound_blob(*payload(path,p.FUNCTION),symbols);programs.append(words);links+=1
  assert all(v==programs[0]for v in programs)
  with patch.multiple(g,GLOBALS=tuple(symbols[n]for n in ['D_800A0498','D_800A049C','D_800A04A0','D_800A04A4']),COEFFICIENT=symbols['D_800A0494'],ENTRY=entry,RNG=symbols['func_150ADA20'],FRNG=symbols['func_150ADA68'],EMIT=symbols['func_151DB5D0']):
   for c in[g.Case(),g.Case(mode=15,phase=8,alias=3,fcsr=3)]:
    models=[g.check(words,c,entry=entry)for words in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=len(models)
 q=dict(whole_raw_word_pins=word_pins,binding_pins=binding_pins,pool_or_other_user_controls=pool_controls,no_word_guards_and_all_corruptions_visible=visible,oversized=oversize,GNU_links=links,guest_rebase_runs=runs,HI_carry_negative_LO_and_JAL_regions_verified=True,source_installed=p.installed(),matching_credit=0);(o/'boundaries.json').write_bytes((json.dumps(q,indent=2)+'\n').encode());print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
