from pathlib import Path
import hashlib,json,re,subprocess,sys
from tools.experiments import game_audio_command_dispatch_1509e730_recovery as recovery
root=recovery.ROOT;out=recovery.OUT
def run():
    where=out/'native';where.mkdir(exist_ok=True)
    from tools.tests.test_game_projected_packet_draw import native_command
    owner=(out/'qualified-source-screen/selected-owner.c').read_text()
    assert hashlib.sha256(owner.encode()).hexdigest()==json.loads((out/'source-reconstruction.json').read_text())['complete_source_sha256']
    assert owner.count('#include <ultra64.h>')==1 and owner.count('extern s32 D_800D3840;')==1
    owner=owner.replace('#include <ultra64.h>','').replace('extern s32 D_800D3840;','')
    template=Path(__file__).with_name('game_audio_command_dispatch_1509e730_native.c.in').read_text();assert template.count('@@OWNER@@')==1
    variants={'selected':owner,'wrong-mask':owner.replace('handle & 0xFFF','handle & 0xFF'),
     'wrong-version-three':owner.replace('if (D_800D3840 == 3) enabled','if (D_800D3840 == 4) enabled'),
     'wrong-legacy-fade':owner.replace('packet[3], 60)','packet[3], 0)'),
     'missing-secondary-handle-mask':owner.replace('packet[4] & 0xFFF','packet[4]'),
     'swapped-command-labels':owner.replace('case 2:','case 99:').replace('case 5:','case 2:').replace('case 99:','case 5:'),
     'discarded-helper-result':re.sub(r'return (func_1000E46C\([^;]+\));',r'(void)\1; return 1;',owner)}
    report={'valid':[],'rejected':{}}
    for label,source in variants.items():
        if label!='selected':assert source!=owner,label
        for optimization in(('-O0','-O2','-O3')if label=='selected'else('-O2',)):
            name=label+optimization;file=where/(name+'.c');exe=where/name
            file.write_text(template.replace('@@OWNER@@',source))
            command=native_command(optimization)+['-fstrict-aliasing','-o',str(exe),str(file)]
            compile_result=subprocess.run(command,cwd=root,capture_output=True,text=True)
            assert compile_result.returncode==0 and not compile_result.stdout and not compile_result.stderr,compile_result.stderr
            run=subprocess.run([str(exe)],cwd=root,capture_output=True,text=True)
            if label=='selected':
                assert run.returncode==0 and run.stdout.strip()=='00003480 00000000 00000000 00000000'and not run.stderr,(run.returncode,run.stdout,run.stderr)
                report['valid'].append(dict(optimization=optimization,cases=13440,strict_aliasing=True,UBSan=True))
            else:
                assert run.returncode==12 and not run.stdout and len(run.stderr.strip())==35,(label,run.returncode,run.stdout,run.stderr)
                report['rejected'][label]=dict(exit_code=run.returncode,observation=run.stderr.strip())
    report.update(complete_owner_source=True,source_installed=recovery.installed(),matching_credit=0,
     limits='Defined SDK32 storage uses one backing array for legal global/packet aliases; no native stack/frame or hardware claim.')
    (out/'native-qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return report
