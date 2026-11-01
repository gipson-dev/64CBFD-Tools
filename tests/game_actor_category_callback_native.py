"""Native32 actor category callback checks and eight effective negative controls."""
from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_actor_category_callback_oracle as g
from tools.experiments.game_actor_category_callback_match import HEADERS

def qualify(root,output,body):
 r,o=Path(root),Path(output)
 headers=HEADERS
 controls=[('wrong-enable-bit',body.replace('0x400000','0x800000')),('wrong-category-byte',body.replace('actor[0x19]','actor[0x1A]')),('wrong-category12-handler',body.replace('case 12: index = 10;','case 12: index = 9;')),('skip-disabled-callback0',body.replace('        index = 0;','        return;',1)),('narrow-event-word',body.replace('    s32 index;','    s32 index;\n    eventAddress = (u8)eventAddress;')),('alter-byte-command',body.replace('(actor, eventAddress, command);','(actor, eventAddress, command ^ 128);')),('wrong-actor-address',body.replace('(actor, eventAddress, command);','(actor + 4, eventAddress, command);')),('wrong-table-index',body.replace('D_80089F64[index]','D_80089F64[(index + 1) % 11]'))]
 assert len(controls)==8 and all(t!=body for _,t in controls)
 rows=[];seen=set()
 for c in g.cases():
  key=(c.flags,c.category,c.command,c.event,c.mutation,c.tableset,c.seed)
  if key in seen:continue
  seen.add(key);idx=g.index(c);ident=g.identity(c,idx);rows.append('{'+','.join('0x%Xu'%v for v in(*key,idx,ident))+'}')
 code=headers+r"""
 static union{u32 align;u8 b[384];} actor;
 static union{u32 align;u8 b[64];} context;
 struct Case{u32 flags,category,command,event,mutation,tableset,seed,index,identity;};
 static const struct Case cases[]={ROWS};static const struct Case *c;
 static u32 calls,error,seenId,seenEvent,seenCommand;
 static s32 event_word(u32 which){return which==0?0:which==1?(s32)context.b:which==2?(s32)(actor.b+24):which==3?(s32)(actor.b+88):(s32)0x87654321u;}
 static void write_word(u8 *p,u32 v){p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
 static void observe(u32 id,void *a,s32 e,u8 cmd){u32 value;
  calls++;seenId=id;seenEvent=(u32)e;seenCommand=cmd;if(a!=actor.b){error=1;return;}
  if(c->mutation){actor.b[25]^=128;*(u32*)(actor.b+88)^=0x80000000u;}
  value=0xC0000000u|(id<<8)|cmd;
  if(c->mutation){if(e==(s32)context.b)write_word(context.b,value);else if(e==(s32)(actor.b+24))write_word(actor.b+24,value);else if(e==(s32)(actor.b+88))write_word(actor.b+88,value);}
 }
 """.replace('ROWS',',\n'.join(rows))
 for i in range(11):code+='static void cb%d(void*a,s32 e,u8 cmd){observe(%d,a,e,cmd);}\n'%(i,i)
 code+='static void(*callbacks[11])(void*,s32,u8)={'+','.join('cb%d'%i for i in range(11))+'};\nvoid(*D_80089F64[11])(void*,s32,u8);\n'
 for i,(_,text)in enumerate([('selected',body)]+controls):code+=text.replace('func_1513DF9C(','root_%d('%i)+'\n'
 code+='static void(*roots[])(void*,s32,u8)={'+','.join('root_%d'%i for i in range(9))+'};\n'
 code+=r"""
 static int run(void){u32 n,k,j,bad,killed=0,value;u8 expectedActor[384],expectedContext[64];
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(k=0;k<9;k++){
   c=&cases[n];for(j=0;j<384;j++)actor.b[j]=expectedActor[j]=(j*29+c->seed*11+90)&255;
   for(j=0;j<64;j++)context.b[j]=expectedContext[j]=(j*29+c->seed*11+90)&255;
   *(u32*)(actor.b+88)=c->flags;write_word(expectedActor+88,c->flags);actor.b[25]=expectedActor[25]=c->category;
   for(j=0;j<11;j++)D_80089F64[j]=callbacks[j];if(!c->tableset)D_80089F64[7]=callbacks[6];
   if(c->mutation){expectedActor[25]^=128;write_word(expectedActor+88,c->flags^0x80000000u);}
   value=0xC0000000u|(c->identity<<8)|(c->command&255);
   if(c->mutation){if(c->event==1)write_word(expectedContext,value);else if(c->event==2)write_word(expectedActor+24,value);else if(c->event==3)write_word(expectedActor+88,value);}
   calls=error=seenId=seenEvent=seenCommand=0;roots[k](actor.b,event_word(c->event),(u8)c->command);
   bad=error||calls!=1||seenId!=c->identity||seenEvent!=(u32)event_word(c->event)||seenCommand!=(c->command&255);
   for(j=0;j<384;j++)if(actor.b[j]!=expectedActor[j])bad=1;for(j=0;j<64;j++)if(context.b[j]!=expectedContext[j])bad=1;
   if(!k&&bad)return 2;if(k&&bad)killed|=1u<<(k-1);
  }
  return killed==255?0:3;
 }
 """+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 reports=[]
 for opt in ['-O0','-O2','-O3']:
  p=o/('native19-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  reports.append(dict(profile=opt,cases=len(rows),executions=len(rows)*9,all_384_actor_and_64_context_bytes=True,all_eight_controls_effective=True,controls=[n for n,_ in controls],UBSan=True,alias_and_unique_callback_tables=True,void_actor_word_byte_interface=True,all_256_categories_and_commands=True))
 return reports
