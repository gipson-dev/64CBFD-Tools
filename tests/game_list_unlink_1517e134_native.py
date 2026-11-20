"""Defined native32 C lists, checked against independent index-list reference."""
import json,subprocess
from tools.experiments import game_list_unlink_1517e134_match as s
from tools.experiments.game_list_render_1517e28c_recovery import RECORD
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def harness(body):
    return '#include <ultra64.h>\n'+RECORD+r'''
static struct Slot {ListRecord1AB530 record;u8 tail[12];} nodes[14];
ListRecord1AB530 *D_800DDD64;
static u32 links[14],head,mode,target,called,error,expectedCalled;
static u32 identity(const void*p){u32 i;if(!p)return 0;for(i=0;i<14;i++)if(p==&nodes[i].record)return i+1;return 0xFFFFFFFFu;}
__attribute__((noinline,noipa)) void func_10004074(void*p){
 u32 i;called++;
 if(identity(p)!=target+1||!expectedCalled||identity(D_800DDD64)!=head)error=1;
 for(i=0;i<14;i++)if(identity(nodes[i].record.next)!=links[i])error=1;
 if(mode==1){D_800DDD64=&nodes[13].record;nodes[target].record.next=0;}
 if(mode==2){D_800DDD64=0;nodes[target].record.next=&nodes[13].record;}
}
BODY
static int run(void){u32 n,i,context,iterations=0;void*arg;
 if(sizeof(void*)!=4||sizeof(ListRecord1AB530)!=52||sizeof(struct Slot)!=64||__builtin_offsetof(ListRecord1AB530,next)!=36)return 10;
 for(n=0;n<13;n++)for(target=0;target<=n;target++)for(mode=0;mode<3;mode++)for(context=0;context<4;context++){
  error=called=0;head=n?1:0;expectedCalled=target<n;
  for(i=0;i<14;i++){links[i]=i+1<n?i+2:0;nodes[i].record.next=links[i]?&nodes[links[i]-1].record:0;nodes[i].record.state28=0x1234;}
  D_800DDD64=head?&nodes[head-1].record:0;
  if(expectedCalled){if(target==0)head=links[0];else links[target-1]=links[target];}
  arg=context==0?0:context==1?&nodes[target].record:context==2?&nodes[0].record:&nodes[13].record;
  func_1517E134(&nodes[target].record,arg);
  if(called!=expectedCalled||error)return 11;
  if(expectedCalled&&mode==1){head=14;links[target]=0;}
  if(expectedCalled&&mode==2){head=0;links[target]=14;}
  if(identity(D_800DDD64)!=head)return 12;
  for(i=0;i<14;i++)if(identity(nodes[i].record.next)!=links[i]||nodes[i].record.state28!=0x1234)return 12;
  iterations++;
 }return iterations==1092?0:13;}
'''.replace('BODY',body)+START

def run():
    where=s.OUT/'native';where.mkdir(exist_ok=True);body=s.SPEC['body'];valid=[];rejected={}
    def execute(name,body,opt):
        p=where/(name+'.c');p.write_text(harness(body));exe=p.with_suffix('')
        q=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(p),'-o',str(exe)],cwd=s.ROOT,capture_output=True,text=True)
        assert q.returncode==0,q.stdout+q.stderr
        return subprocess.run([str(exe)],timeout=15,capture_output=True).returncode
    for opt in('-O0','-O2','-O3'):
        result=execute(opt[1:],body,opt);assert result==0,(opt,result)
        valid.append(dict(optimization=opt,cases=1092,UBSan=True,strict_aliasing=True))
    controls={'wrong-free-argument':body.replace('func_10004074(target);','func_10004074(unusedActor);'),
        'missing-head-unlink':body.replace('D_800DDD64 = ((ListRecord1AB530 *)target)->next;','D_800DDD64 = D_800DDD64;'),
        'wrong-head-predicate':body.replace('target == D_800DDD64','target != D_800DDD64')}
    for name,other in controls.items():
        assert other!=body,name
        code=execute(name,other,'-O2');assert code in(11,12),(name,code);rejected[name]=code
    report=dict(valid=valid,rejected=rejected,compatible_nonnull_targets_only=True)
    (where/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report
