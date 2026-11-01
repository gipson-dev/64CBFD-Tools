"""Native32 cash-label source semantics, live helper effects and full word return."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def controls(body):
 cached=body.replace('    u16 opacity;','    u16 opacity;\n    s32 cachedAmount;').replace('    func_150432CC','    cachedAmount = *(s32 *)(label + 8);\n    func_150432CC').replace('D_800AB254, *(s32 *)(label + 8)','D_800AB254, cachedAmount')
 values=dict(unsigned_duration=body.replace('s16 remaining;','s32 remaining;').replace('*(s16 *)(owner + 0xE)','*(u16 *)(owner + 0xE)'),unsigned_threshold=body.replace('remaining < *(s16 *)(label + 0xC)','remaining < *(u16 *)(label + 0xC)'),unclamped_signed_low16=body.replace('if ((s16)opacity < 0)','if (0)'),cached_amount=cached,reloaded_record=body.replace('*(s32 *)(label + 8)','*(s32 *)(*(u8 **)(owner + 0x48) + 8)'),wrong_identity=body.replace('actor[0x3B]','actor[0x3C]'),wrong_color=body.replace('(50, 125, 28,','(50, 126, 28,'),wrong_attachment_flags=body.replace('0x109','0x108'),wrong_return=body.replace('    return func_15042E3C((s32)D_800AB254, *(s32 *)(label + 8));','    func_15042E3C((s32)D_800AB254, *(s32 *)(label + 8));\n    return 1;'))
 assert len(values)==9 and all(v!=body for v in values.values())and len(set(values.values()))==9
 return values

def harness(selected):
 head,tail=selected.split('/* Draw',1);body='/* Draw'+tail;bad=controls(body)
 code=head+'#include "stdarg.h"\n'+'\n'.join(v.replace('func_151D7000','candidate_'+str(i))for i,v in enumerate([body,*bad.values()]))
 code+=r'''
typedef struct {u8 reserved0[0xE];s16 remaining;u8 reserved10[0x20];u8 flags;u8 reserved31[0x17];u8 *label;u8 reserved4C[0xB4];} NativeOwner;
typedef struct {u8 *actor;u8 identity;u8 reserved[3];s32 amount;s16 threshold;s16 rate;} NativeLabel;
typedef struct {s32 active;u8 reserved4[0x37];u8 identity;u8 reserved3C[0x44];} NativeActor;
typedef struct {u32 before;NativeOwner owner;NativeLabel label;NativeActor actor;NativeLabel alternate;u32 after;} World;
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(NativeOwner)==0x100,"owner extent");
_Static_assert(__builtin_offsetof(NativeOwner,label)==0x48,"record offset");
_Static_assert(__builtin_offsetof(NativeLabel,amount)==8,"amount offset");
_Static_assert(__builtin_offsetof(NativeActor,identity)==0x3B,"identity offset");
static World actual,expected;
static int referenceMode,mode,counts[2],caseCount;static s32 returnWord;static u32 killed;
static u32 logs[2][4][5];
u8 D_800AB254[]="$ %d";
static World *world(void){return referenceMode?&expected:&actual;}
static void logCall(u32 kind,u32 a,u32 b,u32 c,u32 d){int n=counts[referenceMode]++;if(n>=4)__builtin_trap();logs[referenceMode][n][0]=kind;logs[referenceMode][n][1]=a;logs[referenceMode][n][2]=b;logs[referenceMode][n][3]=c;logs[referenceMode][n][4]=d;}
void func_150432CC(s32 actor,s32 flags){World*w=world();logCall(1,(u32)((u8*)(u32)actor-(u8*)w),(u32)flags,0,0);if(mode&1)w->owner.label=(u8*)&w->alternate;if(mode&2)w->label.amount=(s32)0xFEDCBA98u;}
void func_1504332C(u8 r,u8 g,u8 b,u8 a){logCall(2,r,g,b,a);if(mode&4)world()->actor.identity=99;}
void func_15042D78(u8 command){logCall(3,command,0,0,0);if(mode&8)world()->label.amount=(s32)0x87654321u;}
s32 func_15042E3C(s32 fmt,...){va_list args;s32 value;va_start(args,fmt);value=va_arg(args,s32);va_end(args);logCall(4,fmt==(s32)D_800AB254,(u32)value,0,0);return returnWord;}
static s32 reference(void){NativeLabel*l=(NativeLabel*)expected.owner.label;NativeActor*a=(NativeActor*)l->actor;u32 opacity=255,low;s32 remaining=expected.owner.remaining;
 if(!a->active||l->identity!=a->identity)return 0;
 if(remaining<(s32)l->threshold){low=((u32)(remaining*(s32)l->rate))&65535u;opacity=low<32768u?low:0;}
 func_150432CC((s32)a,0x109);func_1504332C(50,125,28,(u8)opacity);func_15042D78(0x81);return func_15042E3C((s32)D_800AB254,l->amount);
}
static int pointerByte(int i){int a=__builtin_offsetof(World,owner)+__builtin_offsetof(NativeOwner,label),b=__builtin_offsetof(World,label)+__builtin_offsetof(NativeLabel,actor),c=__builtin_offsetof(World,alternate)+__builtin_offsetof(NativeLabel,actor);return(i>=a&&i<a+4)||(i>=b&&i<b+4)||(i>=c&&i<c+4);}
static int same(s32 actualResult,s32 expectedResult){int i,j,k;
 if(actualResult!=expectedResult||counts[0]!=counts[1])return 0;
 if((actual.owner.label-(u8*)&actual)!=(expected.owner.label-(u8*)&expected))return 0;
 if((actual.label.actor-(u8*)&actual)!=(expected.label.actor-(u8*)&expected))return 0;
 if((actual.alternate.actor-(u8*)&actual)!=(expected.alternate.actor-(u8*)&expected))return 0;
 for(i=0;i<(int)sizeof(World);i++)if(!pointerByte(i)&&((u8*)&actual)[i]!=((u8*)&expected)[i])return 0;
 for(j=0;j<counts[0];j++)for(k=0;k<5;k++)if(logs[0][j][k]!=logs[1][j][k])return 0;
 return 1;
}
typedef s32(*Candidate)(u8*);static Candidate candidates[]={candidate_0,candidate_1,candidate_2,candidate_3,candidate_4,candidate_5,candidate_6,candidate_7,candidate_8,candidate_9};
static int one(int index,s32 duration,s32 threshold,s32 rate,s32 amount,int gate){int i;s32 got,want;
 for(i=0;i<(int)sizeof(World);i++)((u8*)&actual)[i]=((u8*)&expected)[i]=(u8)(i*17+0x59);
 actual.owner.label=(u8*)&actual.label;expected.owner.label=(u8*)&expected.label;
 actual.label.actor=(u8*)&actual.actor;expected.label.actor=(u8*)&expected.actor;
 actual.alternate.actor=(u8*)&actual.actor;expected.alternate.actor=(u8*)&expected.actor;
 actual.actor.active=expected.actor.active=gate==0?0:1;actual.actor.identity=expected.actor.identity=gate==1?8:7;
 actual.label.identity=expected.label.identity=7;actual.label.amount=expected.label.amount=amount;
 actual.alternate.amount=expected.alternate.amount=0x12345678;actual.owner.remaining=expected.owner.remaining=(s16)duration;
 actual.label.threshold=expected.label.threshold=(s16)threshold;actual.label.rate=expected.label.rate=(s16)rate;
 counts[0]=counts[1]=0;referenceMode=0;got=candidates[index]((u8*)&actual.owner);referenceMode=1;want=reference();
 if(!same(got,want)){if(!index)return 1;killed|=1u<<(index-1);}
 caseCount++;return 0;
}
static int run(void){u32 low;int d,t,r,m,g,v,j;
 static s32 durations[]={-32768,-1,0,1,32767},thresholds[]={-32768,0,32767},rates[]={-32768,-1,1,3,255},returns[]={0,0x50000,-1};
 /* Every low-halfword product occurs with duration1 and a signed rate. */
 for(low=0;low<65536;low++){mode=(int)(low&15);returnWord=returns[low%3];if(one(0,1,32767,(s16)low,(s32)(low*0x10001u),2))return 10;}
 for(d=0;d<5;d++)for(t=0;t<3;t++)for(r=0;r<5;r++)for(m=0;m<16;m++)for(g=0;g<3;g++)for(v=0;v<3;v++){
  mode=m;returnWord=returns[v];for(j=0;j<10;j++)if(one(j,durations[d],thresholds[t],rates[r],(s32)(0x80000000u+(u32)(d*31+r*7)),g))return 11;
 }
 if(killed!=511u||caseCount!=173536)return 12;
 return 0;
}
'''+START
 return code,list(bad)

def run_native(root,out,selected):
 code,names=harness(selected);path=out/'native-cash-label.c';path.write_text(code);rows=[]
 for profile in('-O0','-O2','-O3'):
  exe=out/('native-cash-label'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=root,capture_output=True,text=True)
  (out/('native-cash-label'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  rows.append(dict(profile=profile,exit=0,baseline_cases=76336,negative_cases_per_control=10800,negative_controls=names,all_negative_controls_effective=True,UBSan=True))
 result=dict(private_only=True,installed=False,matching_credit=0,native32=True,defined_typed_native_object_layouts=True,full_object_bytes_and_normalized_pointer_fields_compared=True,full_helper_order_arguments_and_word_return_compared=True,live_helper_mutations=4,retail_text_emitter_is_word_ABI_provider=True,existing_C_void_helper_body_not_claimed_native=True,rows=rows)
 (out/'native-cash-label.json').write_text(json.dumps(result,indent=2)+'\n');return result
