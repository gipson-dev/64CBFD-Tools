"""Native32 whole-C checks for 112 defined input bytes and effective errors."""
import json,subprocess,time
from tools.experiments import game_composite_burst_151a3150_recovery as m
from tools.tests import game_composite_burst_151a3150_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 m.check_inputs();text=m.PIN['replacement'];at=text.index('/* Submit the alternate timed');body=text[at:]
 source=(m.FROZEN/m.SOURCE).read_text();types=[]
 for typename in('CompositeEffectPosition','CompositeEffectInput'):
  end=source.index('} '+typename+';')+len('} '+typename+';');start=source.rfind('typedef struct {',0,end);types.append(source[start:end])
 types='\n'.join(types)+text[:at]+"void func_15152B38(CompositeEffectInput *, u8, s32);\n"
 rows=[]
 for c in g.cases():
  initial=g.fixture(c);_,_,packets=g.reference(c)
  array=lambda bs:'{'+','.join(map(str,bs))+'}'
  rows.append('{%du,%du,%du,%s,%s}'%(c.seed,c.mutation,c.enabled,array(g.data(initial,g.INPUT,192)),array(packets[0])))
 vectors='static const struct Vector vectors[]={\n'+',\n'.join(rows)+'\n};\n'
 prefix='''#include <ultra64.h>
 #define offsetof(t,f) __builtin_offsetof(t,f)
 __attribute__((noreturn))static void quit(int code){__asm__ volatile(".byte 0xcd,0x80" : : "a"(1),"b"(code):"memory");__builtin_unreachable();}
 static void check(int x){if(!x)quit(3);}
 static f32 fp(u32 u){union{u32 u;f32 f;}x;x.u=u;return x.f;}
 static u32 be32(const u8 *p){return(u32)p[0]<<24|(u32)p[1]<<16|(u32)p[2]<<8|p[3];}
 '''+types+'''
 typedef struct{u8 header[0x38];f32 sizeA,sizeB;CompositeEffectPosition position,offset;u8 private58[0x10];u32 flags;u8 tail[0x54];}BurstRecord;
 struct Vector{u32 seed,mutation,enabled;u8 input[192],packet[116];};
 '''+vectors+'''
 static const struct Vector *v;static BurstRecord record;static u32 calls;
 f32 D_800A8D3C,D_800A8D40,D_800A8D44;
 static void comparePacket(CompositeEffectInput *p){
  static const unsigned fields[][2]={
   {0,4},{4,4},{8,4},{12,4},{16,4},{20,4},{24,4},{28,4},{32,4},{36,4},{40,4},
   {44,2},{46,2},{48,2},{50,2},{52,4},{56,4},{60,2},{62,2},{64,2},
   {92,4},{96,4},{100,2},{102,2},{104,2},{106,1},{108,4},{112,1},{113,1},{114,1},{115,1}};
  for(unsigned f=0;f<sizeof(fields)/sizeof(fields[0]);f++){unsigned off=fields[f][0],n=fields[f][1];u32 word=0;for(unsigned i=0;i<n;i++)word|=(u32)((u8*)p)[off+i]<<(8*i);for(unsigned i=0;i<n;i++)check(((word>>(8*(n-i-1)))&255)==v->packet[off+i]);}
  for(unsigned off=0x42;off<=0x58;off++)check(((u8*)p)[off]==v->packet[off]);
 }
 __attribute__((noinline,noclone))void func_15152B38(CompositeEffectInput *p,u8 mode,s32 extra){check(calls++==0&&mode==v->input[12]&&(u32)extra==v->input[1]);comparePacket(p);if(v->mutation)for(unsigned i=0;i<116;i++)if(!((i>=0x59&&i<=0x5b)||i==0x6b))((u8*)p)[i]^=0x5a;}
 '''
 suffix='''
 _Static_assert(sizeof(CompositeEffectInput)==116&&sizeof(BurstRecord)==192,"complete packet and record");
 _Static_assert(offsetof(BurstRecord,sizeA)==0x38&&offsetof(BurstRecord,position)==0x40&&offsetof(BurstRecord,flags)==0x68,"record layout");
 _Static_assert(offsetof(CompositeEffectInput,field14Base)==0x14&&offsetof(CompositeEffectInput,field5C)==0x5c&&offsetof(CompositeEffectInput,privateTail72)==0x72,"packet layout");
 static void(*volatile invoke)(u8*)=func_151A3150;
 static int run(void){for(unsigned n=0;n<sizeof(vectors)/sizeof(vectors[0]);n++){
  v=&vectors[n];for(unsigned i=0;i<192;i++)((u8*)&record)[i]=v->input[i];
  record.sizeA=fp(be32(v->input+0x38));record.sizeB=fp(be32(v->input+0x3c));
  record.position.x=fp(be32(v->input+0x40));record.position.y=fp(be32(v->input+0x44));record.position.z=fp(be32(v->input+0x48));
  record.offset.x=fp(be32(v->input+0x4c));record.offset.y=fp(be32(v->input+0x50));record.offset.z=fp(be32(v->input+0x54));record.flags=be32(v->input+0x68);
  D_800A8D3C=fp(0x3cadab9fu);D_800A8D40=fp(0x3d59e83eu);D_800A8D44=fp(0xbf83f7cfu);calls=0;
  invoke((u8*)&record);check(calls==1);
 }return 0;}
 '''
 variants={'selected':body,
  'force-offset':body.replace('if (*(u32 *)(record + 0x68) & 0x1000)','if (1)'),
  'omit-offset':body.replace('if (*(u32 *)(record + 0x68) & 0x1000)','if (0)'),
  'wrong-scale':body.replace('* D_800A8D3C','* D_800A8D40'),
  'tail-sentinel':body.replace('((s8 *)packet.privateTail72)[1] = -1','((s8 *)packet.privateTail72)[1] = 0'),
  'swapped-mode-owner':body.replace('record[0xC], record[1]','record[1], record[0xC]')}
 results=[]
 for label,fn in variants.items():
  assert label=='selected'or fn!=body
  for opt in(('-O0','-O2')if label=='selected'else('-O2',)):
   path=m.OUT/('native-'+label+opt+'.c');exe=path.with_suffix('');path.write_text(prefix+fn+suffix+START)
   start=time.monotonic();q=subprocess.run(native_command(opt)+[str(path),'-o',str(exe)],cwd=m.ROOT,capture_output=True,text=True)
   assert q.returncode==0 and not q.stderr,(label,q.stdout,q.stderr)
   p=subprocess.run([str(exe)],capture_output=True);assert p.returncode==(0 if label=='selected'else 3),(label,opt,p.returncode)
   row=dict(label=label,opt=opt,exit_code=p.returncode,seconds=round(time.monotonic()-start,3));results.append(row);print(json.dumps(row),flush=True)
 report=dict(cases_per_selected_run=len(rows),runs=results,native32=True,UB_traps=True,defined_packet_bytes=112,uninitialized_padding_bytes_not_read=True,source_installed=m.installed(),c_match_credit=0)
 (m.OUT/'native.json').write_text(json.dumps(report,indent=2)+'\n');m.check_inputs()
if __name__=='__main__':main()
