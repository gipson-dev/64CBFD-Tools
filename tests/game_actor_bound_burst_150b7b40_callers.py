"""Use both original jump tables and the real actor-state call into this parent."""
import hashlib,json,struct,subprocess
from tools.tests import game_actor_bound_burst_150b7b40_oracle as g
from tools.experiments.game_paired_ground_constructor_match import payload
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset,symbol_rows
from tools.experiments.game_path_heading_turn_roles import bound_blob
CALLER,SITE,CASE=0x1507D754,0x1507DA90,0x1507DA88
TABLES=((0x8009B6DC,27,0x77),(0x8009B748,79,5))
def prepare():
 elf=(g.f/'conker/build/conker.us.elf').read_bytes();rom=(g.f/'conker/conker.us.bin').read_bytes();lookup={v[1]:v[2][1]for v in symbol_rows(elf)}
 text=(g.f/'conker/asm/nonmatchings/game_A9D90/func_1507D754.s').read_text();fragment=text.split('endlabel func_1507D754')[0]+'.size func_1507D754,.-func_1507D754\n'
 asm=g.p/'real-caller.s';obj=asm.with_suffix('.o');asm.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.set gp=64\n.text\n'+fragment)
 q=subprocess.run(['mips-linux-gnu-as','-EB','-mtune=vr4300','-march=vr4300','-mabi=32','-I','include','-o',str(obj),str(asm)],cwd=g.source.ROOT/'conker',capture_output=True,text=True);assert q.returncode==0 and not q.stderr,(q.stdout,q.stderr)
 raw,refs=payload(obj,'func_1507D754');words=bound_blob(raw,refs,lookup);truth=rom[0xAAC04:0xAAC04+len(raw)]
 assert len(raw)==1008 and struct.pack('>252I',*words)==truth
 at=elf_slot_offset(elf,CALLER,len(raw));assert elf[at:at+len(raw)]==truth
 assert words[(SITE-CALLER)//4]==0x0D42DED0
 tables={};states=[]
 for address,count,base in TABLES:
  at=elf_slot_offset(elf,address,count*4);data=elf[at:at+count*4];tables.update({address+i:b for i,b in enumerate(data)})
  states.extend(base+i for i,v in enumerate(struct.unpack('>%dI'%count,data))if v==CASE)
 assert states and len(states)==len(set(states)),states
 return words,tables,states,hashlib.sha256(truth).hexdigest()
class Oracle(g.Oracle):
 def __init__(self,caller,parent,tables,state,c):
  initial=g.fixture(c);initial.update(tables);initial[g.ACTOR+4]=state;self.boundaries=0
  super().__init__(caller,c,entry=CALLER,initial=initial,arguments=(g.ACTOR,),connected=dict(zip(range(g.ENTRY,g.ENTRY+1936,4),parent)))
 def record_call(self,target):
  if target==g.ENTRY:
   assert tuple(self.arguments(3))==(g.ACTOR,255,1);self.boundaries+=1;return
  return super().record_call(target)
def main():
 caller,tables,states,sha=prepare();programs=[v for v in g.streams()if v[0]in('retail','captured-model')];assert len(programs)==2
 results={};reports=[]
 for stream_index,(label,parent)in enumerate(programs):
  count=0;calls=0;seen=set()
  for state in states:
   for index,c in enumerate(g.cases()):
    if c.null:continue
    m=Oracle(caller,parent,tables,state,c).run();assert m.boundaries==1 and m.r[2]==0
    assert tuple(m.r[16:24])+tuple(m.r[28:])==m.saved and tuple(m.f[20:])==m.saved_fp
    result=(m.calls,g.public(m.memory),m.r[2],g.data(m.memory,g.STACK+c.phase-56,72))
    key=state,index
    if stream_index==0:results[key]=result
    else:assert result==results[key],('real caller',label,state,c)
    seen.update(m.visits&set(range(g.ENTRY,g.ENTRY+1936,4)));count+=1;calls+=len(m.calls)
  # This caller requires a valid actor; the null-only likely delay is covered
  # by the standalone parent fixture rather than this connected path.
  unseen=set(range(g.ENTRY,g.ENTRY+1936,4))-seen
  assert len(unseen)==2 and sorted(parent[(a-g.ENTRY)//4]for a in unseen)==sorted((0x8FBF007C,0x3C013F80)),(len(seen),sorted(unseen))
  row=dict(stream=label,cases=count,target_reachable_words=len(seen),provider_calls=calls,real_call_boundary_verified=True,caller_return_zero=True,caller_owned_bytes=72,saved_ABI=True,dead_caller_saved_temporaries_unclaimed=True,unvisited=[hex(a)for a in sorted(unseen)]);reports.append(row);print(json.dumps(row),flush=True)
 report=dict(passes=True,streams=reports,caller_words=252,caller_GNU_ROM_and_production_ELF_verified=True,caller_sha256=sha,call_site=SITE,states=states,two_original_jump_tables_used=True,slot=255,context=1,child_providers_modeled=True,other_dispatch_states_unclaimed=True,source_installed=False,c_match_credit=0)
 (g.p/'real-caller-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':main()
