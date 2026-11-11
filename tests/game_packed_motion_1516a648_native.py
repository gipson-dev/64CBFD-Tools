"""SDK32 defined-domain candidate and independent negative controls."""
import itertools,json,subprocess
from tools.experiments import game_packed_motion_1516a648_match as p
from tools.tests import game_packed_motion_1516a648_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 selected=p.body((p.out/"selected-source.c").read_text(),p.NAME)
 controls={"rise":("<< 4","<< 3"),"fall":("<< 2","<< 3"),"rise_limit":("alpha >= 256","alpha >= 128"),"fall_limit":("alpha < 0","alpha < 2"),"end":("state == 0 && alpha == 0","state == 0 && alpha == 1"),"gravity":("-= 300","-= 299"),"height":("+ 10u","+ 11u"),"high_byte":("level >> 8","level >> 7"),"comparison":("< level","<= level"),"bounce":("* -0.5f","* 0.5f")}
 rows=[]
 for i,(state,alpha,ticks,answer,mutation)in enumerate(itertools.product((0,1),(0,1,64,128,254,255),(0,1,16,64),(0xfffffff5,0,32760,0xfffffff6),(0,1,2,3))):
  c=g.Case(state,alpha,ticks,(-32768,-1,0,32767)[(i//16)%4],(-32768,-301,-1,0,1,301,32767)[i%7],answer,mutation,0,i%3);initial=g.fixture(c);want,calls,value=g.reference(c,initial);events=[]
  for target,args in calls:
   if target==g.UPDATE:events.append((1,0,0,0,0))
   elif target==g.HEIGHT:events.append((2,*args))
   else:events.append((3,args[1],0,0,0))
  events += [(0,0,0,0,0)]*(3-len(events));words=[g.read(want,g.OBJ+x,2)for x in(0xe,0x10,0x12,0x18)];bytes_=[want[g.OBJ+x]for x in(0x1f,0x24,0x2c,0x2d)];rows.append((c,value,g.read(want,g.MARK),words,bytes_,len(calls),events))
 code="#include <ultra64.h>\n"+p.DECLS+r"""
 _Static_assert(sizeof(void*)==4 && sizeof(f32)==4 && sizeof(s16)==2,"SDK32");
 typedef struct {u32 type,a,b,c,d;} Event;
 typedef struct {s32 state,alpha,ticks,y,velocity,answer,mutation,seed;u32 value,mark;u16 words[4];u8 bytes[4];u32 count;Event ev[3];} Fixture;
 static u32 ob[0x100/4],mark;static u8 *record=(u8*)ob;static const Fixture *cur;static u32 calls,bad;
 s32 D_800BE9E4;
 static void event(u32 t,u32 a,u32 b,u32 c,u32 d){const Event *e;if(calls>=cur->count){bad=1;calls++;return;}e=&cur->ev[calls++];if(e->type!=t||e->a!=a||e->b!=b||e->c!=c||e->d!=d)bad=1;}
 void func_1516F864(u8 *r){if(r!=record)bad=1;event(1,0,0,0,0);if(cur->mutation&1){*(u16*)(r+0xe)=0xff80;*(u16*)(r+0x10)=100;*(u16*)(r+0x12)=222;*(u16*)(r+0x18)=0xff85;}}
 s32 func_1510F8D8(s16 x,s16 y,s16 z,s32 mode){event(2,(u32)(s32)x,(u32)(s32)y,(u32)(s32)z,(u32)mode);if(cur->mutation&2){*(u16*)(record+0x10)=0xffc0;*(u16*)(record+0x18)=0xff03;}return cur->answer;}
 void func_1516F94C(u8 *r,s32 mode){if(r!=record)bad=1;event(3,(u32)mode,0,0,0);mark=0x13579bdf;}
 """
 for name,text in {"selected":selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!="selected":assert text!=selected,name
  code+="\n"+text.replace(p.NAME,"test_"+name,1)+"\n"
 code+="\nstatic const Fixture fixtures[]={\n"
 for c,value,mark,words,bytes_,count,events in rows:
  arr=lambda a:",".join(str(x&0xffffffff)+"u" for x in a)
  ev=",".join("{"+arr(e)+"}"for e in events);code+="{"+arr((c.state,c.alpha,c.ticks,c.y,c.velocity,c.answer,c.mutation,c.seed,value,mark))+",{"+arr(words)+"},{"+arr(bytes_)+"},"+str(count)+",{"+ev+"}},\n"
 code+="};\n"+r"""
 typedef s32(*Update)(u8*);
 static int check(Update fn){u32 n,i;static const u32 woffs[]={0xe,0x10,0x12,0x18},boffs[]={0x1f,0x24,0x2c,0x2d};
 for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;calls=bad=mark=0;for(i=0;i<0x100;i++)record[i]=(u8)(i*29+cur->seed*11+0x5a);D_800BE9E4=cur->ticks;*(u16*)(record+0xe)=0xfffd;*(u16*)(record+0x10)=(u16)cur->y;*(u16*)(record+0x12)=7;*(u16*)(record+0x18)=(u16)cur->velocity;record[0x1f]=(u8)cur->alpha;record[0x24]=(u8)cur->state;
 if((u32)fn(record)!=cur->value||bad||calls!=cur->count||mark!=cur->mark)return 1;for(i=0;i<4;i++){if(*(u16*)(record+woffs[i])!=cur->words[i]||record[boffs[i]]!=cur->bytes[i])return 1;}}return 0;}
 static int run(void){if(check(test_selected))return 10;
 """.replace("CASE_COUNT",str(len(rows)))
 for i,name in enumerate(controls):code+="if(!check(test_"+name+"))return "+str(20+i)+";\n"
 code+="return 0;}\n"+START.replace("void _start(void)","__attribute__((force_align_arg_pointer)) void _start(void)");src=p.out/"native.c";src.write_text(code);reports={}
 for opt in ("-O0","-O2","-O3"):
  exe=p.out/("native"+opt);v=subprocess.run(native_command(opt)+[str(src),"-o",str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,source_installed=False,byte_exact=False);(p.out/"native.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
