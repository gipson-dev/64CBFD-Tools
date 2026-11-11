"""SDK32 private candidate screen with deterministic helper and control fixtures."""
import itertools,json,subprocess
from tools.experiments import game_attachment_1518a094_match as p
import guest_screen as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=p.body((p.out/"selected-source.c").read_text(),p.NAME)
 controls={
  "identity":("context[0x1D] != resource[0x3B]","context[0x1D] == resource[0x3B]"),
  "lookup":("func_15083E90(context[0x1D])","func_15083E90(context[0x1C])"),
  "enabled":("if (!enabled[7])","if (enabled[7])"),
  "stride":("context[0x1C] * 64","context[0x1C] * 32"),
  "position":("*(f32 *)(context + 4)","*(f32 *)(context + 8)"),
  "setflag":("|= 2;","|= 4;"),
  "clearflag":("&= ~4;","&= ~8;"),
  "emptyflag":("&= ~2;","&= ~4;")}
 rows=[]
 for i,v in enumerate(itertools.product((0,1),(0,1),(0,1),(0,1),(-1,0,1),(0,1),(0,1),(0,1),(0,1,2,3))):
  c=g.Case(*v,phase=0,seed=i%3);initial=g.fixture(c);expected,calls,value=g.reference(c,initial);events=[]
  for target,args in calls:
   if target==g.LOOK:events.append((1,args[0],0,0,0))
   elif target==g.CB:events.append((2,args[2],0,0,0))
   else:events.append((3,args[1],args[2],args[3],args[4]-g.OBJ))
  events+= [(0,0,0,0,0)]*(4-len(events));res=g.read(expected,g.OBJ+0x188);rescode=0 if res==0 else 1 if res==g.RES else 2 if res==g.ALT else 99
  offsets=[0x34,0x38,0x3c,0x40,0x44,0x48];initialwords=[g.read(initial,g.OBJ+x)for x in offsets];inputs=[g.read(initial,g.OBJ+0x170+x)for x in (0,4,8,12,16,20)];final=[g.read(expected,g.OBJ+x)for x in offsets];rows.append((c,value,rescode,g.read(expected,g.OBJ+0x58),initialwords,inputs,final,len(calls),events))
 code="#include <ultra64.h>\n"+p.DECLS+r"""
 _Static_assert(sizeof(void*)==4 && sizeof(f32)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u32 type,a,b,c,d;} Event;
 typedef struct {s32 initial,found,active,same,subtype,cbret,enabled,matrix,mutation,seed;u32 value,rescode,flags;u32 old[6],input[6],output[6],count;Event ev[4];} Fixture;
 static u32 ob[0x220/4],res[0x220/4],alt[0x220/4],matrix[0x400/4];
 static u8 *object=(u8*)ob,*resource=(u8*)res,*alternate=(u8*)alt;
 static const Fixture *cur;static u32 calls,trans,bad;
 SubtypeCallback1B74A0 D_8008D5A0[4];
 static u32 floatbits(f32 f){union{f32 f;u32 u;}v;v.f=f;return v.u;}
 static void event(u32 type,u32 a,u32 b,u32 c,u32 d){const Event *e;if(calls>=cur->count){bad=1;calls++;return;}e=&cur->ev[calls++];if(e->type!=type||e->a!=a||e->b!=b||e->c!=c||e->d!=d)bad=1;}
 u8 *func_15083E90(s32 id){event(1,id,0,0,0);return cur->found?resource:0;}
 static s32 callback(u8 *o,u8 *enabled,s32 subtype){if(o!=object)bad=1;event(2,(u32)subtype,0,0,0);*enabled=cur->enabled;if(cur->mutation&1){*(u8**)(object+0x188)=alternate;*(u32*)(object+0x58)=0x87654321;*(u32*)(object+0x17c)=0x41a00000;}return cur->cbret;}
 void func_150A7960(f32 *m,f32 x,f32 y,f32 z,f32 *a,f32 *b,f32 *c){u32 vals[3]={floatbits(x),floatbits(y),floatbits(z)};if((u8*)m!=(u8*)matrix+128)bad=1;if((u8*)b!=(u8*)a+4||(u8*)c!=(u8*)a+8)bad=1;event(3,vals[0],vals[1],vals[2],(u32)((u8*)a-object));*(u32*)a=vals[0]^0x5a5a5a5a;*(u32*)b=vals[1]^0x5b5b5b5b;*(u32*)c=vals[2]^0x58585858;if(!trans&&(cur->mutation&2)){*(u32*)(object+0x17c)=0x3f123456;*(u32*)(object+0x58)=0x55555555;}trans++;}
 """
 for name,text in {"selected":selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!="selected":assert text!=selected,name
  code+="\n"+text.replace(p.NAME,"test_"+name,1)+"\n"
 code+="\nstatic const Fixture fixtures[]={\n"
 for c,value,rescode,flags,old,inputs,outputs,n,events in rows:
  arr=lambda a:",".join(str(x&0xffffffff)+"u" for x in a)
  ev=",".join("{"+arr(e)+"}"for e in events)
  code+="{"+arr((c.initial,c.found,c.active,c.same,c.subtype,c.cbret,c.enabled,c.matrix,c.mutation,c.seed,value,rescode,flags))+",{"+arr(old)+"},{"+arr(inputs)+"},{"+arr(outputs)+"},"+str(n)+",{"+ev+"}},\n"
 code+="};\n"+r"""
 typedef s32(*Update)(u8*);
 static int check(Update fn){u32 n,i,codevalue;u8 *obj=(u8*)ob,*r=(u8*)res,*a=(u8*)alt;static const u32 offsets[]={0x34,0x38,0x3c,0x40,0x44,0x48};
 for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;calls=trans=bad=0;for(i=0;i<0x220;i++){obj[i]=r[i]=a[i]=(u8)(i*29+cur->seed*11+0x5a);}for(i=0;i<6;i++){*(u32*)(object+offsets[i])=cur->old[i];*(u32*)(object+0x170+i*4)=cur->input[i];}
 *(u8**)(object+0x188)=cur->initial?resource:0;*(u32*)(object+0x58)=0x1234567f;object[0x18d]=0x42;object[0x18e]=(u8)cur->subtype;object[0x18c]=2;*(u32*)resource=*(u32*)alternate=cur->active;resource[0x3b]=alternate[0x3b]=cur->same?0x42:0x43;*(u8**)(resource+0x1d4)=*(u8**)(alternate+0x1d4)=cur->matrix?(u8*)matrix:0;D_8008D5A0[0]=D_8008D5A0[1]=callback;
 if((u32)fn(object)!=cur->value||bad||calls!=cur->count||*(u32*)(object+0x58)!=cur->flags)return 1;for(i=0;i<6;i++)if(*(u32*)(object+offsets[i])!=cur->output[i])return 1;codevalue=*(u8**)(object+0x188)==0?0:*(u8**)(object+0x188)==resource?1:*(u8**)(object+0x188)==alternate?2:99;if(codevalue!=cur->rescode)return 1;}return 0;}
 static int run(void){if(check(test_selected))return 10;
 """.replace("CASE_COUNT",str(len(rows)))
 for i,name in enumerate(controls):code+="if(!check(test_"+name+"))return "+str(20+i)+";\n"
 code+="return 0;}\n"+START.replace("void _start(void)","__attribute__((force_align_arg_pointer)) void _start(void)");src=p.out/"z000-native.c";src.write_text(code);reports={}
 for opt in ("-O0","-O2","-O3"):
  exe=p.out/("z000-native"+opt);v=subprocess.run(native_command(opt)+[str(src),"-o",str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,negative_subtypes_excluded_from_native=True,helpers_modeled=True,source_installed=False,byte_exact=False);(p.out/"z000-native.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
