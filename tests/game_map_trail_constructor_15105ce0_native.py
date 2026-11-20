"""ILP32 strict-aliasing/UBSan source checks against guest-checked vectors."""
from pathlib import Path
import json
import struct
import subprocess
from tools.tests.test_game_projected_packet_draw import native_command
from tools.tests.test_game_row_destination_fill import START

def run(source, guest):
    out=source.OUT/'native';out.mkdir(exist_ok=True)
    rows=bytearray()
    corpus=list(guest.cases())
    add=lambda *v:rows.extend(struct.pack('>%dI'%len(v),*(x&0xFFFFFFFF for x in v)))
    add(len(corpus))
    for c in corpus:
        initial=guest.fixture(c);want,calls,answer,snapshots=guest.reference(initial,c)
        _,extra,priority,context=guest.arguments(c)
        add(c.pieces,c.success,c.seed,c.mode,c.phase,extra,priority,context)
        rows.extend(guest.data(initial,guest.PACKET,80));rows.extend(guest.data(initial,guest.VECTOR,12))
        add(guest.read(initial,guest.LIMIT),guest.read(initial,guest.SCALE))
        rows.extend(guest.data(want,guest.OUTPUT,136));rows.extend(guest.data(want,guest.PACKET,80));rows.extend(guest.data(want,guest.VECTOR,12))
        add(answer,len(snapshots))
        for p in snapshots:rows.extend(p)
        add(len(calls))
        for target,args in calls:add(target,len(args),*args)
    binary=out/'vectors.bin';binary.write_bytes(rows)
    # Linux enters _start without a C call's stack alignment. GCC's inlined
    # harness uses aligned SSE stores at O2; align this entry, not the target.
    start=START.replace('void _start(void)', '__attribute__((force_align_arg_pointer)) void _start(void)')
    text=Path(__file__).with_suffix('.c.in').read_text().replace('@TYPES@',source.PREAMBLE).replace('@BINARY@',binary.relative_to(source.ROOT).as_posix()).replace('@START@',start).replace('@STACK@',str(guest.STACK)).replace('@PIECES@','initialPieces')
    # This declaration is needed by the earlier provider definition.
    text=text.replace('static u32 seed,','static s32 initialPieces;\nstatic u32 seed,').replace('static s32 initialPieces;\nstatic int run','static int run')
    controls={
        'point-selection':source.BODY.replace('i == 0 ? 0 : 3','i == 0 ? 0 : 2'),
        'allocation-size':source.BODY.replace('pieces * 0x34 + pointBytes + extraBytes','pieces * 0x30 + pointBytes + extraBytes'),
        'unsigned-random':source.BODY.replace('(u32)func_150ADA20() %','func_150ADA20() %'),
        'maximum-width':source.BODY.replace('(packet->maximum + 1)','((u16)packet->maximum + 1)'),
        'effect-lifetime':source.BODY.replace('effect.lifetime = 300','effect.lifetime = 301'),
        'second-flags':source.BODY.replace('? 0x80 : 0','? 0x40 : 0'),
        'retained-descriptor':source.BODY.replace('effect.position = packet->points','effect.zero04 = 0;\n        effect.position = packet->points'),
        'reloaded-output-count':source.BODY.replace('record->packet.pieces * 0x30','pieces * 0x30'),
    }
    assert all(body!=source.BODY for body in controls.values())
    receipts=[]
    for label,body,opt in [('valid',source.BODY,opt)for opt in ('-O0','-O2','-O3')]+[(name,body,'-O2')for name,body in controls.items()]:
        path=out/(label+opt+'.c');exe=path.with_suffix('');path.write_text(text.replace('@FRAGMENT@',body))
        built=subprocess.run(native_command(opt)+['-fstrict-aliasing',str(path),'-o',str(exe)],cwd=source.ROOT,capture_output=True,text=True)
        assert built.returncode==0 and not built.stdout and not built.stderr,(label,built.stdout,built.stderr)
        ran=subprocess.run([str(exe)],capture_output=True,timeout=20)
        assert (ran.returncode==0)==(label=='valid'),(label,opt,ran.returncode)
        receipts.append(dict(label=label,profile=opt,exit_code=ran.returncode))
    result=dict(cases_each_profile=len(corpus),profiles=3,controls=len(controls),SDK32=True,strict_aliasing=True,UBSan=True,
                padding_excluded=[103,106,107],original_provider_bodies_executed=False,checks=receipts)
    (source.OUT/'native-report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
