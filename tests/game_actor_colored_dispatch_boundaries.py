import json,struct,subprocess
from tools.tests import game_actor_colored_dispatch_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
NAME='func_151026BC'
def payload(path):
 t,f,r=parse_object(path);a,n=f[NAME]['value'],f[NAME]['size'];return t[a:a+n],{i-a:v for i,v in r.items()if a<=i<a+n}
def assemble(text,label):
 p=g.out/(label+'.s');p.write_text(text);o=p.with_suffix('.o');r=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(o),str(p)],cwd=g.root/'conker',capture_output=True,text=True);assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr);return o
def main():
 whole=(g.root/'conker/asm/12DAB0.s').read_text();body='glabel '+NAME+'\n'+whole.split('glabel '+NAME+'\n',1)[1].split('endlabel '+NAME,1)[0]+'endlabel '+NAME+'\n';body=body.replace('jlabel .L15102720\n','.L15102720:\n')
 original=assemble('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+body+'.size '+NAME+',.-'+NAME+'\n','isolated-original')
 paths=[original]
 for tag in ('mixed-generic','mixed-generated'):
  raw,refs=payload(g.out/(tag+'.o'));text='.set noat\n.set noreorder\n.set gp=64\n.text\n.globl '+NAME+'\n.type '+NAME+',@function\n'+NAME+':\n'
  for i,(word,) in enumerate(struct.iter_unpack('>I',raw)):
   for kind,symbol in refs.get(4*i,[]):text+='.reloc ., '+kind+', '+symbol+'\n'
   text+=f'.word 0x{word:08X}\n'
  paths.append(assemble(text+'.size '+NAME+',.-'+NAME+'\n','isolated-'+tag))
 links=0
 for low in (0,0x7ffc,0x8000,0xfffc):
  syms={'D_800A21A0':0x80010000|low,'D_800A21F4':0x80020000|low,'D_800A2248':0x80030000|low,'D_800A233C':0x80040000|low,'func_15100600':0x150a0000|low,'jtbl_800A2298':0x80090000|low,'jtbl_800A2298_game':0x80090000|low};variants=[]
  for i,path in enumerate(paths):
   script=g.out/f'rebase-{i}-{low:04x}.ld';script.write_text(f'SECTIONS {{ .text 0x{g.ENTRY:X} : SUBALIGN(4) {{ *(.text) }} }}\n');elf=script.with_suffix('.elf');p=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*[f'--defsym={k}=0x{v:X}'for k,v in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert p.returncode==0,p.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],check=True,capture_output=True);variants.append(struct.unpack_from('>75I',binary.read_bytes()));links+=1
  assert variants[0]==variants[1]==variants[2],hex(low)
 actual={'D_800A21A0':g.VEC1,'D_800A21F4':g.VEC2,'D_800A2248':g.BYTE,'D_800A233C':g.FLOAT,'func_15100600':g.HELPER,'jtbl_800A2298_game':g.TABLE};programs=[]
 for path in paths[1:]:
  raw,refs=payload(path);programs.append(bound_blob(raw,refs,actual))
 cuts=0
 for c in (g.Case(0x58,0,0,0),g.Case(0x5a,0,6,0),g.Case(0x59,0x3b,255,8),g.Case(0x59,0x3a,7,0),g.Case(0,0,0,0,False)):
  full=g.Oracle(programs[0],c).run()
  for cut in range(full.all_accesses):
   states=[]
   for words in programs:
    m=g.Oracle(words,c);m.cut=cut
    try:m.run()
    except AccessBoundary:pass
    else:raise AssertionError(('missing cut',c,cut))
    states.append((m.memory,m.r,m.f,m.calls,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition))
   assert states[0]==states[1],(c,cut);cuts+=1
 report=dict(gnu_rebased_links=links,rebases=4,access_cut_pairs=cuts,helper='modeled',source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
