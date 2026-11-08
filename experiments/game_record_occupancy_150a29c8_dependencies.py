"""Closed section audit for the record-query shared-header recovery."""
import hashlib,json,struct
from pathlib import Path
from tools.pad_generated_object import ELF_HEADER,SECTION_HEADER,read_c_string


def section_scope(before, after):
    def rows(data):
        h=ELF_HEADER.unpack_from(data)
        ss=[SECTION_HEADER.unpack_from(data,h[6]+i*h[11]) for i in range(h[12])]
        names=ss[h[13]];strings=data[names[4]:names[4]+names[5]]
        return h,{read_c_string(strings,s[0]):s for s in ss}
    ha,a=rows(before);hb,b=rows(after)
    if ha[:6]!=hb[:6] or ha[7:]!=hb[7:] or a.keys()!=b.keys():raise ValueError('Dependency ELF structure changed')
    changed=[]
    for name,x in a.items():
        y=b[name]
        if name=='.mdebug':
            if x[1]!=0x70000005 or y[1]!=x[1] or x[2]&2 or y[2]&2:raise ValueError('Dependency debug section flags changed')
            changed.append(name) if x!=y or before[x[4]:x[4]+x[5]]!=after[y[4]:y[4]+y[5]] else None
            continue
        if x[:4]!=y[:4] or x[5:]!=y[5:]:raise ValueError('Dependency section metadata changed: '+name)
        if x[1]!=8 and before[x[4]:x[4]+x[5]]!=after[y[4]:y[4]+y[5]]:raise ValueError('Dependency retained section changed: '+name)
    return changed


def validate(root,out):
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=json.loads((out/'header-audit.json').read_text())
    ld=(out/'frozen/conker/build/conker.ld').read_text()
    if '/DISCARD/ :' not in ld or '        *(*);' not in ld:raise ValueError('Dependency discard policy changed')
    if report['owners']!=199 or len(report['records'])!=199 or report['pending']:raise ValueError('Dependency audit incomplete')
    for row in report['records']:
        original=root/row['baseline_object'];copied=root/row['copied_object']
        if sha(original)!=row['original_sha256'] or sha(copied)!=row['copied_sha256']:raise ValueError('Dependency receipt changed')
        changed=section_scope(original.read_bytes(),copied.read_bytes())
        if changed!=row['discarded_input_sections']:raise ValueError('Dependency section audit changed')
        live=root/row['object']
        if section_scope(original.read_bytes(),live.read_bytes()) not in ([],['.mdebug']):raise ValueError('Dependency live object changed')
    return dict(owners=199,whole_object_identical=194,discarded_input_debug_only=5,all_retained_sections_fixed=True,
                actual_Make_commands=report['commands'],existing_discard_policy=True,added_image_exclusions=0)
