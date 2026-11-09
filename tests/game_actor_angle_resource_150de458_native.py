"""Native32 actor image and callback contract; independent serialized expectations."""
import json,subprocess,sys
from pathlib import Path
from tools.experiments.game_actor_angle_resource_150de458_match import ROOT,BUILD,NEW_SOURCE,HEADERS
root=ROOT;out=root/BUILD
from tools.tests import game_actor_angle_resource_150de458_oracle as guest
from tools.experiments.game_remaining_donor_candidates import body
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
source=NEW_SOURCE;selected=body(source,'func_150DE458');header=HEADERS
def controls():
 rows={
 'exact_flag_byte':selected.replace('(actor->flags & 3) == 3','actor->flags == 3'),
 'unsigned_float_ticks':selected.replace('delta = D_800BE9E4','delta = (u32)D_800BE9E4'),
 'wrong_wrap_equality':selected.replace('>= upper','> upper'),
 'wrong_wrap_amount':selected.replace('upper = 360.0f','upper = 180.0f'),
 'wrong_acceleration':selected.replace('actor->velocityY -=','actor->velocityY +='),
 'unsigned_lifetime_compare':selected.replace('s32 remaining;','u32 remaining;'),
 'missing_removal':selected.replace('actor->remove = 1','actor->remove = 0'),
 'unmasked_type':selected.replace('(actor->type & ~0x8000)','actor->type'),
 'single_resource':selected.replace('last != 9','last != 7'),
 'cached_resource':selected.replace('resource++, first += 2','first += 2'),
 'wrong_address_tail':selected.replace('- 0x200u','- 0x100u'),
 'wrong_segment_pair':selected.replace('first = 4','first = 3'),
 'wrong_priority':selected.replace('&extent, 3, 0','&extent, 2, 0'),
 }
 statement='        actor->velocityY -= (u32)actor->verticalAcceleration * (u32)D_800BE9E4;\n'
 rows['late_rate_update']=selected.replace(statement,'').replace('        actor->positionZ +=',statement+'        actor->positionZ +=')
 assert all(v!=selected for v in rows.values());return rows
def image(memory,base,size,fields):
 b=bytearray(memory[base+i]for i in range(size))
 for at,n in fields:b[at:at+n]=reversed(b[at:at+n])
 return b
def main():
 cases=list(guest.cases());fields=[(i,4)for i in(0,4,8,0x3C,0x60,0x64,0x68,0x7C)]+[(i,2)for i in(0x10,0x12,0x14,0x54,0x5A,0x5C,0x5E)]
 qfields=[(i*16+j*4,4)for i in range(8)for j in range(3)]
 array=lambda values:'{'+','.join(str(v)for v in values)+'}'
 rows=[]
 for c in cases:
  initial=guest.fixture(c);expected,calls=guest.reference(initial,c);events=[]
  for target,args in calls:
   events.append([0,*[args[0],0,args[2],args[3],0]]if target==guest.LOAD else[1,*args])
  events+=[[0]*6]*(4-len(events))
  vals=[guest.u32(c.ticks),c.seed,c.variant,c.mutation,c.capacity,guest.read(expected,guest.SYMS['D_800BE9E4']),expected[guest.SYMS['D_800D9ED0']],len(calls)]
  vals=[str(v)+'u'for v in vals]+[array(image(m,guest.ACTOR,160,fields))for m in(initial,expected)]+[array(guest.read(expected,guest.SYMS['D_80090204']+4*i)for i in range(4)),array(image(expected,guest.SYMS['D_800D9ED8'],128,qfields)),'{'+','.join(array(e)for e in events)+'}']
  rows.append('{'+','.join(vals)+'}')
 queue_initial=image(guest.fixture(guest.Case()),guest.SYMS['D_800D9ED8'],128,qfields)
 program=header+r'''
_Static_assert(sizeof(void*)==4&&sizeof(ActorAngleState10B7D0)==160,"actor ABI");
_Static_assert(__builtin_offsetof(ActorAngleState10B7D0,flags)==0x73&&__builtin_offsetof(ActorAngleState10B7D0,velocityY)==0x5C&&__builtin_offsetof(ActorAngleState10B7D0,lifetime)==0x8A,"field layout");
typedef struct {u32 ticks,seed,variant,mutation,capacity,finalTicks,finalCount,ncalls;u8 initial[160],expected[160];u32 table[4];u8 queue[128];u32 calls[4][6];}Fixture;
static const Fixture fixtures[]={
'''+',\n'.join(rows)+r'''
};
static const u8 queueInitial[128]='''+array(queue_initial)+r''';
s32 D_800BE9E4,D_80090204[4];static ActorAngleState10B7D0 actor;static u8 queueBytes[128],queueExpected[128];static u32 count,loads,event,error;static const Fixture*c;
static void copy(u8*d,const u8*s,u32 n){u32 i;for(i=0;i<n;i++)d[i]=s[i];}
static int equal(const u8*a,const u8*b,u32 n){u32 i;for(i=0;i<n;i++)if(a[i]!=b[i])return 0;return 1;}
static void wr32(u8*p,u32 v){u32 i;for(i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static u32 address(u32 i){const u32 a[]={0x81200000u,0xFFFFFFF0u,0,0x80000000u};return a[c->seed%4]+i*0x1000u;}
static u32 extent(u32 i){const u32 a[]={0,1,511,512,513,0x7FFFFFFFu,0x80000000u,0xFFFFFFFFu};return a[(c->seed+i)%8];}
__attribute__((noinline,noclone)) u32 func_1510D0EC(s32 identity,s32*out,s32 priority,s32 retain){const u32*a;
 if(event>=c->ncalls||event>=4){error=1;return 0;}a=c->calls[event++];if(a[0]||a[1]!=(u32)identity||priority!=(s32)a[3]||retain!=(s32)a[4]||!out||((u32)out&3))error=2;
 *out=(s32)extent(loads);if(c->mutation&1){D_800BE9E4=(s32)0x87654321;actor.variant=c->variant^1;}
 if(c->mutation&2){D_80090204[c->variant*2+1]=(s32)(0x12340000u+loads);actor.flags^=3;}
 return address(loads++);}
__attribute__((noinline,noclone)) void func_1510D874(s32 object,s32 start,s32 end,s32 first,s32 last){const u32*a;u8*p;
 if(event>=c->ncalls||event>=4){error=3;return;}a=c->calls[event++];if(a[0]!=1||(u32)object!=(u32)&actor||(u32)start!=a[2]||(u32)end!=a[3]||(u32)first!=a[4]||(u32)last!=a[5])error=4;
 if(count<8){p=queueBytes+count*16;wr32(p,(u32)object);wr32(p+4,(u32)start);wr32(p+8,(u32)end);p[12]=(u8)first;p[13]=(u8)last;count++;}}
'''+selected+'\n'
 for name,text in controls().items():program+=text.replace('func_150DE458(','negative_'+name+'(',1)+'\n'
 program+=r'''
typedef void(*Update)(void*);
static int check(Update fn){u32 n,i;for(n=0;n<sizeof(fixtures)/sizeof(fixtures[0]);n++){c=fixtures+n;loads=event=error=0;count=c->capacity;
 copy((u8*)&actor,c->initial,160);copy(queueBytes,queueInitial,128);copy(queueExpected,c->queue,128);
 for(i=c->capacity;i<c->finalCount;i++)wr32(queueExpected+i*16,(u32)&actor);
 D_800BE9E4=(s32)c->ticks;for(i=0;i<4;i++)D_80090204[i]=(s32)(0x692+i);
 fn(&actor);if(error||event!=c->ncalls||(u32)D_800BE9E4!=c->finalTicks||count!=c->finalCount)return 1;
 if(!equal((u8*)&actor,c->expected,160)||!equal(queueBytes,queueExpected,128))return 2;
 for(i=0;i<4;i++)if((u32)D_80090204[i]!=c->table[i])return 3;
 }return 0;}
static int run(void){if(check(func_150DE458))return 10;
'''
 for i,name in enumerate(controls()):program+='if(!check(negative_'+name+'))return '+str(20+i)+';\n'
 program+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 p=out/'native.c';p.write_text(program);profiles={}
 for opt in('-O0','-O2','-O3'):
  exe=out/('native'+opt);r=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=root,capture_output=True,text=True);assert r.returncode==0 and not r.stdout and not r.stderr,r.stdout+r.stderr
  r=subprocess.run([str(exe)],capture_output=True);assert r.returncode==0,(opt,r.returncode,r.stderr);profiles[opt]=dict(exit=0,cases=len(cases),UBSan=True,strict_aliasing=True,effective_controls=len(controls()))
 report=dict(profiles=profiles,cases_per_profile=len(cases),effective_semantic_controls=list(controls()),all_actor_and_queue_bytes_checked=True,native_extent_always_written=True,serialized_independent_guest_expectations=True)
 (out/'native-contract.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
