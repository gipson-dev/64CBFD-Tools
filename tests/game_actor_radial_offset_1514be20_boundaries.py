import json,struct,subprocess
from tools.tests import game_actor_radial_offset_1514be20_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_1514BE20';programs=[];links=0
 for tag in ('padded_1514BE20_generic','padded_1514BE20_generated','original_1514BE20'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};programs.append(bound_blob(data[a:a+n],refs,{'func_15145128':g.HELPER}))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'func_15145128':0x15140000|low};expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_1514BE20_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x1514BE20 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>76I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition,m.sample)
 cuts=0
 for c in (g.Case(0.,0.,0.,0.,0),g.Case(0.,0.,0.,0.,1),g.Case(-100.,200.,0.,.5,0),g.Case(200.,-100.,200.,1.,1),g.Case(-100.,-100.,200.,2.,1)):
  full=g.Oracle(programs[0],c);full.run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing cut',c,cut))
    models.append(m)
   assert all(state(m)==state(models[0]) for m in models[1:]),(c,cut);cuts+=1
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=64,inserted_words=4,helper='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_1514BE20_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
