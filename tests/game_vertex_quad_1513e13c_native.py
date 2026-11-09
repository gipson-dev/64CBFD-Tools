"""Real SDK record layout, float32 quad geometry and effective native controls."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_vertex_quad_1513e13c_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_vertex_quad_1513e13c_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def mutations(selected):
 rows={
 'quarter-direction':selected.replace('angle - 0x40','angle + 0x40'),
 'same-trig-result':selected.replace('cosine = func_151423D8(angle);','cosine = sine;'),
 'wrong-coordinate':selected.replace('xPlus = x + widthCos;','xPlus = z + widthCos;'),
 'wrong-truncation':selected.replace('yInt = (s32)y;','yInt = (s32)(y + 1.0f);'),
 'wrong-corner-sign':selected.replace('(xPlus - depthSin)','(xPlus + depthSin)'),
 'wrong-corner-stride':selected.replace('record->unk74 =','record->unk64 ='),
 'wrong-width':selected.replace('widthCos = halfWidth * cosine;','widthCos = halfDepth * cosine;'),
 'reassociated-coordinate':selected.replace('record->unk40 = (s32)(xPlus - depthSin);','record->unk40 = (s32)(x + (widthCos - depthSin));'),
 'early-output':selected.replace('    sine =','    record->unk40 = 0;\n    sine =',1),
 'padding-write':selected.replace('    sine =','    *((u8 *)record + 0x47) = 0;\n    sine =',1),
 }
 assert len(rows)==10 and all(v!=selected for v in rows.values());return rows

def rows():
 values=guest.table();result=[]
 coords=((0.,-0.,0.,0.,0.),(12.5,-25.,43.5,110.,80.),(-12.75,-5.75,23.75,-110.,80.),(32767.75,-32769.75,-32768.75,1024.,4096.),(16777216.,0.,16777216.,1.,1.),(1000000.,-2147483648.,-1000000.,1000000.,1000000.))
 for p in coords:
  for angle in range(256):
   for scripted in(0,1):
    words=tuple(guest.bits(v)for v in p);returns=(guest.bits(.75),guest.bits(-.25))if scripted else(guest.cos(angle-64,values),guest.cos(angle,values));expected=guest.geometry(words,*returns)
    result.append('{ {'+','.join('0x%Xu'%x for x in words)+'}, {'+','.join('0x%Xu'%x for x in returns)+'}, {'+','.join(str(x)for x in expected)+'}, %d }'%angle)
 return result

def harness(selected,callers=''):
 variants={'candidate':selected,**mutations(selected)}
 prefix='#include <ultra64.h>\n#include "structs.h"\n'
 prefix+='typedef void(*Builder)(struct210 *,f32,f32,f32,f32,f32,u8);\nstatic Builder subject;\nf32 func_151423D8(u8);\n'
 for name,part in variants.items():prefix+=part.replace('func_1513E13C(',name.replace('-','_')+'(',1)+'\n'
 return prefix+r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(struct210)==0x158,"real SDK record");
_Static_assert(__builtin_offsetof(struct210,unk40)==0x40,"first vertex");
_Static_assert(__builtin_offsetof(struct210,unk74)==0x74,"last vertex");
struct Case {u32 coordinates[5],returns[2];u16 expected[12];u8 angle;};
static const struct Case cases[]={ROWS};static const struct Case*c;
static struct210 record;static u8 before[0x158];static int calls,error,mutate;
static f32 floating(u32 x){union{u32 u;f32 f;}v;v.u=x;return v.f;}
static u32 bits(f32 x){union{u32 u;f32 f;}v;v.f=x;return v.u;}
__attribute__((noinline)) f32 func_151423D8(u8 angle){int i;u8*p=(u8*)&record;
 if(calls>1){error=1;return 0;}
 if(angle!=(u8)(c->angle-(calls==0?64:0)))error=2;
 for(i=0;i<0x158;i++)if(p[i]!=before[i])error=3;
 if(mutate){p[0]^=0x55;before[0]^=0x55;p[0x40]=(u8)(0x12+calls);before[0x40]=p[0x40];}
 return floating(c->returns[calls++]);
}
static const u8 offsets[12]={0x40,0x42,0x44,0x50,0x52,0x54,0x60,0x62,0x64,0x70,0x72,0x74};
CALLERS
static int one(int caller,int allocated){int i;u8*p=(u8*)&record;
 for(i=0;i<0x158;i++)p[i]=before[i]=(u8)(i*29+0x59);
 calls=error=0;
 INVOKE
 if(error||calls!=(caller&&!allocated?0:2))return 1;
 if(!caller||allocated)for(i=0;i<12;i++){before[offsets[i]]=(u8)c->expected[i];before[offsets[i]+1]=(u8)(c->expected[i]>>8);}
 for(i=0;i<0x158;i++)if(p[i]!=before[i])return 2;
 return 0;
}
static int check(Builder fn,int caller){u32 i;int result,allocated;subject=fn;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++)for(mutate=0;mutate<2;mutate++){
  c=&cases[i];for(allocated=caller?0:1;allocated<2;allocated++){result=one(caller,allocated);if(result)return result;}}
 return 0;
}
RUN
'''.replace('ROWS',',\n'.join(rows())).replace('CALLERS',callers).replace('INVOKE',invocation(bool(callers))).replace('RUN',run(bool(callers)))+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')

def invocation(callers):
 args='&record,floating(c->coordinates[0]),floating(c->coordinates[1]),floating(c->coordinates[2]),floating(c->coordinates[3]),floating(c->coordinates[4]),c->angle'
 if not callers:return '(void)caller;(void)allocated;subject('+args+');'
 return 'if(caller){if(invokeCaller(caller,allocated))return 3;}else subject('+args+');'

def run(callers):
 text='static int run(void){if(check(candidate,0))return 1;\n'
 if callers:text+='if(check(candidate,1)||check(candidate,2))return 2;\n'
 else:
  for i,name in enumerate(mutations(body((out/'final-owner.c').read_text(),'func_1513E13C'))):text+='if(!check('+name.replace('-','_')+',0))return '+str(i+20)+';\n'
 return text+'return 0;}\n'

def execute(program,label,opt):
 p=out/(label+'.c');p.write_text(program);exe=p.with_suffix('');r=subprocess.run(native_command(opt)+['-fno-strict-aliasing','-Wno-unused-function',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
 r=subprocess.run([str(exe)],capture_output=True,timeout=30);assert r.returncode==0 and not r.stdout and not r.stderr,(label,r.returncode,r.stderr);return dict(exit=0,UBSan=True)

def main():
 selected=body((out/'final-owner.c').read_text(),'func_1513E13C');program=harness(selected);profiles={opt:execute(program,'native'+opt,opt)for opt in('-O0','-O2','-O3')}
 report=dict(profiles=profiles,cases_per_profile=len(rows())*2,effective_controls=len(mutations(selected)),SDK32_record_layout=True,all_256_angles=True,negative_extents=True,signed32_truncation_then_halfword_wrap=True,reassociation_boundary=True,callback_snapshots=True,untouched_record_bytes=True,guest_parameter_home_mutation_claimed=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
