import json,struct,subprocess
from tools.tests import game_twin_view_vertices_guest as g
from tools.pad_generated_object import parse_object
from tools.experiments.game_path_heading_turn_roles import bound_blob
from tools.tests.test_game_actor_burst_consumer_match import AccessBoundary
def main():
 reports=[]
 for target,owner,index in g.TARGETS:
  name='func_'+target;entry=int(target,16);programs=[];links=0
  for tag in ('padded_'+target+'_generic','padded_'+target+'_generated','original_'+target):
   path=g.out/(tag+'.o');data,fs,rs=parse_object(path);a,n=fs[name]['value'],fs[name]['size'];refs={i-a:v for i,v in rs.items()if a<=i<a+n};actual=dict(func_151D5D60=g.BACKEND,memcpy=g.COPY,D_800DD1D8=g.AXIS_Z,D_800DD1E8=g.AXIS_X);programs.append(bound_blob(data[a:a+n],refs,actual))
   for low in (0,0x7ffc,0x8000,0xfffc):
    syms={'func_151D5D60':0x151d0000|low,'memcpy':0x10010000|low,'D_800DD1D8':0x80010000|low,'D_800DD1E8':0x80020000|low};expected=bound_blob(data[a:a+n],refs,syms);script=g.out/('rebase_'+target+'_%04x_%s.ld'%(low,tag));script.write_text('SECTIONS { .text 0x%X : SUBALIGN(4) { *(.text) } }\n'%entry);elf=script.with_suffix('.elf');r=subprocess.run(['mips-linux-gnu-ld','-T',str(script),'-e',name,*['--defsym=%s=0x%X'%item for item in syms.items()],'-o',str(elf),str(path)],capture_output=True,text=True);assert r.returncode==0,r.stderr
    binary=script.with_suffix('.bin');subprocess.run(['mips-linux-gnu-objcopy','-j','.text','-O','binary',str(elf),str(binary)],capture_output=True,check=True);assert expected==list(struct.unpack_from('>119I',binary.read_bytes()));links+=1
  cuts=0
  for c in (g.Case(success=0),g.Case(fresh=0),g.Case(fresh=1,mutation=1),g.Case(connected=5)):
   full=g.Oracle(programs[0],c,entry);full.run()
   for cut in range(full.all_accesses):
    models=[]
    for ws in programs:
     m=g.Oracle(ws,c,entry);m.cut=cut
     try:m.run()
     except AccessBoundary:pass
     else:raise AssertionError(('missing cut',target,c,cut))
     models.append(m)
    assert all(g.base.state(m)==g.base.state(models[0]) for m in models[1:]),(target,c,cut);cuts+=1
  reports.append(dict(target=target,gnu_rebased_links=links,access_cut_triples=cuts))
 report=dict(targets=reports,guard_rows=0,hardware_or_native_fault_not_qualified=True,source_installed=False);(g.out/'boundaries_screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
