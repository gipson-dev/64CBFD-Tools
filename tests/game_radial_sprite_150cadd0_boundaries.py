"""Scoped guard equivalence, failure controls, slot limits and GNU rebasing."""
from unittest.mock import patch
import csv,io,json,struct,subprocess
from tools.experiments import game_radial_sprite_150cadd0_match as p
from tools.tests import game_radial_sprite_150cadd0_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
from tools import check_ring_updater_150c8a68_pool as pool_check

def pool_controls():
 f=p.OUT/'selected-final/owner-candidate.o';pool_check.verify(f);data=f.read_bytes();h=pool_check.ELF_HEADER.unpack_from(data);headers=[pool_check.SECTION_HEADER.unpack_from(data,h[6]+i*h[11])for i in range(h[12])];n=headers[h[13]];names=data[n[4]:n[4]+n[5]];index=next(i for i,a in enumerate(headers)if pool_check.read_c_string(names,a[0])=='.rodata');pool=headers[index];changes=[]
 for i in range(pool[5]):
  bad=bytearray(data);bad[pool[4]+i]^=1;changes.append(bad)
 bad=bytearray(data);at=h[6]+index*h[11]+8;bad[at:at+4]=(pool[2]|1).to_bytes(4,'big');changes.append(bad)
 bad=bytearray(data);bad[5]=1;changes.append(bad)
 for i,bad in enumerate(changes):
  path=p.OUT/('pool-control-'+str(i)+'.o');path.write_bytes(bad)
  try:pool_check.verify(path)
  except ValueError:pass
  else:raise AssertionError('Corrupt literal section accepted')
 return len(changes)
def main():
 raw,refs=payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION);truth=payload(p.OUT/'original-target.o',p.FUNCTION);assert p.normalize(raw,refs)==truth;w=p.OUT/'boundaries';w.mkdir(exist_ok=True);standalone=w/'raw.o';p.assemble(p.assembly(raw,refs),standalone)
 lines=(p.OUT/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines if v.split(',')[1:3]==[p.MANIFEST['filename'],p.FUNCTION]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guard=w/'target-guards.csv';header=(p.OUT/'selected-guards.csv').read_text().splitlines()[0];guard.write_text(header+'\n'+p.MANIFEST['guard_additions'])
 full=p.pg.load_word_patches(p.OUT/'selected-guards.csv',p.MANIFEST['filename']);scoped=p.pg.load_word_patches(guard,p.MANIFEST['filename']);assert {k:v for k,v in full.items()if k[0]==p.FUNCTION}==scoped;pins={int(row[2],0)for row in csv.reader(io.StringIO(p.MANIFEST['guard_additions']))};assert len(pins)==38
 # Every emitted access/pointer into the live private packet follows one map.
 private=((0x2c,124),);mapped=0
 for i,(word,)in enumerate(struct.iter_unpack('>I',raw)):
  op,base,at=word>>26,word>>21&31,word&65535
  if base!=29 or op not in(9,35,40,41,43,49,57):continue
  width=1 if op==40 else 2 if op==41 else 0 if op==9 else 4
  region=next(((start,n)for start,n in private if start<=at<start+n),None)
  if region is None:assert 4*i not in pins;continue
  assert 4*i in pins and at+width<=sum(region) and int.from_bytes(truth[0][4*i:4*i+4],'big')==word-4;mapped+=1
 assert mapped==38
 for a,n in private:
  assert a-4>=0x20 and a-4+n<=168
  assert all(a+n<=z or z+m<=a for z,m in private if z!=a)
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,p.MANIFEST['filename'],word_patches_path=guard),lambda f:p.pg.emit_padded_assembly(f,p.OUT/'original-target.s',filename=p.MANIFEST['filename'],word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  out=w/f'padded-{i}.o';p.assemble(emit(standalone),out);assert payload(out,p.FUNCTION)==truth;outputs.append(out)
 rejected=visible=0
 for at in range(0,568,4):
  changed=bytearray(raw);changed[at+3]^=4;f=w/'changed.o';p.assemble(p.assembly(changed,refs),f)
  for i,emit in enumerate(emitters):
   if at in pins:
    try:emit(f)
    except ValueError as error:assert 'expected'in str(error).lower()or'patch'in str(error).lower();rejected+=1
    else:raise AssertionError('Corrupt guarded word accepted')
   else:
    out=w/f'visible-{i}.o';p.assemble(emit(f),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 binding_controls=0
 for at in refs:
  changed={k:list(v)for k,v in refs.items()};kind,name=changed[at][0];changed[at]=[(kind,name+'_wrong')]
  try:p.normalize(raw,changed)
  except AssertionError:binding_controls+=1
  else:raise AssertionError('Binding pin bypassed')
 over=w/'oversize.o';p.assemble(p.assembly(raw+bytes(4),refs),over);oversize=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:oversize.append('rejected')
  else:assert '__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 data,bindings=truth;names={n for a in bindings.values()for _,n in a};calls={n for a in bindings.values()for k,n in a if k=='R_MIPS_26'};links=runs=0
 for group,(entry,low)in enumerate([(g.ENTRY,0),(0x250cadd0,0x7ff8),(0x350cadd0,0x8000),(0x450cadd0,0xfff8)]):
  symbols={n:(entry&0xf0000000)+0x00210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});programs=[]
  for i,f in enumerate([p.OUT/'normalized-target.o',*outputs,p.OUT/'original-target.o']):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;body=sections(elf)['.text'][1];assert not any(body[568:]);words=list(struct.unpack_from('>142I',body));assert words==g.bound_blob(*payload(f,p.FUNCTION),symbols);programs.append(words);links+=1
  assert all(v==programs[0]for v in programs)
  replacements=dict(ENTRY=entry,RNG=symbols['func_150ADA20'],FRNG=symbols['func_150ADA68'],DIRECTION=symbols['func_15143794'],SUBMIT=symbols['func_15132A4C'],CONSTANTS=tuple(symbols['D_%08X'%a]for a in g.CONSTANTS))
  with patch.multiple(g,**replacements):
   for c in[g.Case(),g.Case(mode=7,phase=8,fcsr=3)]:
    models=[g.check(ws,c,entry=entry)for ws in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:]);runs+=len(models)

 q=dict(all_private_accesses_and_pointers_mapped=38,frame_saved_and_incoming_outgoing_homes_unchanged=True,guarded_corruptions_rejected=rejected,unguarded_corruptions_visible=visible,binding_pins=binding_controls,literal_pool_corruptions_rejected=pool_controls(),full_and_scoped_target_guard_rows_equal=True,GNU_links=links,guest_rebase_runs=runs,oversized=oversize,source_installed=p.installed(),matching_credit=0);(p.OUT/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
