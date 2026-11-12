import json,struct,subprocess
from tools.tests import game_twin_effect_constructors_b_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_151B50F4';programs=[];links=0
 for tag in ('padded_151B50F4_generic','padded_151B50F4_generated','original_151B50F4'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
  actual={'D_800AA3E8':g.CONST,'D_800AA3EC':g.CONST+4,'D_800AA3F0':g.CONST+8,'D_800AA3F4':g.CONST+12,'func_150ADA68':g.RANDF,'func_150ADA20':g.RANDI,'func_151D9014':g.EMIT}
  programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'D_800AA3E8':0x80010000|low,'D_800AA3EC':0x80020000|low,'D_800AA3F0':0x80030000|low,'D_800AA3F4':0x80040000|low,'func_150ADA68':0x150a0000|low,'func_150ADA20':0x150b0000|low,'func_151D9014':0x151d0000|low}
   expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_151B50F4_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x151B50F4 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   assert expected==list(struct.unpack_from('>82I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.observed,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0
 for c in (g.cases()[0],g.cases()[71],g.cases()[-1]):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=10,inserted_words=0,helpers='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_151B50F4_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
