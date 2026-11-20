"""Replay real owner recipes, deriving GLOBAL_ASM membership from the proposal.

Only a historical proposal whose membership differs from the live source needs
the Make command-line variable override. Current installed sources use the
unmodified natural recipe. The consumer source/Makefile are never changed here.
"""
from pathlib import Path
import json,re,shlex,subprocess
from tools.experiments.game_actor_state_tick_integration import same_functions
from tools.tests.game_owner_pool import normalized_pools

def actual_Make(root,out,wanted,compact,guards,source,object_path,selected,label,functions):
    conker=root/'conker';proposal=out/(label+'-proposed-source.c');proposal.write_text(selected)
    shadow=out/('make-'+label);target=shadow/Path(object_path).relative_to('conker/build');target.parent.mkdir(parents=True,exist_ok=True)
    mixed='#pragma GLOBAL_ASM('in selected
    live_mixed='#pragma GLOBAL_ASM('in(root/source).read_text()
    command=['make','-n','-B','BUILD_DIR='+shadow.relative_to(conker).as_posix()]
    if mixed!=live_mixed:command.append('GLOBAL_ASM_C_FILES='+source.removeprefix('conker/')if mixed else'GLOBAL_ASM_C_FILES=')
    command.append(target.relative_to(conker).as_posix())
    plan=subprocess.run(command,cwd=conker,capture_output=True,text=True,check=True)
    (out/(label+'-Make-plan.txt')).write_text(plan.stdout+plan.stderr);commands=[]
    diagnostics=lambda text:re.sub(r'\S+\.c, line \d+:','<owner>:',text)
    for line in plan.stdout.replace('\\\n','').splitlines():
        args=shlex.split(line)
        if not args or args[0]=='rm':continue
        assert args[0]in('../ido/ido5.3_recomp/cc','python3','mips-linux-gnu-as'),args
        args=[proposal.relative_to(conker).as_posix()if a==source.removeprefix('conker/')else guards.relative_to(conker).as_posix()if a=='retail_word_patches.us.csv'else a for a in args]
        redirect=None
        if '>'in args:
            assert args.count('>')==1 and args[-2]=='>'
            redirect=(conker/args[-1]).resolve();redirect.relative_to(shadow.resolve());args=args[:-2]
        q=subprocess.run(args,cwd=conker,capture_output=True,text=True);assert q.returncode==0,q.stdout+q.stderr
        if args[0]=='../ido/ido5.3_recomp/cc':
            assert args.count('-O2')==args.count('-g3')==1
            expected=out/('after-diagnostics.txt'if label=='target'else label+'-after-diagnostics.txt')
            assert diagnostics(q.stdout+q.stderr)==diagnostics(expected.read_text())
        else:assert not q.stderr and(not q.stdout or redirect is not None),q.stdout+q.stderr
        if redirect:redirect.write_text(q.stdout)
        commands.append(args)
    assert len(commands)==(5 if mixed else 3),(len(commands),mixed)
    assert target.read_bytes()==wanted.read_bytes(),'Actual Make object differs'
    assert same_functions(compact,Path(str(target)+'.compact'))==functions
    assert normalized_pools(compact)==normalized_pools(Path(str(target)+'.compact'))
    (out/(label+'-Make-commands.json')).write_text(json.dumps(commands,indent=2)+'\n')
    return dict(commands=len(commands),padded_object_equal=True,profile='existing O2/g3',mixed_GLOBAL_ASM_recipe=mixed,
        natural_live_recipe=mixed==live_mixed,proposal_membership_override=mixed!=live_mixed)
