"""Independent bounded SDK32 native model, with semantic negative controls."""
import json,subprocess
from tools.experiments import game_descriptor_record_151a7950_match as p
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def main():
 source=(p.out/'selected-source.c').read_text()
 a=source.index('s32 func_151A7950('); b=source.index('\n\ns32 func_151A7A90',a)
 selected=source[a:b]
 controls={
  'allocator_kind':('0x2D, parameter','0x2C, parameter'),
  'allocator_size':('+ 0x80u','+ 0x7Cu'),
  'allocator_mode':('1, mode, 1','1, mode ^ 1, 1'),
  'copy_size':('source, 0x50','source, 0x4C'),
  'end_pointer':('* 24;','* 20;'),
  'initial_zero':('+ 4) = 0.0f','+ 4) = 1.0f'),
  'last_one':('- 16) = 1.0f','- 16) = 0.0f'),
  'zero_size':('0x6C, 0x10','0x6C, 0x0C'),
  'derived_value':('<< 6) + 0x140u','<< 6) + 0x144u'),
 }
 code='''#include <ultra64.h>\n#include <string.h>\n'''+r'''
 _Static_assert(sizeof(void*)==4 && sizeof(s32)==4,"SDK32");
 static u32 storage[128], expected_storage[128], source_storage[64], expected_source_storage[64];
 static u8 *record=(u8*)storage,*expected=(u8*)expected_storage,*data=(u8*)source_storage,*expected_data=(u8*)expected_source_storage;
 static s32 scenario_alloc,scenario_count,scenario_mutation,scenario_mode,bad,calls;
 u8 *func_15167A68(s32 kind,s32 parameter,s32 bytes,s32 flag,s32 mode,s32 tail){
  if(calls++!=0 || kind!=0x2d || (u32)parameter!=0x87654321u || (u32)bytes!=(u32)(0x40+scenario_count*24+0x80) || flag!=1 || mode!=(scenario_mode&255) || tail!=1)bad=1;
  if(scenario_mutation==1)*(s16*)(data+2)=1;
  return scenario_alloc?record:0;
 }
 void *memcpy(void *d,const void *s,size_t size){u32 i;u8 *dst=d;const u8 *src=s;
  if(calls++!=1 || dst!=record+0x10 || src!=data || size!=0x50)bad=1;
  for(i=0;i<size;i++)dst[i]=src[i];
  if(scenario_mutation==2)*(s16*)(data+2)=2;
  return d;
 }
 void bzero(void *d,int size){int i;u8 *dst=d;
  if(calls++!=2 || dst!=record+0x6c || size!=0x10)bad=1;
  for(i=0;i<size;i++)dst[i]=0;
 }
 '''
 for name,text in {'selected':selected,**{n:selected.replace(x,y,1) for n,(x,y) in controls.items()}}.items():
     if name!='selected': assert text!=selected,name
     code+='\n'+text.replace(p.NAME,'test_'+name,1)+'\n'
 code+=r'''
 typedef s32(*Test)(u8*,s32,u8,s32);
 static int check(Test fn){int alloc,count,mutation,mode,i,k;u32 v;u8 *last;
  for(alloc=0;alloc<2;alloc++)for(count=-1;count<=3;count++)for(mutation=0;mutation<3;mutation++)for(mode=0;mode<2;mode++){
   scenario_alloc=alloc;scenario_count=count;scenario_mutation=mutation;scenario_mode=mode?511:0;bad=calls=0;
   for(i=0;i<512;i++)record[i]=expected[i]=(u8)(i*29+0x5a);
   for(i=0;i<256;i++)data[i]=expected_data[i]=(u8)(i*29+0x5a);
   *(s16*)(data+2)=*(s16*)(expected_data+2)=(s16)count;
   v=(u32)fn(data,0x40,(u8)scenario_mode,(s32)0x87654321u);
   if(bad || calls!=(alloc?3:1) || v!=(alloc?(u32)record:0))return 1;
   if(mutation==1)*(s16*)(expected_data+2)=1;
   if(alloc){
    for(i=0;i<0x50;i++)expected[0x10+i]=expected_data[i];
    if(mutation==2)*(s16*)(expected_data+2)=2;
    k=*(s16*)(expected_data+2);
    *(u8**)(expected+0x64)=expected+0x80;
    *(u8**)(expected+0x60)=expected+0x80+k*24;
    *(u32*)(expected+0x68)=0;
    for(i=0;i<3;i++)*(u32*)(expected+0x80+4*i)=0;
    last=expected+0x80+k*24-24;
    *(u32*)(last+0)=0;*(u32*)(last+4)=0;*(u32*)(last+8)=0x3f800000;
    for(i=0;i<16;i++)expected[0x6c+i]=0;
    *(u32*)(expected+0x7c)=(u32)((s32)*(s16*)(expected+0x12)*64+0x140);
    if(*(u8**)(record+0x60)!=record+0x80+k*24 || *(u8**)(record+0x64)!=record+0x80)return 1;
   }
   for(i=0;i<512;i++)if((!alloc || i<0x60 || i>=0x68) && record[i]!=expected[i])return 1;
   for(i=0;i<256;i++)if(data[i]!=expected_data[i])return 1;
  }
  return 0;
 }
 static int run(void){if(check(test_selected))return 10;
 '''
 for i,name in enumerate(controls):code+='if(!check(test_'+name+'))return '+str(20+i)+';\n'
 code+='return 0;}\n'+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)')
 src=p.out/'native.c';src.write_text(code);reports={}
 for opt in ('-O0','-O2','-O3'):
     exe=p.out/('native'+opt)
     v=subprocess.run(native_command(opt)+['-fno-builtin',str(src),'-o',str(exe)],cwd=p.root,capture_output=True,text=True)
     assert v.returncode==0 and not v.stdout and not v.stderr,(opt,v.stdout,v.stderr)
     v=subprocess.run([str(exe)],capture_output=True)
     assert v.returncode==0,(opt,v.returncode,v.stderr)
     reports[opt]=dict(cases=60,negative_controls=len(controls),UBSan=True)
 report=dict(profiles=reports,helpers_modeled=True,overlapping_copy_excluded=True,bounded_backing_arrays=True,source_installed=False,byte_exact=False)
 (p.out/'native.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);return report
