import itertools,json,struct,subprocess
from tools.tests import game_scene_transition_dispatch_guest as g
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
NAME='func_1501C730'
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 programs=[];links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  syms={'D_800D2132':0x80010000|low,'D_800CC2D0':0x80020000|low,'D_800CC382':(0x80020000|low)+0xb2,'D_800BE615':0x80030000|low,'D_800BE616':0x80040000|low,'D_800DD2C0':0x80050000|low,'D_800BE9F4':0x80060000|low,'D_800BEA00':0x80070000|low,'D_800BEA04':0x80080000|low,'func_1501C53C':0x150a0000|low,'func_15016680':0x150b0000|low,'jtbl_800969A0_game':0x80090000|low,'jtbl_800969A0':0x80090000|low}
  variants=[]
  for tag in ('generic','generated','original'):
   path=g.out/(tag+'.o');script=g.out/f'rebase_{tag}_{low:04x}.ld';script.write_text(f'SECTIONS {{ .text 0x{g.ENTRY:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={k}=0x{v:X}' for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
   variants.append(struct.unpack_from('>74I',binary.read_bytes()));links+=1
  assert variants[0]==variants[1]==variants[2],hex(low)
 for tag in ('generic','generated'):
  data,fs,rs=parse_object(g.out/(tag+'.o'));a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n}
  actual={'D_800D2132':g.RESULT,'D_800CC2D0':g.PRIOR-0xb2,'D_800BE615':g.MODE,'D_800BE616':g.GATE,'D_800DD2C0':g.CHANNEL,'D_800BE9F4':g.SCENE,'D_800BEA00':g.ARG4,'D_800BEA04':g.ARG3,'func_1501C53C':g.RESET,'func_15016680':g.ADVANCE,'jtbl_800969A0_game':g.TABLE}
  programs.append(bound_blob(data[a:a+n],refs,actual))
 cuts=0
 for cmd,gate,mutation in itertools.product((0,1,2,3,4,5,6,7),(0,1),(0,1)):
  c=g.Case(cmd,gate,mutation,0);full=g.Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   models=[]
   for ws in programs:
    m=g.Oracle(ws,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing cut',c,cut))
    models.append(m)
   assert state(models[0])==state(models[1]),(c,cut);cuts+=1
 report=dict(gnu_rebased_links=links,rebases=4,access_cut_pairs=cuts,providers_modeled=True,source_installed=False)
 (g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
