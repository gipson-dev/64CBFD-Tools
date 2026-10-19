"""Source-only neighbor-row frame, scalar lifetime and loop-shape experiments."""
import argparse
import json
from pathlib import Path
import re

from tools.experiments import game_neighbor_row_builder_candidates as source

BUILD = source.BUILD + '/homes'
BASE = dict(source.shapes())['byte-fill-narrow']


def inline_selected(body):
    return body.replace('    u8 *selected;\n','').replace(
        '                selected = D_800CC2D0 + slot * 0x32C;\n','').replace(
        '*(f32 *)(selected + 0x14)','*(f32 *)(D_800CC2D0 + slot * 0x32C + 0x14)').replace(
        '*(f32 *)(selected + 0x1C)','*(f32 *)(D_800CC2D0 + slot * 0x32C + 0x1C)')


def inline_actor(body):
    return body.replace('    u8 *actor;\n','').replace(
        '            actor = D_800CC2D0 + (u32)i * 0x32C;\n','').replace(
        'actor != NULL','(u32)(D_800CC2D0 + (u32)i * 0x32C) != 0').replace(
        '*(f32 *)(actor +','*(f32 *)(D_800CC2D0 + (u32)i * 0x32C +').replace(
        'actor[0x65]','D_800CC2D0[(u32)i * 0x32C + 0x65]').replace(
        'actor[0x13C]','D_800CC2D0[(u32)i * 0x32C + 0x13C]')


def declarations(body, names):
    head,tail=body.split('\n\n',1)
    lines=head.splitlines(); first=next(i for i,s in enumerate(lines) if s.startswith('    '))
    old=lines[first:]; by_name={re.search(r'(\w+);$',s)[1]:s for s in old}
    if set(names)!=set(by_name) or len(names)!=len(by_name):raise ValueError('Declaration permutation is not closed')
    return '\n'.join(lines[:first]+[by_name[n] for n in names])+'\n\n'+tail


def byte_indices(body):
    body=body.replace('    s32 copy;','    s32 copy;\n    s32 indexBytes;\n    s32 slotBytes;')
    body=body.replace('    group = groups[slot];','    slotBytes = slot * 4;\n    group = *(s32 *)((u8 *)groups + slotBytes);')
    body=body.replace('state + slot * 4 +','state + slotBytes +')
    body=body.replace('teams[slot]','*(s32 *)((u8 *)teams + slotBytes)')
    for name in ('groups','teams','states'):
        body=body.replace(name+'[i]','*(s32 *)((u8 *)'+name+' + indexBytes)')
    body=body.replace('active[i]','*active')
    head,tail=body.split('    for (i = 0; i < count; i++) {\n',1)
    loop,rest=tail.split('    for (i = used * 4;',1)
    if not loop.endswith('    }\n'):raise ValueError('Outer loop end moved')
    return head+'    i = 0;\n    indexBytes = 0;\n    if (count > 0) {\n        do {\n'+loop[:-6]+(
        '        i++;\n        indexBytes += 4;\n        active++;\n'
        '        } while (i != count);\n    }\n    for (i = used * 4;')+rest


def quad_disabled(body):
    old=('        for (i = 0; i != 64; i += 4) {\n'
         '            *(s32 *)((u8 *)neighbors + start * 4 + i) = -1;\n        }')
    new=('        for (i = 0; i != 64; i += 16) {\n'+''.join(
        '            *(s32 *)((u8 *)neighbors + start * 4 + i + %d) = -1;\n'%at
        for at in (0,4,8,12))+'        }')
    if body.count(old)!=1:raise ValueError('Disabled fill shape moved')
    return body.replace(old,new)


def quad_copy(body):
    old=('                for (copy = used; copy > position; copy--) {\n'
         '                    neighbors[start + copy] = neighbors[start + copy - 1];\n'
         '                    scores[start + copy] = scores[start + copy - 1];\n                }')
    one=('                        neighbors[start + copy] = neighbors[start + copy - 1];\n'
         '                        scores[start + copy] = scores[start + copy - 1];\n'
         '                        copy--;\n')
    four=''.join('                        %s[start + copy - %d] = %s[start + copy - %d];\n'%(name,k,name,k+1)
        for k in range(4) for name in ('neighbors','scores'))
    new=('                copy = used;\n                if (position < used) {\n'
         '                    if (((used - position) & 3) != 0) {\n                        do {\n'+one+
         '                        } while (copy != used - ((used - position) & 3));\n                    }\n'
         '                    if (copy != position) {\n                        do {\n'+four+
         '                        copy -= 4;\n                        } while (copy != position);\n'
         '                    }\n                }')
    if body.count(old)!=1:raise ValueError('Shift loop shape moved')
    return body.replace(old,new)


def quad_final(body):
    old=('    for (i = used * 4; i < 64; i += 4) {\n'
         '        *(s32 *)((u8 *)neighbors + start * 4 + i) = -1;\n    }')
    four=''.join('                *(s32 *)((u8 *)neighbors + start * 4 + copy + %d) = -1;\n'%at for at in (0,4,8,12))
    new=('    i = used;\n    if (used < 16) {\n'
         '        if (((16 - used) & 3) != 0) {\n            do {\n'
         '                neighbors[start + i] = -1;\n                i++;\n'
         '            } while (i != used + ((16 - used) & 3));\n        }\n'
         '        if (i != 16) {\n            copy = i * 4;\n            do {\n'+four+
         '                copy += 16;\n            } while (copy != 64);\n        }\n    }')
    if body.count(old)!=1:raise ValueError('Final fill shape moved')
    return body.replace(old,new)


def candidates():
    yield 'frontier',BASE
    for name in ('nearest','distance','start','score'):
        yield 'hint-'+name,BASE.replace('    s32 '+name+';','    register s32 '+name+';')
    yield 'hint-minimum-and-distance',BASE.replace('    s32 nearest;','    register s32 nearest;').replace(
        '    s32 distance;','    register s32 distance;')
    yield 'inline-selected',inline_selected(BASE)
    yield 'inline-actor',inline_actor(BASE)
    compact=inline_actor(inline_selected(BASE))
    yield 'inline-both-addresses',compact
    yield 'compact-quad-disabled',quad_disabled(compact)
    yield 'frontier-quad-disabled',quad_disabled(BASE)
    old=('                for (copy = used; copy > position; copy--) {\n'
         '                    neighbors[start + copy] = neighbors[start + copy - 1];\n'
         '                    scores[start + copy] = scores[start + copy - 1];\n                }')
    new=('                for (copy = used; copy > position;) {\n'
         '                    neighbors[start + copy] = neighbors[start + copy - 1];\n'
         '                    copy--;\n'
         '                    scores[start + copy + 1] = scores[start + copy];\n                }')
    yield 'compact-mid-shift-decrement',compact.replace(old,new)
    yield 'compact-quad-mid-shift',quad_disabled(compact.replace(old,new))
    yield 'compact-quad-disabled-final',quad_final(quad_disabled(compact))
    yield 'compact-quad-copy-final',quad_final(quad_copy(compact))
    yield 'compact-all-quad',quad_final(quad_copy(quad_disabled(compact)))
    for label,body in (('frontier',BASE),('compact',compact)):
        head=body.split('\n\n',1)[0]
        names=[re.search(r'(\w+);$',s)[1] for s in head.splitlines() if s.startswith('    ')]
        yield label+'-reverse-locals',declarations(body,list(reversed(names)))
        homes=['used','score','group','slot','mask','groups','count','states','neighbors','scores','start']
        yield label+'-homes-first',declarations(body,homes+[n for n in names if n not in homes])
        yield label+'-homes-last',declarations(body,[n for n in names if n not in homes]+homes)
        early=['nearest','distance','teams','active','mode','primaryCount']
        yield label+'-saved-values-first',declarations(body,early+[n for n in names if n not in early])
    for label,body in (('frontier',BASE),('compact',compact)):
        arm=body.replace('        return 0;\n    }\n    group =', '    } else {\n    group =').replace(
            '    return 0;\n}', '    }\n    return 0;\n}')
        yield label+'-single-return',arm
        yield label+'-conditional-minimum',body.replace(
            '            if (distance < nearest) {\n                nearest = distance;\n            }',
            '            nearest = distance < nearest ? distance : nearest;')
        entry=body.replace('    state = (u8 *)D_800D23B0;\n    groups', '    groups',1)
        before,after=entry.split('    *(s8 *)(state + 0x1704)',1)
        before=before.replace('state +','(u8 *)D_800D23B0 +')
        entry=before+'    state = (u8 *)D_800D23B0;\n    *(s8 *)(state + 0x1704)'+after
        yield label+'-direct-entry-tables',entry
        no_state=body.replace('    u8 *state;\n','').replace('    state = (u8 *)D_800D23B0;\n','').replace(
            '        state = (u8 *)D_800D23B0;\n','')
        yield label+'-direct-context-expressions',re.sub(r'\bstate\b','((u8 *)D_800D23B0)',no_state)
    for label,body in (('frontier',BASE),('compact',compact),('selected-only',inline_selected(BASE))):
        indexed=byte_indices(body)
        yield label+'-byte-indices',indexed
        yield label+'-byte-indices-word-fill',indexed.replace(
            'for (i = used * 4; i < 64; i += 4) {\n        *(s32 *)((u8 *)neighbors + start * 4 + i) = -1;',
            'for (i = used; i < 16; i++) {\n        neighbors[start + i] = -1;')
        yield label+'-byte-indices-i32-primary',indexed.replace('    s8 primaryCount;','    s32 primaryCount;')


SELECTED = quad_final(quad_copy(quad_disabled(inline_actor(inline_selected(BASE)))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--filter');p.add_argument('--normal',action='store_true')
    p.add_argument('--selected',action='store_true')
    args=p.parse_args();root=Path(__file__).resolve().parents[2];out=root/BUILD;rows={}
    for name,body in ([('selected',SELECTED)] if args.selected else candidates()):
        if args.filter and args.filter not in name:continue
        _,_,row=source.compile_candidate(root,out,name,body,normal=args.normal)
        rows[name]={k:v for k,v in row.items() if k!='bindings'}
        print(json.dumps(dict(candidate=name,**rows[name])),flush=True)
    (out/'screen.json').write_text(json.dumps(rows,indent=2)+'\n')
