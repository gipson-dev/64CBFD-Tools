"""Retail caller census and both real C spawn wrappers with the actual quad."""
import json,sys
from pathlib import Path
from tools.experiments.game_vertex_quad_1513e13c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_vertex_quad_1513e13c_native as native
from tools.experiments.game_remaining_donor_candidates import body
from tools.experiments.game_remaining_donor_candidates import function_span

def wrappers():
 text=(root/'conker/src/game_169510.c').read_text();parts=[]
 for name in('func_1513C4EC','func_1513C5B0'):
  adjusted=text.replace('struct210 *'+name+'(','void *'+name+'(');a,b=function_span(adjusted,name);parts.append(adjusted[a:b].replace('void *'+name+'(','struct210 *'+name+'('))
 return r'''
struct210 *func_1513C350(struct210 *,s32,u8,u8,u8,s32,s32,struct167 *,s32,u8,s32);
void func_1513E13C(struct210 *p,f32 x,f32 y,f32 z,f32 w,f32 d,u8 a){subject(p,x,y,z,w,d,a);}
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wint-conversion"
#pragma GCC diagnostic ignored "-Wincompatible-pointer-types"
'''+ '\n'.join(parts)+r'''
#pragma GCC diagnostic pop
static int factoryMode,allocate,factoryCalls;
__attribute__((noinline)) struct210 *func_1513C350(struct210 *descriptor,s32 table,u8 a,u8 b,u8 variant,s32 count,s32 user,struct167 *payload,s32 extra,u8 channel,s32 context){
 factoryCalls++;if((u32)descriptor!=0x12345678||table!=-321||a!=201||b!=7||variant!=199||extra!=-333||channel!=254||context!=0x76543210)error=4;
 if(factoryMode==1){f32*p=(f32*)payload;if(count!=3||user!=-7||!p||bits(p[0])!=c->coordinates[0]||bits(p[1])!=c->coordinates[1]||bits(p[2])!=c->coordinates[2])error=5;}
 else if(count||user||payload)error=6;
 return allocate?&record:NULL;
}
static int invokeCaller(int mode,int allocated){struct210 *result;factoryMode=mode;allocate=allocated;factoryCalls=0;
 if(mode==1)result=func_1513C4EC(0x12345678,-321,201,7,floating(c->coordinates[0]),floating(c->coordinates[1]),floating(c->coordinates[2]),floating(c->coordinates[3]),floating(c->coordinates[4]),c->angle,199,3,-7,-333,254,0x76543210);
 else result=func_1513C5B0(0x12345678,-321,201,7,floating(c->coordinates[0]),floating(c->coordinates[1]),floating(c->coordinates[2]),floating(c->coordinates[3]),floating(c->coordinates[4]),c->angle,199,-333,254,0x76543210);
 return factoryCalls!=1||result!=(allocated?&record:NULL);
}
'''

def main():
 rom=(root/'conker/conker.us.bin').read_bytes();entry=0x1513E13C;jal=(0x0C000000|((entry>>2)&0x3FFFFFF)).to_bytes(4,'big');calls=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==jal];ptrs=[i for i in range(0,len(rom)-3,4)if rom[i:i+4]==entry.to_bytes(4,'big')]
 assert calls==[0x169A44,0x169AE4] and not ptrs,(calls,ptrs)
 selected=body((out/'final-owner.c').read_text(),'func_1513E13C');program=native.harness(selected,wrappers());profiles={opt:native.execute(program,'caller-native'+opt,opt)for opt in('-O0','-O2','-O3')}
 report=dict(profiles=profiles,cases_per_profile=len(native.rows())*10,real_C_wrappers=['func_1513C4EC','func_1513C5B0'],aligned_ROM_JALs=[hex(x)for x in calls],aligned_literal_pointers=0,factory_failure_skips_quad=True,allocated_pointer_return_checked=True,all_factory_arguments_checked=True,legacy_pointer_conversion_diagnostics_scoped=True,bounded_factory=True,full_gameplay_claimed=False)
 (out/'caller.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
