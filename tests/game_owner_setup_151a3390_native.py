"""Actual native32 C, 43 defined descriptor bytes and effective source controls."""
from dataclasses import replace
import json,subprocess,time
from tools.experiments import game_owner_setup_151a3390_recovery as m
from tools.tests import game_owner_setup_151a3390_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 m.check_inputs();text=m.PIN['replacement'];at=text.index('/* Submit the owner');types,body=text[:at],text[at:]
 rows=[]
 for seed in range(256):
  for variant in range(4):
   c=g.Case(seed,variant&1,channel=(seed*13+variant*37)&255);_,_,packets=g.reference(c)
   rows.append('{%du,%du,%du,0x%Xu,0x%Xu,{%s}}'%(seed,c.channel,c.mutation,g.BITS[seed%8],g.BITS[(seed+3)%8],','.join(map(str,packets[0]))))
 prefix='''#include <ultra64.h>
 typedef struct NativeRecord225 struct225;
 __attribute__((noreturn))static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code):"memory");__builtin_unreachable();}
 static void check(int x){if(!x)quit(3);}
 static f32 fp(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
 static u32 bits(f32 f){union{u32 u;f32 f;}x;x.f=f;return x.u;}
 static void setFloat(f32 *p,u32 word){for(unsigned i=0;i<4;i++)((u8*)p)[i]=(u8)(word>>(8*i));}
 '''+types+'''
 struct Vector{u32 identity,channel,mutation,first,second;u8 packet[48];};
 static const struct Vector vectors[]={
 '''+',\n'.join(rows)+'''};
 static const struct Vector *v;static union{u32 words[32];u8 bytes[128];}owner;
 static u32 calls;static OwnerSetupDescriptor151A3390 *retained;
 f32 D_800A8D50,D_800A8D54;
 static void comparePacket(OwnerSetupDescriptor151A3390 *p){
  static const unsigned fields[][2]={{8,4},{12,4},{16,4},{20,4},{24,2},{26,2},{28,2},{32,4},{36,4}};
  check(p->owner==owner.bytes&&p->identity==v->packet[4]&&p->attachment==v->packet[5]);
  for(unsigned f=0;f<sizeof(fields)/sizeof(fields[0]);f++){unsigned off=fields[f][0],n=fields[f][1];u32 word=0;for(unsigned i=0;i<n;i++)word|=(u32)((u8*)p)[off+i]<<(8*i);for(unsigned i=0;i<n;i++)check(((word>>(8*(n-i-1)))&255)==v->packet[off+i]);}
  for(unsigned i=40;i<=46;i++)check(((u8*)p)[i]==v->packet[i]);
 }
 static void effect(unsigned ordinal){
  if(v->mutation){
   owner.bytes[0x3b]^=0x51+ordinal;D_800A8D50=fp(0xbf800000u+ordinal);D_800A8D54=fp(0x40000000u+ordinal);
   for(unsigned i=4;i<48;i++)if(i!=6&&i!=7&&i!=30&&i!=31&&i!=47)((u8*)retained)[i]^=0x35+ordinal;
  }
 }
 __attribute__((noinline,noclone))u8 *func_151A3504(void *input,u8 channel){check(calls++==0&&channel==v->channel);retained=input;comparePacket(retained);effect(0);return v->mutation?owner.bytes:0;}
 __attribute__((noinline,noclone))void func_151A4590(u8 * volatile p,u8 channel){check(calls++==1&&p==owner.bytes&&channel==v->channel);effect(1);}
 __attribute__((noinline,noclone))void func_151A499C(void *p,u8 channel){check(calls++==2&&p==owner.bytes&&channel==v->channel);effect(2);}
 __attribute__((noinline,noclone))s32 func_10010154(u16 id,void *p,u16 flags,s16 volume,u16 distance){check(calls++==3&&id==0x1aa&&p==owner.bytes&&flags==0x55f0&&volume==1000&&distance==4000);effect(3);return -1;}
 __attribute__((noinline,noclone))struct225 *func_15160A58(u8 *p,u8 kind,void *vector,u8 header,s16 lifetime,s32 a,s32 b,s32 c,s32 d,s32 unused9,s32 unused10,s8 tag,s32 extra,u8 flags,u8 priority,s32 user){
  f32 *pos=vector;check(calls++==4&&p==owner.bytes&&kind==1&&header==2&&lifetime==300&&a==80&&b==255&&c==255&&d==117&&unused9==255&&unused10==0&&tag==-1&&extra==0&&flags==0&&priority==v->channel&&user==1);
  check(bits(pos[0])==0&&bits(pos[1])==0&&bits(pos[2])==0);pos[0]=fp(0x80000000);effect(4);return 0;
 }
 '''
 suffix='''
 _Static_assert(sizeof(void*)==4&&sizeof(OwnerSetupDescriptor151A3390)==48,"o32 descriptor");
 _Static_assert(__builtin_offsetof(OwnerSetupDescriptor151A3390,value14)==20&&__builtin_offsetof(OwnerSetupDescriptor151A3390,value28)==40&&__builtin_offsetof(OwnerSetupDescriptor151A3390,reserved2F)==47,"descriptor offsets");
 static void(*volatile invoke)(u8*,u8)=func_151A3390;
 static int run(void){for(unsigned i=0;i<sizeof(vectors)/sizeof(vectors[0]);i++){
  v=&vectors[i];for(unsigned j=0;j<128;j++)owner.bytes[j]=(j*13+v->identity)&255;owner.bytes[0x3b]=v->identity;
  calls=0;retained=0;setFloat(&D_800A8D50,v->first);setFloat(&D_800A8D54,v->second);invoke(owner.bytes,v->channel);check(calls==5);
 }return 0;}
 '''
 variants={'selected':body,
 'wrong-identity':body.replace('owner[0x3B]','owner[0x3C]'),
 'descriptor-byte':body.replace('descriptor.value2E = 31','descriptor.value2E = 30'),
 'audio-distance':body.replace('1000, 4000','1000, 4001'),
 'zero-vector':body.replace('position[0] = 0.0f','position[0] = 1.0f'),
 'call-order':body.replace('func_151A4590(owner, channel)','func_151A499C(owner, channel)'),
 'factory-priority':body.replace('0, 0, channel, 1','0, 0, 0, 1')}
 results=[]
 for label,fn in variants.items():
  assert label=='selected'or fn!=body
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=m.OUT/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START)
   start=time.monotonic();q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=m.ROOT,capture_output=True,text=True)
   assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==(0 if label=='selected'else 3),(label,opt,p.returncode)
   row=dict(label=label,opt=opt,exit_code=p.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_selected_run=len(rows),runs=results,native32=True,UB_traps=True,defined_descriptor_bytes=43,padding_not_observed_or_mutated=True,five_providers_and_16_arguments=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs()
if __name__=='__main__':main()
