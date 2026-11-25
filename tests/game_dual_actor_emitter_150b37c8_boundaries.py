"""Scoped guard equivalence, failure controls, slot limits and GNU rebasing."""
from unittest.mock import patch
import csv,io,json,struct,subprocess
from tools.experiments import game_dual_actor_emitter_150b37c8_match as p
from tools.tests import game_dual_actor_emitter_150b37c8_guest as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_classifier_candidates import sections


def pool_controls():
 from tools.tests.game_owner_pool import normalized_pools
 expected={'.rodata':None,'.data':None}
 for f in[p.OUT/'selected-final/owner-candidate.o',p.OUT/'selected-final/owner-before.o']:
  assert normalized_pools(f)==expected
 expected={'.rodata':None,'.data':(b'',())}
 for f in[p.OUT/'baseline'/p.MANIFEST['object'],p.OUT/'qualified-owner/generic.o',p.OUT/'qualified-owner/generated.o']:
  assert normalized_pools(f)==expected
 return 0

def main():
 raw,refs=payload(p.OUT/'selected-final/owner-candidate.o',p.FUNCTION);truth=payload(p.OUT/'original-target.o',p.FUNCTION);assert p.normalize(raw,refs)==truth;w=p.OUT/'boundaries';w.mkdir(exist_ok=True);standalone=w/'raw.o';p.assemble(p.assembly(raw,refs),standalone)
 lines=(p.OUT/'baseline/conker/retail_layout.us.txt').read_text().splitlines();rows=[v for v in lines if v.split(',')[1:3]==[p.MANIFEST['filename'],p.FUNCTION]];assert len(rows)==1;layout=w/'layout.csv';layout.write_text(lines[0]+'\n'+rows[0]+'\n');guard=w/'target-guards.csv';header=(p.OUT/'selected-guards.csv').read_text().splitlines()[0];guard.write_text(header+'\n'+p.MANIFEST['guard_additions'])
 full=p.pg.load_word_patches(p.OUT/'selected-guards.csv',p.MANIFEST['filename']);scoped=p.pg.load_word_patches(guard,p.MANIFEST['filename']);assert {k:v for k,v in full.items()if k[0]==p.FUNCTION}==scoped;pins={int(row[2],0)for row in csv.reader(io.StringIO(p.MANIFEST['guard_additions']))};assert len(pins)==85
 assert raw[:0x3c]==truth[0][:0x3c] and raw[0x2c8:]==truth[0][0x2c8:]
 from tools.tests import game_dual_actor_emitter_150b37c8_symbolic as symbolic
 proof=symbolic.main()
 slot=p.OUT/'original-slot.s';slot.write_text((p.OUT/'original-target.s').read_text()+'\n/* E0F58 150B3AA8 00000000 */ nop\n/* E0F5C 150B3AAC 00000000 */ nop\n')
 emitters=[lambda f:p.pc.emit_padded_assembly(f,layout,p.MANIFEST['filename'],word_patches_path=guard),lambda f:p.pg.emit_padded_assembly(f,slot,filename=p.MANIFEST['filename'],word_patches_path=guard)];outputs=[]
 for i,emit in enumerate(emitters):
  out=w/f'padded-{i}.o';p.assemble(emit(standalone),out);assert payload(out,p.FUNCTION)==truth;outputs.append(out)
 rejected=visible=0
 for at in range(0,736,4):
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
 over=w/'oversize.o';p.assemble(p.assembly(raw+bytes(16),refs),over);oversize=[]
 for emit in emitters:
  try:text=emit(over)
  except ValueError:oversize.append('rejected')
  else:assert '__retail_overflow_'+p.FUNCTION in text;oversize.append('visible overflow')
 data,bindings=truth;names={n for a in bindings.values()for _,n in a};calls={n for a in bindings.values()for k,n in a if k=='R_MIPS_26'};links=runs=0
 for group,(entry,low)in enumerate([(g.ENTRY,0),(0x250b37c8,0x7ff8),(0x350b37c8,0x8000),(0x450b37c8,0xfff8)]):
  symbols={n:(entry&0xf0000000)+0x00210000+0x20000*i+low for i,n in enumerate(sorted(calls))};symbols.update({n:0x80100000+0x20000*i+low for i,n in enumerate(sorted(names-calls))});programs=[]
  for i,f in enumerate([p.OUT/'normalized-target.o',*outputs,p.OUT/'original-target.o',standalone]):
   script=w/f'{group}-{i}.ld';script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');q=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.FUNCTION,*[f'--defsym={n}=0x{a:X}'for n,a in symbols.items()],'-o',str(elf),str(f)],capture_output=True,text=True);assert q.returncode==0,q.stderr;body=sections(elf)['.text'][1];assert not any(body[736:]);words=list(struct.unpack_from('>184I',body));assert words==g.bound_blob(*payload(f,p.FUNCTION),symbols);programs.append(words);links+=1
  assert all(v==programs[0]for v in programs[:-1])
  replacements=dict(ENTRY=entry,FRNG=symbols['func_150ADA68'],RNG=symbols['func_150ADA20'],SUBMIT=symbols['func_1513C73C'],FACTORY=symbols['func_15147DA0'],TEMPLATE=symbols['D_80088700'])
  with patch.multiple(g,**replacements):
   for c in[g.Case(),g.Case(mode=15,phase=8,fcsr=3)]:
    models=[g.check(ws,c,entry=entry)for ws in programs];assert all(g.state(m)==g.state(models[0])for m in models[1:-1])
    observable=lambda m:(g.public(m.memory,c),g.packet_snapshots(m.memory,c),m.r,m.f,m.fcsr,m.hi,m.lo,m.calls,m.observations)
    assert observable(models[-1])==observable(models[0]);runs+=len(models)

 q=dict(symbolic_observation_proof=proof,checked_private_spill_bytes=4,private_frame_patch=False,frame_saved_and_incoming_outgoing_homes_unchanged=True,guarded_corruptions_rejected=rejected,unguarded_corruptions_visible=visible,binding_pins=binding_controls,literal_pool_corruptions_rejected=pool_controls(),no_owner_literal_or_data_pools=True,full_and_scoped_target_guard_rows_equal=True,GNU_links=links,guest_rebase_runs=runs,oversized=oversize,source_installed=p.installed(),matching_credit=0);(p.OUT/'boundaries.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps(q),flush=True);return q
if __name__=='__main__':main()
