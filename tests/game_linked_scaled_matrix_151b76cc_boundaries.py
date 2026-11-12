import json,struct,subprocess
from tools.tests import game_linked_scaled_matrix_151b76cc_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_151B76CC';programs=[];links=0
 actual={'func_150A8050':g.ROTATE,'func_150A7960':g.TRANSFORM}
 for tag in ('padded_151B76CC_generic','padded_151B76CC_generated','original_151B76CC'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfff8):
   syms={'func_150A8050':0x150A0000|low,'func_150A7960':0x150B0000|low};expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_151B76CC_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x151B76CC : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf');v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>74I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0
 for c in (g.Case(-2.,.5,-3.,0,0,0),g.Case(-0.,2.,0.,1,1,0),g.Case(.5,-2.,9.,0,0,1),g.Case(2.,1.,-3.,1,1,1)):
  full=g.Oracle(programs[0],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing cut',c,cut))
    models.append(m)
   assert all(state(m)==state(models[0])for m in models[1:]),(c,cut);cuts+=1
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=38,inserted_words=0,helpers='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False);(g.out/'boundaries_151B76CC_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
