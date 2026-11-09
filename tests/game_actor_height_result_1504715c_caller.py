"""Retail/linked call census and original native position-query caller."""
import bisect,csv,json,struct,sys,subprocess
from pathlib import Path
from unittest.mock import patch
from tools.experiments.game_actor_height_result_1504715c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.match_progress import load_elf_functions
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests import test_game_actor_height_result_builder as fixture
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
ENTRY=0x1504715C
def main():
 rom=(root/'conker/conker.us.bin').read_bytes();jal=0x0C000000|((ENTRY>>2)&0x3FFFFFF);sites=[];pointers=[]
 for i,(w,)in enumerate(struct.iter_unpack('>I',rom[:len(rom)&~3])):
  if w==jal:sites.append(i*4)
  if w==ENTRY:pointers.append(i*4)
 fs,_,addresses=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump');linked={n:[addresses[n]+4*i for i,w in enumerate(ws)if w==jal]for n,ws in fs.items()if jal in ws}
 with(root/'conker/progress.csv').open(newline='')as f:rows=sorted((int(r['offset']),int(r['length']),r['function'])for r in csv.DictReader(f)if r.get('section')=='game')
 starts=[a for a,n,f in rows];retail={}
 for at in sites:
  pc=at-0x2D4B0+0x15000000;i=bisect.bisect_right(starts,pc)-1;a,n,name=rows[i];assert a<=pc<a+n;retail.setdefault(name,[]).append(pc)
 assert set(linked)<=set(retail)and len(sites)==53 and len(linked)==25 and not pointers
 for name in linked:assert len(retail[name])==len(linked[name]),name
 missing={n:dict(retail_calls=len(retail[n]),existing_linked_words=len(fs[n]),reason='Retail call absent in pre-existing non-matching caller')for n in set(retail)-set(linked)}
 before,_,_=load_elf_functions(str(out/'frozen/conker/build/conker.us.elf'),'mips-linux-gnu-objdump');assert all(fs[n]==before[n]for n in retail)
 with patch.object(fixture,'__file__',str(root/'tools/tests/test_game_actor_height_result_builder.py')),patch.object(fixture.highest,'__file__',str(root/'tools/tests/test_game_highest_height_query.py')):fixture.GameActorHeightResultBuilderTests.setUpClass()
 try:prefix=fixture.GameActorHeightResultBuilderTests.source
 finally:fixture.GameActorHeightResultBuilderTests.doClassCleanups()
 old=body(prefix,'func_1504715C');selected=body((out/'final-owner.c').read_text(),'func_1504715C');prefix=prefix.replace(old,selected).replace('i < sizeof(actor)','(u32)i < sizeof(actor)').replace('i < sizeof(output)','(u32)i < sizeof(output)')
 caller=body((root/'conker/src/game/generated_E7970.c').read_text(),'func_150BA930')
 prefix+='''
f32 D_8009FE60=-1000.0f;
static int query_calls,query_error;
s32 func_15046C80(f32 *start,u16 mode,f32 lower,HeightResult71820 *result){
 query_calls++;
 if(start[0]!=-12.75f || start[1]!=94.25f || start[2]!=23.75f || lower!=-105.75f || mode || result!=&output || result->flags!=41 || result->state!=2 || result->value!=(s32)&entities[0] || result->vertices[0]!=988)query_error=1;
 return (s32)0x87654321;
}
'''+caller+'''
static int run(void){
 f32 position[3];
 initialize();actor.flags=0x200000;actor.entityIndex=1;helper_return=256;mutation=42;
 if(func_150BA930(position,(u8*)&actor,&output,0)!=(s32)0x87654321 || query_calls!=1 || query_error || calls!=1 || error)return 1;
 if(position[0]!=-12.75f || position[1]!=-5.75f || position[2]!=23.75f)return 2;
 initialize();query_calls=query_error=0;
 if(func_150BA930(position,(u8*)&actor,0,0)!=1 || query_calls || calls)return 3;
 return 0;
}
'''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native-caller.c';p.write_text(prefix);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native-caller'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-function',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,real_caller='func_150BA930',final_query_bounded=True)
 report=dict(retail_callers=retail,linked_callers=linked,preexisting_missing_calls=missing,literal_call_count=len(sites),literal_address_values=pointers,native_caller=profiles,all_other_caller_linked_bodies_unchanged=True,complete_caller_guest_or_hardware_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(literal_call_count=len(sites),caller_functions=len(retail),native_profiles=profiles)),flush=True);return report
if __name__=='__main__':main()
