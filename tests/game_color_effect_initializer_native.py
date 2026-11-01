"""Native32 pool/guard bytes and eight effective private-candidate controls."""
from pathlib import Path
import json,struct,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
from tools.tests import game_color_effect_initializer_oracle as g
from tools.experiments.game_color_effect_initializer_candidates import HEADERS
def qualify(root,output,body):
 r,o=Path(root),Path(output);headers=HEADERS
 controls=[('accept-sixth-record',body.replace('D_800DF7B4 < 5','D_800DF7B4 <= 5')),('narrow-mode',body.replace('record->mode = mode;','record->mode = (u8)mode;')),('wrong-rate-field',body.replace('record->rate = rate;','record->blend = rate;')),('missing-current-targetRed',body.replace('record->currentRed = startRed;','')),('wrong-target-targetGreen',body.replace('record->targetGreen = targetGreen;','record->targetGreen = targetRed;')),('wrong-stride',body.replace('&D_800DF700[D_800DF7B4]','(ColorEffectRecord *)((u8 *)D_800DF700 + D_800DF7B4 * 40)')),('short-vector-clear',body.replace('bzero(record->state, 12)','bzero(record->state, 8)')),('return-next-index',body.replace('return ++D_800DF7B4 - 1;','return ++D_800DF7B4;'))]
 assert len(controls)==8 and all(x!=body for _,x in controls)
 rows=[]
 for c in g.cases():
  if c.count<0:continue
  expected=bytearray((i*29+c.seed*11+90)&255 for i in range(288));answer=0xFFFFFFFF;count=c.count
  if count<5:
   p=count*36
   for i in range(6):expected[p+i]=c.colors[i]&255
   for i in range(3):expected[p+6+i]=c.colors[i]&255
   expected[p+16:p+20]=struct.pack('<I',c.mode);expected[p+20:p+24]=struct.pack('<I',c.rate);expected[p+24:p+36]=bytes(12);answer=count;count+=1
  # Native has little-endian word/float members; all byte fields remain literal.
  fields=[str(c.count),'0x%Xu'%c.mode,'0x%Xu'%c.rate,'{'+','.join('0x%Xu'%x for x in c.colors)+'}',str(c.seed),'0x%Xu'%answer,str(count),'{'+','.join(str(x)for x in expected)+'}']
  rows.append('{'+','.join(fields)+'}')
 code=headers+'\nColorEffectRecord D_800DF700[8];s32 D_800DF7B4;\nvoid bzero(void *p,int n){u8 *b=p;while(n-->0)*b++=0;}\n'
 for i,(_,text)in enumerate([('selected',body)]+controls):code+=text.replace('func_15187EC0(','root_%d('%i)+'\n'
 code+='typedef s32(*Root)(s32,f32,u8,u8,u8,u8,u8,u8);static Root roots[]={'+','.join('root_%d'%i for i in range(9))+'};\n'
 code+='struct Case{s32 count;u32 mode,rate,colors[6],seed,answer; s32 finalCount;u8 bytes[288];};static const struct Case cases[]={'+',\n'.join(rows)+'};\n'
 code+=r"""
 static int run(void){u32 n,k,j,bad,killed=0;union{u32 word;f32 mode;} rate;const struct Case *c;u8 *bytes=(u8*)D_800DF700;
  for(n=0;n<sizeof(cases)/sizeof(cases[0]);n++)for(k=0;k<9;k++){
   c=&cases[n];for(j=0;j<288;j++)bytes[j]=(j*29+c->seed*11+90)&255;D_800DF7B4=c->count;rate.word=c->rate;
   bad=(u32)roots[k]((s32)c->mode,rate.mode,(u8)c->colors[0],(u8)c->colors[1],(u8)c->colors[2],(u8)c->colors[3],(u8)c->colors[4],(u8)c->colors[5])!=c->answer||D_800DF7B4!=c->finalCount;
   for(j=0;j<288;j++)if(bytes[j]!=c->bytes[j])bad=1;
   if(!k&&bad)return 2;if(k&&bad)killed|=1u<<(k-1);
  }
  return killed==255?0:3;
 }
 """+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 reports=[]
 for opt in ['-O0','-O2','-O3']:
  p=o/('native19-'+opt[1:]);p.with_suffix('.c').write_text(code);q=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(q.stdout,q.stderr);q=subprocess.run([str(p)],capture_output=True);assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
  reports.append(dict(profile=opt,cases=len(rows),executions=len(rows)*9,all_288_pool_and_guard_bytes_checked=True,all_eight_controls_effective=True,controls=[n for n,_ in controls],UBSan=True,valid_native_counts_only=True))
 return reports
