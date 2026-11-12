import json,struct,subprocess
from tools.tests import game_registered_update_walker_151670c0_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_151670C0';programs=[];links=0
 for tag in ('padded_151670C0_generic','padded_151670C0_generated','original_151670C0'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
  actual={'D_8008B4A8':g.TABLE,'D_800DCE50':g.LISTS,'D_800DD190':g.DEPTH,'D_800DD198':g.SLOTS};programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'D_8008B4A8':0x80010000|low,'D_800DCE50':0x80020000|low,'D_800DD190':0x80030000|low,'D_800DD198':0x80040000|low}
   expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_151670C0_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x151670C0 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   assert expected==list(struct.unpack_from('>74I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.observed,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 c=g.Case(pattern=3,mutation=3,depth=2,phase=8);full=g.Oracle(programs[0],c);full.run();cuts=0
 for cut in range(full.all_accesses):
  models=[]
  for ws in programs:
   m=g.Oracle(ws,c);m.cut=cut
   try:m.run()
   except AccessBoundary:pass
   else:raise AssertionError(('missing cut',cut))
   models.append(m)
  assert all(state(m)==state(models[0]) for m in models[1:]),cut;cuts+=1
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=35,inserted_words=0,callbacks='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_151670C0_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
