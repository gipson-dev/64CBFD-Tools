"""Native 32-bit semantic checks for the session reset candidate."""
import json
import subprocess
from tools.experiments import game_session_reset_match as source
from tools.tests.test_game_row_destination_fill import START

def main():
    p=source.OUT
    selected=source.MANIFEST['body']
    prefix='''typedef int s32; typedef unsigned int u32; typedef unsigned char u8;
    #define NULL ((void *)0)
    struct Guard {u8 before; u8 data[20];u8 after;};static struct Guard guard;
    #define D_800E0950 guard.data
    u8 D_800D9921,D_800D9920,D_800D9928,D_800D9938,D_800D9929,D_800D9939,D_800D992A[12],D_800D993A[12],D_800D9890,D_800BE500[5],D_800D9950[3],D_80088980,D_80088B40;
    void *D_800D9894; void *D_800D98D0[4],*D_800D9AA0[3],*D_800BE4F0; u8 *D_80088870;
    static int calls,fail;
    void func_15012470(void){if(calls++!=0)fail=1;D_800D9921=7;}
    void func_15008A10(void){if(calls++!=1)fail=1;D_800D9921=8;}
    void func_15012770(void){if(calls++!=2)fail=1;D_800D9921=9;}
    void bzero(void *v,u32 n){u8 *p=(u8*)v;u32 i;if(calls++!=3||v!=D_800BE500||n!=5)fail=1;for(i=0;i<n;i++)p[i]=0;}
    '''
    test='''
    int run(void){int seed,i;for(seed=1;seed<=24;seed++){
     calls=fail=0;guard.before=0x33;guard.after=0x44;for(i=0;i<20;i++)guard.data[i]=(u8)seed;
     for(i=0;i<12;i++)D_800D992A[i]=D_800D993A[i]=(u8)seed;
     D_800D9921=D_800D9920=D_800D9928=D_800D9938=D_800D9929=D_800D9939=D_800D9890=(u8)seed;
     D_800D9894=(void*)1;for(i=0;i<4;i++)D_800D98D0[i]=(void*)1;D_80088870=(void*)1;for(i=0;i<5;i++)D_800BE500[i]=seed;for(i=0;i<3;i++){D_800D9950[i]=seed;D_800D9AA0[i]=(void*)1;}D_80088980=D_80088B40=seed;D_800BE4F0=(void*)1;
     func_1500E5C0();if(fail||calls!=4)return 1;if(guard.before!=0x33||guard.after!=0x44)return 2;for(i=0;i<20;i++)if(guard.data[i])return 3;
     for(i=0;i<12;i++)if(D_800D992A[i]||D_800D993A[i])return 4;if(D_800D9921||D_800D9920||D_800D9928||D_800D9938||D_800D9929||D_800D9939||D_800D9890||D_800D9894)return 5;
     for(i=0;i<4;i++)if(D_800D98D0[i])return 6;if(D_80088870)return 7;for(i=0;i<5;i++)if(D_800BE500[i])return 8;for(i=0;i<3;i++)if(D_800D9950[i]||D_800D9AA0[i])return 9;if(D_80088980||D_80088B40||D_800BE4F0)return 10;
     }return 0;}
    '''
    results={}
    for name,src in [('selected',selected),('bad-counter-bound',selected.replace('i < 20','i < 16'))]:
     for opt in ('-O0','-O2','-O3'):
      f=p/('native-typed-reset-'+name+opt+'.c');exe=f.with_suffix('');f.write_text(prefix+src+test+START);args=['cc','-m32',opt,'-std=c99','-fno-strict-aliasing','-ffreestanding','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(f),'-o',str(exe)];v=subprocess.run(args,capture_output=True,text=True);assert v.returncode==0,v.stderr;v=subprocess.run([str(exe)],timeout=10);results[name+opt]=v.returncode
    assert all(results['selected'+o]==0 for o in ('-O0','-O2','-O3')) and all(results['bad-counter-bound'+o]!=0 for o in ('-O0','-O2','-O3')),results
    print(json.dumps(dict(cases=24,results=results,scope='32-bit freestanding native C, bounded globals and modeled helper calls; no guest access-order claim'),indent=2))


if __name__ == "__main__":
    main()
