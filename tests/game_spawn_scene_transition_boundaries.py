import json,struct,subprocess
from tools.tests import game_spawn_scene_transition_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_1507DFE4'
def state(m):return(m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 links=cuts=0;programs=[]
 for tag in ('generic','generated','original'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
  actual={'D_800C35EA':g.MODE,'D_800BE9F0':g.SCENE,'D_800C3670':g.FLAG0,'D_800C3671':g.FLAG1,'func_15084D70':g.QUERY,'func_15022190':g.TRANSFORM,'func_1501D348':g.DISPATCH};programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'D_800C35EA':0x80010000|low,'D_800BE9F0':0x80020000|low,'D_800C3670':0x80030000|low,'D_800C3671':0x80040000|low,'func_15084D70':0x150a0000|low,'func_15022190':0x150b0000|low,'func_1501D348':0x151d0000|low}
   expected=bound_blob(data[a:a+n],refs,syms);script=g.out/(f'rebase_{tag}_{low:04x}.ld');script.write_text(f'SECTIONS {{ .text 0x{g.ENTRY:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={k}=0x{v:X}'for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>76I',binary.read_bytes()));links+=1
 corpus=g.cases()
 for c in (corpus[0],corpus[151],corpus[-1]):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,query_and_dispatch_modeled=True,source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
