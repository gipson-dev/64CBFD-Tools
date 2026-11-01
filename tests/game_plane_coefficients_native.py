"""Native32 typed aggregate plane coefficients against rounded reference fixtures."""
import json,subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def harness(selected,rows,reference):
 head,body=selected.split('/* Publish',1);body='/* Publish'+body
 bad=dict(nx_sign=body.replace('aby * acz - abz * acy','aby * acz + abz * acy'),
  ny_sign=body.replace('-abx * acz','abx * acz'),nz_sign=body.replace('abx * acy - aby * acx','abx * acy + aby * acx'),
  wrong_point=body.replace('points.a[0] - points.b[0]','points.a[0] - points.c[0]'),
  wrong_dot=body.replace('nx * points.a[0]','nx * points.b[0]'),
  omit_publish=body.replace('D_800CC214 = ny;','D_800CC214 = 0.0f;'),
  dot_association=body.replace('nx * points.a[0] + ny * points.a[1] + nz * points.a[2]','nx * points.a[0] + (ny * points.a[1] + nz * points.a[2])'))
 assert len(set(bad.values()))==7 and all(v!=body for v in bad.values())
 code=head+'\n'.join(v.replace('func_15049350','candidate_'+str(i))for i,v in enumerate([body,*bad.values()]))
 code+='\nf32 D_800CC210,D_800CC214,D_800CC218,D_800CC21C;\n'
 code+='typedef struct {u32 words[9];u32 expected[4];} Case;\nstatic const Case cases[]={\n'
 code+=',\n'.join('{{%s},{%s}}'%(','.join('0x%Xu'%x for x in words),','.join('0x%Xu'%x for x in reference(words)))for words in rows)+'\n};\n'
 code+=r'''
typedef char Size[sizeof(PlanePoints)==36 && __builtin_offsetof(PlanePoints,b)==12 && __builtin_offsetof(PlanePoints,c)==24?1:-1];
typedef union {u32 u;f32 f;} Word;
typedef struct {u32 before;PlanePoints points;u32 after;} World;
typedef void (*Candidate)(PlanePoints);
'''
 code+='static Candidate candidates[]={'+','.join('candidate_'+str(i)for i in range(8))+'};\n'
 code+=r'''
static int run(void){u32 i,j,k,killed=0;World w,original;Word x;u32 observed[4];int same;
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  w.before=0x12345678;w.after=0x87654321;
  for(k=0;k<9;k++){x.u=cases[i].words[k];if(k<3)w.points.a[k]=x.f;else if(k<6)w.points.b[k-3]=x.f;else w.points.c[k-6]=x.f;}
  original=w;
  for(j=0;j<8;j++){
   x.u=0xA5A5A5A5;D_800CC210=D_800CC214=D_800CC218=D_800CC21C=x.f;
   candidates[j](w.points);
   x.f=D_800CC210;observed[0]=x.u;x.f=D_800CC214;observed[1]=x.u;x.f=D_800CC218;observed[2]=x.u;x.f=D_800CC21C;observed[3]=x.u;
   same=1;for(k=0;k<4;k++)if(observed[k]!=cases[i].expected[k])same=0;
   for(k=0;k<sizeof(World);k++)if(((u8*)&w)[k]!=((u8*)&original)[k])return 12;
   if(!same){if(!j)return 10;killed|=1u<<(j-1);}
  }
 }
 return killed==127u?0:11;
}
'''+START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
 return code,list(bad)

def run_native(root,out,selected,rows,reference):
 code,names=harness(selected,rows,reference);path=out/'native-plane.c';path.write_text(code);result=[]
 for profile in ('-O0','-O2','-O3'):
  exe=out/('native-plane'+profile);q=subprocess.run(native_command(profile)+['-o',str(exe),str(path)],cwd=root,capture_output=True,text=True)
  (out/('native-plane'+profile+'-compile.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,(profile,q.stdout,q.stderr)
  q=subprocess.run([str(exe)],cwd=root,capture_output=True);assert q.returncode==0,(profile,q.returncode,q.stderr)
  result.append(dict(profile=profile,UBSan=True,baseline_cases=len(rows),negative_controls=names,all_controls_effective=True))
 report=dict(native32=True,aggregate_size_and_offsets_asserted=True,input_and_canaries_unchanged=True,reference='independent rounded Python binary32 fixtures',hardware_FCSR_claimed=False,rows=result)
 (out/'native-plane.json').write_text(json.dumps(report,indent=2)+'\n');return report
