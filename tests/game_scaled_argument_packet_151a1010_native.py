"""Defined numeric native32 domain for both recovered private source forms."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,os,subprocess,sys
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments import game_scaled_argument_packet_151a1010_recovery as m
from tools.tests import game_scaled_argument_packet_151a1010_oracle as g
p,r=m.OUT,m.ROOT

def main():
 record=json.loads((m.FROZEN/'fingerprints.json').read_text())
 def immutable():
  m.check_inputs()
 immutable();spans=(-32768,-32767,-1,0,1,15,16,31,32,33,63,64,32735,32736,32767);factors=((0.0,-0.0),(1.0,1.0),(-1.0,2.0),(0.125,0.75),(22.0,819.5),(100.0,512.25),(5000.0,2048.5),(-5000.0,-2048.5))
 cases=[g.Case(span=a,scale=b,rate=c,variant=v,flags=g.old.u32(0x87654321+i*0x10203))for i,(a,(b,c),v)in enumerate(itertools.product(spans,factors,(0,255)))]
 cases += [g.Case(span=spans[i%len(spans)],scale=factors[i%len(factors)][0],rate=factors[i%len(factors)][1],variant=i,flags=g.old.u32(i*0x1020304))for i in range(256)]
 retail=g.original(g.ENTRY,111);rows=[]
 for c in cases:
  expected=g.reference(c);assert g.Machine(retail,c).run().calls_seen==[expected]
  rows.append('{%du,%du,%du,%du,%du,%du,{%s}}'%(g.old.u32(c.span),g.bits(c.scale),g.bits(c.rate),c.variant,g.old.u32(c.flags),0,','.join('%du'%n for n in expected)))
 floats={0,1,2,3,4,10,17};types=['f32'if i in floats else's32'for i in range(28)];types[26]='u32';params=', '.join(t+' a'+str(i)for i,t in enumerate(types));prototype='void func_151A11CC('+params+');\n'
 prefix='''typedef signed int s32;typedef unsigned int u32;typedef signed short s16;typedef unsigned short u16;typedef signed char s8;typedef unsigned char u8;typedef float f32;
 void *memcpy(void *d,const void *s,unsigned n){u8 *a=d;const u8 *b=s;for(unsigned i=0;i<n;i++)a[i]=b[i];return d;}
 __attribute__((noreturn)) static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code) : "memory");__builtin_unreachable();}
 static void check(int good){if(!good)quit(3);}
 static float fp(u32 n){float value;memcpy(&value,&n,4);return value;}
 static u32 bits(float value){u32 n;memcpy(&n,&value,4);return n;}
 const f32 D_800A8D28=1500.0f;
 '''+prototype
 harness='''
 _Static_assert(sizeof(void*)==4,"native32 required");
 struct Vector {u32 span,scale,rate,variant,flags,unused,expected[28];};
 static const struct Vector vectors[]={VECTORS};
 static u32 expected[28];static unsigned calls;
 void func_151A11CC(PARAMS){u32 actual[]={ACTUAL};unsigned i;calls++;for(i=0;i<28;i++)check(actual[i]==expected[i]);}
 static int run(void){unsigned i,j,n;const struct Vector *v;
 for(i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){v=&vectors[i];for(j=0;j<28;j++)expected[j]=v->expected[j];calls=0;
 func_151A1010(fp(expected[0]),fp(expected[1]),fp(expected[2]),(s16)v->span,fp(v->scale),fp(v->rate),(u8)v->variant,(s32)v->flags);check(calls==1);}
 /* Exhaust every representable short input; expected span math uses unsigned
    modulo followed by explicit signed interpretation, independent of source. */
 v=&vectors[2];for(j=0;j<28;j++)expected[j]=v->expected[j];
 for(n=0;n<65536;n++){s32 input=n<32768?(s32)n:(s32)n-65536;s32 adjusted;u32 wrapped=(n+65504u)&65535u;
 adjusted=wrapped<32768?(s32)wrapped:(s32)wrapped-65536;expected[15]=adjusted>0?(u32)adjusted:1u;expected[25]=(u32)(adjusted+16);calls=0;
 func_151A1010(fp(expected[0]),fp(expected[1]),fp(expected[2]),(s16)input,fp(v->scale),fp(v->rate),(u8)v->variant,(s32)v->flags);check(calls==1);}
 return 0;}
 '''.replace('VECTORS',',\n'.join(rows)).replace('PARAMS',params).replace('ACTUAL',','.join('bits(a%d)'%i if i in floats else'(u32)a%d'%i for i in range(28)))+START
 flags=native_command('-O0')+['-std=gnu11','-mstackrealign','-fsanitize=float-cast-overflow','-fno-sanitize-recover=all'];profiles=[]
 def run(label,body,options):
  path=p/(label+'.c');path.write_text(prefix+body+harness);exe=p/label
  done=subprocess.run([*flags,*options,'-o',str(exe),str(path)],capture_output=True,text=True);assert done.returncode==0 and not done.stderr,(label,done.stderr)
  return subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
 bodies={'fitted':m.PIN['fitted_source']}
 for label,body in bodies.items():
  for opt in('-O0','-O2','-O3'):
   for alias in('-fstrict-aliasing','-fno-strict-aliasing'):
    done=run('native-'+label+opt+alias,body,[opt,alias]);assert done.returncode==0 and not done.stdout and not done.stderr,(label,opt,alias,done.returncode,done.stderr);profiles.append(dict(source=label,options=[opt,alias],cases=len(cases)+65536))
 body=bodies['fitted'];controls={
 'direct-float-to-short':body.replace('(s16)(s32)','(s16)'),
 'clamped-final-span':body.replace('    finalSpan = (s32)span + 16;\n    if (clampedSpan <= 0) clampedSpan = 1;','    if (clampedSpan <= 0) clampedSpan = 1;\n    finalSpan = (s32)clampedSpan + 16;'),
 'narrow-full32-output':body.replace('(s32)(90.0f * rate)','(s16)(s32)(90.0f * rate)'),
 'signed-variant':body.replace('variant, flags','(s8)variant, flags'),
 }
 negatives=[]
 for label,changed in controls.items():
  assert changed!=body;done=run('native-negative-'+label,changed,['-O2','-fstrict-aliasing']);assert done.returncode!=0,('ineffective negative',label);negatives.append(dict(name=label,exit=done.returncode))
 immutable();report=dict(private_only=True,c_match_credit=0,native32=True,guest_derived_vectors=len(cases),exhaustive_short_inputs=65536,cases_per_profile=len(cases)+65536,profiles=profiles,UBSan_and_float_cast_traps=True,effective_controls=negatives,domain='finite values and products inside s32 truncation range; integer narrowing uses target two-complement semantics',production_state_matches_audited_inputs=len(record['inputs']))
 (p/'native-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
