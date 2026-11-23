"""Complete renderer with actual SDK32 types and independent native fixtures."""
from pathlib import Path
from dataclasses import replace
import hashlib,itertools,json,struct,subprocess,sys
from tools.experiments import game_compact_sprite_renderer_15168118_match as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_compact_sprite_renderer_15168118_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
NUMERIC={0x14:4,0x18:4,0x1C:2,0x20:2,0x22:2,0x24:2,0x34:2,0x36:2,0x44:2}
TOKENS={'packet':0xF001,'sync':0xF002}
def fnv(values):
 h=2166136261
 for v in values:h=((h^(v&0xFFFFFFFF))*16777619)&0xFFFFFFFF
 return h
def metadata_id(p):return(g.META,g.SYMS['D_800907FC'],g.SYMS['D_8009053C']).index(p)+1
def state_values(m,c,count):
 values=[];i=0
 while i<0x4C:
  if i==0x10:values.append(metadata_id(g.get(m,g.STATE+i)));i+=4
  elif i in NUMERIC:values.append(g.get(m,g.STATE+i,NUMERIC[i]));i+=NUMERIC[i]
  else:values.append(m[g.STATE+i]);i+=1
 for idx,(p,n)in enumerate(((g.META,64),(g.SYMS['D_800907FC'],16),(g.SYMS['D_8009053C'],16))):
  if idx==c.special:
   value=g.get(m,p);values.append(0xF003 if value==g.FRAMES else value);start=4
  else:start=0
  values.extend(m[p+i]for i in range(start,n))
 values.append(g.get(m,g.SYMS['D_800D2C9C']))
 values.extend(g.get(m,g.SYMS['D_800A4AC8']+4*i)for i in range(80))
 values.extend(g.get(m,g.OUTPUT+4*i)for i in range(count*2))
 return values
def trace_hash(log):
 values=[]
 for name,args,*extra in log:
  values.extend((g.NAMES.index(name)+1,len(args)))
  values.extend(TOKENS[v]if isinstance(v,str)else v for v in args)
  if name=='func_15095760':values.extend(extra[0])
  else:values.extend(extra)
 return fnv(values)
def native_cases():
 base=[c for c in g.cases()if c.view in(0,1)and c.phase==0]
 angles=(-1080,-720,-360,-270,-180,-90,0,45,90,135,180,225,270,315,360,450,720,1080)
 extra=[g.Case(width=-32768,height=-3000,yaw=y,pitch=-30,position=p,flags=f,orientation=a,frame_table=True)
  for y,p,f,a in itertools.product(angles,(-32768,-1,0,257,32767),(0,0x300),(0,255))]
 return list(dict.fromkeys(base+extra)),extra
def controls(body):
 controls={
 'missing-flip-x':body.replace('if (state->flags & 4) packet.flipFlags = 1;','if (0) packet.flipFlags = 1;'),
 'wrong-flip-y':body.replace('state->flags & 8','state->flags & 4'),
 'unsigned-phase-index':body.replace('[state->phase >> 8]','[(u16)state->phase >> 8]'),
 'wrong-packed-phase':body.replace('(u32)(s32)state->phase << 8','(u32)(s32)state->phase << 7'),
 'missing-turn-fold':body.replace('while (angle >= 360.0f) angle -= 360.0f;','while (0) angle -= 360.0f;'),
 'missing-half-turn-fold':body.replace('if (angle >= 180.0f) angle -= 180.0f;','if (0) angle -= 180.0f;'),
 'wrong-quarter-reflection':body.replace('angle = 180.0f - angle','angle = 90.0f - angle'),
 'missing-width-minimum':body.replace('if (dimension < 0x400) dimension = 0x400;','if (0) dimension = 0x400;'),
 'wrong-height-width-clamp':body.replace('if (baseWidth < 0)','if (baseWidth > 0)'),
 'wrong-height-subtract':body.replace(' - (f32)dimension',' + (f32)dimension'),
 'wrong-custom-flag':body.replace('state->flags & 0x100','state->flags & 0x80'),
 'wrong-combiner-byte':body.replace('>> 16','>> 8'),
 'wrong-render-mode-bit':body.replace('extraMode = 0x100000;','extraMode = 0x200000;').replace('D_800D2C9C | 0x100000 |','D_800D2C9C | 0x200000 |'),
 'wrong-primitive-green':body.replace('primaryGreen = state->green;','primaryGreen = state->red;'),
 'wrong-primitive-alpha':body.replace('primaryAlpha = state->alpha;','primaryAlpha = 255;'),
 'wrong-blue-fallback':body.replace('red = green = 128; blue = 255;','red = green = 128; blue = 128;'),
 'missing-final-draw':body.replace('return func_15095760(output, (s16 *)&packet);','return output;'),
 }
 assert all(v!=body for v in controls.values());return controls
def program(body):
 source=(o/'selected-v2/selected-owner.c').read_text();lo=source.index('typedef struct {',source.index('/* Measured compact sprite view;'));hi=source.index('} CompactSpriteState;',lo)+len('} CompactSpriteState;');view=source[lo:hi]
 rows,extra=native_cases();raw=g.bound_blob(*g.payload(o/'selected-v2/candidate.o','func_15168118'),g.SYMS);retail=g.bound_blob(*g.payload(o/'original-target.o','func_15168118'),g.SYMS)
 # Added camera/phase cases are independently checked in both complete MIPS
 # streams before their model expectations are admitted to the native table.
 for c in extra:
  m=g.fixture(c);g.put(m,g.SYMS['D_800D2C9C'],0x40000);want,log,value=g.reference(m,c)
  for ws in(raw,retail):
   machine=g.Oracle(ws,m,c);machine.run();assert(machine.observations,machine.r[2],g.public(machine.memory))==(log,value,g.public(want)),c
 def arr(xs):return'{'+','.join('0x%Xu'%(int(x)&0xFFFFFFFF)for x in xs)+'}'
 encoded=[]
 for c in rows:
  m=g.fixture(c);g.put(m,g.SYMS['D_800D2C9C'],0x40000);want,log,value=g.reference(m,c)
  encoded.append(arr([c.flags,c.texture_type,c.width,c.height,g.bits(c.yaw),g.bits(c.pitch),c.orientation,c.position,c.view,c.special,c.frame_table,c.effect,fnv(state_values(want,c,len(log))),trace_hash(log),len(log),(value-g.OUTPUT)//8]))
 initial=g.fixture(g.Case());coefs=[g.get(initial,g.SYMS[n])for n in('D_800A6CA0','D_800A6CA4')]
 pre='#include <ultra64.h>\n#include "structs.h"\n'+view+'\n'+packet.MANIFEST['declarations']+r'''
extern u32 D_800A4AC8[80];extern struct108 *D_800DBFF0;
Gfx *func_15142FBC(Gfx*,u32,u32,u8*);Gfx *func_15095760(Gfx*,s16*);f32 fabsf(f32);
typedef union{u32 words[16];u8 bytes[64];}NativeMetadata;
static NativeMetadata metadata[3];
/* Fixture bindings for the two address-comparison symbols. */
#define D_800907FC (metadata[1].bytes)
#define D_8009053C (metadata[2].bytes)
'''
 selected=body.replace('func_15168118(','subject(')
 support=r'''
_Static_assert(sizeof(void*)==4&&sizeof(Gfx)==8&&sizeof(CompactSpriteState)==76&&sizeof(CompactSpriteDrawPacket)==20,"SDK32 and measured partial views");
_Static_assert(sizeof(struct108)==0x9A0&&__builtin_offsetof(struct108,unk380)==0x380&&__builtin_offsetof(struct108,unk388)==0x388,"SDK camera layout");
#define OFF(T,F,V) _Static_assert(__builtin_offsetof(T,F)==V,"Measured "#T"."#F)
OFF(CompactSpriteState,texture,0x10);OFF(CompactSpriteState,renderSettings,0x14);OFF(CompactSpriteState,orientation,0x18);OFF(CompactSpriteState,phase,0x1C);OFF(CompactSpriteState,x,0x20);OFF(CompactSpriteState,y,0x22);OFF(CompactSpriteState,z,0x24);OFF(CompactSpriteState,width,0x34);OFF(CompactSpriteState,height,0x36);OFF(CompactSpriteState,red,0x3C);OFF(CompactSpriteState,green,0x3D);OFF(CompactSpriteState,blue,0x3E);OFF(CompactSpriteState,alpha,0x3F);OFF(CompactSpriteState,environmentRed,0x40);OFF(CompactSpriteState,environmentGreen,0x41);OFF(CompactSpriteState,environmentBlue,0x42);OFF(CompactSpriteState,flags,0x44);
OFF(CompactSpriteDrawPacket,x,0);OFF(CompactSpriteDrawPacket,y,2);OFF(CompactSpriteDrawPacket,z,4);OFF(CompactSpriteDrawPacket,width,6);OFF(CompactSpriteDrawPacket,height,8);OFF(CompactSpriteDrawPacket,flipFlags,0xD);OFF(CompactSpriteDrawPacket,descriptor,0x10);
typedef struct{u32 flags,kind,width,height,yaw,pitch,orientation,phase,view,special,frames,effect,stateHash,traceHash,calls,steps;}Row;
static const Row rows[]={ROWS};static const Row*c;
static struct{u8 before[16];CompactSpriteState object;u8 after[16];}box;
static struct{u8 before[16];Gfx commands[32];u8 after[16];}out;
static struct{u8 before[16];struct108 records[2];u8 after[16];}cameras;
static u32 frameData[256] __attribute__((section(".frames")));
u32 D_800A4AC8[80],D_800D2C9C;struct108 *D_800DBFF0;
f32 D_800A6CA0,D_800A6CA4;
static u8*packet,*sync;static u32 trace,calls,error;
static void hash(u32*h,u32 v){*h=(*h^v)*16777619u;}
static void fill(u8*p,u32 n,u8 v){u32 i;for(i=0;i<n;i++)p[i]=v;}
static f32 real(u32 b){union{u32 b;f32 f;}v;v.b=b;return v.f;}
f32 fabsf(f32 x){union{u32 b;f32 f;}v;v.f=x;v.b&=0x7FFFFFFFu;return v.f;}
static u32 readle(const u8*p,u32 n){u32 v=0,i;for(i=0;i<n;i++)v|=(u32)p[i]<<(i*8);return v;}
static u32 metaId(const u8*p){u32 i;for(i=0;i<3;i++)if(p==metadata[i].bytes)return i+1;error++;return 0;}
static u32 cursorId(Gfx*p){u32 at=(u32)p,base=(u32)out.commands;if(at<base||at>base+sizeof(out.commands)||((at-base)&7)){error++;return 0;}return(at-base)/8;}
static u32 pointerRole(u32 id,u32 i){return id==0?(i==8?1:i==9?2:0):id==1?0:id==6?(i==1?1:0):i==(id==2?2:id==3?3:id==4?7:5)?2:0;}
static u32 canonical(u32 id,u32 i,u32 value){u32 role=pointerRole(id,i);if(role)return role==1?0xF001:0xF002;
 if(i==0)return 0x50000+cursorId((Gfx*)value)*8;
 if(id==0&&i==1){u32 n=metaId((u8*)value);return n==1?0x70000:n==2?SPECIAL1:SPECIAL2;}return value;}
static void observe(u32 id,u32*a,u32 n){u32 i,j;hash(&trace,id+1);hash(&trace,n);for(i=0;i<n;i++)hash(&trace,canonical(id,i,a[i]));
 if(id==6){for(i=0;i<10;i+=2){u32 value=readle(packet+i,2);hash(&trace,value>>8);hash(&trace,value&255);}for(i=10;i<20;i++)hash(&trace,packet[i]);}
 else{hash(&trace,*sync);if(id==0)hash(&trace,packet[13]);}calls++;(void)j;}
static void effects(u32 id){CompactSpriteState*s=&box.object;
 if(id==0&&(c->effect&1)){s->width=-2000;s->height=-511;s->orientation=129;}
 if(id==2&&(c->effect&2)){s->flags^=0x201;s->red^=0x5A;s->environmentRed^=0xA5;}
 if(id==4&&(c->effect&4)){s->flags|=1;s->environmentGreen^=0xAA;}
}
static Gfx*provider(u32 id,u32*a,u32 n){u32 i,sum=0,index=cursorId((Gfx*)a[0]);if(index>=32){error++;return out.commands;}
 if(id==0){packet=(u8*)a[8];sync=(u8*)a[9];}observe(id,a,n);
 if(id==0){u8 mask=packet[13];for(i=0;i<20;i++)packet[i]=(u8)(i*11+3);packet[13]=mask;}
 if(id!=1&&id!=6)*sync=0;
 for(i=1;i<n;i++)if(!pointerRole(id,i)){u32 value=canonical(id,i,a[i]);if(value<STACKLO||value>=STACKHI)sum+=value;}
 out.commands[index].words.w0=0xA0000000u|id;out.commands[index].words.w1=sum;
 effects(id);return out.commands+index+1;
}
Gfx*func_15142E24(Gfx*p,void*s,s32 phase,s32 width,s32 height,s32 value,s32 image,u8 kind,u8*attachment,u8*dirty,s32 flags){u32 a[]={(u32)p,(u32)s,(u32)phase,(u32)width,(u32)height,(u32)value,(u32)image,kind,(u32)attachment,(u32)dirty,(u32)flags};return provider(0,a,11);}
Gfx*func_15142B7C(Gfx*p,u32 a,u32 b){u32 v[]={(u32)p,a,b};return provider(1,v,3);}
Gfx*func_1513F4E4(Gfx*p,u8 a,u8*b){u32 v[]={(u32)p,a,(u32)b};return provider(2,v,3);}
Gfx*func_15142FBC(Gfx*p,u32 a,u32 b,u8*d){u32 v[]={(u32)p,a,b,(u32)d};return provider(3,v,4);}
Gfx*func_15142CF0(Gfx*p,s32 a,s32 b,s32 red,s32 green,s32 blue,s32 alpha,u8*d){u32 v[]={(u32)p,a,b,red,green,blue,alpha,(u32)d};return provider(4,v,8);}
Gfx*func_15142C10(Gfx*p,s32 red,s32 green,s32 blue,s32 alpha,u8*d){u32 v[]={(u32)p,red,green,blue,alpha,(u32)d};return provider(5,v,6);}
Gfx*func_15095760(Gfx*p,s16*q){u32 v[]={(u32)p,(u32)q};return provider(6,v,2);}
static u32 numericSize(u32 i){return i==0x14||i==0x18?4:i==0x1C||i==0x20||i==0x22||i==0x24||i==0x34||i==0x36||i==0x44?2:0;}
static u32 stateHash(void){u32 h=2166136261u,i=0,n,k;u8*b=(u8*)&box.object;
 while(i<76){if(i==0x10){hash(&h,metaId(box.object.texture));i+=4;}else if((n=numericSize(i))){hash(&h,readle(b+i,n));i+=n;}else hash(&h,b[i++]);}
 for(k=0;k<3;k++){n=k?16:64;i=0;if(k==c->special){u32 value=metadata[k].words[0];hash(&h,value==(u32)(frameData+128)?0xF003:value);i=4;}for(;i<n;i++)hash(&h,metadata[k].bytes[i]);}
 hash(&h,D_800D2C9C);for(i=0;i<80;i++)hash(&h,D_800A4AC8[i]);for(i=0;i<calls;i++){hash(&h,out.commands[i].words.w0);hash(&h,out.commands[i].words.w1);}return h;
}
static u32 cameraHash(void){u32 h=2166136261u,i;for(i=0;i<sizeof(cameras.records);i++)hash(&h,((u8*)cameras.records)[i]);return h;}
void __attribute__((force_align_arg_pointer)) _start(void){u32 n,i,k,savedCamera;int result=0;
 for(n=0;n<sizeof(rows)/sizeof(rows[0]);n++){
  c=rows+n;trace=2166136261u;calls=0;error=0;packet=sync=0;
  fill(box.before,16,0xD1);fill(box.after,16,0xD2);fill(out.before,16,0xD3);fill(out.after,16,0xD4);fill(cameras.before,16,0xD5);fill(cameras.after,16,0xD6);
  for(i=0;i<76;i++)((u8*)&box.object)[i]=(u8)(i*13+7);for(k=0;k<3;k++)for(i=0;i<64;i++)metadata[k].bytes[i]=(u8)(i*13+7);
  for(i=0;i<sizeof(out.commands);i++)((u8*)out.commands)[i]=(u8)(i*13+7);fill((u8*)cameras.records,sizeof(cameras.records),0xA6);
  box.object.texture=metadata[c->special].bytes;box.object.renderSettings=0x000D0011;box.object.orientation=(s32)c->orientation;box.object.phase=(s16)c->phase;
  box.object.x=-32768;box.object.y=19;box.object.z=32767;box.object.width=(s16)c->width;box.object.height=(s16)c->height;box.object.flags=(u16)c->flags;
  metadata[c->special].words[0]=c->frames?(u32)(frameData+128):0x2345678;metadata[c->special].bytes[10]=(u8)c->kind;
  for(i=0;i<256;i++)frameData[i]=0x61000000u+i*0x10101u;frameData[128+((s16)c->phase>>8)]=0x456789A;
  D_800DBFF0=cameras.records;cameras.records[c->view].unk380=real(c->yaw);cameras.records[c->view].unk388=real(c->pitch);
  D_800A6CA0=real(COEF0);D_800A6CA4=real(COEF1);D_800D2C9C=0x40000;for(i=0;i<80;i++)D_800A4AC8[i]=0x01020304u*i^0xA55AA55Au;
  savedCamera=cameraHash();{Gfx*answer=subject(out.commands,&box.object,(s16)c->view);k=cursorId(answer);}
  for(i=0;i<16;i++)if(box.before[i]!=0xD1||box.after[i]!=0xD2||out.before[i]!=0xD3||out.after[i]!=0xD4||cameras.before[i]!=0xD5||cameras.after[i]!=0xD6)error++;
  for(i=calls*8;i<sizeof(out.commands);i++)if(((u8*)out.commands)[i]!=(u8)(i*13+7))error++;
  if(stateHash()!=c->stateHash||trace!=c->traceHash||calls!=c->calls||k!=c->steps||cameraHash()!=savedCamera||error){u32 diagnostic[8]={n,stateHash(),c->stateHash,trace,c->traceHash,calls,k,error};__asm__ volatile("int $0x80"::"a"(4),"b"(2),"c"(diagnostic),"d"(32));result=1;break;}
 }
 __asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 for old,new in{'ROWS':',\n'.join(encoded),'SPECIAL1':hex(g.SYMS['D_800907FC']),'SPECIAL2':hex(g.SYMS['D_8009053C']),'STACKLO':hex(g.STACK-2048),'STACKHI':hex(g.STACK+512),'COEF0':hex(coefs[0]),'COEF1':hex(coefs[1])}.items():support=support.replace(old,new)
 return pre+selected+'\n'+support,selected,len(rows),len(extra)
def main():
 body=(o/'selected-v2/body.c').read_text();text,subject,count,extra=program(body);profiles={}
 def run(text,label,opt):
  source=o/(label+'.c');source.write_text(text);exe=o/(label+opt)
  cmd=native_command(opt)+['-fstrict-aliasing','-Wl,--section-start=.frames=0x11000000',str(source),'-o',str(exe)]
  q=subprocess.run(cmd,cwd=r,capture_output=True,text=True);(o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0 and not q.stdout and not q.stderr,(label,q.stdout+q.stderr)
  return subprocess.run([str(exe)],capture_output=True,timeout=60)
 opts=('-O0',)if '--first'in sys.argv else('-O0','-O2','-O3')
 for opt in opts:
  q=run(text,'native',opt);assert q.returncode==0 and not q.stdout and not q.stderr,(opt,q.returncode,list(struct.unpack('<%dI'%(len(q.stderr)//4),q.stderr))if len(q.stderr)%4==0 else q.stderr)
  profiles[opt]=dict(cases=count,SDK32=True,strict_aliasing=True,UBSan=True)
 effective=[]
 if '--first'not in sys.argv:
  for name,changed in controls(body).items():
   q=run(text.replace(subject,changed.replace('func_15168118(','subject(')),'native-control-'+name,'-O2');assert q.returncode!=0,('Ineffective source control',name);effective.append(dict(name=name,returncode=q.returncode))
 report=dict(profiles=profiles,additional_camera_phase_cases_checked_in_both_MIPS_streams=extra,effective_source_controls=effective,all_17_used_record_offsets_and_packet_camera_layouts_asserted=True,full_records_metadata_mode_table_commands_and_ordered_provider_observations=True,record_output_camera_canaries=True,limits='SDK32 native views0/1, aligned metadata, finite bounded float conversions, modeled graphics providers. Negative views, arbitrary helper internals, FCSR and gameplay are outside this native domain.',source_installed=packet.installed(),matching_credit=0)
 (o/('native-first.json'if '--first'in sys.argv else'native.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
