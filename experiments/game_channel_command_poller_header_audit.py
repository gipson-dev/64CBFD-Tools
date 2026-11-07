"""Actual header-consumer recipes and closed object/whole-image accounting.

The frozen source/object inventory belongs to the consumer's ignored packet.
Debug and auxiliary-symbol changes are recorded, named relocations are rebuilt,
and the linked image is compared literally, with no excluded byte ranges.
"""
import argparse,collections,concurrent.futures,json,re,shlex,struct,subprocess
from pathlib import Path
from tools.experiments import game_channel_command_poller_match as match
from tools.experiments.game_actor_state_tick_integration import same_functions,symbol_rows
from tools.experiments.game_record_address_relocator_match import dependent_sections


def audit_owner(old,new,target=False,qualified=None):
    count=same_functions(old,new,(match.FUNCTION,)if target else())
    if target:
        if new.read_bytes()!=qualified.read_bytes():raise ValueError('Actual target recipe differs from qualified complete owner')
        return dict(functions_fixed=count,identical=False,changed_sections=[dict(section='qualified target body, size and seven bindings')],symbol_changes=dict(removed=[],added=[]))
    a,b=dependent_sections(old.read_bytes()),dependent_sections(new.read_bytes())
    if a.keys()!=b.keys():raise ValueError('Header consumer section set changed')
    def symbols(parts):
        raw=parts['.symtab'][1];strings=parts['.strtab'][1];rows=[]
        for i in range(len(raw)//16):
            f=struct.unpack_from('>IIIBBH',raw,16*i);n=strings[f[0]:].split(b'\0',1)[0].decode();rows.append((n,f))
        return rows
    old_symbols,new_symbols=symbols(a),symbols(b);changes=[]
    for n,(h,data)in a.items():
        hh,dd=b[n]
        if data==dd and h==hh:continue
        if n.startswith('.rel.'):
            if not(h[1]==hh[1]==9 and h[5:]==hh[5:]):raise ValueError('Header relocation section shape changed')
            expected=bytearray()
            for i in range(0,len(data),8):
                offset,word=struct.unpack_from('>II',data,i);name,fields=old_symbols[word>>8];indices=[j for j,(nn,ff)in enumerate(new_symbols)if nn==name and ff[1:]==fields[1:]]
                if len(indices)!=1:raise ValueError('Header relocation lost its unique named definition')
                expected.extend(struct.pack('>II',offset,indices[0]<<8|word&255))
            if bytes(expected)!=dd:raise ValueError('Header named relocation changed')
        elif n not in('.mdebug','.symtab','.strtab'):
            if tuple(h[i]for i in(0,1,2,3,5,6,7,8,9))!=tuple(hh[i]for i in(0,1,2,3,5,6,7,8,9))or data!=dd:raise ValueError('Header loaded/ordinary section changed: '+n)
        elif h[2]&2 or hh[2]&2:
            raise ValueError('Header metadata unexpectedly allocated')
        if data!=dd:changes.append(dict(section=n,before_size=len(data),after_size=len(dd),before_sha256=match.sha(data),after_sha256=match.sha(dd)))
    aa=collections.Counter((n,*f[1:])for p,n,f,s in symbol_rows(old.read_bytes()));bb=collections.Counter((n,*f[1:])for p,n,f,s in symbol_rows(new.read_bytes()))
    return dict(functions_fixed=count,identical=old.read_bytes()==new.read_bytes(),changed_sections=changes,symbol_changes=dict(removed=list((aa-bb).elements()),added=list((bb-aa).elements())))


def audit_phase(root,out,production=False):
    root,out=Path(root),Path(out);scope=json.loads((out/'header-active-scope.json').read_text());manifest=json.loads((out/'header-input-sha256.json').read_text());results=[]
    allowed={match.SOURCE,match.candidate.INIT,match.candidate.HEADER,match.ELF,'conker/build/conker.us.bin','graphify-out/graph.json'}|{'conker/build/'+n+'.o'for n in scope['sources']}
    for n,h in manifest.items():
        if match.sha((out/'header-frozen'/n).read_bytes())!=h:raise ValueError('Header frozen input changed: '+n)
        if (not production or n not in allowed)and match.sha((root/n).read_bytes())!=h:raise ValueError('Header protected phase input changed: '+n)
    qualified=out/'match-qualified-owner/generated_AD6B0.c.o'
    for source in scope['sources']:
        old=out/'header-frozen/conker/build'/(source+'.o');new=(root/'conker/build'if production else out/'header-shadow')/(source+'.o')
        r=audit_owner(old,new,source=='src/game/generated_AD6B0.c',qualified)
        results.append(dict(source='conker/'+source,object='conker/build/'+source+'.o',shadow=new.relative_to(root).as_posix(),before_sha256=match.sha(old.read_bytes()),after_sha256=match.sha(new.read_bytes()),**r))
    if production:image=root/match.ELF
    else:
        ld=(out/'header-frozen'/match.LINKER).read_text()
        for r in results:
            old=r['object'].removeprefix('conker/');new=r['shadow'].removeprefix('conker/')
            if old not in ld:raise ValueError('Header owner absent from active linker: '+old)
            ld=ld.replace(old,new)
        p=out/'header-linked';p.mkdir(exist_ok=True);(p/'conker.ld').write_text(ld)
        image=p/'conker.us.elf'
        subprocess.run(['mips-linux-gnu-ld','-T',str((p/'conker.ld').relative_to(root/'conker')),'-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt','-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch','-o',str(image.relative_to(root/'conker'))],cwd=root/'conker',capture_output=True,check=True)
    before=(out/'header-frozen'/match.ELF).read_bytes();truth=(root/match.ROM_IMAGE).read_bytes()[match.ROM:match.ROM+288];delta=match.strict_image(before,image.read_bytes(),truth)
    result=dict(owners=len(results),all_loaded_code_data_and_bindings_fixed_except_Game_target=True,strict_full_image_changed_bytes=delta,strict_exclusions=0,qualified_elf_sha256=match.sha(image.read_bytes()),records=results)
    (out/('header-production-qualification.json'if production else'header-shadow-qualification.json')).write_text(json.dumps(result,indent=2)+'\n');return result


def build_shadow(root,out):
    """Reproduce all inventoried actual Make commands, without touching live inputs."""
    root,out=Path(root),Path(out);conker=root/'conker';scope=json.loads((out/'header-active-scope.json').read_text());shadow=out/'header-shadow';overlay=out/'header-overlay';overlay.mkdir(exist_ok=True);(overlay/'functions.h').write_bytes((out/'qualified-functions.h').read_bytes())
    replacements={'src/init_12560.c':(out/'qualified-init_12560.c').relative_to(conker).as_posix(),'src/game/generated_AD6B0.c':(out/'proposed-owner.c').relative_to(conker).as_posix()}
    def one(source):
        target=(shadow/(source+'.o')).relative_to(conker).as_posix();(conker/target).parent.mkdir(parents=True,exist_ok=True)
        plan=subprocess.run(['make','-n','-B','-o','Makefile','BUILD_DIR='+shadow.relative_to(conker).as_posix(),target],cwd=conker,capture_output=True,text=True,check=True);label=source.replace('/','_');(out/('header-plan-'+label+'.log')).write_text(plan.stdout+plan.stderr);diagnostics=[]
        for line in plan.stdout.replace('\\\n','').splitlines():
            args=shlex.split(line)
            if not args or args[0]=='rm':continue
            if args[0]not in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'):raise ValueError('Unknown header Make command')
            args=[replacements.get(x,x)for x in args]
            if args[0]=='../ido/ido5.3_recomp/cc':args[1:1]=['-I',overlay.relative_to(conker).as_posix()]
            redirect=None
            if '>'in args:
                if args[-2]!='>'or args.count('>')!=1:raise ValueError('Unknown header Make redirect')
                redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
            r=subprocess.run(args,cwd=conker,capture_output=True,text=True)
            if r.returncode:raise ValueError((source,args,r.stdout,r.stderr))
            diagnostics.append(r.stdout+r.stderr if redirect is None else r.stderr)
            if redirect is not None:redirect.write_text(r.stdout)
        (out/('header-diagnostics-'+label+'.log')).write_text(''.join(diagnostics))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(one,scope['sources']))
    return audit_phase(root,out)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--rebuild',action='store_true');p.add_argument('--production',action='store_true');a=p.parse_args();root=match.candidate.ROOT;out=root/match.BUILD
    if a.rebuild and a.production:p.error('Choose isolated rebuild or production audit')
    result=build_shadow(root,out)if a.rebuild else audit_phase(root,out,a.production)
    print(json.dumps({k:v for k,v in result.items()if k!='records'},indent=2))
