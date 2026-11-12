from pathlib import Path
import sys,random,subprocess,json,importlib.util
from tools.experiments import game_position_interpolation_match as source
root=source.root;p=source.out
from tools.tests import game_position_interpolation_guest as g
from tools.tests.test_game_point_transform_match import read
from tools.tests.test_game_row_destination_fill import START

def main():
 rng=random.Random(0x10bee); cases=[]; offsets=(0x10,0x12,0x14,0x3c,0x3e);factors=(0,0x80000000,0x3f000000,0xbf000000,0x3f800000,0x3eaaaaab)
 for i in range(200):
  vals=[rng.randrange(-32768,32768) for _ in range(8)];ticks=(0,1,2,3,-1,20)[i%6];factor=factors[i%len(factors)];actor=0x20000;m=g.fixture(actor,vals,ticks,factor)
  try:external,_=g.run(g.ret,m,actor)
  except AssertionError as e:
   if e.args and isinstance(e.args[0],tuple) and e.args[0][0]=='float outside bounded model':continue
   raise
  expected=[read(external,actor+o,2) for o in offsets]
  cases.append((vals,ticks,factor,expected))
 assert len(cases)>=180
 entries=',\n'.join('{{%s},%d,0x%08Xu,{%s}}' % (','.join(str(x) for x in v),t,f,','.join(str(x) for x in e)) for v,t,f,e in cases)
 base=source.MANIFEST['body'];sources={'selected':base,'bad-scale':base.replace('16384.0f','8192.0f'),'clamp-early':base.replace('    p[0x10/2]', '    if (1.0f < t) t = 1.0f;\n    p[0x10/2]',1),'swap-xy':base.replace('p[0x10/2] = (s32)((x1-x0)*t+x0);','p[0x10/2] = (s32)((y1-y0)*t+y0);').replace('p[0x12/2] = (s32)((y1-y0)*t+y0);','p[0x12/2] = (s32)((x1-x0)*t+x0);')}
 fixture='''typedef short s16; typedef int s32; typedef unsigned int u32; typedef unsigned short u16; typedef float f32;\nf32 D_800A0068; s32 D_800BE9E4;\n'''
 casecode='''struct Case { s16 v[8]; s32 tick; u32 factor; u16 expect[5]; };\nstatic const struct Case cases[]={\n'''+entries+'''\n};\nint run(void) { static const int in[]={62,63,64,65,66,67,30,31}; static const int out[]={8,9,10,30,31}; int i,j; s16 data[96]; union {u32 u; f32 f;} factor; for(i=0;i<(int)(sizeof(cases)/sizeof(cases[0]));i++){ for(j=0;j<96;j++)data[j]=(s16)0x5aa5;for(j=0;j<8;j++)data[in[j]]=cases[i].v[j];factor.u=cases[i].factor;D_800A0068=factor.f;D_800BE9E4=cases[i].tick;func_150BE2E8(data);for(j=0;j<5;j++)if((u16)data[out[j]]!=cases[i].expect[j])return 1;}return 0;}\n'''
 results={}
 for name,body in sources.items():
  for opt in ('-O0','-O2','-O3'):
   source_file=p/('native_'+name+opt+'.c');exe=source_file.with_suffix('');source_file.write_text(fixture+body+'\n'+casecode+START)
   args=['cc','-m32',opt,'-std=c99','-fno-strict-aliasing','-msse2','-mfpmath=sse','-mstackrealign','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-ffp-contract=off','-Wall','-Wextra','-Werror',str(source_file),'-o',str(exe)]
   x=subprocess.run(args,capture_output=True,text=True);assert x.returncode==0,x.stderr[:4000]
   x=subprocess.run([str(exe)],timeout=10);results[name+opt]=x.returncode
 assert all(results['selected'+o]==0 for o in ('-O0','-O2','-O3')),results
 assert all(results[n+o]!=0 for n in ('bad-scale','clamp-early','swap-xy') for o in ('-O0','-O2','-O3')),results
 sanitizer_source=p/'native_selected-O2.c';sanitizer_exe=p/'native_selected_ubsan'
 args=['cc','-m32','-O2','-std=c99','-fno-strict-aliasing','-msse2','-mfpmath=sse','-mstackrealign','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-ffp-contract=off','-fsanitize=undefined','-fsanitize-undefined-trap-on-error','-Wall','-Wextra','-Werror',str(sanitizer_source),'-o',str(sanitizer_exe)]
 built=subprocess.run(args,capture_output=True,text=True);assert built.returncode==0,built.stderr[:4000]
 checked=subprocess.run([str(sanitizer_exe)],timeout=10);assert checked.returncode==0,checked.returncode
 print(json.dumps(dict(native32_cases=len(cases),results=results,scope='finite, in-range, nonoverlapping buffers'),indent=2))


if __name__ == "__main__":main()
