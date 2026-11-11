"""Both padders, pinned corruption checks, rebases and access prefixes."""
import csv,io,json,re,struct,subprocess,sys
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.tests import game_packed_motion_1516a648_oracle as g
from tools.experiments import game_packed_motion_1516a648_match as n
from tools import pad_generated_object
sys.modules.setdefault('pad_generated_object',pad_generated_object)
from tools import pad_c_object
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def assemble(text,label):
 path=p.out/(label+'.s');path.write_text(text);obj=path.with_suffix('.o');v=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(path)],cwd=p.root/'conker',capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(v.stdout,v.stderr);return obj
def words(obj,s):
 raw,refs=p.payload(obj);return p.bound_blob(raw,refs,s)
def main():
 asm=p.out/'original-target.s';full=(p.root/'conker/asm/197120.s').read_text();start=full.index('glabel '+p.NAME+'\n');end=full.index('endlabel '+p.NAME,start)+len('endlabel '+p.NAME);asm.write_text(full[start:end]+'\n')
 raw,refs=p.payload(p.out/'independent-selected.o');normal,nrefs=n.normalize(raw,refs);text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+p.NAME+'\n.type '+p.NAME+',@function\n'+p.NAME+':\n'
 for i,(w,)in enumerate(struct.iter_unpack('>I',raw)):
  for kind,name in refs.get(i*4,[]):text+='.reloc ., '+kind+', '+name+'\n'
  text+='.word 0x%08X\n'%w
 obj=assemble(text+'.size '+p.NAME+',.-'+p.NAME+'\n','target-raw');lines=(p.root/'conker/retail_layout.us.txt').read_text().splitlines();selected=[l for l in lines[1:]if l.split(',')[1:3]==['generated_197120',p.NAME]];assert len(selected)==1;layout=p.out/'target-layout.csv';layout.write_text(lines[0]+'\n'+selected[0]+'\n');fields=next(csv.reader(io.StringIO((p.root/'conker/retail_word_patches.us.csv').read_text())));stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(n.rows(raw,refs));guard=p.out/'target-guards.csv';guard.write_text(stream.getvalue())
 a=assemble(pad_c_object.emit_padded_assembly(obj,layout,'generated_197120',word_patches_path=guard),'target-generic');b=assemble(pad_generated_object.emit_padded_assembly(obj,p.out/'original-target.s',filename='generated_197120',word_patches_path=guard),'target-generated');local=re.sub(r'(?m)^  jlabel (\S+)',r'  \1:',asm.read_text());original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+local+'\n.size '+p.NAME+',.-'+p.NAME+'\n','original-reference');assert p.payload(a)==p.payload(b)==p.payload(original)==(normal,nrefs)
 failures=0
 for i in range(292):
  wrong=bytearray(raw);wrong[i]^=1
  try:n.normalize(bytes(wrong),refs)
  except ValueError:failures+=1
  else:raise AssertionError(i)
 for at,es in refs.items():
  for change in(0,1):
   wrong=dict(refs);wrong[at]=[(kind+'_stale'if change else kind,name if change else name+'_stale')for kind,name in es]
   try:n.normalize(raw,wrong)
   except ValueError:failures+=1
   else:raise AssertionError(at)
 guardfails=0;rows=n.rows(raw,refs)
 for i in range(len(rows)):
  altered=[dict(x)for x in rows];altered[i]['expected']='0x%08X'%(int(altered[i]['expected'],16)^1);stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(altered);bad=p.out/'bad-guard.csv';bad.write_text(stream.getvalue())
  try:pad_c_object.emit_padded_assembly(obj,layout,'generated_197120',word_patches_path=bad)
  except (ValueError,AssertionError):guardfails+=1
  else:raise AssertionError(i)
 links=0
 for low in(0,0x7FFC,0x8000,0xFFFC):
  syms=dict(D_800BE9E4=0x80400000+low,func_1516F864=0x15210000+low,func_1510F8D8=0x15220000+low,func_1516F94C=0x15230000+low)
  for i,path in enumerate((obj,a,b,original)):
   expected=words(path,syms);script=p.out/('rebase-%X-%d.ld'%(low,i));script.write_text('SECTIONS { .text 0x1516A648 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',p.NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr;binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>73I',binary.read_bytes()));links+=1
 syms=dict(D_800BE9E4=g.TICKS,func_1516F864=g.UPDATE,func_1510F8D8=g.HEIGHT,func_1516F94C=g.CONTACT);programs=(words(obj,syms),words(a,syms),words(b,syms),words(original,syms));assert programs[1]==programs[2]==programs[3];quads=0
 for c in (g.Case(0,0,1,0,0,0,0),g.Case(0,1,1,0,0,0,0),g.Case(1,255,0,0,0,0,0),g.Case(1,2,64,0,-301,32767,3),g.Case(0,255,0xffffffff,-1,32767,0,2),g.Case(1,1,0x40000000,32767,-32768,0xfffffff5,1)):
  whole=g.Oracle(programs[3],c);whole.run()
  for cut in range(whole.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('Missing access cut',cut))
    models.append(m)
   x,y,z,w=models;assert g.public(x.memory)==g.public(w.memory);assert all((v.memory,v.r,v.f,v.calls,v.trace,v.current_pc,v.delay_of)==(w.memory,w.r,w.f,w.calls,w.trace,w.current_pc,w.delay_of)for v in(y,z));quads+=1
 assert struct.unpack_from('>I',(p.root/'conker/conker.us.bin').read_bytes(),p.ROM+292)[0]==0
 r=dict(body_words=73,slot_words=74,padding_words=1,guards=6,generic_generated_original_equal=True,byte_and_binding_corruptions=failures,individual_guard_corruptions=guardfails,GNU_rebased_links=links,access_cut_quads=quads,raw_private_stack_or_portable_faults_not_qualified=True,source_installed=False);(p.out/'boundaries.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True);return r
if __name__=='__main__':main()
