import json,struct,subprocess
from tools.tests import game_effect_descriptor_150c1e34_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary

def main():
 NAME='func_150C1E34';programs=[];links=0
 for tag in ('padded_150C1E34_generic','padded_150C1E34_generated','original_150C1E34'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
  actual={'D_800A0228':g.CONST,'func_151429E0':g.COLOR,'func_150ADA20':g.RANDOM,'func_1518CA80':g.EMIT}
  programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ff8,0x8000,0xfff8):
   syms={'D_800A0228':0x80010000|low,'func_151429E0':0x15140000|low,'func_150ADA20':0x150a0000|low,'func_1518CA80':0x15180000|low}
   expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_150C1E34_%04x_%s.ld'%(low,tag))
   script.write_text('SECTIONS { .text 0x150C1E34 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   assert expected==list(struct.unpack_from('>72I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.packet,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0
 for c in (g.Case(0.,0.,0.,0.,0.,0.,0.,0),g.Case(1.25,-2.,3.5,-1.5,7.,8.,4.5,15,8,1),g.Case(-23.125,4.25,17.75,19.,-2.,-4.125,-19.75,0xffffffff)):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=48,inserted_words=1,helpers='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_150C1E34_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
