"""Discriminate equivalent index trees after observing UOPT's shared multiply."""
import argparse
import json
from pathlib import Path

from tools.experiments import game_view_overlay_pass as source


def candidates():
    # Each replacement is a complete parenthesized expression, including shifts.
    expressions=('((u32)view * 0x180)',
        '((((u32)view << 2) - (u32)view) << 7)',
        '(((u32)view * 3) << 7)',
        '(((u32)view << 7) * 3)')
    for label,indices in (('wrapped-mixed',(1,2,3)),('multiply-shift',(0,2,3)),
            ('shift-multiply',(1,0,3)),('shift-pair',(1,2,0)),('multiply-distinct',(0,2,1))):
        for direct in (False,True):
            body=source.INITIAL
            if direct:body=body.replace('    s32 narrowedView;\n','').replace(
                '    narrowedView = (s16)view;\n','').replace('narrowedView','(s16)view')
            parts=body.split(expressions[0]);assert len(parts)==4
            body=parts[0]+''.join(expressions[k]+parts[i+1] for i,k in enumerate(indices))
            yield 'address-'+label+('-direct' if direct else '-local'),body


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--filter',default='')
    args=parser.parse_args();root=Path(__file__).resolve().parents[2]
    for name,body in candidates():
        if args.filter not in name:continue
        _,_,row=source.measure(root,root/source.BUILD,name,body)
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','raw_sha256')}),flush=True)


if __name__=='__main__':main()
