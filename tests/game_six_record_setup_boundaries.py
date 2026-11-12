import json,struct,subprocess
from tools.tests import game_six_record_setup_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_15010110'
def state(m):return(m.memory,m.r,m.f,m.calls,m.packets,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 links=cuts=0;programs=[]
 for tag in ('generic','generated','original'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
  actual={'D_800B0E00':g.OBJECTS,'D_80090298':g.PARAM-0x50,'D_800963A0':g.RECORDS,'func_15195AA8':g.SETUP,'func_151ACBD4':g.EMIT};programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'D_800B0E00':0x80010000|low,'D_80090298':0x80020000|low,'D_800963A0':0x80030000|low,'func_15195AA8':0x150a0000|low,'func_151ACBD4':0x150b0000|low}
   expected=bound_blob(data[a:a+n],refs,syms);script=g.out/(f'rebase_{tag}_{low:04x}.ld');script.write_text(f'SECTIONS {{ .text 0x{g.ENTRY:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
   p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={k}=0x{v:X}'for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>74I',binary.read_bytes()));links+=1
 corpus=g.cases()
 for c in (corpus[0],corpus[31],corpus[-1]):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,helpers='modeled',source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
