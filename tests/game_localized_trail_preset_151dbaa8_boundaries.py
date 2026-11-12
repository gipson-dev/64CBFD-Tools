import json,struct,subprocess
from tools.tests import game_localized_trail_preset_151dbaa8_oracle as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 NAME='func_151DBAA8';programs=[];links=0
 for tag in ('padded_151DBAA8_generic','padded_151DBAA8_generated','original_151DBAA8'):
  path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[NAME]['value'],fs[NAME]['size'];refs={i-a:v for i,v in rs.items() if a<=i<a+n};actual={'D_800AB4C0':g.CONST,'D_800AB4C4':g.CONST+4,'D_800AB4C8':g.CONST+8,'D_800AB4CC':g.CONST+12,'func_15153F18':g.HELPER};programs.append(bound_blob(data[a:a+n],refs,actual))
  for low in (0,0x7ffc,0x8000,0xfffc):
   syms={'D_800AB4C0':0x80010000|low,'D_800AB4C4':0x80020000|low,'D_800AB4C8':0x80030000|low,'D_800AB4CC':0x80040000|low,'func_15153F18':0x15150000|low};expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_151DBAA8_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x151DBAA8 : SUBALIGN(4) { *(.text) } }\n');elf=script.with_suffix('.elf')
   v=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',NAME,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert v.returncode==0,v.stderr
   binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>75I',binary.read_bytes()));links+=1
 def state(m):return(m.memory,m.r,m.f,m.calls,m.packet,m.call_args,m.trace,m.current_pc,m.delay_of,m.hi,m.lo,m.condition)
 cuts=0
 for c in (g.Case((0,0,0),0,0,0,0,0),g.Case((0x3f800000,0xc0200000,0x40400000),-1,255,255,0xffffffff,1),g.Case((0x7fc01234,0x80000000,0x7f800000),65535,0x1ff,0x12345678,0x12345678,1)):
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
 report=dict(gnu_rebased_links=links,access_cut_triples=cuts,guard_rows=68,inserted_words=1,helper='modeled',hardware_or_native_fault_not_qualified=True,source_installed=False)
 (g.out/'boundaries_151DBAA8_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
