"""Native32 linked-state refresh, live aliases and eight effective controls."""
from pathlib import Path
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests import game_linked_state_refresh_oracle as g

def qualify(root,output,body):
 r,o=Path(root),Path(output)
 controls=[('ignore-inactive',body.replace('if (*(s32 *)actor == 0) invalid = 1;','if (0) invalid = 1;')),('wrong-identity-byte',body.replace('actor[0x3B]','actor[0x3C]')),('cache-mode',body.replace('    u8 invalid;','    u8 invalid;\n    u8 cachedMode;').replace('    invalid = 0;','    invalid = 0;\n    cachedMode = ((u8 *)entry)[0x2C];').replace('if (((u8 *)link)[4] == 6)','if (cachedMode == 6)')),('skip-zero-result-invalidation',body.replace('result = func_1519F1C8(*link, ((u8 *)link)[4]);','result = func_1519F1C8(*link, ((u8 *)link)[4]);\n        if (result == 0) invalid = 0;')),('wrong-output-slot',body.replace('outputs->first = result','outputs->third = result')),('skip-cleanup',body.replace('func_151A0928((u8 *)entry);','(void)entry;')),('overwrite-flags',body.replace('entry->unkD |= 1;','entry->unkD = 1;')),('inverted-resource-gate',body.replace('*(s32 *)(actor + 0x1D4) != 0','*(s32 *)(actor + 0x1D4) == 0'))]
 assert len(controls)==8 and all(t!=body for _,t in controls)
 cases=[];seen=set()
 for c in g.cases():
  key=(c.active,c.match,c.gate,c.mode,c.result,c.mutation,c.alias,c.seed)
  if key in seen:continue
  seen.add(key);cases.append('{'+','.join('0x%Xu'%v for v in key)+'}')
 code=r'''
 #include <ultra64.h>
 typedef struct {u8 prefix[13];u8 unkD;s16 unkE;} struct260;
 typedef struct {s32 first,second,third,fourth;} FourWord1CC440;
 static union{u32 align;u8 b[1472];} world,expected;
 struct Case{u32 active,match,gate,mode,result,mutation,alias,seed;};
 static const struct Case cases[]={ROWS};static const struct Case*c;
 static u32 refreshCalls,cleanupCalls,badPointer,observedState,observedMode;
 #define RECORD (world.b+64)
 #define STATE (world.b+384)
 #define NEWSTATE (world.b+640)
 #define ACTOR (world.b+896)
 static u8*expected_at(u8*p){return expected.b+(p-world.b);}
 static u8*old_state(void){return c->alias?RECORD-44:STATE;}
 static void setword(u8*p,u32 v){*(u32*)p=v;}
 static void mutate(u8*entry,u32 expectedOnly){u8*link=expectedOnly?expected_at(entry):entry;
  if(c->mutation&1){static const u8 modes[]={0,6,7,255};link[44]=modes[c->mode%4];}
  if(c->mutation&2)setword(link+40,(u32)NEWSTATE);
  if(c->mutation&4){link[13]^=64;*(u16*)(link+14)=0x2468;}
 }
 static s32 func_1519F1C8(u8*state,u8 mode){refreshCalls++;observedState=(u32)state;observedMode=mode;mutate(RECORD,0);return(s32)c->result;}
 void func_151A0928(u8*entry);
 '''.replace('ROWS',',\n'.join(cases))
 owner=(o/'before-conker_src_game_generated_1CC440.c').read_text();lo,hi=function_span(owner,'func_151A0928');helper=owner[lo:hi].replace('func_151A0928(','real_cleanup(')
 code+=helper+'\nvoid func_151A0928(u8*entry){cleanupCalls++;if(entry!=RECORD){badPointer=1;return;}real_cleanup(entry);}\n'
 for i,(_,text)in enumerate([('selected',body)]+controls):code+=text.replace('func_151A084C(','root_%d('%i)+'\n'
 code+='static void(*roots[])(struct260*)={'+','.join('root_%d'%i for i in range(9))+'};\n'
 code+=r'''
 static int run(void){u32 n,k,j,invalid,refresh,expectedMode,expectedState,killed=0,bad;u8*s,*actor,*out,*ep;
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(k=0;k<9;k++){
   c=&cases[n];for(j=0;j<1472;j++)world.b[j]=(j*29+c->seed*11+90)&255;
   s=old_state();setword(RECORD+40,(u32)s);RECORD[44]=c->mode;RECORD[13]=0xA4;*(u16*)(RECORD+14)=0x1234;
   setword(s+24,(u32)ACTOR);s[28]=0x87;setword(ACTOR,c->active);ACTOR[59]=c->match?0x87:0x86;setword(ACTOR+468,c->gate);
   for(j=0;j<1472;j++)expected.b[j]=world.b[j];ep=expected_at(RECORD);
   s=(u8*)*(u32*)(ep+40);actor=(u8*)*(u32*)expected_at(s+24);out=s+88;
   invalid=*(u32*)expected_at(actor)==0;
   if(expected_at((u8*)*(u32*)(ep+40))[28]!=expected_at(actor)[59])invalid=1;
   refresh=!invalid&&*(u32*)expected_at(actor+468)!=0;expectedState=*(u32*)(ep+40);expectedMode=ep[44];
   if(refresh){invalid=1;mutate(RECORD,1);setword(expected_at(out+(ep[44]==6?0:8)),c->result);}
   if(invalid){u32 mode=ep[44];u8*current=(u8*)*(u32*)(ep+40);setword(expected_at(current+88+(mode==6?4:12)),0);*(u16*)(ep+14)=65535;ep[13]|=1;}
   refreshCalls=cleanupCalls=badPointer=observedState=observedMode=0;roots[k]((struct260*)RECORD);
   bad=badPointer||refreshCalls!=refresh||cleanupCalls!=invalid;
   if(refresh&&(observedState!=expectedState||observedMode!=expectedMode))bad=1;
   for(j=0;j<1472;j++)if(world.b[j]!=expected.b[j])bad=1;
   if(!k&&bad)return 2;if(k&&bad)killed|=1u<<(k-1);
  }
  return killed==255?0:3;
 }
 '''+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 reports=[]
 for opt in ('-O0','-O2','-O3'):
  p=o/('native10-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  reports.append(dict(profile=opt,cases=len(cases),executions=len(cases)*9,all_1472_public_bytes_checked=True,live_link_and_mode_mutations=True,output_mode_alias=True,all_256_mode_bytes=True,real_cleanup_C_body_used=True,eight_controls_effective=True,controls=[n for n,_ in controls],UBSan=True))
 return reports
