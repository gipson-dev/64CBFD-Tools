"""Execute the selected SDK32 callback through its actual C wrapper."""
import subprocess
from tools.experiments import game_map_record_dispatch_15104a80_recovery as source
from tools.tests import game_map_record_dispatch_15104a80_oracle as g
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START
def native_checks(out):
    rows=[]
    for c in g.cases():
        want=g.expected(c);actor=(g.selected(c)-g.ACTORS)//812 if g.selected(c)else -1
        rows.append('{%d,0x%Xu,%d,%d,%d,%d,%d},'%(c.kind,c.mask,c.active,c.delta,c.seed,actor,want[0]if want else 0))
    prelude='''#include <ultra64.h>
#include "structs.h"
extern struct127 D_800CC2D0[26];
extern struct131 *D_800DBEF4;
void func_151494E0(s32,u8);
'''
    harness=r'''
typedef char Layout[(sizeof(void*)==4&&sizeof(struct127)==812&&sizeof(struct131)==160&&sizeof(MapPacket131F30)==12&&sizeof(MapSequence131F30)==9)?1:-1];
typedef struct {u32 kind,mask;int active,delta,seed,actor,command;} Row;
static const Row rows[]={ROWS};static const Row *row;
struct127 D_800CC2D0[26];static u8 records[9*160] __attribute__((aligned(8)));struct131 *D_800DBEF4;
static u32 masks[11];u32 *D_800DBF94;
MapSequence131F30 D_800A2380,D_800A238C,D_800A2398;
static u8 D_800A5770[16];static int called,error;
static u8 snapshot[sizeof(records)+sizeof(D_800CC2D0)+sizeof(masks)+27+sizeof(D_800DBEF4)+sizeof(D_800DBF94)+sizeof(D_800A5770)];
static int status(int i){return row->active==0?0:row->active==1?-1:((row->active==2&&i==0)||(row->active==3&&i==24)||(row->active==4&&i%3==0)||(row->active==5&&i==25))?17:0;}
static int equal_or_save(int save){u8 *parts[9]={(u8*)records,(u8*)D_800CC2D0,(u8*)masks,D_800A2380.bytes,D_800A238C.bytes,D_800A2398.bytes,(u8*)&D_800DBEF4,(u8*)&D_800DBF94,D_800A5770};u32 sizes[9]={sizeof(records),sizeof(D_800CC2D0),sizeof(masks),9,9,9,sizeof(D_800DBEF4),sizeof(D_800DBF94),sizeof(D_800A5770)},i,j,n=0;
 for(i=0;i<9;i++)for(j=0;j<sizes[i];j++,n++){if(save)snapshot[n]=parts[i][j];else if(snapshot[n]!=parts[i][j])return 0;}return 1;}
static void setup(void){u32 i,j;int index=row->delta/160;u8 *a=(u8*)records,*b=(u8*)D_800CC2D0;MapSequence131F30 *seqs[3]={&D_800A2380,&D_800A238C,&D_800A2398};
 for(i=0;i<sizeof(records);i++)a[i]=(u8)(i*29+row->seed+0x5A);
 for(i=0;i<sizeof(D_800CC2D0);i++)b[i]=(u8)(i*17+row->seed+0xA5);
 for(i=0;i<26;i++)D_800CC2D0[i].interaction_state=status((int)i);
 for(i=0;i<11;i++)masks[i]=0xAAAA5555u^i;
 D_800DBEF4=(struct131*)(records+4*160);D_800DBF94=&masks[5];masks[5+index]=row->mask;
 records[4*160+row->delta+0x72]=(u8)row->kind;
 for(i=0;i<3;i++)for(j=0;j<9;j++)seqs[i]->bytes[j]=(u8)(j*19+i*37+row->seed);
 equal_or_save(1);called=error=0;}
void func_15169260(void *queue,s32 mode,s32 payload,u8 command){u32 j;void *expected=row->actor<0?0:&D_800CC2D0[row->actor];
 if(queue!=&D_800A5770||mode!=2||called++||command!=row->command){error=1;return;}
 if(command==0x35){MapPacket131F30 *p=(MapPacket131F30*)payload;int k=0xF9-(int)row->kind;
  if(p->length!=9||p->actor!=expected){error=2;return;}
  for(j=0;j<9;j++)if(p->sequence[j]!=(u8)(j*19+k*37+row->seed))error=3;
 }else if(command==0x38){if(*(struct127**)payload!=expected)error=4;}else error=5;
}
void func_151494E0(s32 payload,u8 command){func_15169260(&D_800A5770,2,payload,command);}
static int run(void){u32 i;for(i=0;i<sizeof(rows)/sizeof(rows[0]);i++){row=&rows[i];setup();func_15104A80((struct131*)(records+4*160+row->delta));
 if(error||called!=(row->command!=0)||!equal_or_save(0))return 1;}return 0;}
'''.replace('ROWS','\n'.join(rows))
    changes={
        'last_slot':('i < 25','i < 24'),
        'inactive_selection':('interaction_state != 0','interaction_state == 0'),
        'wrong_bit':('1U << i','1U << ((i + 1) & 31)'),
        'record_stride':('/ 0xA0','/ 0xA4'),
        'packet_length':('packet.length = 9','packet.length = 8'),
        'sequence_source':('first = D_800A2380','first = D_800A238C'),
        'actor_command':('0x38);','0x39);'),
        'last_actor':('i < 25 && actor == 0','i < 25'),
        'null_pointer_payload':('actorOnly = actor','actorOnly = 0'),
    }
    controls={n:source.FRAGMENT.replace(a,b)for n,(a,b)in changes.items()};assert all(v!=source.FRAGMENT for v in controls.values())
    profiles=[]
    for opt in('-O0','-O2','-O3'):
        codes={}
        for name,body in[('selected',source.FRAGMENT),*controls.items()]:
            path=out/('native'+opt+'-'+name+'.c');exe=path.with_suffix('');path.write_text(prelude+body+harness+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)'))
            result=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
            if result.returncode or result.stdout or result.stderr:raise ValueError(result.stdout+result.stderr)
            result=subprocess.run([str(exe)],capture_output=True,timeout=45);assert(result.returncode==0)==(name=='selected'),(opt,name,result.returncode,result.stderr[:200]);codes[name]=result.returncode
        profiles.append(dict(profile=opt,cases=len(rows),effective_source_controls=len(controls),exit_codes=codes,UBSan=True,strict_aliasing=True))
    return dict(profiles=profiles,actual_SDK32_types=True,original_C_wrapper=True,complete_public_byte_snapshots=True,all_byte_kinds=True)
