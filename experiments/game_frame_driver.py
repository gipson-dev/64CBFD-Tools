"""Recover the scheduler-message frame driver and display-list pass ordering."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
from unittest.mock import patch

from tools.experiments import game_frame_sequence as previous
from tools.tests import frame_sequence_checkpoint as checkpoint
from tools.experiments import game_packet_rectangle as engine
from tools.experiments.game_actor_classifier_candidates import sections
from tools.pad_generated_object import parse_object
from tools import pad_c_object

BUILD='conker/build/game-frame-driver'
OWNER,FUNCTION,ENTRY,ROM,WORDS='game_45B80','func_1501878C',0x1501878C,0x45C3C,412
PATHS=dict(previous.PATHS,os_message='conker/include/2.0L/PR/os_message.h')
BASELINE=dict(previous.BASELINE,**checkpoint.AFTER,
    os_message='241238eea37d71382b7a3c994d5837e4482d77548a4cbdaeb30b9f67013cdfb7')
build=previous.build
DECLARATIONS='''/* Scheduler-message and display-list interfaces used by the frame driver. */
extern Gfx *D_800BE9C8, *D_800BE9CC;
extern void *D_800BEB9C;
extern u8 D_800C1060[];
extern Mtx D_80089470;
extern LookAt D_800D9B90[];
extern u8 D_800BE630[], D_800BEBA0, D_800BEAC2;
extern s32 D_800BEBA4;
s32 func_1517E1AC(void);
void func_151412BC(void);
s32 func_151E51EC(void);
void func_1501A39C(void);
void func_1510B3B0(void);
void func_1510B51C(void);
void func_1501905C(void);
void func_1515D69C(void);
s32 func_15167310(void);
void func_15018F80(s16);
Gfx *func_15019464(Gfx *, s16);
void func_15019414(void);
s32 func_15019BB8(Gfx *, s32);
s32 func_15019E60(Gfx *);
s32 func_151E84B0(s32);
s32 func_15043384(s32);
void func_150347E8(void);
void func_1502E474(void);
s32 func_15189118(s32);
s32 func_15084A18(void);
void func_15125628(void);
void func_1510D404(void);
s32 func_15114A1C(void);
s32 func_1517CFC4(void);
s32 func_1501C880(s32, s32);
s32 func_151F2CDC(void);
void func_151F2BE8(void);
void func_151F2C4C(void);

'''
INITIAL='''/* Consume one scheduler message, submit its frame passes, or drain shutdown. */
s32 func_1501878C(void) {
    OSMesg message = NULL;
    Gfx *savedCommands;
    s16 view;
    Gfx **commands = (Gfx **)&D_800BE9D0;

    osRecvMesg(&D_800BEA10, &message, OS_MESG_BLOCK);
    D_8002AC60 = 0;
    D_8002AC64 = 800;
    switch (*(s16 *)message) {
        case 2:
            func_1517E1AC();
            if (D_800DC9F0 != 0) {
                func_151412BC();
            }
            (*(s16 *)&D_800BEAA8)--;
            if (D_800BE615 != 0 && *(s16 *)&D_800BEAA8 == 0) {
                func_10004074(D_800BE9C8);
                func_10004074(D_800BE9CC);
                D_800BE9C8 = NULL;
                return 0;
            }
            break;
        case 1:
            if (D_800BE615 != 0) {
                break;
            }
            func_151E51EC();
            if (D_800BE615 != 0) {
                break;
            }
            if (D_800BE614 != 0) {
                func_1501A39C();
                D_800BE614 = 0;
            }
            if (D_800D9AF0 != 0) {
                func_1510B3B0();
            }
            if (D_800D9B18 != 0) {
                func_1510B51C();
            }
            func_1501905C();
            if (D_800BEAC0 == 0 && func_15019130() == 0) {
                break;
            }
            *commands = (Gfx *)func_1501A680((s32)*commands);
            func_1515D69C();
            func_15167310();
            for (view = 0; view <= D_80082FA0; view++) {
                D_80082FA4 = D_800BE630[view];
                func_15018F80((s16)D_80082FA4);
                *commands = func_15019464(*commands, (s16)D_80082FA4);
            }
            if (D_800BEBA0 == 0) {
                LookAt *lookAt = D_800D9B90;
                gSPLoadUcodeEx((*commands)++, D_800C1060, D_800BEB9C, 0x800);
                gSPClearGeometryMode((*commands)++, G_ZBUFFER | G_SHADE | G_CULL_BOTH |
                    G_FOG | G_TEXTURE_GEN | G_TEXTURE_GEN_LINEAR | G_LOD | G_SHADING_SMOOTH);
                gSPSetGeometryMode((*commands)++, G_ZBUFFER | G_SHADE | G_LIGHTING | G_SHADING_SMOOTH);
                gSPMatrix((*commands)++, &D_80089470, G_MTX_MODELVIEW | G_MTX_LOAD | G_MTX_NOPUSH);
                gSPLookAt((*commands)++, lookAt + D_800BE9C0);
            }
            for (view = 0; view <= D_80082FA0; view++) {
                s32 overflow;
                savedCommands = *commands;
                D_80082FA4 = D_800BE630[view];
                *commands = (Gfx *)func_1515D6D0((s32)*commands, D_80082FA4);
                *commands = (Gfx *)func_150195A0((s32)*commands, (s16)D_80082FA4);
                overflow = (*commands - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4;
                if (overflow != 0) {
                    *commands = savedCommands;
                }
            }
            D_80082FA4 = 0;
            func_15019414();
            *commands = (Gfx *)func_150198FC((s32)*commands);
            for (view = 0; view <= D_80082FA0; view++) {
                D_80082FA4 = D_800BE630[view];
                *commands = (Gfx *)func_1515D6D0((s32)*commands, D_80082FA4);
                *commands = (Gfx *)func_15019CC8((s32)*commands, D_80082FA4);
                if (D_800BEAC0 == 0 && D_80082FA0 > 0) {
                    *commands = (Gfx *)func_15019BB8(*commands, D_80082FA4);
                }
            }
            *commands = (Gfx *)func_15019E60(*commands);
            if (D_800BEAC0 == 0 && D_80082FA0 == 0) {
                for (view = 0; view <= D_80082FA0; view++) {
                    D_80082FA4 = D_800BE630[view];
                    *commands = (Gfx *)func_15019BB8(*commands, D_80082FA4);
                }
            }
            *commands = (Gfx *)func_151E84B0((s32)*commands);
            *commands = (Gfx *)func_15043384((s32)*commands);
            func_150347E8();
            func_1502E474();
            func_15189118(0);
            func_15084A18();
            func_15125628();
            gDPFullSync((*commands)++);
            gSPEndDisplayList((*commands)++);
            func_10004674();
            func_1510D404();
            func_15114A1C();
            func_1517CFC4();
            func_1501C880(0, 1);
            D_800BE9B4 = 0;
            if (D_800BEAC0 != 0) {
                D_800BEAC2 = 2;
            } else if (D_800BEAC2 > 0) {
                D_800BEAC2--;
            }
            if (D_800BEAC1 != D_800BEAC0) {
                D_800BEAC0 = D_800BEAC1;
                if (D_800BEAC0 != 0) {
                    func_1000E2F4(1);
                    func_10011E94(1);
                    if (func_151F2CDC() != 0) {
                        func_151F2BE8();
                    }
                } else {
                    func_1000E2F4(0);
                    func_10011E94(0);
                    if (func_151F2CDC() != 0) {
                        func_151F2C4C();
                    }
                }
            }
            break;
        case 4:
            while (func_151DCFD8(1) != 0) {}
            for (;;) {}
    }
    return 1;
}'''


def freeze(root,out):
    from tools.tests import frame_driver_checkpoint as current
    out.mkdir(parents=True,exist_ok=True)
    read=Path.read_bytes
    with patch.object(Path,'read_bytes',lambda p:current.previous_input(read(p),p,root)), \
            patch.multiple(engine,PATHS=PATHS,BASELINE=BASELINE):
        engine.freeze(root,out)


def return_interfaces(before):
    changes=(('void func_15019BB8(Gfx *arg0, s32 arg1)', 's32 func_15019BB8(Gfx *arg0, s32 arg1)'),
        ('    func_151674F8((void *)temp_v0, 4, sp2A, 1);',
         '    return (s32)func_151674F8((void *)temp_v0, 4, sp2A, 1);'),
        ('void func_15019E60(Gfx *arg0)','s32 func_15019E60(Gfx *arg0)'),
        ('    func_15043384(func_151E8620(func_1501A490(arg0, 0xFF, 0, 0, 0, 0)));',
         '    return func_15043384(func_151E8620(func_1501A490(arg0, 0xFF, 0, 0, 0, 0)));'))
    for old,new in changes:
        if before.count(old)!=1:raise ValueError('Unknown frame-driver return predecessor')
        before=before.replace(old,new,1)
    return before


def recovered_owner(before,body=INITIAL,typed_cursor=None):
    before=return_interfaces(before)
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!='s32 func_1501878C() {\n    return 0;\n}':
        raise ValueError('Unknown frame-driver predecessor')
    result=before[:lo]+body+before[hi:]
    for old in ('// something big and interesting\n',
        '/* Non-matching C placeholders for asm/nonmatchings/game_45B80/func_1501878C.s. */\n'):
        if result.count(old)!=1:raise ValueError('Unknown frame-driver annotation')
        result=result.replace(old,'',1)
    result=result.replace('s32 func_1501878C();','s32 func_1501878C(void);',1)
    anchor='/* Generated placeholder declarations. */\n'
    if result.count(anchor)!=1:raise ValueError('Unknown frame-driver declarations')
    result=result.replace(anchor,DECLARATIONS+anchor,1)
    if typed_cursor is None:typed_cursor='*commands' not in body
    if typed_cursor:
        result=typed_display_list_owner(result)
        if typed_cursor=='volatile':result=result.replace('extern Gfx *D_800BE9D0;', 'extern Gfx *volatile D_800BE9D0;',1)
    return result


def typed_display_list_owner(text):
    include='#include "variables.h"'
    if text.count(include)!=1:raise ValueError('Unknown frame-driver variable include')
    text=text.replace(include,'''/* This owner uses the display-list label as an SDK pointer, not an integer. */
#define D_800BE9D0 FrameDriverLegacyDisplayListAddress
#include "variables.h"
#undef D_800BE9D0
extern Gfx *D_800BE9D0;''',1)
    old='D_800BE9D0 = D_800BE9D8[D_800BE9C0];'
    if text.count(old)!=1:raise ValueError('Unknown frame-driver cursor initializer')
    return text.replace(old,'D_800BE9D0 = (Gfx *)D_800BE9D8[D_800BE9C0];',1)


def typed_body(body=INITIAL):
    return body.replace('    Gfx **commands = (Gfx **)&D_800BE9D0;\n','').replace('*commands','D_800BE9D0')


def light_pair(body):
    return body.replace('gSPLookAt((*commands)++, lookAt + D_800BE9C0);',
        'gSPLookAtX((*commands)++, lookAt + D_800BE9C0);\n'
        '                gSPLight((*commands)++, (u8 *)(lookAt + D_800BE9C0) + 16, 1);')


def measure(root,out,label,body=INITIAL,flags=('-O2','-g3'),interfaces_only=False,typed_cursor=None):
    freeze(root,out)
    before=(out/'before-dispatch_owner').read_text()
    content=return_interfaces(before) if interfaces_only else recovered_owner(before,body,typed_cursor)
    obj,diagnostics=build.compile_owner(root,out,content,label,flags)
    text,functions,rel=parse_object(obj)
    data,placed=build.link_owner(root,out,obj,OWNER)
    f=functions[FUNCTION]
    words=list(struct.unpack_from('>%dI'%(f['size']//4),data,placed[FUNCTION]['value']))
    truth=struct.unpack_from('>412I',(out/'before-retail_rom').read_bytes(),ROM)
    row=dict(label=label,flags=flags,words=len(words),frame=((-words[0])&65535) if words[0]>>16==0x27BD else 0,
        differences=sum(a!=b for a,b in zip(words,truth))+abs(len(words)-WORDS),diagnostics=diagnostics,
        raw_sha256=hashlib.sha256(text[f['value']:f['value']+f['size']]).hexdigest(),
        relocations={a-f['value']:v for a,v in rel.items() if f['value']<=a<f['value']+f['size']},
        pools={n:d.hex() for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d},
        different_words=[(i*4,'0x%08X'%a,'0x%08X'%b) for i,(a,b) in enumerate(zip(words,truth)) if a!=b])
    (out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    return obj,words,row


def compact_boolean_body():
    return typed_body(light_pair(INITIAL)).replace('    Gfx *savedCommands;\n','').replace(
        '                s32 overflow;\n','                Gfx *savedCommands;\n').replace(
        '                LookAt *lookAt = D_800D9B90;\n','').replace('lookAt + D_800BE9C0','D_800D9B90 + D_800BE9C0').replace(
        '                overflow = (D_800BE9D0 - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4;\n                if (overflow != 0)',
        '                if (((D_800BE9D0 - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4) ? 1 : 0)')


def integer_cursor_body(body):
    body=body.replace('Gfx *savedCommands;','s32 savedCommands;').replace('(D_800BE9D0)++','(D_800BE9D0 += 8) - 8')
    body=body.replace('D_800BE9D0 = (Gfx *)','D_800BE9D0 = ')
    body=body.replace('D_800BE9D0 = func_15019464(D_800BE9D0,','D_800BE9D0 = (s32)func_15019464((Gfx *)D_800BE9D0,')
    for name in ('func_15019BB8','func_15019E60'):
        body=body.replace(name+'(D_800BE9D0',name+'((Gfx *)D_800BE9D0')
    body=body.replace('(D_800BE9D0 - ((Gfx **)&D_800BE9C8)[D_800BE9C0])',
        '((D_800BE9D0 - (s32)((Gfx **)&D_800BE9C8)[D_800BE9C0]) >> 3)')
    return body


SELECTED=compact_boolean_body()
RAW_SHA256='891ed2b97a7d62cd4862c65ce530b933b33f3ebd8858baafd7df5dc0e5f3b178'
CALL_OFFSET,STORE_OFFSET=0x4D4,0x4D8
ROLE_RANGES=((0x234,0x338),(0x4FC,0x52C))
CONDITION_RANGE=(0x558,0x5B4)
SLOT_SHA256='5c3fb4784448084a751c6175b07270540a55247037a4e7ca820a708e35f276b9'
STRUCTURAL_SHA256='8b2248e1229b704fe281289cc1b81e79fad87098e09cc81e56854c33864fa5d5'
SERIALIZATION=(
    (('D_800D9B90','D_800D9F60','D_800D1890','D_80088B60'),(1,2,3,0),
        ((0x800D9B90,0,16,0,65521),(0x800D9F60,0,16,0,65521),(0x800D1890,0,16,0,65521),(0x80088B60,0,16,0,65521))),
    (('osPiGetCmdQueue','D_800AA98C','D_80089970'),(2,0,1),
        ((0x100275F0,40,18,0,3),(0x800AA98C,0,16,0,65521),(0x80089970,0,16,0,65521))),
    (('D_800BEB9C','func_1501A680'),(1,0),((0x800BEB9C,0,16,0,65521),(0x1501A680,76,18,0,5))),
)
RELOCATIONS={
    0x1C: [('R_MIPS_HI16', 'D_800BEA10')],
    0x24: [('R_MIPS_LO16', 'D_800BEA10')],
    0x2C: [('R_MIPS_26', 'osRecvMesg')],
    0x34: [('R_MIPS_HI16', 'D_8002AC60')],
    0x3C: [('R_MIPS_LO16', 'D_8002AC60')],
    0x40: [('R_MIPS_HI16', 'D_8002AC64')],
    0x48: [('R_MIPS_LO16', 'D_8002AC64')],
    0x54: [('R_MIPS_HI16', 'D_800BE615')],
    0x5C: [('R_MIPS_LO16', 'D_800BE615')],
    0x7C: [('R_MIPS_26', 'func_1517E1AC')],
    0x84: [('R_MIPS_HI16', 'D_800DC9F0')],
    0x88: [('R_MIPS_LO16', 'D_800DC9F0')],
    0x94: [('R_MIPS_26', 'func_151412BC')],
    0x9C: [('R_MIPS_HI16', 'D_800BEAA8')],
    0xA0: [('R_MIPS_LO16', 'D_800BEAA8')],
    0xA4: [('R_MIPS_HI16', 'D_800BE615')],
    0xAC: [('R_MIPS_LO16', 'D_800BE615')],
    0xC8: [('R_MIPS_HI16', 'D_800BE9C8')],
    0xD4: [('R_MIPS_26', 'func_10004074')],
    0xD8: [('R_MIPS_LO16', 'D_800BE9C8')],
    0xDC: [('R_MIPS_HI16', 'D_800BE9CC')],
    0xE0: [('R_MIPS_26', 'func_10004074')],
    0xE4: [('R_MIPS_LO16', 'D_800BE9CC')],
    0xE8: [('R_MIPS_HI16', 'D_800BE9C8')],
    0xEC: [('R_MIPS_LO16', 'D_800BE9C8')],
    0x104: [('R_MIPS_26', 'func_151E51EC')],
    0x110: [('R_MIPS_HI16', 'D_800BE614')],
    0x114: [('R_MIPS_LO16', 'D_800BE614')],
    0x12C: [('R_MIPS_26', 'func_1501A39C')],
    0x138: [('R_MIPS_HI16', 'D_800D9AF0')],
    0x13C: [('R_MIPS_LO16', 'D_800D9AF0')],
    0x148: [('R_MIPS_26', 'func_1510B3B0')],
    0x150: [('R_MIPS_HI16', 'D_800D9B18')],
    0x154: [('R_MIPS_LO16', 'D_800D9B18')],
    0x160: [('R_MIPS_26', 'func_1510B51C')],
    0x168: [('R_MIPS_26', 'func_1501905C')],
    0x170: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x174: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x180: [('R_MIPS_26', 'func_15019130')],
    0x18C: [('R_MIPS_HI16', 'D_800BE9D0')],
    0x190: [('R_MIPS_LO16', 'D_800BE9D0')],
    0x194: [('R_MIPS_26', 'func_1501A680')],
    0x19C: [('R_MIPS_26', 'func_1515D69C')],
    0x1A4: [('R_MIPS_26', 'func_15167310')],
    0x1AC: [('R_MIPS_HI16', 'D_80082FA0')],
    0x1B0: [('R_MIPS_LO16', 'D_80082FA0')],
    0x1C0: [('R_MIPS_HI16', 'D_800BE630')],
    0x1C4: [('R_MIPS_HI16', 'D_80082FA4')],
    0x1C8: [('R_MIPS_LO16', 'D_80082FA4')],
    0x1CC: [('R_MIPS_LO16', 'D_800BE630')],
    0x1DC: [('R_MIPS_26', 'func_15018F80')],
    0x1E8: [('R_MIPS_26', 'func_15019464')],
    0x210: [('R_MIPS_HI16', 'D_800BEBA0')],
    0x214: [('R_MIPS_LO16', 'D_800BEBA0')],
    0x218: [('R_MIPS_HI16', 'D_80082FA4')],
    0x21C: [('R_MIPS_HI16', 'D_800BE630')],
    0x220: [('R_MIPS_LO16', 'D_800BE630')],
    0x228: [('R_MIPS_LO16', 'D_80082FA4')],
    0x22C: [('R_MIPS_HI16', 'D_800D9B90')],
    0x230: [('R_MIPS_LO16', 'D_800D9B90')],
    0x23C: [('R_MIPS_HI16', 'D_800BEB9C')],
    0x24C: [('R_MIPS_LO16', 'D_800BEB9C')],
    0x254: [('R_MIPS_HI16', 'D_800C1060')],
    0x260: [('R_MIPS_LO16', 'D_800C1060')],
    0x2C0: [('R_MIPS_HI16', 'D_80089470')],
    0x2CC: [('R_MIPS_LO16', 'D_80089470')],
    0x2F0: [('R_MIPS_HI16', 'D_800BE9C0')],
    0x2F8: [('R_MIPS_LO16', 'D_800BE9C0')],
    0x314: [('R_MIPS_HI16', 'D_800BE9C0')],
    0x324: [('R_MIPS_LO16', 'D_800BE9C0')],
    0x350: [('R_MIPS_26', 'func_1515D6D0')],
    0x360: [('R_MIPS_26', 'func_150195A0')],
    0x36C: [('R_MIPS_HI16', 'D_800BE9C0')],
    0x370: [('R_MIPS_LO16', 'D_800BE9C0')],
    0x374: [('R_MIPS_HI16', 'D_800BE9C8')],
    0x378: [('R_MIPS_HI16', 'D_800BEBA4')],
    0x384: [('R_MIPS_LO16', 'D_800BE9C8')],
    0x388: [('R_MIPS_LO16', 'D_800BEBA4')],
    0x3D4: [('R_MIPS_26', 'func_15019414')],
    0x3DC: [('R_MIPS_26', 'func_150198FC')],
    0x3FC: [('R_MIPS_26', 'func_1515D6D0')],
    0x40C: [('R_MIPS_26', 'func_15019CC8')],
    0x418: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x41C: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x438: [('R_MIPS_26', 'func_15019BB8')],
    0x460: [('R_MIPS_26', 'func_15019E60')],
    0x46C: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x470: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x49C: [('R_MIPS_26', 'func_15019BB8')],
    0x4C0: [('R_MIPS_26', 'func_151E84B0')],
    0x4CC: [('R_MIPS_26', 'func_15043384')],
    0x4D4: [('R_MIPS_26', 'func_150347E8')],
    0x4DC: [('R_MIPS_26', 'func_1502E474')],
    0x4E4: [('R_MIPS_26', 'func_15189118')],
    0x4EC: [('R_MIPS_26', 'func_15084A18')],
    0x4F4: [('R_MIPS_26', 'func_15125628')],
    0x52C: [('R_MIPS_26', 'func_10004674')],
    0x534: [('R_MIPS_26', 'func_1510D404')],
    0x53C: [('R_MIPS_26', 'func_15114A1C')],
    0x544: [('R_MIPS_26', 'func_1517CFC4')],
    0x550: [('R_MIPS_26', 'func_1501C880')],
    0x558: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x55C: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x560: [('R_MIPS_HI16', 'D_800BE9B4')],
    0x564: [('R_MIPS_LO16', 'D_800BE9B4')],
    0x56C: [('R_MIPS_HI16', 'D_800BEAC2')],
    0x570: [('R_MIPS_HI16', 'D_800BEAC2')],
    0x574: [('R_MIPS_LO16', 'D_800BEAC2')],
    0x584: [('R_MIPS_LO16', 'D_800BEAC2')],
    0x598: [('R_MIPS_HI16', 'D_800BEAC1')],
    0x59C: [('R_MIPS_LO16', 'D_800BEAC1')],
    0x5A0: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x5A4: [('R_MIPS_HI16', 'D_800BEAC0')],
    0x5B0: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x5B4: [('R_MIPS_LO16', 'D_800BEAC0')],
    0x5C0: [('R_MIPS_26', 'func_1000E2F4')],
    0x5C8: [('R_MIPS_26', 'func_10011E94')],
    0x5D0: [('R_MIPS_26', 'func_151F2CDC')],
    0x5E0: [('R_MIPS_26', 'func_151F2BE8')],
    0x5F0: [('R_MIPS_26', 'func_1000E2F4')],
    0x5F8: [('R_MIPS_26', 'func_10011E94')],
    0x600: [('R_MIPS_26', 'func_151F2CDC')],
    0x610: [('R_MIPS_26', 'func_151F2C4C')],
    0x620: [('R_MIPS_26', 'func_151DCFD8')],
    0x630: [('R_MIPS_26', 'func_151DCFD8')],
}


def placed_offset(offset):
    return offset+4 if offset>STORE_OFFSET else offset


def swapped_temporary(word,registers=None):
    op=word>>26
    registers=registers or {2:4,4:2}
    def field(shift):
        nonlocal word
        old=word>>shift&31
        word=(word&~(31<<shift))|(registers.get(old,old)<<shift)
    if op==0:
        if word&63 not in (0,33):raise ValueError('Unknown graphics temporary instruction')
        field(21);field(16);field(11)
    elif op in (4,5,6,7,9,13,20,21,22,23,35,36,40,43):
        field(21);field(16)
    elif op==15:
        field(16)
    else:raise ValueError('Unknown graphics temporary opcode')
    return word


def normalized_word(word,offset):
    if offset==CALL_OFFSET:
        if word!=0x0C000000:raise ValueError('Unknown frame publication call')
        return 0xAE220000
    if offset==STORE_OFFSET:
        if word!=0xAE220000:raise ValueError('Unknown frame publication store')
        return 0x0C000000
    op=word>>26
    if op in (1,4,5,6,7,20,21,22,23):
        immediate=word&65535
        target=offset+4+(immediate if immediate<32768 else immediate-65536)*4
        if not 0<=target<WORDS*4-4:raise ValueError('Branch outside compact frame driver')
        displacement=(placed_offset(target)-placed_offset(offset)-4)//4
        if not -32768<=displacement<32768:raise ValueError('Frame branch overflow')
        word=(word&0xFFFF0000)|(displacement&65535)
    if any(lo<=offset<hi for lo,hi in ROLE_RANGES):
        word=swapped_temporary(word)
    if offset==0x5AC:
        if word!=0x24020001:raise ValueError('Unknown likely-delay success return')
    elif CONDITION_RANGE[0]<=offset<CONDITION_RANGE[1]:
        word=swapped_temporary(word,{2:3,3:2})
        if offset==0x5A8:
            if word>>26!=20 or (word>>21&31,word>>16&31)!=(2,3):
                raise ValueError('Unknown commutative frame-state comparison')
            word=(word&~0x03FF0000)|(3<<21)|(2<<16)
    return word


def derived_guards(obj):
    checked_object(obj)
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    if len(raw)!=1644 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256:
        raise ValueError('Unknown frame-driver source object')
    rows=[]
    for offset,word in enumerate(struct.unpack('>411I',raw)):
        offset*=4
        replacement=normalized_word(word,offset)
        expected=relocations.get(f['value']+offset,[])
        changed=expected
        if offset==CALL_OFFSET:
            if expected!=[('R_MIPS_26','func_150347E8')]:raise ValueError('Unknown publication call binding')
            changed=[]
        elif offset==STORE_OFFSET:
            if expected:raise ValueError('Unexpected publication store binding')
            changed=[('R_MIPS_26','func_150347E8')]
        if replacement==word and offset!=STORE_OFFSET:continue
        spec=lambda items:';'.join(kind+':'+name for kind,name in items) or '-'
        rows.append(dict(filename=OWNER,function=FUNCTION,offset='0x%X'%offset,
            expected='0x%08X'%word,replacement='0x%08X'%replacement,
            expected_relocations=spec(expected),replacement_relocations=spec(changed),
            note='Normalize frame-driver temporary roles and independent publication schedule',
            insert_after='0x00000000' if offset==STORE_OFFSET else '',insert_after_relocations='',omit='false'))
    return rows


def checked_object(obj):
    text,functions,relocations=parse_object(obj)
    f=functions[FUNCTION]
    raw=text[f['value']:f['value']+f['size']]
    bindings={a-f['value']:rows for a,rows in relocations.items() if f['value']<=a<f['value']+f['size']}
    pools={n:d for n,(_,d) in sections(obj).items() if n.startswith(('.rodata','.rdata','.data','.sdata','.lit','.bss','.sbss')) and d}
    if len(raw)!=1644 or hashlib.sha256(raw).hexdigest()!=RAW_SHA256 or bindings!=RELOCATIONS or pools:
        raise ValueError('Unknown frame-driver object/bindings/pools')
    return raw,bindings


def warning_sites(text,diagnostics):
    import re
    lines,source_lines=diagnostics.splitlines(),text.splitlines(keepends=True)
    if len(lines)!=12:raise ValueError('Changed frame-driver diagnostic count')
    result=[]
    for i,(name,expected) in enumerate(previous.WARNING_SITES):
        header,actual,caret=lines[i*3:i*3+3]
        match=re.fullmatch(r'cfe: Warning 712: [^\n]+, line (\d+): illegal combination of pointer and integer',header)
        returned=i==3 and actual.strip()=='return '+expected
        if match is None or actual.strip()!=(('return ' if returned else '')+expected):
            raise ValueError('Unknown frame-driver owner diagnostic')
        count=(9,28,12,46)[i]+(7 if returned else 0)
        if caret!=' '+'-'*count+'^':raise ValueError('Changed frame-driver warning column')
        number=int(match[1])
        if not 0<number<=len(source_lines) or source_lines[number-1].strip()!=actual.strip():
            raise ValueError('Warning does not identify its physical source line')
        offset=sum(map(len,source_lines[:number-1]))
        lo,hi=build.function_span(text,name)
        if not lo<=offset<hi:raise ValueError('Warning moved to another function')
        result.append((name,712,expected))
    return result


def guarded_manifest(out,obj):
    before=(out/'before-guards').read_bytes()
    parsed=csv.DictReader(io.StringIO(before.decode()))
    names=parsed.fieldnames
    if any(r['filename']==OWNER and r['function']==FUNCTION for r in parsed):
        raise ValueError('Frame driver already has guards')
    added=io.StringIO(newline='')
    writer=csv.DictWriter(added,fieldnames=names,lineterminator='\n')
    writer.writerows(derived_guards(obj))
    return before+added.getvalue().encode()


def checked_manifest(data,out,obj):
    if data!=guarded_manifest(out,obj):raise ValueError('Changed frame-driver guard fixture')
    return data


def qualify(root,out):
    obj,words,row=measure(root,out,'qualified',SELECTED)
    before=(out/'before-dispatch_owner').read_text()
    baseline,diagnostics=build.compile_owner(root,out,before,'neighbor-before')
    if warning_sites(before,diagnostics)!=warning_sites(recovered_owner(before,SELECTED),row['diagnostics']):
        raise ValueError('New frame-driver owner diagnostics')
    old,new=parse_object(baseline),parse_object(obj)
    if set(old[1])!=set(new[1]):raise ValueError('Frame-driver owner function set changed')
    binding=lambda parsed,f:{a-f['value']:rows for a,rows in parsed[2].items() if f['value']<=a<f['value']+f['size']}
    for name,f in old[1].items():
        if name==FUNCTION:continue
        g=new[1][name]
        if old[0][f['value']:f['value']+f['size']]!=new[0][g['value']:g['value']+g['size']] or binding(old,f)!=binding(new,g):
            raise ValueError('Frame-driver neighbor code/bindings changed: '+name)
    guards=guarded_manifest(out,obj)
    manifest=out/'qualified-guards.csv'
    if not manifest.exists():manifest.write_bytes(guards)
    checked_manifest(manifest.read_bytes(),out,obj)
    assembly=pad_c_object.emit_padded_assembly(obj,root/PATHS['layout'],OWNER,word_patches_path=manifest)
    path=out/'qualified-padded.s'
    path.write_text(assembly)
    padded=path.with_suffix('.o')
    subprocess.run(['mips-linux-gnu-as','-EB','-march=vr4300','-o',str(padded),str(path)],capture_output=True,check=True)
    data,functions=build.link_owner(root,out,padded,OWNER)
    f=functions[FUNCTION]
    slot=data[f['value']:f['value']+1648]
    truth=(out/'before-retail_rom').read_bytes()[ROM:ROM+1648]
    row=dict(row,slot_words=f['size']//4,new_guards=len(derived_guards(obj)),
        inserted_nops=1,slot_sha256=hashlib.sha256(slot).hexdigest(),byte_exact=slot==truth)
    (out/'qualification.json').write_text(json.dumps(row,indent=2)+'\n')
    if f['size']!=1648 or slot!=truth:
        differences=sum(a!=b for a,b in zip(struct.unpack('>412I',slot),struct.unpack('>412I',truth)))
        raise ValueError('Derived frame-driver guard schedule is not byte exact: %d words'%differences)
    return obj,padded,words,row


def slot_expected_image(before,slot):
    from tools.tests.test_game_record_constructor_match import elf_slot_offset
    from tools.tests.test_game_one_shot_timer_match import symbol_rows
    if hashlib.sha256(before).hexdigest()!=BASELINE['elf']:raise ValueError('Unknown frame-driver predecessor ELF')
    row=next(r for r in symbol_rows(before) if r[1]==FUNCTION)
    if row[2][1:3]!=(ENTRY,12) or len(slot)!=1648 or hashlib.sha256(slot).hexdigest()!=SLOT_SHA256:
        raise ValueError('Unknown frame-driver predecessor extent/slot')
    data=bytearray(before)
    at=elf_slot_offset(before,ENTRY,1648)
    data[at:at+1648]=slot
    struct.pack_into('>I',data,row[0]+8,1648)
    return bytes(data)


def expected_inputs(root,out):
    return dict(elf=serialize_metadata(slot_expected_image((out/'before-elf').read_bytes(),(out/'predicted-slot.bin').read_bytes())),
        dispatch_owner=recovered_owner((out/'before-dispatch_owner').read_text(),SELECTED).encode(),
        guards=(out/'qualified-guards.csv').read_bytes())


def serialize_metadata(data):
    from tools.tests import test_game_actor_burst_packet_match as symbols
    from tools.tests.test_game_one_shot_timer_match import canonical_symbols
    if hashlib.sha256(data).hexdigest()!=STRUCTURAL_SHA256:raise ValueError('Unknown frame-driver structural prediction')
    result=bytearray(data)
    with patch.object(symbols,'SERIALIZATION',SERIALIZATION):symbols.apply_burst_symbol_serialization(result)
    if canonical_symbols(result)!=canonical_symbols(data) or sum(a!=b for a,b in zip(data,result))!=111:
        raise ValueError('Changed frame-driver symbol/string serialization accounting')
    return bytes(result)


def prelink_prediction(root,out):
    _,padded,_,_=qualify(root,out)
    capture=out/'link-inputs.json'
    if not capture.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('Frame driver link capture must precede installation')
        (out/'before-linkscript').write_bytes((root/'conker/build/conker.ld').read_bytes())
        (out/'before-owner.o').write_bytes((root/'conker/build/src'/(OWNER+'.c.o')).read_bytes())
        capture.write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest()
            for n in ('before-linkscript','before-owner.o')},indent=2)+'\n')
    for name,digest in json.loads(capture.read_text()).items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Changed frame-driver link capture')
    link=(out/'before-linkscript').read_text()
    needle='build/src/'+OWNER+'.c.o(.text);'
    if link.count(needle)!=1:raise ValueError('Expected one frame-driver owner selector')
    for name,obj in (('baseline',out/'before-owner.o'),('prediction',padded)):
        script=out/(name+'.ld')
        script.write_text(link.replace(needle,str(obj.relative_to(root/'conker'))+'(.text);',1))
        result=subprocess.run(['mips-linux-gnu-ld','-T',str(script.relative_to(root/'conker')),
            '-T','undefined_syms.us.txt','-T','undefined_funcs.us.txt','-T','undefined_syms_auto.txt',
            '-T','undefined_funcs_auto.txt','--no-check-sections','--no-warn-mismatch',
            '-o',str((out/('prelink-'+name+'.elf')).relative_to(root/'conker'))],
            cwd=root/'conker',capture_output=True,text=True)
        if result.returncode:raise ValueError(result.stderr)
    before=(out/'before-elf').read_bytes()
    if (out/'prelink-baseline.elf').read_bytes()!=before:raise ValueError('Link inputs do not reproduce frame-driver predecessor')
    data,functions=build.link_owner(root,out,padded,OWNER)
    slot=data[functions[FUNCTION]['value']:functions[FUNCTION]['value']+1648]
    target=out/'predicted-slot.bin'
    if not target.exists():target.write_bytes(slot)
    if target.read_bytes()!=slot:raise ValueError('Changed first frame-driver slot prediction')
    expected=expected_inputs(root,out)
    predicted=(out/'prelink-prediction.elf').read_bytes()
    if predicted!=expected['elf']:raise ValueError('Frame driver link differs from complete slot/extent prediction')
    hashes={k:hashlib.sha256(v).hexdigest() for k,v in expected.items()}
    initial=out/'initial-prediction.json'
    if not initial.exists():
        if {k:hashlib.sha256((root/p).read_bytes()).hexdigest() for k,p in PATHS.items()}!=BASELINE:
            raise ValueError('Frame driver prediction must precede installation')
        initial.write_text(json.dumps(hashes,indent=2)+'\n')
    if json.loads(initial.read_text())!=hashes:raise ValueError('Changed first frame-driver prediction')
    row=dict(after=hashes,changed_ELF_bytes=sum(a!=b for a,b in zip(before,predicted)),
        metadata_exclusions=0,metadata_serialization_bytes=111,slot_bytes=1648,body_bytes=1644,new_guards=55,inserted_nops=1)
    (out/'prelink-prediction.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def forms():
    yield 'initial',INITIAL
    yield 'typed-global',typed_body(INITIAL)
    yield 'typed-light-pair',typed_body(light_pair(INITIAL))
    yield 'typed-light-pair-boolean',typed_body(light_pair(INITIAL)).replace(
        'overflow = (D_800BE9D0 - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4;',
        'overflow = ((D_800BE9D0 - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4) ? 1 : 0;')
    yield 'late-command-address',INITIAL.replace('Gfx **commands = (Gfx **)&D_800BE9D0;',
        'Gfx **commands;').replace('            *commands = (Gfx *)func_1501A680',
        '            commands = (Gfx **)&D_800BE9D0;\n            *commands = (Gfx *)func_1501A680',1)
    yield 'message-last',INITIAL.replace('    OSMesg message = NULL;\n','').replace('    Gfx **commands',
        '    OSMesg message = NULL;\n    Gfx **commands',1)
    yield 'saved-after-view',INITIAL.replace('    Gfx *savedCommands;\n    s16 view;',
        '    s16 view;\n    Gfx *savedCommands;')
    yield 'explicit-overflow',INITIAL.replace(
        'overflow = (*commands - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4;',
        'overflow = ((*commands - ((Gfx **)&D_800BE9C8)[D_800BE9C0]) > D_800BEBA4) ? 1 : 0;')
    yield 'recheck-disabled',INITIAL.replace('D_800BEAC0 = D_800BEAC1;\n                if (D_800BEAC0 != 0)',
        'D_800BEAC0 = D_800BEAC1;\n                if (*(volatile u8 *)&D_800BEAC0 != 0)')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--screens',action='store_true')
    p.add_argument('--profiles',action='store_true')
    p.add_argument('--interfaces-only',action='store_true')
    p.add_argument('--qualify',action='store_true')
    p.add_argument('--prelink',action='store_true')
    args=p.parse_args()
    if args.qualify or args.prelink:
        row=prelink_prediction(args.root,args.root/BUILD) if args.prelink else qualify(args.root,args.root/BUILD)[-1]
        print(json.dumps(row,indent=2))
        return
    rows=[('initial',INITIAL,('-O2','-g3'))]
    if args.screens:rows=[(name,body,('-O2','-g3')) for name,body in forms()]
    if args.profiles:rows=[('profile-'+name,INITIAL,flags) for name,flags in
        (('o2g3',('-O2','-g3')),('o2',('-O2',)),('o1g3',('-O1','-g3')))]
    if args.interfaces_only:rows=[('interfaces-only',INITIAL,('-O2','-g3'))]
    for name,body,flags in rows:
        try:row=measure(args.root,args.root/BUILD,name,body,flags,args.interfaces_only)[2]
        except subprocess.CalledProcessError as error:
            row=dict(label=name,status='compiler_profile_rejected',flags=flags,diagnostics=error.stderr)
            (args.root/BUILD/(name+'-rejected.json')).write_text(json.dumps(row,indent=2)+'\n')
            print(json.dumps(row),flush=True)
            continue
        print(json.dumps({k:row[k] for k in ('label','words','frame','differences','diagnostics','raw_sha256')}),flush=True)


if __name__=='__main__':main()
