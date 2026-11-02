"""Typed 32-bit calls on finite table-domain inputs, with effective controls."""
from pathlib import Path
import json, struct, subprocess

def qualify(root, output, source, oracle):
    tables = [(output/'retail-table.bin').read_bytes(), struct.pack('>256H', *[(i*40503+0xFEDC)&65535 for i in range(256)])]
    values = oracle.corpus()
    controls = {
        'selected': source,
        'missing-sign': source.replace('return -base;', 'return base;'),
        'signed-table': source.replace('base = D_80098E00[index];', 'base = (short)D_80098E00[index];'),
        'missing-fraction': source.replace('* fraction)', '* 1.0f)').replace('    f32 fraction;\n', '').replace('    fraction = scaled - (f32)index;\n', ''),
        'early-endpoint': source.replace('index < 255', 'index < 254'),
        'wrong-divisor': source.replace('/ 65536.0f', '/ 65535.0f'),
        'wrong-endpoint': source.replace(': D_80099010', ': 0.0f'),
        'stub': source[:source.index('{')+1]+'return 0.0f; }\n',
    }
    assert all(v != source for k,v in controls.items() if k != 'selected')
    prefix = 'typedef unsigned int u32;typedef int s32;typedef unsigned short u16;typedef float f32;\n#define fabsf __builtin_fabsf\nu16 D_80098E00[256];f32 D_8009900C,D_80099010,D_80099014;\n'
    prefix += 'static const u32 inputs[]={'+','.join('0x%Xu'%v for v in values)+'};\n'
    prefix += 'static const u16 tables[2][256]={'+','.join('{'+','.join(str(v) for v in struct.unpack('>256H',t))+'}' for t in tables)+'};\n'
    prefix += 'static const u32 expected[2][%d]={'%len(values)+','.join('{'+','.join('0x%Xu'%oracle.reference(v,t) for v in values)+'}' for t in tables)+'};\n'
    suffix = '''
static f32 (* volatile call)(f32) = func_150488C8;
int run(void){
 union{u32 u;f32 f;} in,out,c;u32 i,j;
 if(sizeof(void*)!=4||sizeof(u16)!=2||sizeof(f32)!=4)return 9;
 c.u=0x437FFFFFu;D_8009900C=c.f;c.u=0x477FFF00u;D_80099010=c.f;c.u=0x3FC90FDBu;D_80099014=c.f;
 for(j=0;j<2;j++){
  for(i=0;i<256;i++)D_80098E00[i]=tables[j][i];
  for(i=0;i<sizeof(inputs)/sizeof(inputs[0]);i++){in.u=inputs[i];out.f=call(in.f);if(out.u!=expected[j][i])return 1;}
  for(i=0;i<256;i++)if(D_80098E00[i]!=tables[j][i])return 8;
 }
 return 0;
}
void _start(void){int status=run();__asm__ volatile("int $0x80"::"a"(1),"b"(status):"memory");__builtin_unreachable();}
'''
    results=[]
    for opt in ('-O0','-O2','-O3'):
        for label, body in controls.items():
            p=output/('native-'+label+'-'+opt[1:]+'.c');p.write_text(prefix+body+suffix);binary=p.with_suffix('.bin')
            command=['cc','-m32',opt,'-std=c11','-msse2','-mfpmath=sse','-mstackrealign','-fno-builtin','-ffp-contract=off','-fexcess-precision=standard','-ffreestanding','-static','-fno-stack-protector','-fno-pie','-no-pie','-nostdlib','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-unused-parameter','-fsanitize=undefined,float-cast-overflow','-fsanitize-undefined-trap-on-error','-Wl,-e,_start','-o',str(binary),str(p)]
            q=subprocess.run(command,cwd=root,capture_output=True,text=True);assert q.returncode==0,(label,q.stderr)
            q=subprocess.run([str(binary)],capture_output=True,timeout=20);assert q.returncode==(0 if label=='selected' else 1),(opt,label,q.returncode,q.stdout.hex(),q.stderr)
            results.append(dict(profile=opt,label=label,status=q.returncode))
    report=dict(success=True,inputs_per_table=len(values),tables=2,profiles=['O0','O2','O3'],effective_controls_per_profile=7,typed_function_pointer=True,stack_realigned=True,UBSan=True,finite_domain='abs(input) <= 1',NaN_FCSR_hardware_not_qualified=True,results=results)
    (output/'private-native-v6.json').write_text(json.dumps(report,indent=2)+'\n');return report
