"""Every target word, binding and guard, plus independent GNU rebases."""
from pathlib import Path
from tools.experiments import game_owner_effect_packet_1514e31c_packet as target_packet
import csv,io,json,struct,subprocess,sys
from tools import pad_generated_object as pg
sys.modules.setdefault('pad_generated_object',pg)
from tools import pad_c_object as pc
from tools.experiments.game_local_vector_transform_15117da4_match import assembly
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.experiments.game_actor_classifier_candidates import sections
R=target_packet.ROOT;O=target_packet.OUT;B=O/'baseline';FN='func_1514E31C';OWNER='generated_179F30'
def assemble(text,path):
 s=path.with_suffix('.s');s.write_text(text);p=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I',str(R/'conker/include'),'-o',str(path),str(s)],capture_output=True,text=True);assert p.returncode==0,p.stderr
def main():
 target_packet.prepare()
 raw,refs=payload(O/'selected-owner.o',FN);truth=payload(O/'original-target.o',FN)
 w=O/'boundaries';w.mkdir(exist_ok=True);rows=(B/'conker/retail_layout.us.txt').read_text().splitlines();selected=[s for s in rows if s.split(',')[1:3]==[OWNER,FN]];assert len(selected)==1
 layout=w/'layout.csv';layout.write_text(rows[0]+'\n'+selected[0]+'\n');header=(O/'selected-guards.csv').read_text().splitlines()[0]+'\n';guards=w/'guards.csv';added=list(csv.reader(io.StringIO((O/'guard-additions.csv').read_text())));assert len(added)==32
 def save_guards(path,values):
  out=io.StringIO(newline='');out.write(header);csv.writer(out,lineterminator='\n').writerows(values);path.write_text(out.getvalue())
 save_guards(guards,added)
 emitters=[lambda p:pc.emit_padded_assembly(p,layout,OWNER,word_patches_path=guards),lambda p:pg.emit_padded_assembly(p,O/'original-target.s',filename=OWNER,word_patches_path=guards)]
 obj=w/'raw.o';assemble(assembly(raw,refs,FN),obj);outs=[]
 for i,emit in enumerate(emitters):
  p=w/f'padded-{i}.o';assemble(emit(obj),p);assert payload(p,FN)==truth;outs.append(p)
 # CSV application is independent from the structural role/permutation proof.
 manual=bytearray(raw)
 for row in added:
  off=int(row[2],0);assert int.from_bytes(manual[off:off+4],'big')==int(row[3],0)
  tag=refs.get(off,[]);tag=tag[0][0]+':'+tag[0][1]if tag else '-';assert tag==row[5]==row[6]
  manual[off:off+4]=int(row[4],0).to_bytes(4,'big')
 assert(bytes(manual),refs)==truth;manual_obj=w/'manual.o';assemble(assembly(manual,refs,FN),manual_obj)
 visible=word_rejected=bindings_visible=binding_rejected=guard_injected=necessary=0
 for off in range(0,492,4):
  bad=bytearray(raw);bad[off+3]^=4;p=w/'changed.o';assemble(assembly(bad,refs,FN),p)
  for i,emit in enumerate(emitters):
   try:text=emit(p)
   except ValueError as e:assert 'stale 'in str(e);word_rejected+=1
   else:
    result=w/f'visible-{i}.o';assemble(text,result);assert payload(result,FN)!=truth;visible+=1
 for off in refs:
  bad={k:list(v)for k,v in refs.items()};kind,name=bad[off][0];bad[off]=[(kind,name+'_wrong')];p=w/'wrong-binding.o';assemble(assembly(raw,bad,FN),p)
  for i,emit in enumerate(emitters):
   try:text=emit(p)
   except ValueError as e:assert 'stale 'in str(e);binding_rejected+=1
   else:
    result=w/f'binding-visible-{i}.o';assemble(text,result);assert payload(result,FN)!=truth;bindings_visible+=1
 for row in added:
  off=int(row[2],0);bad={k:list(v)for k,v in refs.items()};bad[off]=[('R_MIPS_LO16','D_guard_injected')];p=w/'guard-injected.o';assemble(assembly(raw,bad,FN),p)
  for emit in emitters:
   try:emit(p)
   except ValueError as e:assert 'stale 'in str(e);guard_injected+=1
   else:raise AssertionError(('guard accepted unexpected binding',off))
  save_guards(guards,[r for r in added if r is not row])
  for i,emit in enumerate(emitters):
   result=w/f'missing-guard-{i}.o';assemble(emit(obj),result);assert payload(result,FN)!=truth;necessary+=1
  save_guards(guards,added)
 assert(visible,word_rejected,bindings_visible,binding_rejected,guard_injected,necessary)==(182,64,14,0,64,64)
 p=w/'oversize.o';assemble(assembly(raw+bytes(16),refs,FN),p);overflow=[]
 for emit in emitters:
  try:text=emit(p)
  except ValueError as e:overflow.append(dict(result='rejected',reason=str(e)))
  else:assert '__retail_overflow_'+FN in text;overflow.append(dict(result='visible overflow'))
 links=0
 for group,low in enumerate((0,0x7ffc,0x8000,0xfffc)):
  entry=0x1514e31c+group*0x10000000
  syms={f'D_{a:08X}':0x80010000+group*0x01000000+i*0x10000+((low+i*4)&65535) for i,a in enumerate((0x800a5e18,0x800a5e1c))}
  syms.update({n:0x150a0000+group*0x10000000+i*0x10000+low for i,n in enumerate(('func_15189FF0','func_1514EC1C','func_15160A58'))})
  expected=bound_blob(*truth,syms)
  for tag,path in [('raw',obj),('manual',manual_obj),('retail',O/'original-target.o'),('generic',outs[0]),('generated',outs[1])]:
   ld=w/f'{group}-{tag}.ld';ld.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=ld.with_suffix('.elf')
   q=subprocess.run(['mips-linux-gnu-ld','-T',str(ld),'-e',FN,*[f'--defsym={n}=0x{v:X}'for n,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert q.returncode==0,q.stderr
   blob=sections(elf)['.text'][1];assert not any(blob[492:]);words=list(struct.unpack_from('>123I',blob));assert words==bound_blob(*payload(path,FN),syms)
   if tag!='raw':assert words==expected
   links+=1
 report=dict(all_word_mutations_visible_or_rejected=visible+word_rejected,guard_word_rejections=word_rejected,all_binding_mutations_visible_or_rejected=bindings_visible+binding_rejected,guard_binding_rejections=binding_rejected,all_32_guard_unexpected_binding_rejections=guard_injected,all_32_guard_removals_visible=necessary,GNU_links=links,independent_symbol_groups=4,signed_HI16_LO16_carries=True,raw_manual_retail_generic_generated_routes=True,overflow=overflow,source_installed=target_packet.installed(),matching_credit=0)
 (O/'boundaries.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
 return report
if __name__=='__main__':main()
