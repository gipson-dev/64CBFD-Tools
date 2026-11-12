import json,struct,subprocess
from tools.tests import game_oscillating_effect_151db97c_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_151DB97C';programs=[];links=0
 actual={'D_800BE9E4':g.TICK,'func_15131918':g.DAMP,'func_151423D8':g.SINE}
 for tag in ('padded_151DB97C_generic','padded_151DB97C_generated','original_151DB97C'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
  programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={name:base|low for name,base in zip(actual,(0x80010000,0x15010000,0x15020000))};expected=bound_blob(data[a:a+n],refs,syms)
   script=g.out/('rebase_151DB97C_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x151DB97C : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   assert expected==list(struct.unpack_from('>75I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0;cases=list(g.cases())
 for c in (cases[0],next(c for c in cases if c.flags==2 and c.mutation==3),next(c for c in cases if c.flags==3 and c.mutation==6)):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=0,inserted_words=0,helpers='modeled with mutations',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_151DB97C_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
