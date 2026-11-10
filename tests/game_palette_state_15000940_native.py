"""Defined native32 palette objects, retail presets and effective controls."""
import json,subprocess
from tools.experiments import game_palette_state_15000940_match as p
from tools.experiments.game_actor_state_tick_integration import elf_slot_offset
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 body=(p.out/'selected-body.c').read_text(encoding='utf-8');elf=(p.out/'frozen/conker/build/conker.us.elf').read_bytes();at=elf_slot_offset(elf,0x800A2CD0,84);preset=elf[at:at+84]
 pre='''#include <ultra64.h>
#include "variables.h"
struct104 context;
struct104 *D_800B0DF0 = &context;
u8 D_800A2CD0[8][3], D_800A2CE8[4], D_800A2CEC[24], D_800A2D04[32];
struct Half {u32 before;u16 v[12];u32 after;} halves;
struct Bytes {u32 before;u8 v[12];u32 after;} first, second, third, zeros;
struct Common {u32 before;u8 v[3];u8 pad;u32 after;} common;
#define D_800D9E70 halves.v
#define D_800D9E88 first.v
#define D_800D9E98 second.v
#define D_800D9EA8 third.v
#define D_800D9EB4 common.v
#define D_800D9EB8 zeros.v
#define D_800D9EB7 common.v[3]
#define D_800D9EC4 zeros.v[12]
_Static_assert(sizeof(void*)==4 && sizeof(s32)==4 && sizeof(u16)==2,"SDK ABI");
_Static_assert(__builtin_offsetof(struct104,unk29)==0x29,"context selector");
'''
 code=pre+body+'\n'
 changes={
 'wrong-half-zero':('*halfCursor++ = 0;','*halfCursor++ = 1;'),
 'wrong-byte-zero':('*zeroCursor++ = 0;','*zeroCursor++ = 1;'),
 'wrong-common':('*common++ = thirdValue;','*common++ = thirdValue ^ 1;'),
 'wrong-first':('*firstCursor++ = firstValue;','*firstCursor++ = thirdValue; (void)firstValue;'),
 'wrong-second':('*secondCursor++ = secondValue;','*secondCursor++ = thirdValue; (void)secondValue;'),
 'wrong-third':('*thirdCursor++ = thirdValue;','*thirdCursor++ = firstValue;'),
 'two-channels':('common != &D_800D9EB7','common != &common.v[2]'),
 'three-rows':('zeroByte != &D_800D9EC4','zeroByte != &zeros.v[9]'),
 'wrong-second-scale':('selectors[1] * 3','selectors[1] * 2'),
 'wrong-third-scale':('selectors[2] * 3','selectors[2] * 2')}
 for i,(label,(a,b))in enumerate(changes.items()):assert body.count(a)==1,(label,a);code+=body.replace('func_15000940','bad%d'%i).replace(a,b)+'\n'
 code+='static const u8 preset[84] = {'+','.join(map(str,preset))+'};\n'
 code+='''static void fill(void *p,u32 n,u32 seed){u8 *v=p;u32 i;for(i=0;i<n;i++)v[i]=(u8)(i*29+seed*11+90);}
static int equal(const void *a,const void *b,u32 n){const u8 *x=a,*y=b;u32 i;for(i=0;i<n;i++)if(x[i]!=y[i])return 0;return 1;}
static int check(void (*fn)(s32),u32 index,u32 seed,u32 synthetic,u32 unused){
 struct Half h;struct Bytes f,s,t,z;struct Common c;u32 i,j;u8 *a,*b,*d;u8 saved[84];
 fill(&halves,sizeof halves,seed);fill(&first,sizeof first,seed+1);fill(&second,sizeof second,seed+2);fill(&third,sizeof third,seed+3);fill(&zeros,sizeof zeros,seed+4);fill(&common,sizeof common,seed+5);
 h=halves;f=first;s=second;t=third;z=zeros;c=common;context.unk29=(u8)index;
 for(i=0;i<24;i++)((u8*)D_800A2CD0)[i]=preset[i];
 for(i=0;i<4;i++)D_800A2CE8[i]=synthetic?(u8)(i*47+seed):preset[24+i];
 for(i=0;i<24;i++)D_800A2CEC[i]=synthetic?(u8)(i*73+seed):preset[28+i];
 for(i=0;i<32;i++)D_800A2D04[i]=synthetic?(u8)(i*197+seed):preset[52+i];
 if(synthetic){D_800A2CD0[index][0]=0;D_800A2CD0[index][1]=(u8)(seed&7);D_800A2CD0[index][2]=(u8)((seed*5+1)&7);}
 for(i=0;i<24;i++)saved[i]=((u8*)D_800A2CD0)[i];for(i=0;i<4;i++)saved[24+i]=D_800A2CE8[i];for(i=0;i<24;i++)saved[28+i]=D_800A2CEC[i];for(i=0;i<32;i++)saved[52+i]=D_800A2D04[i];
 a=D_800A2CE8+3*D_800A2CD0[index][0];b=D_800A2CEC+3*D_800A2CD0[index][1];d=D_800A2D04+3*D_800A2CD0[index][2];
 for(i=0;i<4;i++)for(j=0;j<3;j++){h.v[3*i+j]=0;z.v[3*i+j]=0;c.v[j]=d[j];t.v[3*i+j]=d[j];f.v[3*i+j]=a[j];s.v[3*i+j]=b[j];}
 fn((s32)unused);
 if(!equal(&h,&halves,sizeof h)||!equal(&f,&first,sizeof f)||!equal(&s,&second,sizeof s)||!equal(&t,&third,sizeof t)||!equal(&z,&zeros,sizeof z)||!equal(&c,&common,sizeof c))return 73;
 if(context.unk29!=index)return 74;
 for(i=0;i<24;i++)if(saved[i]!=((u8*)D_800A2CD0)[i])return 75;for(i=0;i<4;i++)if(saved[24+i]!=D_800A2CE8[i])return 75;for(i=0;i<24;i++)if(saved[28+i]!=D_800A2CEC[i])return 75;for(i=0;i<32;i++)if(saved[52+i]!=D_800A2D04[i])return 75;
 return 0;}
int main(void){u32 i,j,k;int v;void (*selected)(s32)=func_15000940;
 for(i=0;i<8;i++)for(j=0;j<5;j++)for(k=0;k<3;k++){v=check(selected,i,j,0,k==0?0:k==1?0x80000000u:0xFFFFFFFFu);if(v)return v;}
 for(i=0;i<8;i++)for(j=0;j<256;j++){v=check(selected,i,j,1,j*0x13579BDFu);if(v)return v;}
'''
 for i,label in enumerate(changes):code+=' {int witness=0;for(i=0;i<8;i++){v=check(bad%d,i,i+3,0,0);if(v==73)witness=1;else if(v)return v;}if(!witness)return %d;}\n'%(i,90+i)
 code+='return 0;}\n'+START
 code=code.replace('} first, second, third, zeros;','} nativeFirst, nativeSecond, nativeThird, zeros;').replace('} common;','} nativeCommon;').replace('int main(void)','int run(void)')
 for name,new in [('first','nativeFirst'),('second','nativeSecond'),('third','nativeThird'),('common','nativeCommon')]:
  code=code.replace(name+'.v',new+'.v').replace('&'+name+',','&'+new+',').replace('sizeof '+name,'sizeof '+new).replace('='+name+';','='+new+';')
 path=p.out/'native.c';path.write_text(code);profiles={}
 for opt in('-O0','-O2','-O3'):
  binary=p.out/('native-'+opt[1:]);cmd=native_command(opt,True)+['-fstrict-aliasing',str(path),'-o',str(binary)];a=subprocess.run(cmd,cwd=p.root,capture_output=True,text=True);assert a.returncode==0 and not a.stdout and not a.stderr,(opt,a.stdout,a.stderr);r=subprocess.run([str(binary)],capture_output=True);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stdout,r.stderr);profiles[opt]=dict(cases=2168,UBSan=True,strict_aliasing=True,effective_completed_controls=10,SDK_layout_asserted=True)
 report=dict(profiles=profiles,actual_table_domain_only=True,comparison_includes_object_guards_and_all_input_bytes=True,end_labels_represented_by_valid_one_past_array_pointers=True)
 (p.out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
