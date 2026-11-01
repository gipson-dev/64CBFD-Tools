"""Typed native32 lifetime dispatcher checks with live callbacks and effective controls."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def controls(body):
 cached_flags=body.replace('    s16 opacity;','    s16 opacity;\n    u16 savedFlags;').replace('    if ((method =','    savedFlags = *(u16 *)(owner + 0x24);\n    if ((method =').replace('if ((*(u16 *)(owner + 0x24) & 8)','if ((savedFlags & 8)')
 cached_timer=body.replace('    s16 opacity;','    s16 opacity;\n    s16 savedTime;').replace('    if ((method =','    savedTime = *(s16 *)(owner + 0x22);\n    if ((method =').replace('*(s16 *)(owner + 0x22) < *(s16 *)(owner + 0x26)','savedTime < *(s16 *)(owner + 0x26)').replace('opacity = *(s16 *)(owner + 0x22) *','opacity = savedTime *')
 values=dict(unsigned_expiry=body.replace('if (*(s16 *)(owner + 0x22) < 0)','if ((u32)*(u16 *)(owner + 0x22) < controlZero)'),expired_callback=body.replace(' && !expired',''),method_mask=body.replace('owner[0x68] & 15','owner[0x68] & 7'),cached_flags=cached_flags,cached_timer=cached_timer,unsigned_opacity=body.replace('if (opacity < owner[0x2E])','if ((u16)opacity < owner[0x2E])'),wrong_fade_gate=body.replace('owner + 0x24) & 8','owner + 0x24) & 4'),clamped_opacity=body.replace('if (opacity < owner[0x2E])','if (opacity < 0) opacity = 0;\n        if (opacity < owner[0x2E])'),missing_release=body.replace('if (expired) func_1516972C(owner);','if (0) func_1516972C(owner);'),early_expiry=body.replace('if (*(s16 *)(owner + 0x22) < 0)','if (*(s16 *)(owner + 0x22) <= 0)'))
 assert len(values)==10 and len(set(values.values()))==10 and all(v!=body for v in values.values())
 return values

def harness(selected):
 head,tail=selected.split('/* Advance',1);body='/* Advance'+tail;bad=controls(body)
 code=head+'static volatile u32 controlZero;\n'+'\n'.join(v.replace('func_15154C90','candidate_'+str(i)) for i,v in enumerate([body,*bad.values()]))
 code+=r'''
typedef struct {u8 reserved0[0x22];s16 duration;u16 flags;s16 threshold;s16 rate;u8 reserved2A[4];u8 opacity;u8 reserved2F[0x39];u8 method;u8 reserved69[0x17];} NativeOwner;
typedef struct {u32 before;NativeOwner owner;u32 after;} World;
typedef char LayoutDuration[__builtin_offsetof(NativeOwner,duration)==0x22?1:-1];
typedef char LayoutFlags[__builtin_offsetof(NativeOwner,flags)==0x24?1:-1];
typedef char LayoutThreshold[__builtin_offsetof(NativeOwner,threshold)==0x26?1:-1];
typedef char LayoutRate[__builtin_offsetof(NativeOwner,rate)==0x28?1:-1];
typedef char LayoutOpacity[__builtin_offsetof(NativeOwner,opacity)==0x2E?1:-1];
typedef char LayoutMethod[__builtin_offsetof(NativeOwner,method)==0x68?1:-1];
typedef char LayoutSize[sizeof(NativeOwner)==0x80 && sizeof(World)==0x88?1:-1];
static World actual,expected;
static int referenceMode,mutation,counts[2],logs[2][4],invalid;static s32 answer;
static u32 killed,cases; s32 D_800BE9E4;
static void effect(NativeOwner *owner){
 if(mutation&1)owner->duration=-3;
 if(mutation&2){owner->flags=8;owner->threshold=32767;}
 if(mutation&4)owner->rate=-1;
 if(mutation&8)owner->opacity=5;
}
static void record(int event){int k=referenceMode;if(counts[k]>=4){invalid=1;return;}logs[k][counts[k]++]=event;}
static s32 provider(u8 *owner,int method){NativeOwner *want=referenceMode?&expected.owner:&actual.owner;if(owner!=(u8*)want)invalid=1;record(method);effect(want);return answer;}
void func_1516972C(u8 *owner){if(owner!=(u8*)(referenceMode?&expected.owner:&actual.owner))invalid=1;record(100);}
'''
 for i in range(16):code+='static s32 method_%d(u8 *p){return provider(p,%d);}\n'%(i,i)
 code+='s32 (*D_8008ACC8[])(u8 *)={'+','.join('method_'+str(i) for i in range(16))+'};\n'
 code+=r'''
static s32 sign16(u32 value){value&=65535u;return value&32768u?(s32)value-65536:(s32)value;}
static void reference(void){NativeOwner *owner=&expected.owner;int expired=0;u32 low;int method;
 if(owner->flags&1){low=((u32)(s32)owner->duration-(u32)D_800BE9E4)&65535u;owner->duration=(s16)sign16(low);expired=low>=32768u;}
 method=owner->method%16;
 if(method && !expired){record(method);effect(owner);expired=answer==0;}
 if((owner->flags&8) && (s32)owner->duration<(s32)owner->threshold){s32 product=sign16((u32)((s32)owner->duration*(s32)owner->rate));if(product<(s32)owner->opacity)owner->opacity=(u8)product;}
 if(expired)record(100);
}
typedef void (*Candidate)(u8*);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i) for i in range(11))+'};\n'
 code+=r'''
static int one(int index,s32 duration,s32 delta,u16 flags,int method,s16 rate,u8 opacity){int i,same=1;
 for(i=0;i<(int)sizeof(World);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=(u8)(i*17+0x59);
 actual.owner.duration=expected.owner.duration=(s16)duration;actual.owner.flags=expected.owner.flags=flags;
 actual.owner.threshold=expected.owner.threshold=10;actual.owner.rate=expected.owner.rate=rate;
 actual.owner.opacity=expected.owner.opacity=opacity;actual.owner.method=expected.owner.method=(u8)(0xA0|method);
 D_800BE9E4=delta;counts[0]=counts[1]=0;invalid=0;referenceMode=0;candidates[index]((u8*)&actual.owner);referenceMode=1;reference();
 if(invalid||counts[0]!=counts[1])same=0;
 for(i=0;i<counts[0]&&i<4;i++)if(logs[0][i]!=logs[1][i])same=0;
 for(i=0;i<(int)sizeof(World);i++)if(((u8*)&actual)[i]!=((u8*)&expected)[i])same=0;
 cases++;if(!same){if(!index)return 1;killed|=1u<<(index-1);}return 0;
}
static int run(void){u32 low;int d,t,f,m,v,c,j;
 static s32 durations[]={-32768,-1,0,1,32767},deltas[]={(-2147483647-1),-1,0,1,2147483647},answers[]={0,1,-1,0x50000};
 static u16 flags[]={0,1,8,9};static int methods[]={0,4,8,15};
 mutation=0;answer=1;
 for(low=0;low<65536;low++)if(one(0,1,0,8,0,(s16)low,(u8)low))return 10;
 for(d=0;d<5;d++)for(t=0;t<5;t++)for(f=0;f<4;f++)for(m=0;m<4;m++)for(v=0;v<4;v++)for(c=0;c<16;c++){
  mutation=c;answer=answers[v];for(j=0;j<11;j++)if(one(j,durations[d],deltas[t],flags[f],methods[m],255,200))return 11;
 }
 if(killed!=1023u || cases!=347136u)return 12;return 0;
}
'''+START
 return code,list(bad)

def run_native(root,out,selected):
 code,names=harness(selected);path=out/'native-lifetime.c';path.write_text(code);rows=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-lifetime'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=root,capture_output=True,text=True)
  (out/('native-lifetime'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,exit=0,UBSan=True,baseline_cases=91136,negative_cases_per_control=25600,negative_controls=names,all_controls_effective=True))
 result=dict(private_only=True,installed=False,matching_credit=0,native32=True,typed_objects_and_canaries=True,all_object_bytes_and_ordered_calls_compared=True,callback_mutations=4,rows=rows)
 (out/'native-lifetime.json').write_text(json.dumps(result,indent=2)+'\n');return result
