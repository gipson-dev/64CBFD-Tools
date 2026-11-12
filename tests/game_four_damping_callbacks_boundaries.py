import json,struct,subprocess
from tools.tests import game_four_damping_callbacks_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 reports=[]
 for target,owner,index in g.TARGETS:
  name='func_'+target;entry=int(target,16);programs=[];links=0
  for tag in ('padded_'+target+'_generic','padded_'+target+'_generated','original_'+target):
   path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};programs.append(bound_blob(data[a:a+n],refs,{'D_800BE9E4':g.TICK}))
   for low in (0,0x7ffc,0x8000,0xfffc):
    syms={'D_800BE9E4':0x80010000|low};expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_'+target+'_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);elf=script.with_suffix('.elf');r=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert r.returncode==0,r.stderr
    binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>106I',binary.read_bytes()));links+=1
  cuts=0
  for tick in (0,1,4,5):
   c=next(c for c in g.cases() if c.tick==tick);full=g.Oracle(programs[0],c,entry);full.run()
   for cut in range(full.all_accesses):
    models=[]
    for ws in programs:
     m=g.Oracle(ws,c,entry);m.cut=cut
     try:m.run()
     except AccessBoundary:pass
     else:raise AssertionError(('missing cut',target,c,cut))
     models.append(m)
    assert all(state(m)==state(models[0]) for m in models[1:]),(target,c,cut);cuts+=1
  high=g.Case(0xffffffff,g.bits(1.),g.bits(-2.),g.bits(.75),0,0);high_cuts=0
  for cut in range(80):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,high,entry);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing high-tick cut',target,cut))
    models.append(m)
   assert all(state(m)==state(models[0]) for m in models[1:]),(target,'high tick',cut);high_cuts+=1
  reports.append(dict(target=target,gnu_rebased_links=links,access_cut_triples=cuts,high_tick_prefix_cuts=high_cuts))
 report=dict(targets=reports,guard_rows=0,helpers='none',hardware_or_native_fault_not_qualified=True,source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
