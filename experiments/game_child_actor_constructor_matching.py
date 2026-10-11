"""Closed full-frame, actor-base, register-cycle and scheduling normalization."""
import csv
import io
import struct
from tools.experiments import game_child_actor_constructor_candidates as recovery
from tools.experiments.game_actor_attachment_update_matching import register
from tools.pad_generated_object import parse_object

ENTRY, ROM, WORDS = recovery.ENTRY, recovery.ROM, recovery.WORDS
FUNCTION, SOURCE, SELECTED = recovery.FUNCTION, recovery.SOURCE, recovery.SELECTED
RAW = tuple(int(word, 16) for word in '''
27BDFFB0 AFB2001C AFB10018 AFB00014 00808025 00E08825 00A09025 AFBF0024
AFB30020 AFA60058 8FA40058 0C000000 00002825 8FA40058 0C000000 00002825
0C000000 00000000 3C030000 24630000 00437023 2401032C 01C1001A 00007812
241800FF 030FC823 A059003B A05100AB 8FA80060 00409825 00402025 AC480000
0C000000 AFA30028 8FA40058 24060001 240900FF A2660232 A26601CA A2690125
8FAA0028 2401032C 00002825 020A5823 0161001A 00006012 258D0001 A26D0065
AE72005C A2660123 A2640004 92020066 A2620066 3043FFEF A2630066 A2630066
920E01DD A26E01DD 921801DE A27801DE 920F01DE 8FA20068 A26F01DF 921901E0
A27901E0 920801E1 A26801E1 920901E2 14400009 A26901E2 3C013F80 44810000
00000000 E660014C E6600150 E6600154 10000009 E6600158 C604014C E664014C
C6060150 E6660150 C6080154 E6680154 C60A0158 E66A0158 8FB00064 A2620101
0C000000 A27000AC 320A0001 11400014 320F0002 8E6B00F8 3C180000 3C014F80
356C4000 AE6C00F8 8FAD0058 000D7080 030EC021 8F180000 9702000E C670014C
44829000 04410004 46809120 44813000 00000000 46062100 46048202 E6680270
11E00003 AFA00040 24190001 AFB90040 3C120000 26520000 8E480000 00008825
02608025 0502000B 00115080 0C000000 24040001 AE020304 8E490000 26310001
26100004 0131082A 1020FFF8 00000000 00115080 01535821 8D6C0300 240D0001
11800002 00000000 A26D0301 0C000000 00000000 AE620314 3C0E0000 91CE0000
24010001 02602025 15C10003 00003025 10000002 24100001 00008025 12000002
3C010000 A0200000 0C000000 8FA50058 8FB80028 2401032C 8FA50058 02782023
0081001A 00002012 24060001 0C000000 00000000 02602025 8FA5006C 8FA60040
0C000000 8FA70070 12000004 02601025 24190001 3C010000 A0390000 8FBF0024
8FB00014 8FB10018 8FB2001C 8FB30020 03E00008 27BD0050
'''.split())
RELOCATIONS = {
    44: [('R_MIPS_26', 'func_1503D774')],
    56: [('R_MIPS_26', 'func_1503D660')],
    64: [('R_MIPS_26', 'func_1505ED34')],
    72: [('R_MIPS_HI16', 'D_800CC2D0')],
    76: [('R_MIPS_LO16', 'D_800CC2D0')],
    128: [('R_MIPS_26', 'func_150615DC')],
    352: [('R_MIPS_26', 'func_1503D774')],
    376: [('R_MIPS_HI16', 'D_800D1C90')],
    404: [('R_MIPS_LO16', 'D_800D1C90')],
    464: [('R_MIPS_HI16', 'D_80082FA0')],
    468: [('R_MIPS_LO16', 'D_80082FA0')],
    492: [('R_MIPS_26', 'func_1515D480')],
    556: [('R_MIPS_26', 'func_1515D440')],
    568: [('R_MIPS_HI16', 'D_800C35EA')],
    572: [('R_MIPS_LO16', 'D_800C35EA')],
    608: [('R_MIPS_HI16', 'D_800C3638')],
    612: [('R_MIPS_LO16', 'D_800C3638')],
    616: [('R_MIPS_26', 'func_150839B8')],
    652: [('R_MIPS_26', 'func_150837D4')],
    672: [('R_MIPS_26', 'func_150838EC')],
    692: [('R_MIPS_HI16', 'D_800C3638')],
    696: [('R_MIPS_LO16', 'D_800C3638')]
}


def gp(word, mapping):
    op, rs = word >> 26, word >> 21 & 31
    if op in (2, 3): return word
    if op == 17:
        fields = (16,) if rs in (0, 4) else ()
    elif op == 0:
        fields = (21, 16, 11)
    elif op == 1:
        fields = (21,)
    elif op in (49, 53, 57, 61):
        fields = (21,)
    else:
        fields = (21, 16)
    for shift in fields:
        value = word >> shift & 31
        word = register(word, shift, mapping.get(value, value))
    return word


def fp(word, mapping):
    op, rs = word >> 26, word >> 21 & 31
    fields = ((11,) if rs in (0, 4) else (16, 11, 6) if rs in (16, 20) else ()) if op == 17 else (16,) if op in (49, 53, 57, 61) else ()
    for shift in fields:
        value = word >> shift & 31
        word = register(word, shift, mapping.get(value, value))
    return word


def recipe(words):
    if tuple(words) != RAW:
        raise ValueError('stale complete child actor constructor body')
    code = [(gp(w, {18:19, 19:18}), RELOCATIONS.get(i*4, [])) for i,w in enumerate(words)]
    for i in (178,179): code[i] = (words[i], [])
    def edit(i, word): code[i] = (word, code[i][1])
    edit(0, code[0][0] + 24)
    edit(181, code[181][0] - 24)
    edit(1, code[1][0] + 4)
    edit(8, code[8][0] - 4)
    for i,w in enumerate(words):
        if w >> 26 in (35,43) and w >> 21 & 31 == 29 and (w & 65535) >= 0x50:
            edit(i, code[i][0] - 24)
    for i in (113,115,167): edit(i, code[i][0] - 20)

    # Initial actor-base and slot computation; delay the value store into its call.
    for i in range(18,32):
        edit(i, gp(code[i][0], {3:14,14:15,15:24,24:25,25:8,8:9}))
    def mapped(i, mapping): return gp(code[i][0], mapping), code[i][1]
    base_hi = mapped(18, {14:11})
    base_lo = mapped(19, {14:11})
    parent_map = {6:3,9:10,10:11,11:12,12:13,13:14,2:25,3:8}
    parent = [base_hi,base_lo] + [mapped(i,parent_map) for i in
        (43,41,44,34,35,45,36,46,37,38,39,47,48,49,50,51,42,52,53,54,55)]
    out = code[:31] + [code[32],code[31]] + parent
    assert len(out) == 56
    out += [mapped(i,{14:9,24:10,15:11,25:12,8:13,9:14}) for i in range(56,70)]
    out += code[70:90]

    # Convert unsigned magnitude in F16/F18, then load scale in F6 and multiply.
    magnitude_map = {10:15,15:12,11:25,24:10,12:24,13:8,14:9,2:11}
    floating_map = {16:6,18:16,4:18,6:4}
    magnitude = []
    for i in (90,91,92,93,94,95,96,97,98,99,100,101,102,104,105,106,107,108,109,103,110,111):
        word,uses = mapped(i,magnitude_map)
        word = fp(word,floating_map)
        if i == 110:
            left,right = word >> 11 & 31,word >> 16 & 31
            word = register(register(word,11,right),16,left)
        magnitude.append((word,uses))
    out += magnitude
    assert len(out) == 112

    # The same inclusive live-limit loop, with closed temporaries and index sum.
    loop_map = {15:12,25:13,8:14,9:15,10:25,11:24,12:8,13:9,14:10}
    for i in range(112,156):
        word,uses = mapped(i,loop_map)
        if i == 133:
            left,right = word >> 21 & 31,word >> 16 & 31
            word = register(register(word,21,right),16,left)
        out.append((word,uses))

    # Rematerialize the constant base instead of reading the removed private spill.
    out += [base_hi,base_lo,mapped(159,{24:11}),code[157],code[160],code[161],
        code[158],code[163],code[162]]
    out += code[165:172]
    out += [mapped(172,{25:13}),code[173],mapped(174,{25:13})]
    out += code[175:]
    assert len(out) == WORDS
    return out


def guard_rows(path):
    text, functions, relocations = parse_object(path)
    target = functions[FUNCTION]
    if target['size'] != 728: raise ValueError('unexpected complete child constructor extent')
    start = target['value']
    relative = {o-start:uses for o,uses in relocations.items() if start <= o < start+target['size']}
    if relative != RELOCATIONS: raise ValueError('stale complete child constructor relocations')
    words = struct.unpack_from('>182I',text,start)
    fitted = recipe(words)
    def encode(uses): return ';'.join(kind+':'+symbol for kind,symbol in uses) or '-'
    return [dict(filename='generated_AEB40',function=FUNCTION,offset='0x%X'%(i*4),
        expected='0x%08X'%old,replacement='0x%08X'%new,
        expected_relocations=encode(relative.get(i*4,[])),replacement_relocations=encode(uses),
        note='Check complete child constructor; normalize closed frame base register schedule',
        insert_after='',insert_after_relocations='',omit='false')
        for i,(old,(new,uses)) in enumerate(zip(words,fitted))]


def compile_candidate(root,out,name,body=SELECTED,profile='o2g3'):
    return recovery.compile_candidate(root,out,name,body,profile)


def append_guards(path,before,obj):
    if path.read_bytes()!=before or not before.endswith(b'\n'):
        raise ValueError('stale child constructor guard manifest')
    reader = csv.DictReader(io.StringIO(before.decode('ascii')))
    if any(row['function']==FUNCTION for row in reader):
        raise ValueError('child constructor guards already published')
    output = io.StringIO(newline='')
    csv.DictWriter(output,fieldnames=reader.fieldnames,lineterminator='\n').writerows(guard_rows(obj))
    path.write_bytes(before+output.getvalue().encode('ascii'))
