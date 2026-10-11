"""Screen complete lazy-loader exit shapes without changing installed inputs."""
import argparse
import hashlib
import json
from pathlib import Path

from tools.experiments import game_third_resource_loader_lifetime_candidates as lifetime

ENTRY,ROM,WORDS=lifetime.ENTRY,lifetime.ROM,lifetime.WORDS
FUNCTION,SOURCE,SYMBOLS=lifetime.FUNCTION,lifetime.SOURCE,lifetime.SYMBOLS
ORIGINAL=lifetime.QUALIFIED
QUALIFIED=ORIGINAL.replace('loaded = 2;\n        goto done;','return loaded = 2;').replace(
    '    loaded = 0;\ndone:', '    loaded = 0;\n    goto done;\ndone:')
SOURCE_SHA='52e22c65fca3a59f418c6589b84d9653e432e7343e1351d47b3fbf3353c38ae2'
GUARDS,OLD_BLOCK=lifetime.GUARDS,lifetime.NEW_BLOCK
GUARDS_SHA='0aea2b7a3d2d610fcb8c6f4fa02cac6922af82868a9b447c70ccdd16b6db35b4'
NEW_BLOCK=b'''generated_6A3D0,func_1503D774,0x078,0xAC6A0000,0x00001025,-,-,Normalize lazy-loader final independent status and publication schedule,,,false
generated_6A3D0,func_1503D774,0x07C,0x00001025,0xAC6A0000,-,-,Normalize lazy-loader final independent status and publication schedule,,,false
'''
target_rows=lifetime.target_rows


def install(before):
    if before.count(ORIGINAL)!=1 or hashlib.sha256(before.encode('ascii')).hexdigest()!=SOURCE_SHA:
        raise ValueError('stale third-loader status body or owner')
    return before.replace(ORIGINAL,QUALIFIED)


def install_guards(before):
    if hashlib.sha256(before).hexdigest()!=GUARDS_SHA or before.count(OLD_BLOCK)!=1:
        raise ValueError('stale third-loader status guard block')
    after=before.replace(OLD_BLOCK,NEW_BLOCK)
    assert len(target_rows(before))==4 and len(target_rows(after))==2
    return after


def historical_source(root):
    source=(root/SOURCE).read_text()
    if QUALIFIED not in source:
        assert source.count(ORIGINAL)==1 or source.count(lifetime.ORIGINAL)==1
        return source
    assert source.count(QUALIFIED)==1
    before=source.replace(QUALIFIED,ORIGINAL)
    assert hashlib.sha256(before.encode('ascii')).hexdigest()==SOURCE_SHA
    assert install(before)==source
    lifetime.require_current_slot(root)
    return before


def historical_guards(root):
    current=(root/GUARDS).read_bytes()
    if NEW_BLOCK not in current:
        assert current.count(OLD_BLOCK)==1 or current.count(lifetime.OLD_BLOCK)==1
        return current
    assert current.count(NEW_BLOCK)==1 and len(target_rows(current))==2
    before=current.replace(NEW_BLOCK,OLD_BLOCK)
    assert hashlib.sha256(before).hexdigest()==GUARDS_SHA
    assert install_guards(before)==current
    assert (root/SOURCE).read_text()==install(historical_source(root))
    lifetime.require_current_slot(root)
    return before


def compile_candidate(root,out,name,source=QUALIFIED,profile='owner'):
    return lifetime.compile_candidate(root,out,name,source,profile)


def body(kind='s32', shared=True, success_first=False, expression=False):
    request='loaded = (%s)func_1502B6BC(&output, 2, 0, 2, 0x11, identity);'%kind
    failure='        *slot = NULL;\n'
    success='        *slot = (struct124 *)loaded;\n        *slot = *(struct124 **)loaded;\n'
    if shared:
        failure+='        loaded = (%s)2;\n'%kind
        success+='        loaded = (%s)0;\n'%kind
        tail='    return (s32)loaded;'
    else:
        failure+='        return 2;\n'
        success+='        return 0;\n'
        tail=''
    if success_first:
        gate='    if (loaded != 0) {\n'+success+'    } else {\n'+failure+'    }\n'
    else:
        gate='    if (loaded == 0) {\n'+failure+'    } else {\n'+success+'    }\n'
    if expression:
        gate=gate.replace('if (loaded '+('!=' if success_first else '==')+' 0)',
            'if (('+request[:-1]+') '+('!=' if success_first else '==')+' 0)')
        request=''
    return '''s32 func_1503D774(s32 identity, %s loaded) {
    s32 output;
    struct124 **slot = &D_800D1C90[identity];

    if (*slot != NULL) {
        return 0;
    }

    %s
%s%s
}'''%(kind,request,gate,tail)


def candidates():
    yield 'installed',lifetime.QUALIFIED
    for kind in ('s32','u32','void *','struct124 *','u32 *'):
        tag=kind.replace(' ','').replace('*','p')
        for shared in (False,True):
            for success_first in (False,True):
                yield tag+('-shared' if shared else '-early')+('-success' if success_first else '-failure'),body(kind,shared,success_first)
        yield tag+'-inline-early',body(kind,False,False,True)
        casted=lifetime.QUALIFIED.replace('s32 loaded','%s loaded'%kind).replace(
            '(s32)func_1502B6BC','(%s)func_1502B6BC'%kind).replace('loaded = 2;','loaded = (%s)2;'%kind).replace(
            'loaded = 0;','loaded = (%s)0;'%kind).replace('return loaded;','return (s32)loaded;')
        yield tag+'-goto',casted
        yield tag+'-register-goto',casted.replace('%s loaded)'%kind,'register %s loaded)'%kind)
        yield tag+'-identity-status',casted.replace('loaded = (%s)2;'%kind,'identity = 2;').replace(
            'loaded = (%s)0;'%kind,'identity = 0;').replace('return (s32)loaded;','return identity;')
    for before,after,name in (
            ('return loaded;','return loaded & 2;','masked-status'),
            ('return loaded;','return loaded ? 2 : 0;','boolean-status'),
            ('return loaded;','return (u32)loaded;','unsigned-return'),
            ('return loaded;','return (s32)(void *)loaded;','pointer-return'),
            ('loaded = 2;\n        goto done;','return loaded = 2;','assigned-failure-return'),
            ('loaded = 0;\ndone:\n    return loaded;','done:\n    return loaded = 0;','negative-cleared-failure-status')):
        yield name,lifetime.QUALIFIED.replace(before,after)
    early=body('s32',False,False)
    yield 'return-result-plus-two',early.replace('return 2;','return loaded + 2;')
    yield 'assigned-early-status',early.replace('return 2;','return loaded = 2;').replace(
        '        return 0;\n    }','        return loaded = 0;\n    }')
    yield 'failure-comma',early.replace('*slot = NULL;\n        return 2;','return (*slot = NULL, 2);')
    yield 'labelled-early-success',early.replace('''    } else {
        *slot = (struct124 *)loaded;
        *slot = *(struct124 **)loaded;
        return 0;
    }''','''    }
    *slot = (struct124 *)loaded;
    *slot = *(struct124 **)loaded;
    return 0;''')
    selected=lifetime.QUALIFIED.replace('loaded = 2;\n        goto done;','return loaded = 2;')
    yield 'final-dead-label-removed',selected.replace('done:\n','')
    yield 'final-assigned-success-return',selected.replace('    loaded = 0;\ndone:\n    return loaded;',
        '    return loaded = 0;')
    yield 'final-constant-success-return',selected.replace('    loaded = 0;\ndone:\n    return loaded;',
        '    loaded = 0;\n    return 0;')
    yield 'final-comma-success-return',selected.replace('    *slot = *(struct124 **)loaded;\n    loaded = 0;\ndone:\n    return loaded;',
        '    return (*slot = *(struct124 **)loaded, loaded = 0);')
    yield 'final-reuse-header-word',selected.replace('    *slot = *(struct124 **)loaded;',
        '    loaded = *(s32 *)loaded;\n    *slot = (struct124 *)loaded;').replace('done:\n','')
    for kind in ('struct124 *','s32','u32'):
        tag=kind.replace(' ','').replace('*','p')
        for declaration in ('before','after'):
            extra='    %s first;\n'%kind
            shaped=selected.replace('    s32 output;',extra+'    s32 output;' if declaration=='before' else '    s32 output;\n'+extra.rstrip())
            tail='    first = *(%s *)loaded;\n    loaded = 0;\n    *slot = (struct124 *)first;\n    return loaded;'%kind
            shaped=shaped.replace('    *slot = *(struct124 **)loaded;\n    loaded = 0;\ndone:\n    return loaded;',tail)
            yield 'final-header-'+tag+'-'+declaration,shaped
    yield 'final-header-scoped',selected.replace('    *slot = *(struct124 **)loaded;\n    loaded = 0;\ndone:\n    return loaded;',
        '    {\n        struct124 *first = *(struct124 **)loaded;\n        loaded = 0;\n        *slot = first;\n    }\n    return loaded;')
    for shape,tail in (
            ('header-before-clear','    identity = *(s32 *)loaded;\n    loaded = 0;\n    *slot = (struct124 *)identity;\ndone:\n    return loaded;'),
            ('header-after-store','    identity = *(s32 *)loaded;\n    *slot = (struct124 *)identity;\n    loaded = 0;\ndone:\n    return loaded;'),
            ('header-label-before-store','    identity = *(s32 *)loaded;\n    loaded = 0;\ndone:\n    *slot = (struct124 *)identity;\n    return loaded;'),
            ('header-label-before-clear','    identity = *(s32 *)loaded;\ndone:\n    loaded = 0;\n    *slot = (struct124 *)identity;\n    return loaded;'),
            ('header-goto-return','    identity = *(s32 *)loaded;\n    loaded = 0;\n    *slot = (struct124 *)identity;\n    goto done;\ndone:\n    return loaded;'),
            ('explicit-goto','    *slot = *(struct124 **)loaded;\n    loaded = 0;\n    goto done;\ndone:\n    return loaded;')):
        yield 'schedule-'+shape,selected.replace('    *slot = *(struct124 **)loaded;\n    loaded = 0;\ndone:\n    return loaded;',tail)
    for before,tag in (('    *slot = (struct124 *)loaded;','publication'),
            ('    *slot = *(struct124 **)loaded;','header'),('    loaded = 0;','clear')):
        yield 'schedule-label-'+tag,selected.replace(before,'schedule:\n'+before)
    scheduled=selected.replace('    loaded = 0;\ndone:', '    loaded = 0;\n    goto done;\ndone:')
    for name,expression in (
            ('unsigned-header','(struct124 *)*(u32 *)loaded'),
            ('volatile-header','*(struct124 *volatile *)loaded'),
            ('volatile-word-header','(struct124 *)*(volatile u32 *)loaded'),
            ('indexed-header','((struct124 **)loaded)[0]'),
            ('header-assignment','(struct124 *)(loaded = *(s32 *)loaded)')):
        yield 'tail-'+name,scheduled.replace('*(struct124 **)loaded',expression)
    for name,expression in (('xor','loaded ^ loaded'),('subtract','loaded - loaded'),
            ('mask','loaded & 0'),('conditional','loaded ? 0 : 0')):
        yield 'tail-clear-'+name,scheduled.replace('    loaded = 0;','    loaded = '+expression+';')
    yield 'tail-comma',scheduled.replace('    *slot = *(struct124 **)loaded;\n    loaded = 0;',
        '    *slot = *(struct124 **)loaded, loaded = 0;')
    yield 'tail-empty-else',scheduled.replace('        return loaded = 2;\n    }','        return loaded = 2;\n    } else {\n    }')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='schedule-explicit-goto');parser.add_argument('--profiles',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    out=root/'conker/build/game-third-resource-loader-status';records=[]
    for name,source in candidates():
        if args.filter and args.filter not in name: continue
        for profile in ('owner','retail') if args.profiles else ('owner',):
            try:
                meta,words=lifetime.compile_candidate(root,out,name+'-'+profile,source,profile)
            except ValueError as error:
                meta=dict(name=name+'-'+profile,error=str(error))
            records.append(meta)
            print(meta['name'],meta.get('body_words'),meta.get('frame'),meta.get('differences'),meta.get('error',''),flush=True)
    (out/'measurements.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__':main()
