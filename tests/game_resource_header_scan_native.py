"""Reuse the established complete-table fixture; require nine semantic negatives."""
from pathlib import Path
import json,subprocess
from tools.tests.test_game_texture_metadata_and_maintenance import GameTextureMetadataAndMaintenanceTests as Legacy
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def qualify(root,output,body):
 r,o=Path(root),Path(output)
 variants=[('baseline',body),('skip-alignment',body.replace('            source--;','            (void)source;')),('ignore-header-skip',body.replace('header = buffer + skip;','header = buffer;')),('missing-advance-skip',body.replace('amount = *length + skip;','amount = *length;')),('signed-length',body.replace('amount = *length + skip;','amount = *(s16 *)length + skip;'))]
 cached=body.replace('        amount = *length + skip;\n','').replace('        func_10004514(source, buffer, 16, 1);','        amount = *length + skip;\n        func_10004514(source, buffer, 16, 1);')
 variants.append(('cached-length-before-DMA',cached));variants.append(('wrong-byte-order',body.replace('header[2]','header[TEMP]').replace('header[3]','header[2]').replace('header[TEMP]','header[3]')))
 variants.append(('short-count',body.replace('+ 7762','+ 7761')));variants.append(('omit-free',body.replace('func_10004074(buffer);','(void)buffer;')))
 variants.append(('invented-null-gate',body.replace('    source = (u32)&D_1A37E0;','    if (buffer == NULL) return;\n    source = (u32)&D_1A37E0;')))
 assert len(set(v for _,v in variants))==10
 Legacy.setUpClass();reports=[]
 try:
  old=Legacy.bodies['func_15003570'];assert Legacy.fixture.count(old)==1
  run='''int run(void){int i,mode;
 for(mode=0;mode<2;mode++){
  reset();mutateLength=mode;func_15003570();
  if(error||allocations!=1||dmas!=7762||frees!=1||!fences())return 1;
  for(i=0;i<7762;i++)if(D_800B87A0[i]!=(u16)header_for(i)||D_80091D20[i]!=(mode?(u16)(i*17):length_for(i)))return 2;
 }
 reset();failHeader=1;func_15003570();return 99;}
 '''
  for opt in ('-O0','-O2','-O3'):
   controls=[]
   for index,(name,code)in enumerate(variants):
    program=Legacy.fixture.replace(old,code)+run+START.replace('void _start(void)','__attribute__((force_align_arg_pointer)) void _start(void)');p=o/('native12-'+opt[1:]+'-'+name);p.with_suffix('.c').write_text(program)
    q=subprocess.run(native_command(opt)+['-mstackrealign','-fno-strict-aliasing','-Wno-unused-function',str(p.with_suffix('.c')),'-o',str(p)],cwd=r,capture_output=True,text=True);assert q.returncode==0,(opt,name,q.stdout,q.stderr)
    q=subprocess.run([str(p)],capture_output=True,timeout=15)
    if index:assert q.returncode in(1,2,99),(opt,name,q.returncode,q.stderr);controls.append(name)
    else:assert q.returncode==0,(opt,q.returncode,q.stdout,q.stderr)
   reports.append(dict(profile=opt,complete_scans=2,records_per_scan=7762,entry_checks=15524,null_first_DMA_prefix=True,controls=controls,nine_controls_effective=True,UBSan=True,table_and_buffer_fences_checked=True,live_length_after_DMA=True,hardware_providers_mocked=True))
 finally:Legacy.doClassCleanups()
 return reports
