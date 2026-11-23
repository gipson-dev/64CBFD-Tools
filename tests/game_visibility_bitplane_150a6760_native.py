"""SDK32 bounded decoder output checks derived from an independent guest model."""
from pathlib import Path
import json,subprocess,sys
from tools.experiments import game_visibility_bitplane_150a6760_screen as packet
r,o=packet.ROOT,packet.OUT
from tools.tests import game_visibility_bitplane_150a6760_guest as g
from tools.tests.test_game_projected_packet_draw import native_command
def program():
 rows=[]
 def arr(xs):return '{'+','.join(str(v)for v in xs)+'}'
 for case in g.cases():
  m,args,meta=g.fixture(case);expected,_=g.reference(m,args)
  actual=g.machine(__import__('struct').unpack_from('>64I',(r/'conker/conker.us.bin').read_bytes(),0xD3C10),m,args)
  assert g.public(actual.memory)==g.public(expected)
  vals=lambda mem:[g.read(mem,g.NODES+16*i+j,2)for i in range(17)for j in(0,4,12)]
  rows.append('{'+','.join((*map(str,case),str(meta['index']),str(meta['offset']),str(meta['seed']),arr(vals(m)),arr(vals(expected))))+'}')
 src='#include <ultra64.h>\n'+(o/'declarations.c').read_text()+r'''
_Static_assert(sizeof(void*)==4&&sizeof(long)==4,"SDK32 ABI");
_Static_assert(sizeof(VisibilityBitCursor)==4,"cursor extent");
_Static_assert(sizeof(VisibilityOutputNode)==16,"node extent");
_Static_assert(__builtin_offsetof(VisibilityOutputNode,alternateOffset)==4,"alternate link");
_Static_assert(__builtin_offsetof(VisibilityOutputNode,nextOffset)==12,"primary link");
u8 *D_800BE5D0,*D_800BE5D8;
VisibilityBitCursor *D_800BE5D4;
s16 D_800DBE30[32];VisibilityOutputNode *D_800DBE48;
static struct {u8 before[16];VisibilityOutputNode nodes[17];u8 after[16];} output;
static u8 stream[0x8040];static s16 tree[48];static VisibilityBitCursor cursors[8];
struct Row {s32 plane,count,kind,remaining,links,index,offset,seed;u16 initial[51],expected[51];};
static const struct Row rows[]={ROWS};
BODY
static void set_tree(s32 at,s16 value,s16 left,s16 right){s16 *p=tree+16+at/2;p[0]=value;p[1]=left;p[2]=right;}
static u32 check(const struct Row *c){
 s32 i,j;u32 checksum=0;u8 *p=(u8*)output.nodes;
 for(i=0;i<16;i++)output.before[i]=output.after[i]=0x6D;
 for(i=0;i<272;i++)p[i]=(i*29+c->seed*13+0x31)&255;
 for(i=0;i<17;i++){
  output.nodes[i].flags=(s16)c->initial[3*i];output.nodes[i].alternateOffset=(s16)c->initial[3*i+1];output.nodes[i].nextOffset=(s16)c->initial[3*i+2];
 }
 for(i=0;i<0x8040;i++)stream[i]=0x67;
 for(i=0;i<32;i++)stream[c->offset+i]=(i*73+c->seed*11+0x5A)&255;
 for(i=0;i<48;i++)tree[i]=0;
 if(c->kind==0)set_tree(0,0x7FFF,0,0);
 else if(c->kind==1){set_tree(0,-1,-16,16);set_tree(-16,0x55,0,0);set_tree(16,0xAA,0,0);}
 else{set_tree(0,-1,-16,16);set_tree(-16,-2,-32,32);set_tree(16,-3,32,48);set_tree(-32,0,0,0);set_tree(32,0x7FFF,0,0);set_tree(48,0xA5,0,0);}
 for(i=0;i<8;i++){cursors[i].byteOffset=0x1234;cursors[i].remainingBits=6;}
 for(i=0;i<32;i++)D_800DBE30[i]=0;
 D_800BE5D0=stream;D_800BE5D4=cursors+2;D_800BE5D8=(u8*)tree+32;D_800DBE48=c->count?output.nodes:NULL;
 D_800DBE30[c->plane]=(s16)c->index;D_800BE5D4[c->index].byteOffset=(u16)c->offset;D_800BE5D4[c->index].remainingBits=(s16)c->remaining;
 for(i=0;i<48;i++)checksum=checksum*33+(u16)tree[i];
 subject(c->plane);
 for(i=0;i<17;i++){
  if((u16)output.nodes[i].flags!=c->expected[3*i]||(u16)output.nodes[i].alternateOffset!=c->expected[3*i+1]||(u16)output.nodes[i].nextOffset!=c->expected[3*i+2])return 1;
  for(j=0;j<16;j++)if(j!=0&&j!=1&&j!=4&&j!=5&&j!=12&&j!=13&&p[i*16+j]!=(u8)((i*16+j)*29+c->seed*13+0x31))return 2;
 }
 for(i=0;i<16;i++)if(output.before[i]!=0x6D||output.after[i]!=0x6D)return 3;
 {u32 after=0;for(i=0;i<48;i++)after=after*33+(u16)tree[i];if(after!=checksum)return 4;}
 for(i=0;i<32;i++)if(stream[c->offset+i]!=(u8)(i*73+c->seed*11+0x5A))return 5;
 for(i=0;i<8;i++)if(cursors[i].byteOffset!=(i==c->index+2?c->offset:0x1234)||cursors[i].remainingBits!=(i==c->index+2?c->remaining:6))return 6;
 if(D_800BE5D0!=stream||D_800BE5D4!=cursors+2||D_800BE5D8!=(u8*)tree+32||D_800DBE48!=(c->count?output.nodes:NULL))return 7;
 return 0;
}
static int run(void){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){u32 error=check(rows+i);if(error)return error;}D_800BE5D0=NULL;D_800BE5D4=NULL;D_800BE5D8=NULL;D_800DBE48=NULL;subject(0);subject(31);return 0;}
void _start(void){int result=run();__asm__ volatile("int $0x80"::"a"(1),"b"(result));__builtin_unreachable();}
'''
 body=(o/'initialized.c').read_text().replace('func_150A6760(','subject(')
 return src.replace('ROWS',',\n'.join(rows)).replace('BODY',body),body
def main():
 src,body=program();profiles={}
 def run(text,label,opt):
  file=o/(label+'.c');file.write_text(text);exe=o/(label+opt)
  q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(file),'-o',str(exe)],cwd=r,capture_output=True,text=True)
  (o/(label+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(label,q.stderr)
  result=subprocess.run([str(exe)],capture_output=True,timeout=60);return result
 for opt in('-O0','-O2','-O3'):
  q=run(src,'native',opt);assert(q.returncode,q.stdout,q.stderr)==(0,b'',b''),(opt,q.returncode,q.stderr)
  profiles[opt]=dict(cases=len(g.cases()),SDK32=True,UBSan=True,strict_aliasing=True)
 controls={
 'wrong-plane-mask':body.replace('~(1U << plane)','~(1U << (plane ^ 1))'),
 'wrong-eight-node-symbol-group':body.replace('if (bit < 7)','if (bit < 6)'),
 'wrong-byte-boundary':body.replace('remaining = 7;','remaining = 6;')}
 for label,changed in controls.items():
  assert changed!=body;q=run(src.replace(body,changed),'control-'+label,'-O2');assert q.returncode==1,(label,q.returncode,q.stderr)
 report=dict(profiles=profiles,effective_output_comparison_controls=list(controls),null_stream_defined_early_return=True,complete_17_node_fields_and_opaque_bytes_checked=True,node_canaries_and_readonly_inputs=True,source_installed=False,matching_credit=0,limits='Allocated non-overlapping SDK32 fixtures; planes0,1,7,11,15,31 are bounded backing tests, not an established production caller domain. No unrestricted C alias, full caller, fault, FCSR, hardware or gameplay claim.')
 (o/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
if __name__=='__main__':main()
