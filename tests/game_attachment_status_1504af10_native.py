"""Exhaustive packed flags, SDK canaries and Python-derived callback cases."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_attachment_status_1504af10_match import ROOT,BUILD
root=ROOT;out=root/BUILD
from tools.tests import game_attachment_status_1504af10_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def mutations(selected):
 rows={
 'zero-gate':selected.replace('(flags != 0)','(flags == 0)'),
 'ignored-disabled-bit':selected.replace('(((s32) flags >> 0xF) == 0)','1'),
 'force-low-byte':selected.replace('(force != 0)','((u8)force != 0)'),
 'release-low-byte':selected.replace('(release != 0)','((u8)release != 0)'),
 'wrong-category-mask':selected.replace('(flags >> 0xC) & 7','(flags >> 0xC) & 3'),
 'resolver-low-byte-truth':selected.replace('(kind != 0)','((u8)kind != 0)'),
 'category-low-byte':selected.replace('(kind == 3)','((u8)kind == 3)'),
 'cached-record-index':selected.replace('slot = actor->unk92 & 0xFFF;','slot = flags & 0xFFF;'),
 'missing-release-clear':selected.replace('actor->unk92 = 0;','actor->unk92 = actor->unk92;'),
 'wrong-owner-bias':selected.replace('+ 0x64','+ 0x63'),
 'wrong-status-mask':selected.replace('0xFF9F','0xFFDF'),
 'unsigned-height-offset':selected.replace('(s16) actor->unk90','(u16) actor->unk90'),
 }
 assert len(rows)==12 and all(v!=selected for v in rows.values()),[k for k,v in rows.items()if v==selected];return rows
def cases():
 result=[c for c in guest.cases()if not c.alias and 0<=c.actor_index<26 and c.effects in(0,1)]
 for answer in(0x10000,0x10003):result.append(guest.replace(guest.Case(),flags=1,answer=answer,resolved=7))
 for index in range(26):result.append(guest.replace(guest.Case(),actor_index=index))
 return result
def row(c):
 m=guest.fixture(c);slots=(c.flags&4095,c.resolved&4095);addresses=[table+index*160 for table in(guest.TABLE0,guest.TABLE1)for index in slots]
 for at in addresses:
  for offset,value in((16,0x1234),(18,0xEDCC),(20,3000)):guest.put(m,at+offset,value,2)
 want,calls,_=guest.reference(m,c);p=guest.actor(c);fields=[c.flags,c.force,c.release,c.answer,c.resolved,c.effects,c.actor_index,c.field,*c.positions,c.offset,guest.read(want,p+146,2),*[guest.read(want,p+20+4*i)for i in range(3)],guest.read(want,p+144,2),int(guest.read(want,guest.SYMS['D_800DBEF4'])==guest.TABLE1)]
 for at in addresses:fields +=[want[at+78],want[at+79],*[guest.read(want,at+i,2)for i in(16,18,20)]]
 fields +=[len(calls),1];assert len(fields)==40;return '{ {'+','.join('0x%Xu'%guest.u32(v)for v in fields)+'} }'
def program(selected):
 source='#include <ultra64.h>\n#include "structs.h"\nstruct127 D_800CC2D0[26];\nstruct131 *D_800DBEF4;\ns32 func_1504AEF4(s32,s32);\n'
 for name,part in {'candidate':selected,**mutations(selected)}.items():source+=part.replace('func_1504AF10(',name.replace('-','_')+'(',1)+'\n'
 real=body((root/'conker/src/game_77AD0.c').read_text(),'func_1504AEF4').replace('func_1504AEF4(','realZeroResolver(',1);source+=real+'\n'
 actions=[]
 for high in range(16):
  a=[]
  for force,release in((0,0),(0,1),(1,0),(1,1)):
   value=0
   if force or high<8:
    if high&7==0:value=1
    elif high&7==3:value=4 if release else 3 if force else 2
   a.append(value)
  actions.append('{'+','.join(map(str,a))+'}')
 source+=r'''
_Static_assert(sizeof(void*)==4,"native32");
_Static_assert(sizeof(struct127)==812,"SDK actor");
_Static_assert(sizeof(struct131)==160,"SDK record");
_Static_assert(__builtin_offsetof(struct127,unk92)==146,"packed attachment");
_Static_assert(__builtin_offsetof(struct131,unk4F)==79,"record status");
struct Row{u32 w[40];};static const struct Row rows[]={ROWS};static struct Row sweep;
static const u8 actions[16][4]={ACTIONS};static const u8 status[256]={STATUS};
static struct131 table0[4096],table1[4096];static struct131*records[4];static const struct Row*c;
static int calls,error;static u32 expectedCalls;
static f32 floating(u32 n){union{u32 u;f32 f;}v;v.u=n;return v.f;}
static u32 bits(f32 f){union{u32 u;f32 f;}v;v.f=f;return v.u;}
static void initializeRecord(struct131*p){u32 i;u8*b=(u8*)p;for(i=0;i<160;i++)b[i]=(u8)(i*29+0xA5);p->unk4F=(s8)c->w[7];p->unk10=0x1234;p->unk12=(s16)0xEDCC;p->unk14=3000;}
__attribute__((noinline)) s32 func_1504AEF4(s32 id,s32 output){struct127*p=&D_800CC2D0[c->w[6]];u32 i;calls++;
 if(calls!=1||(u32)id!=(c->w[0]&0x7FFF)||!output||((u32)output&3)||p->unk92!=c->w[0]||D_800DBEF4!=table0)error=1;
 for(i=0;i<4;i++)if(records[i]->unk4E!=123||(u8)records[i]->unk4F!=c->w[7])error=2;
 if(!c->w[39])return realZeroResolver(id,output);
 *(u32*)(u32)output=c->w[4];
 if(c->w[5]&1){p->unk92=(u16)(c->w[0]^0x55);D_800DBEF4=table1;p->x_position=-12.75f;p->y_position=-4.25f;p->z_position=15.5f;p->unk90=0xFFE0;}
 return(s32)c->w[3];
}
typedef void(*Subject)(struct127*,s32,s32);
static int one(Subject fn){u32 i,j,n;struct127*p;u8*b;struct131*q;
 p=&D_800CC2D0[c->w[6]];b=(u8*)p;for(i=0;i<812;i++)b[i]=(u8)(i*13+0x59);
 p->unk92=(u16)c->w[0];p->x_position=floating(c->w[8]);p->y_position=floating(c->w[9]);p->z_position=floating(c->w[10]);p->unk90=(u16)c->w[11];
 records[0]=&table0[c->w[0]&4095];records[1]=&table0[c->w[4]&4095];records[2]=&table1[c->w[0]&4095];records[3]=&table1[c->w[4]&4095];for(i=0;i<4;i++)initializeRecord(records[i]);D_800DBEF4=table0;calls=error=0;expectedCalls=c->w[38];
 fn(p,(s32)c->w[1],(s32)c->w[2]);
 if(error||(u32)calls!=expectedCalls||p->unk92!=c->w[12]||bits(p->x_position)!=c->w[13]||bits(p->y_position)!=c->w[14]||bits(p->z_position)!=c->w[15]||p->unk90!=c->w[16]||D_800DBEF4!=(c->w[17]?table1:table0))return 1;
 for(i=0;i<812;i++)if(!(20<=i&&i<32)&&!(144<=i&&i<148)&&b[i]!=(u8)(i*13+0x59))return 2;
 for(j=0;j<4;j++){q=records[j];n=18+j*5;if(q->unk4E!=c->w[n]||(u8)q->unk4F!=c->w[n+1]||(u16)q->unk10!=c->w[n+2]||(u16)q->unk12!=c->w[n+3]||(u16)q->unk14!=c->w[n+4])return 3;
  b=(u8*)q;for(i=0;i<160;i++)if(!(16<=i&&i<22)&&i!=78&&i!=79&&b[i]!=(u8)(i*29+0xA5))return 4;}
 return 0;
}
static void sweepRow(u32 flags,u32 mode){u32 i,j,action,index=(flags>>8)%26;for(i=0;i<40;i++)sweep.w[i]=0;
 sweep.w[0]=flags;sweep.w[1]=mode>>1;sweep.w[2]=mode&1;sweep.w[4]=7;sweep.w[6]=index;sweep.w[7]=flags&255;sweep.w[8]=0x41480000;sweep.w[9]=0xC0200000;sweep.w[10]=0x422E0000;sweep.w[11]=0xFFFF;
 sweep.w[12]=flags;sweep.w[13]=sweep.w[8];sweep.w[14]=sweep.w[9];sweep.w[15]=sweep.w[10];sweep.w[16]=sweep.w[11];
 for(j=0;j<4;j++){i=18+j*5;sweep.w[i]=123;sweep.w[i+1]=sweep.w[7];sweep.w[i+2]=0x1234;sweep.w[i+3]=0xEDCC;sweep.w[i+4]=3000;}
 action=flags?actions[flags>>12][mode]:0;sweep.w[38]=action==1;
 if(action>=2){if(action==4)sweep.w[12]=0;
  for(j=0;j<2;j++){if(j==1&&(flags&4095)!=7)continue;i=18+j*5;sweep.w[i]=action==2?100+index:0;
   if(action==2){sweep.w[i+1]=status[sweep.w[7]];sweep.w[i+2]=12;sweep.w[i+3]=65533;sweep.w[i+4]=43;}}}
}
static int check(Subject fn){u32 flags,mode,i;int result;
 for(flags=0;flags<65536;flags++)for(mode=0;mode<4;mode++){sweepRow(flags,mode);c=&sweep;result=one(fn);if(result)return result;}
 for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){c=&rows[i];result=one(fn);if(result)return result;}
 return 0;
}
static int run(void){if(check(candidate))return 1;
'''.replace('ROWS',',\n'.join(row(c)for c in cases())).replace('ACTIONS',','.join(actions)).replace('STATUS',','.join(str((n&0x9F)|0x20)for n in range(256)))
 for i,name in enumerate(mutations(selected)):source+='if(!check('+name.replace('-','_')+'))return '+str(i+20)+';\n'
 return source+'return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
def main():
 selected=body((out/'final-owner.c').read_text(),'func_1504AF10');p=out/'native.c';p.write_text(program(selected));profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fno-strict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert not r.returncode and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True,timeout=60);assert r.returncode==0 and not r.stdout and not r.stderr,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,UBSan=True,full_flag_mode_cases=262144,scripted_cases=len(cases()),effective_controls=12)
 report=dict(profiles=profiles,all_65536_packed_flags=True,all_26_actors=True,SDK32_layout=True,full_actor_and_record_canaries=True,real_zero_resolver_C_in_flag_sweep=True,nonzero_returns_are_interface_extensions=True,guest_aliases_claimed=False)
 (out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
