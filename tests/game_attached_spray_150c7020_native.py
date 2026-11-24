"""SDK32 execution: initialized packet fields only, with effective comparison controls."""
from dataclasses import replace
import hashlib,json,subprocess
from tools.experiments import game_attached_spray_150c7020_match as p
from tools.tests import game_attached_spray_150c7020_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def selected():
 text=p.MANIFEST['selected_source'];return text[text.index('typedef struct {'):text.index('/* Submit a scaled point-difference')]
def source():
 rows=[]
 cases=[replace(c,lifetime=g.half(c.lifetime),seed=0)for c in g.cases()if c.phase==0 and c.mode in(0,1,4,5)]
 cases += [g.Case(tag=i,mode=(0,1,4,5)[i%4],lifetime=(0,1,-1,-32768,32767)[i%5],rng=(i,3*i+17,i+66,5*i+26))for i in range(256)]
 for c in cases:
  initial=g.fixture(c);_,calls,obs=g.reference(initial,c)
  packets=obs if obs else [bytes(60),bytes(60)]
  row='{'+','.join(str(g.u32(v))+'U'for v in(c.owner,c.lifetime,c.tag,c.coefficient,c.mode))+',{'+','.join(str(g.u32(v))+'U'for v in c.rng)+'},{{'+','.join(str(v)for v in packets[0])+'},{'+','.join(str(v)for v in packets[1])+'}}}'
  rows.append(row)
 text='''#include <ultra64.h>
u32 func_150ADA20(void);
'''+selected()+'''
typedef char check_size[sizeof(AttachedSprayPacket)==60?1:-1];
typedef char check_owner[__builtin_offsetof(AttachedSprayPacket,owner)==4?1:-1];
typedef char check_lifetime[__builtin_offsetof(AttachedSprayPacket,lifetime)==42?1:-1];
typedef char check_coefficient[__builtin_offsetof(AttachedSprayPacket,coefficient)==52?1:-1];
typedef struct {u32 owner,life,tag,coefficient,mode,rng[4];u8 expected[2][60];} Row;
static const Row rows[]={\n'''+',\n'.join(rows)+'''};
f32 D_800A0490;
static u8 owner[64],alternate[64];static const Row *c;static int bad,stage,draw,submitted;static u32 failed_case,failed_at,failed_value,failed_expected;
static u32 integer(const u8 *v,int n){u32 result=0;for(int i=n-1;i>=0;i--)result=(result<<8)|v[i];return result;}
static void store_float(u32 b){union{u32 i;f32 f;}v;v.i=b;D_800A0490=v.f;}
void func_1516962C(s32 kind,void *actorPointer,u8 flags){u8 *actor=actorPointer;
 if(stage++!=0||kind!=0x29||actor!=owner||flags!=0x12)bad=1;
 if(c->mode&1){owner[0x3B]^=0x55;store_float(c->coefficient^0x80000000U);}
}
u32 func_150ADA20(void){
 if(stage==0||draw>=4||submitted!=draw/2)bad=1;
 return c->rng[(draw++)&3];
}
void *func_15134DAC(AttachedSprayPacket *packet,s32 kind){
 static const u8 fields[][2]={{0,1},{4,4},{8,1},{12,4},{16,4},{20,4},{24,4},{28,4},{32,4},{36,1},{38,2},{40,2},{42,2},{46,1},{47,1},{48,1},{52,4},{56,1},{57,1}};
 const u8 *bytes=(const u8*)packet;
 if(kind||submitted>=2||draw!=2*(submitted+1))bad=1;
 for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++){
  int at=fields[i][0],n=fields[i][1];u32 value=integer(bytes+at,n),expected=0;
  if(at==4){if(value==(u32)owner)value=0x30000;else if(value==(u32)alternate)value=0x32000;}
  for(int j=0;j<n;j++)expected=(expected<<8)|c->expected[submitted&1][at+j];
  if(value!=expected){bad=1;failed_at=at;failed_value=value;failed_expected=expected;}
 }
 if(submitted++==0&&(c->mode&4)){
  u8 *changed=(u8*)packet;for(int i=0;i<60;i++)changed[i]=(i*7+0x39)&255;
  for(unsigned i=0;i<sizeof(fields)/sizeof(fields[0]);i++){int at=fields[i][0],n=fields[i][1];for(int j=0;j<n/2;j++){u8 byte=changed[at+j];changed[at+j]=changed[at+n-1-j];changed[at+n-1-j]=byte;}}
 }
 return (void*)0x60000;
}
static int run(void){
 for(unsigned i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
  c=&rows[i];stage=draw=submitted=0;owner[0x3B]=alternate[0x3B]=c->tag;store_float(c->coefficient);
  func_150C7020(c->owner?owner:0,(s16)c->life,0xFF,0x89ABCDEF);
  if(stage!=(c->owner?1:0)||draw!=(c->owner?4:0)||submitted!=(c->owner?2:0))bad=1;
  if(bad){failed_case=i;break;}
 }
 return bad?42:0;
}
__attribute__((force_align_arg_pointer)) void _start(void){int result=run();if(result){u32 values[]={failed_case,failed_at,failed_value,failed_expected};char message[36];int ignored;for(int i=0;i<4;i++){for(int j=0;j<8;j++)message[9*i+j]="0123456789abcdef"[(values[i]>>(28-j*4))&15];message[9*i+8]=i==3?'\\n':' ';}__asm__ volatile("int $0x80":"=a"(ignored):"0"(4),"b"(2),"c"(message),"d"(36):"memory");}__asm__ volatile("int $0x80"::"a"(1),"b"(result):"memory");__builtin_unreachable();}
'''
 # Mutation packets use a known portable seed, independent of stack padding.
 assert all(c.seed==0 for c in cases if c.mode&4),[(c.seed,c.mode)for c in cases if c.mode&4 and c.seed]
 return text,len(cases)
def main():
 text,count=source();reports={};controls=[]
 def run(name,body,opt):
  f=p.OUT/(name+'.c');exe=p.OUT/(name+'.exe');f.write_text(body);command=native_command(opt)+[str(f),'-o',str(exe)];q=subprocess.run(command,cwd=p.ROOT,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr;assert not q.stderr,q.stderr
  q=subprocess.run([str(exe)],cwd=p.ROOT,capture_output=True,text=True);return dict(exit=q.returncode,diagnostic=q.stdout+q.stderr,source_sha256=sha(f),binary_sha256=sha(exe),command=command)
 for opt in('-O0','-O2','-O3'):
  q=run('native-'+opt[1:],text,opt);assert q['exit']==0,q;reports[opt]=q
 original=selected()
 mutations=[('first-event','packet.eventCode = 13;','packet.eventCode = 14;'),('second-event','packet.eventCode = 12;','packet.eventCode = 11;'),('size-range','% 66U','% 65U'),('spread-range','% 26U','% 25U'),('default-life','packet.lifetime = 300;','packet.lifetime = 301;'),('owner-tag','owner[0x3B]','owner[0x3A]'),('second-direction','packet.parameters[3] = 15.0f;','packet.parameters[3] = -15.0f;'),('retained-mode','packet.eventCode = 12;','packet.mode = 0; packet.eventCode = 12;'),('coefficient','packet.coefficient = D_800A0490;','packet.coefficient = 0.4720000327f;'),('prepare-kind','func_1516962C(0x29,owner,0x12);','func_1516962C(0x28,owner,0x12);')]
 for name,a,b in mutations:
  assert a in original;changed=original.replace(a,b);body=text.replace(original,changed,1);q=run('native-'+name,body,'-O2');assert q['exit']==42,(name,q);controls.append(dict(name=name,comparison_exit=42,source_sha256=q['source_sha256'],binary_sha256=q['binary_sha256']))
 q=dict(cases_per_profile=count,profiles=reports,effective_source_controls=controls,SDK32=True,strict_aliasing_and_UBSan=True,initialized_fields_only=True,portable_provider_mutations=True,no_signal_or_UBSan_trap_counted=True,source_installed=p.installed(),matching_credit=0);(p.OUT/'native.json').write_text(json.dumps(q,indent=2)+'\n');print(json.dumps({k:v for k,v in q.items()if k not in('profiles','effective_source_controls')}),flush=True);return q
if __name__=='__main__':main()
