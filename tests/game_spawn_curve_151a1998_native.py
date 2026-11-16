"""Finite native32 complete-C checks; private padding is guest-only evidence."""
from pathlib import Path
import hashlib,importlib.util,itertools,json,struct,subprocess,sys,time
from tools.experiments import game_spawn_curve_151a1998_recovery as m
from tools.experiments.game_remaining_donor_candidates import function_span
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def main():
 o=m.OUT;r=m.ROOT;assert m.check_inputs()
 from tools.tests import game_spawn_curve_151a1998_oracle as g
 source=(o/'proposed-owner.c').read_text();a,z=function_span(source,'func_151A1998');body=source[a:z]
 ta=source.index('typedef struct {\n    u8 *descriptor;');tz=source.index('} EmissionPacket151A11E4;',ta)+len('} EmissionPacket151A11E4;');packet=source[ta:tz]
 cases=[g.Case(seed=seed,initial_phase=p,dt=dt,mutation=mut,success=success)for seed,p,dt,mut,success in itertools.product(range(8),(-1.,0.,1.,1.25,2.75),(0.,.5),range(8),range(3))]
 enum={g.S['func_150ADA20']:0,g.S['func_150ADA68']:1,g.S['func_151423D8']:2,g.S['func_15167D84']:3,g.S['memcpy']:4}
 rows=[]
 for c in cases:
  mem,calls,packets,curves=g.reference(c);assert len(packets)<=4 and len(calls)<=52
  events=[]
  for target,args in calls:
   kind=enum[target];x=args[0]if kind==2 else args[4]if kind==3 else args[2]if kind==4 else 0;y=args[5]if kind==3 else 0
   events.append('{%du,%du,%du}'%(kind,x,y))
  array=lambda bs:'{'+','.join(map(str,bs))+'}'
  packs='{'+','.join(array(p)for p in packets)+'}'if packets else'{{0}}';curv='{'+','.join(array(p)for p in curves)+'}'if curves else'{{0}}'
  rows.append('{%du,%du,%du,%du,%du,%du,%du,%du,%du,%du,%s,%s,{%s}}'%(c.seed,g.bits(c.initial_phase),g.bits(c.dt),c.mutation,c.success,len(packets),len(curves),len(calls),g.read(mem,g.INPUT+0x38),0,packs,curv,','.join(events)or'{0}'))
 vectors='static const struct Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n'
 prefix='''typedef unsigned char u8;typedef signed char s8;typedef signed short s16;typedef unsigned short u16;typedef int s32;typedef unsigned int u32;typedef float f32;
 #define NULL ((void*)0)
 #define offsetof(t,f) __builtin_offsetof(t,f)
 typedef struct{f32 x,y,z;} EffectPacketPosition1CC440;
 typedef struct{EffectPacketPosition1CC440 position;f32 sourceValueA,phase,sourceValueB;s16 parameters[4];}RecordEffectPacket1CC440;
 typedef struct{u8 header[40];RecordEffectPacket1CC440 state;}struct260;
 __attribute__((noreturn)) static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code):"memory");__builtin_unreachable();}
 static void check(int x){if(!x)quit(3);}
 static f32 fp(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
 static u32 bits(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
 f32 D_800BE9A4;u8 D_80090B60[1024],D_80090D34[32];
 '''+packet+'''
 struct Event{u32 kind,a,b;};
 struct Vector{u32 seed,phase,dt,mutation,success,packets,copies,events,finalPhase,pad;u8 packet[4][56],curve[4][20];struct Event event[52];};
 '''+vectors+'''
 static const struct Vector *v;static struct260 record;static u8 output[512];static u32 ri,si,fi,emits,copies,eventIndex;static EmissionPacket151A11E4 *lastPacket;
 static void event(u32 kind,u32 a,u32 b){check(eventIndex<v->events);const struct Event *e=&v->event[eventIndex++];check(e->kind==kind&&e->a==a&&e->b==b);}
 static void mutateInteger(void){if(ri%6==5&&(v->mutation&1)){record.state.position.x=-8;record.state.position.y=9;record.state.position.z=-10;record.state.parameters[0]=20;record.state.parameters[1]=7;record.state.parameters[2]=55;record.state.parameters[3]=9;record.header[12]=129;record.header[1]=254;}if(ri%6==0&&(v->mutation&4)&&lastPacket)lastPacket->curveFlags=0x220;}
 __attribute__((noinline,noclone))s32 func_150ADA20(void){static const u32 values[]={0,1,2,5,17,255,0xffffffffu,3};event(0,0,0);u32 result=values[(ri+v->seed)%8];mutateInteger();ri++;return(s32)result;}
 __attribute__((noinline,noclone))f32 func_150ADA68(void){static const f32 values[]={0,.25f,.5f,.75f,-.5f,1.25f,-1.5f,2};event(1,0,0);return values[(fi+++v->seed)%8];}
 __attribute__((noinline,noclone))f32 func_151423D8(u8 angle){static const f32 values[]={0,.25f,-.5f,.75f,-1,1.5f};event(2,angle,0);return values[(si+++angle+v->seed)%6];}
 static void comparePacket(EmissionPacket151A11E4 *p,const u8 *expected){
  static const unsigned fields[][2]={{0,4},{4,4},{12,2},{14,2},{16,2},{18,2},{20,2},{22,2},{24,2},{28,1},{29,1},{30,1},{31,1},{32,2},{34,2},{36,2},{38,2},{40,2},{42,1},{44,1},{45,1},{46,1},{47,1},{48,1},{49,1},{50,1},{52,2}};
  check(p->descriptor==D_80090D34);
  for(unsigned f=0;f<sizeof(fields)/sizeof(fields[0]);f++){unsigned off=fields[f][0],n=fields[f][1];u32 value=0;for(unsigned i=0;i<n;i++)value|=(u32)((u8*)p)[off+i]<<(8*i);if(off==0)value=0x80090d34u;for(unsigned i=0;i<n;i++)check(((value>>(8*(n-i-1)))&255)==expected[off+i]);}
 }
 __attribute__((noinline,noclone))u8 *func_15167D84(void *packet,s32 alternate,s32 extra,s8 marker,u8 mode,s32 owner){event(3,mode,(u32)owner);check(emits<v->packets&&alternate==0&&extra==20&&marker==-1);lastPacket=packet;comparePacket(lastPacket,v->packet[emits]);if(emits==0&&(v->mutation&2))record.state.phase=2.25f;u8 *answer=v->success==1||(v->success==2&&emits%2==0)?output+emits*128:NULL;emits++;return answer;}
 __attribute__((noinline,noclone))void *memcpy(void *dest,const void *src,u32 n){event(4,n,0);check(copies<v->copies&&n==20&&dest==output+(emits-1)*128+80);const s16 *curve=src;for(unsigned i=0;i<10;i++){u16 value=(u16)curve[i];check((value>>8)==v->curve[copies][2*i]&&(value&255)==v->curve[copies][2*i+1]);}copies++;for(unsigned i=0;i<n;i++)((u8*)dest)[i]=((const u8*)src)[i];return dest;}
 '''
 suffix='''
 _Static_assert(sizeof(void*)==4&&sizeof(EmissionPacket151A11E4)==56,"native32 packet");
 _Static_assert(sizeof(RecordEffectPacket1CC440)==32&&offsetof(struct260,state)==40,"record payload");
 _Static_assert(offsetof(EmissionPacket151A11E4,x)==16&&offsetof(EmissionPacket151A11E4,age)==40&&offsetof(EmissionPacket151A11E4,curveFlags)==52,"packet field offsets");
 static int run(void){for(unsigned index=0;index<sizeof(vectors)/sizeof(vectors[0]);index++){
  v=&vectors[index];for(unsigned i=0;i<sizeof(record.header);i++)record.header[i]=165;
  record.header[12]=(v->seed*17)&255;record.header[1]=(255-v->seed*13)&255;
  record.state.position.x=1.25f+v->seed;record.state.position.y=-2.5f-v->seed;record.state.position.z=3.75f+v->seed*.5f;
  record.state.sourceValueA=3.5f;record.state.phase=fp(v->phase);record.state.sourceValueB=1;
  record.state.parameters[0]=16+(v->seed%4)*4;record.state.parameters[1]=3;record.state.parameters[2]=40;record.state.parameters[3]=20;
  D_800BE9A4=fp(v->dt);D_80090B60[0x1d8]=1;ri=si=fi=emits=copies=eventIndex=0;lastPacket=NULL;
  func_151A1998(&record);check(eventIndex==v->events&&emits==v->packets&&copies==v->copies&&bits(record.state.phase)==v->finalPhase);
  }return 0;}
 '''
 variants={'selected':body,
  'reset-persistent-flags':body.replace('        do {','        do {\n            packet.curveFlags = 0x120;'),
  'short-curve-copy':body.replace('memcpy(scratch.pointer + 0x50, curve, 20)','memcpy(scratch.pointer + 0x50, curve, 18)'),
  'wrong-position-fraction':body.replace('packet.fractionZ = (s32)(targetZ * 256.0f)','packet.fractionZ = (s32)(targetX * 256.0f)')}

 results=[]
 for label,fn in variants.items():
  assert label=='selected'or fn!=body
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=o/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START)
   start=time.monotonic();q=subprocess.run(native_command(opt)+['-fsanitize=float-cast-overflow',str(path),'-o',str(exe)],cwd=r,capture_output=True,text=True)
   assert q.returncode==0 and not q.stderr,(label,opt,q.stdout,q.stderr)
   result=subprocess.run([str(exe)],capture_output=True);assert (result.returncode==0)==(label=='selected'),(label,opt,result.returncode)
   row=dict(label=label,opt=opt,exit_code=result.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 assert m.check_inputs();report=dict(cases_per_selected_run=len(cases),runs=results,native32=True,UB_and_float_cast_traps=True,private_padding_bytes_not_asserted=True,source_installed=m.installed(),c_match_credit=0)
 (o/'native.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
