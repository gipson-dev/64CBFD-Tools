"""SDK32 typed canvas aliases, complete C relay and observed result controls."""
import itertools,json,subprocess
from tools.experiments import game_base_color_output_1513137c_match as p
from tools.tests import game_base_color_output_1513137c_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
r,o=p.ROOT,p.OUT
def controls():
 body=p.MANIFEST['body'];rows=[('selector','switch (record[0x70])','switch (record[0x71])'),('red','record[0x24]','record[0x25]'),('green','record[0x29]','record[0x28]'),('zero-alpha','*alpha = 0;','*alpha = 1;'),('scale-shift','>> 8','>> 7'),('alpha-product','record[0x2B] * record[0x27]','record[0x27] * record[0x27]'),('case-six','case 6:','case 9:'),('case-eight','case 8:','case 10:'),('zero-chain','*red = *green = *blue;','*red = *green = 1;'),('store-order','*red = record[0x24];\n            *green = record[0x25];\n            *blue = record[0x26];','*blue = record[0x26];\n            *green = record[0x25];\n            *red = record[0x24];')];result={}
 for name,a,b in rows:assert a in body,name;result[name]=body.replace(a,b)
 assert '*alpha = record[0x2B];'in body
 result['cached-alpha']=body.replace('    switch (record[0x70])','    s32 cachedAlpha = record[0x2B];\n    switch (record[0x70])').replace('*alpha = record[0x2B];','*alpha = cachedAlpha;')
 result['cached-scale']=body.replace('    switch (record[0x70])','    s32 cachedScale = record[0x2C];\n    switch (record[0x70])').replace('record[0x2C] *','cachedScale *')
 return result
def rows(wrapper=False):
 result=[]
 for mode,seed,layout in itertools.product(range(256),(0,5),(0,3,8,9)if wrapper else range(10)):
  initial={i:(i*29+seed*53+0x5a)&255 for i in range(256)};initial[64+0x70]=mode;initial[64+0x71]=(mode+seed*17)&255;pointers=g.old.LAYOUTS[layout];other=g.old.LAYOUTS[(layout+3)%10]
  if wrapper:initial=g.old.channels(initial,64,other,little=True)
  expected,_=g.channels(initial,pointers,record=64,little=True);result.append('{'+','.join(map(str,(mode,seed,layout,(layout+3)%10)))+',{'+','.join(map(str,(expected[i]for i in range(256))))+'}}')
 return result
def main():
 direct,relay=rows(),rows(True);variants=controls();prefix='#include <ultra64.h>\n'+p.MANIFEST['color']+'\n'+p.MANIFEST['body']+'\n'+p.MANIFEST['relay']+'\n'
 for name,body in variants.items():prefix+=body.replace('func_1513137C','control_'+name.replace('-','_'))+'\n'
 header='typedef struct{u32 mode,seed,layout,other;u8 expected[256];}Vector;\n';header+='static const Vector direct[]={'+','.join(direct)+'};\nstatic const Vector relay[]={'+','.join(relay)+'};\n';(o/'native-vectors.h').write_bytes(header.encode())
 suffix='''
#include "native-vectors.h"
_Static_assert(sizeof(void*)==4 && sizeof(s16)==2,"SDK32");
static const u32 layouts[][4]={@LAYOUTS@};
static s16 canvas[128];
typedef void(*Update)(s16*,s16*,s16*,s16*,u8*);
static int check(Update fn,s32 wrapper){u32 i,j,n=wrapper?sizeof(relay)/sizeof(*relay):sizeof(direct)/sizeof(*direct);u8 *b=(u8*)canvas;const Vector *v;const u32 *a,*c;
 for(i=0;i<n;i++){v=(wrapper?relay:direct)+i;for(j=0;j<256;j++)b[j]=(u8)(j*29+v->seed*53+0x5a);b[64+0x70]=(u8)v->mode;b[64+0x71]=(u8)(v->mode+v->seed*17);a=layouts[v->layout];c=layouts[v->other];
 if(wrapper)func_1513164C((s16*)(b+a[0]),(s16*)(b+a[1]),(s16*)(b+a[2]),(s16*)(b+a[3]),(s16*)(b+c[0]),(s16*)(b+c[1]),(s16*)(b+c[2]),(s16*)(b+c[3]),b+64);
 else fn((s16*)(b+a[0]),(s16*)(b+a[1]),(s16*)(b+a[2]),(s16*)(b+a[3]),b+64);
 for(j=0;j<256;j++)if(b[j]!=v->expected[j])return 1;
 }return 0;}
static u8 outcomes[@COUNT@];
static int run(void){s32 n;if(check(func_1513137C,0)||check(func_1513137C,1))return 10;
@CHECKS@
__asm__ volatile("int $0x80":"=a"(n):"0"(4),"b"(1),"c"(outcomes),"d"(sizeof(outcomes)):"memory");
return n==(s32)sizeof(outcomes)?0:11;}
'''.replace('@LAYOUTS@',','.join('{'+','.join(map(str,row))+'}'for row in g.old.LAYOUTS)).replace('@COUNT@',str(len(variants))).replace('@CHECKS@','\n'.join(f'outcomes[{i}]=(u8)check(control_{name.replace("-","_")},0);if(outcomes[{i}]!=1)return {20+i};'for i,name in enumerate(variants)))+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 source=o/'native.c';source.write_bytes((prefix+suffix).encode());profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=o/('native-'+opt[1:]);q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(source),'-o',str(exe)],capture_output=True,text=True);(o/('native-'+opt[1:]+'-compile.txt')).write_bytes((q.stdout+q.stderr).encode());assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.stderr)
  q=subprocess.run([str(exe)],capture_output=True,timeout=60);assert q.returncode==0 and q.stdout==bytes([1]*len(variants))and not q.stderr,(opt,q.returncode,q.stderr,q.stdout);(o/('native-'+opt[1:]+'-outcomes.bin')).write_bytes(q.stdout);profiles[opt]=dict(cases=len(direct),complete_C_relay_cases=len(relay),SDK32=True,strict_aliasing=True,UBSan=True,aligned_typed_halfword_canvas=True,all_256_modes=True,observed_control_comparison_bytes=list(q.stdout),binary_sha256=p.sha(exe),outcomes_sha256=p.sha(o/('native-'+opt[1:]+'-outcomes.bin')))
 report=dict(profiles=profiles,effective_source_controls=[dict(control=n,observed_comparison=1)for n in variants],no_signal_or_UBSan_trap_counted=True,void_result_not_compared=True,precomputed_little_endian_reference=True,whole_canvas_and_canaries_compared=True,source_sha256=p.sha(source),source_installed=p.installed(),matching_credit=0);(o/'native.json').write_bytes((json.dumps(report,indent=2)+'\n').encode());print(json.dumps(dict(cases=len(direct),relay_cases=len(relay),profiles=list(profiles),controls=len(variants))),flush=True);return report
if __name__=='__main__':main()
