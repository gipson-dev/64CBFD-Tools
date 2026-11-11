"""Defined SDK32 legacy-ABI constructor screen and negative controls."""
import itertools,json,subprocess
from tools.experiments import game_effect_record_151580b0_match as p
from tools.tests import game_effect_record_151580b0_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 source=(p.out/"selected-source.c").read_text();a=source.index("s32 func_151580B0(data,");b=source.index("\n\nvoid func_151581D8",a);selected=source[a:b]
 controls={"kind":("(u8)alternate ?","!(u8)alternate ?"),"size":("+ 0xF8u","+ 0xF7u"),"copy":("data, 0x44","data, 0x40"),"owner_field":("+ 0xD8","+ 0xD4"),"extra_field":("+ 0xF4","+ 0xF8"),"zero_count":("i < 4","i < 3"),"owner_gate":("if (entryCount != 0)","if (entryCount == 0)"),"entry_count":("i <= D_80082FA0","i < D_80082FA0"),"clock":("= func_1515D440();","= func_1515D440() + 1;"),"mode":("(u8)mode, 1","(u8)(mode ^ 1), 1")}
 rows=[]
 for i,(alloc,owner,alternate,mode,count,mutation)in enumerate(itertools.product((0,1),(0,1),(0,1,0x100,0x101),(0,0x1ff),(-1,0,2,3),(0,1,2,4,8,16,27))):
  c=g.Case(alloc,owner,alternate,mode,count,mutation,0,i%3);initial=g.fixture(c);want,calls,value=g.reference(c,initial);events=[]
  for target,args in calls:
   if target==g.ALLOC:events.append((1,*args))
   elif target==g.COPY:events.append((2,args[2],0,0,0,0,0))
   elif target==g.ENTRY:events.append((3,0,0,0,0,0,0))
   else:events.append((4,0,0,0,0,0,0))
  events += [(0,0,0,0,0,0,0)]*(7-len(events));offsets=(0xd8,0xe0,0xe4,0xe8,0xec,0xf0,0xf4);old=[g.read(initial,g.RECORD+x)for x in offsets];final=[g.read(want,g.RECORD+x)for x in offsets];copy=[want[g.RECORD+0x10+j]for j in range(0x44)];rows.append((c,value!=0,g.read(want,g.COUNT),old,final,want[g.RECORD+0xdc],want[g.SOURCE+0x10],copy,len(calls),events))
 code="#include <ultra64.h>\n#include <string.h>\n"+r"""
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 typedef struct {u32 type,a,b,c,d,e,f;} Event;
 typedef struct {s32 alloc,owner,alternate,mode,count,mutation,seed;u32 value,finalcount;u32 old[7],final[7];u8 dc,src;u8 copy[68];u32 eventcount;Event ev[7];} Fixture;
 static u32 obj[0x180/4],src[256/4],ownerbuf[256/4];static u8 *record=(u8*)obj,*data=(u8*)src,*owner=(u8*)ownerbuf;static const Fixture *cur;static u32 calls,entries,bad;
 s32 D_80082FA0;
 static void event(u32 t,u32 a,u32 b,u32 c,u32 d,u32 e,u32 f){const Event *v;if(calls>=cur->eventcount){bad=1;calls++;return;}v=&cur->ev[calls++];if(v->type!=t||v->a!=a||v->b!=b||v->c!=c||v->d!=d||v->e!=e||v->f!=f)bad=1;}
 void *func_15167A68(s32 kind,s32 parameter,s32 bytes,s32 a3,s32 mode,s32 flag){event(1,(u32)kind,(u32)parameter,(u32)bytes,(u32)a3,(u32)mode,(u32)flag);if(cur->mutation&1){data[0x10]^=0x5a;D_80082FA0=2;}return cur->alloc?record:0;}
 void *memcpy(void *dst,const void *srcptr,size_t size){u32 i;u8 *d=dst;const u8 *s=srcptr;if(dst!=record+0x10||srcptr!=data)bad=1;event(2,size,0,0,0,0,0);for(i=0;i<size;i++)d[i]=s[i];if(cur->mutation&2)record[0xdc]^=0x80;return dst;}
 s32 func_1515D480(s32 o){u32 ordinal=entries++;if(o!=(s32)owner)bad=1;event(3,0,0,0,0,0,0);if(!ordinal){if(cur->mutation&4)D_80082FA0=-1;if(cur->mutation&8)D_80082FA0=3;if(cur->mutation&16)record[0xe0]^=0x20;}return (s32)(0xabc00000u+ordinal);}
 s32 func_1515D440(void){event(4,0,0,0,0,0,0);return 0x1234abcd;}
 """
 for name,text in {"selected":selected,**{n:selected.replace(a,b,1)for n,(a,b)in controls.items()}}.items():
  if name!="selected":assert text!=selected,name
  code+="\n"+text.replace(p.NAME,"test_"+name,1)+"\n"
 code+="\nstatic const Fixture fixtures[]={\n"
 for c,value,count,old,final,dc,src,copy,num,events in rows:
  arr=lambda a:",".join(str(x&0xffffffff)+"u" for x in a)
  ev=",".join("{"+arr(e)+"}"for e in events);code+="{"+arr((c.alloc,c.owner,c.alternate,c.mode,c.count,c.mutation,c.seed,int(value),count))+",{"+arr(old)+"},{"+arr(final)+"},"+arr((dc,src))+",{"+arr(copy)+"},"+str(num)+",{"+ev+"}},\n"
 code+="};\n"+r"""
 typedef s32(*Update)(s32,s32,s32,s32,s32,s32,s32);
 static int check(Update fn){u32 n,i,v;static const u32 offs[]={0xd8,0xe0,0xe4,0xe8,0xec,0xf0,0xf4};
 for(n=0;n<CASE_COUNT;n++){cur=fixtures+n;calls=entries=bad=0;for(i=0;i<0x180;i++)record[i]=(u8)(i*29+cur->seed*11+0x5a);for(i=0;i<256;i++)data[i]=owner[i]=(u8)(i*29+cur->seed*11+0x5a);for(i=0;i<7;i++)*(u32*)(record+offs[i])=cur->old[i];D_80082FA0=cur->count;
 v=(u32)fn((s32)data,cur->owner?(s32)owner:0,0x12345678,cur->alternate,0x7fffff40,cur->mode,(s32)0x87654321);if(v!=(cur->value?(u32)record:0)||bad||calls!=cur->eventcount||(u32)D_80082FA0!=cur->finalcount||record[0xdc]!=cur->dc||data[0x10]!=cur->src)return 1;for(i=0;i<7;i++){u32 want=(i==0&&cur->value&&cur->owner)?(u32)owner:cur->final[i];if(*(u32*)(record+offs[i])!=want)return 1;}for(i=0;i<68;i++)if(record[0x10+i]!=cur->copy[i])return 1;}return 0;}
 static int run(void){if(check(test_selected))return 10;
 """.replace("CASE_COUNT",str(len(rows)))
 for i,name in enumerate(controls):code+="if(!check(test_"+name+"))return "+str(20+i)+";\n"
 code+="return 0;}\n"+START.replace("void _start(void)","__attribute__((force_align_arg_pointer)) void _start(void)");src=p.out/"native.c";src.write_text(code);reports={}
 for opt in ("-O0","-O2","-O3"):
  exe=p.out/("native"+opt);v=subprocess.run(native_command(opt)+[str(src),"-o",str(exe)],cwd=p.root,capture_output=True,text=True);assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr);v=subprocess.run([str(exe)],capture_output=True);assert v.returncode==0,(opt,v.returncode,v.stderr);reports[opt]=dict(cases=len(rows),negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,overlapping_copy_excluded=True,source_installed=False,byte_exact=False);(p.out/"native.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report),flush=True);return report
