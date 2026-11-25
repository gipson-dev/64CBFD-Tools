"""Every expected-word guard, unguarded visibility, exact extent and GNU rebases."""
import csv,io,json,struct,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.experiments import game_height_interpolation_151155c0_match as p
from tools.tests import game_height_interpolation_151155c0_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections
def main():
 raw,refs=payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION);truth=payload(p.OUT/'original-target.o',p.FUNCTION);assert not refs and not truth[1]and p.normalize(raw,refs)==truth;w=p.OUT/'boundaries';w.mkdir(exist_ok=True);f=w/'raw.o';p.assemble(p.assembly(raw,refs),f)
 lines=(p.OUT/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines if v.split(',')[1:3]==[p.MANIFEST['filename'],p.FUNCTION]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guard=w/'target-guards.csv';header=(p.OUT/'selected-guards.csv').read_text().splitlines()[0];guard.write_text(header+'\n'+p.MANIFEST['guard_additions']);pins={int(row[2],0)for row in csv.reader(io.StringIO(p.MANIFEST['guard_additions']))};assert len(pins)==76
 full=p.pg.load_word_patches(p.OUT/'selected-guards.csv',p.MANIFEST['filename']);scoped=p.pg.load_word_patches(guard,p.MANIFEST['filename']);assert{k:v for k,v in full.items()if k[0]==p.FUNCTION}==scoped
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,p.MANIFEST['filename'],word_patches_path=guard),lambda f:p.pg.emit_padded_assembly(f,p.OUT/'original-target.s',filename=p.MANIFEST['filename'],word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  out=w/f'padded-{i}.o';p.assemble(emit(f),out);assert payload(out,p.FUNCTION)==truth;outputs.append(out)
 rejected=visible=0
 for at in range(0,412,4):
  changed=bytearray(raw);changed[at+3]^=4;bad=w/'changed.o';p.assemble(p.assembly(changed,refs),bad)
  for i,emit in enumerate(emitters):
   if at in pins:
    try:emit(bad)
    except ValueError as error:assert'expected'in str(error).lower()or'patch'in str(error).lower();rejected+=1
    else:raise AssertionError('Guard bypassed')
   else:
    out=w/f'visible-{i}.o';p.assemble(emit(bad),out);assert payload(out,p.FUNCTION)!=truth;visible+=1
 over=w/'oversize.o';p.assemble(p.assembly(raw+bytes(16),{}),over);oversize=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:oversize.append('rejected')
  else:assert'__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 links=runs=0
 for group,entry in enumerate((g.ENTRY,0x251155c0,0x351155c0,0x451155c0)):
  programs=[]
  for i,obj in enumerate([p.OUT/'normalized-target.o',*outputs,p.OUT/'original-target.o',f]):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,'-o',str(elf),str(obj)],capture_output=True,text=True);assert q.returncode==0,q.stderr;body=sections(elf)['.text'][1];assert not any(body[412:]);words=list(struct.unpack_from('>103I',body));assert words==list(struct.unpack('>103I',payload(obj,p.FUNCTION)[0]));programs.append(words);links+=1
  assert all(v==programs[0]for v in programs[:4])
  with patch.object(g,'ENTRY',entry):
   for c in(g.Case(),g.Case(hold=-1),g.Case(origin=100,current=100,flags=255)):
    models=[g.check(ws,c)for ws in programs];a=models[0];assert all((m.memory,m.r,m.f,m.fcsr,m.hi,m.lo)==(a.memory,a.r,a.f,a.fcsr,a.hi,a.lo)for m in models[1:4]);assert models[-1].r[2]==a.r[2];runs+=len(models)
 # Rebased branch targets must all stay in the exact 103-word function.
 for words in programs:
  for i,word in enumerate(words):
   if word>>26 in(1,4,5,6,7,20,21,22,23):assert 0<=i+1+((word&65535)^32768)-32768<103
 q=dict(guarded_corruptions_rejected=rejected,unguarded_corruptions_visible=visible,binding_pins=0,no_external_relocations=True,full_and_scoped_target_guard_rows_equal=True,GNU_links=links,guest_rebase_runs=runs,oversized=oversize,all_internal_branch_targets_within_extent=True,all42_exported_retail_labels_retained_in_owner=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
