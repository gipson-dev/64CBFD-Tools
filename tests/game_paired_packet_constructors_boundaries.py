import json,struct,subprocess
from tools.tests import game_paired_packet_constructors_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def state(m):return(m.memory,m.r,m.f,m.calls,m.packet,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
def main():
 links=cuts=0;corpus=list(g.cases())
 for name,entry,glob in (('func_1514E00C',0x1514e00c,0x800a5e08),('func_1514E194',0x1514e194,0x800a5e10)):
  programs=[]
  for tag in ('generic','generated','retail'):
   path=g.out/(name+'_'+tag+'.o');data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n}
   actual={f'D_{glob:08X}':glob,f'D_{glob+4:08X}':glob+4,'func_15189FF0':g.ALLOC,'func_1514EC1C':g.ATTACH,'func_151D74B0':g.EFFECT};programs.append(bound_blob(data[a:a+n],refs,actual))
   for low in (0,0x7ffc,0x8000,0xfffc):
    syms={f'D_{glob:08X}':0x80010000|low,f'D_{glob+4:08X}':0x80020000|low,'func_15189FF0':0x150a0000|low,'func_1514EC1C':0x150b0000|low,'func_151D74B0':0x151d0000|low}
    expected=bound_blob(data[a:a+n],refs,syms);script=g.out/(f'{name}_{tag}_{low:04x}.ld');script.write_text(f'SECTIONS {{ .text 0x{entry:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf')
    p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*[f'--defsym={k}=0x{v:X}'for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
    binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True)
    assert expected==list(struct.unpack_from('>98I',binary.read_bytes()));links+=1
  for c in (corpus[0],corpus[31],corpus[-1]):
   full=g.Oracle(programs[0],c,entry,glob);full.run()
   for cut in range(full.all_accesses):
    models=[]
    for ws in programs:
     m=g.Oracle(ws,c,entry,glob);m.cut=cut
     try:m.run()
     except AccessBoundary:pass
     else:raise AssertionError(('missing cut',name,c,cut))
     models.append(m)
    assert all(state(m)==state(models[0])for m in models[1:]),(name,c,cut);cuts+=1
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,helpers='modeled',source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
