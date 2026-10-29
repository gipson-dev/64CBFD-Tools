"""Path-node gate: semantic C, checked normalization and literal image audit."""
from pathlib import Path
import hashlib,json,re,struct,subprocess
from collections import Counter
from tools.experiments.game_remaining_donor_candidates import compile_owner,link_owner,function_span
from tools.experiments.game_four_head_lookup_match import payload as function_payload
from tools.experiments.game_actor_state_tick_integration import same_functions,elf_slot_offset,symbol_rows
import sys
sys.path.insert(0,str(Path.cwd()/'tools'))
from tools.pad_c_object import emit_padded_assembly
from tools.tests.game_owner_pool import normalized_pools
from tools.match_progress import load_elf_functions
from tools.check_game_data_layout import audit_layout
FUNCTION,OWNER='func_1507B974','game_A28B0'
ENTRY,ROM,BODY,SIZE=0x1507B974,0xA8E24,212,212
SOURCE='conker/src/game_A28B0.c'
OBJECT='conker/build/src/game_A28B0.c.o'
ASM='conker/retail_layout.us.txt'
LAYOUT='conker/retail_layout.us.txt'
BUILD='conker/build/game-path-node-gate-match'
RODATA_SYMBOL=None
RAW_SHA='12f74897e681a69f4ba76a54c5f8b1a1ce23c073375b1b68b1e4a635191289cc'
SNAPSHOT_SHA='eda04e4366a67516366c3826dd922705a594ed16651195d8aceffdd51d73d5d8'
BEFORE_ELF_SHA='c87acd173db00d4dab0aa26c42b4d5327ae436e94d716985c057ddebe3b0ef45'
TRUTH_SHA='82f082c81dba1d2a66a9bd9bd405488aa37a67d4cd2e02f18b60690cbd102f4f'
BINDINGS={8: [('R_MIPS_HI16', 'D_800D154C')], 12: [('R_MIPS_LO16', 'D_800D154C')], 16: [('R_MIPS_HI16', 'D_800CC2D0')], 20: [('R_MIPS_LO16', 'D_800CC2D0')], 28: [('R_MIPS_HI16', 'D_800D2104')], 88: [('R_MIPS_LO16', 'D_800D2104')], 32: [('R_MIPS_HI16', 'D_800D1893')], 108: [('R_MIPS_LO16', 'D_800D1893')], 128: [('R_MIPS_HI16', 'D_800D1891')], 132: [('R_MIPS_LO16', 'D_800D1891')], 140: [('R_MIPS_HI16', 'D_800D1892')], 144: [('R_MIPS_LO16', 'D_800D1892')], 168: [('R_MIPS_HI16', 'D_800D1892')], 172: [('R_MIPS_LO16', 'D_800D1892')], 152: [('R_MIPS_HI16', 'D_800D1890')], 192: [('R_MIPS_LO16', 'D_800D1890')], 188: [('R_MIPS_26', 'func_15075400')]}
ORIGINAL_BINDINGS={8: [('R_MIPS_HI16', 'D_800D154C')], 12: [('R_MIPS_LO16', 'D_800D154C')], 16: [('R_MIPS_HI16', 'D_800CC2D0')], 20: [('R_MIPS_LO16', 'D_800CC2D0')], 32: [('R_MIPS_HI16', 'D_800D2104')], 88: [('R_MIPS_LO16', 'D_800D2104')], 100: [('R_MIPS_HI16', 'D_800D1893')], 112: [('R_MIPS_LO16', 'D_800D1893')], 28: [('R_MIPS_HI16', 'D_800D1891')], 136: [('R_MIPS_LO16', 'D_800D1891')], 140: [('R_MIPS_HI16', 'D_800D1892')], 144: [('R_MIPS_LO16', 'D_800D1892')], 168: [('R_MIPS_HI16', 'D_800D1892')], 172: [('R_MIPS_LO16', 'D_800D1892')], 188: [('R_MIPS_26', 'func_15075400')], 152: [('R_MIPS_HI16', 'D_800D1890')], 192: [('R_MIPS_LO16', 'D_800D1890')]}
HEADERS='#include <ultra64.h>\n#include "variables.h"\nvoid func_15075400(s32);\n'
DECLARATIONS=''
SELECTED='/* Toggle the selected path-record key gate before the optional script step. */\nvoid func_1507B974(void) {\n    struct127 *actor = D_800D154C;\n    u8 *node;\n\n    if (actor->unk65 != 0) {\n        actor = &D_800CC2D0[actor->unk65 - 1];\n    }\n    node = ((u8 **)D_800D2104)[actor->unk13F];\n    node += actor->unk21E * 8;\n    node += D_800D1893 * 8;\n    if (D_800D1891 == *(u16 *)(node + 6)) {\n        D_800D1892 ^= 1;\n    }\n    if (D_800D1892 != 0) {\n        func_15075400(D_800D1890);\n    }\n}\n'

def check_owner_diagnostics(diagnostics,text):
    def context(m):
        line=int(m[2]);lines=text.splitlines()
        if not 1<=line<=len(lines):raise ValueError('Invalid diagnostic source location')
        return m[1]+'<'+lines[line-1].strip()+'>'+m[3]
    normalized=re.sub(r'(?m)^(cfe: [^\n]*?: )[^\n]+?, line (\d+)(: [^\n]+)$',context,diagnostics)
    if diagnostics.count('cfe: Warning')!=14 or sha(normalized.encode())!='9473c032a9f1128692445cdfed68b83c2a3fcdf75a830a340910995604fc9c11':raise ValueError('Inherited path-node owner diagnostics changed')
    return 14


sha=lambda b:hashlib.sha256(b).hexdigest()

def payload(obj):return function_payload(obj,FUNCTION)

def checked_payload(raw,bindings):
    if len(raw)!=212 or sha(raw)!=RAW_SHA or bindings!=BINDINGS:raise ValueError('Path-node gate body/bindings changed')
    return raw,bindings

def recovered_owner(before):
    start,end=function_span(before,FUNCTION)
    if before[start:end]!='s32 func_1507B974() {\n    return 0;\n}':raise ValueError('Path-node placeholder changed')
    after=before[:start]+SELECTED.rstrip()+before[end:]
    declaration='s32 func_1507B974();'
    if after.count(declaration)!=1:raise ValueError('Path-node declaration changed')
    after=after.replace(declaration,'void func_1507B974(void);',1)
    marker='/* Non-matching C placeholders for asm/nonmatchings/game_A28B0/func_1507B974.s. */\n'
    if after.count(marker)!=1:raise ValueError('Path-node placeholder marker changed')
    after=after.replace(marker,'',1)
    start=after.index('// NON-MATCHING: dont think D_800D2104 is correct')
    end=after.index('void func_1507BA48',start)
    return after[:start]+after[end:]




def snapshot(output):
    data=(output/'input-snapshot.json').read_bytes()
    if sha(data)!=SNAPSHOT_SHA:raise ValueError('Path-node gate snapshot changed')
    values={}
    for name,wanted in json.loads(data)['INPUTS'].items():
        b=(output/('before-'+name.replace('/','_'))).read_bytes()
        if sha(b)!=wanted:raise ValueError('Path-node gate frozen input changed: '+name)
        values[name]=b
    if sha(values['conker/build/conker.us.elf'])!=BEFORE_ELF_SHA:raise ValueError('Path-node gate predecessor changed')
    return values

def check_inputs(root,output,installed=False):
    values=snapshot(output);changes={}
    if installed:changes={'conker/retail_word_patches.us.csv':guard_manifest(values['conker/retail_word_patches.us.csv']),SOURCE:recovered_owner(values[SOURCE].decode()).encode(),OBJECT:(output/'qualified-padded.o').read_bytes(),'conker/build/conker.us.elf':predicted_image(values['conker/build/conker.us.elf'],values['conker/conker.us.bin'][ROM:ROM+SIZE])}
    for name,b in values.items():
        if(root/name).read_bytes()!=changes.get(name,b):raise ValueError('Path-node gate live input differs: '+name)
    return values

METADATA_GROUPS=()
def reorder_metadata(before,result):
 rows={p:(n,f,s)for p,n,f,s in symbol_rows(before)}
 for first,names,order in METADATA_GROUPS:
  group=[rows[first+16*i]for i in range(len(names))]
  if tuple(n for n,_,_ in group)!=names:raise ValueError('Path-node gate named metadata group changed')
  strings=b''.join(n.encode()+b'\0'for n in names);start=group[0][2]
  if before[start:start+len(strings)]!=strings:raise ValueError('Path-node gate symbol-name block changed')
  offset=0;name_offset=group[0][1][0]
  for slot,index in enumerate(order):
   name,fields,_=group[index];encoded=name.encode()+b'\0';struct.pack_into('>IIIBBH',result,first+16*slot,name_offset+offset,*fields[1:]);result[start+offset:start+offset+len(encoded)]=encoded;offset+=len(encoded)
  if offset!=len(strings):raise ValueError('Path-node gate metadata length changed')


def predicted_image(before,truth):
    if sha(before)!=BEFORE_ELF_SHA or len(truth)!=SIZE or sha(truth)!=TRUTH_SHA:raise ValueError('Path-node gate frozen image changed')
    result=bytearray(before);at=elf_slot_offset(before,ENTRY,SIZE);result[at:at+SIZE]=truth
    rows=[x for x in symbol_rows(before)if x[1]==FUNCTION]
    if len(rows)!=1 or rows[0][2][1:3]!=(ENTRY,12):raise ValueError('Path-node gate original extent changed')
    struct.pack_into('>I',result,rows[0][0]+8,BODY)
    reorder_metadata(before,result)
    return bytes(result)

def check_image(before,actual,truth):
    if actual!=predicted_image(before,truth):raise ValueError('Path-node gate strict whole image mismatch')
    expected=Counter((n,f[1],BODY if n==FUNCTION else f[2],*f[3:])for _,n,f,_ in symbol_rows(before));observed=Counter((n,*f[1:])for _,n,f,_ in symbol_rows(actual))
    if expected!=observed:raise ValueError('Path-node gate named definitions changed')

NEW_GUARDS=[{'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x008', 'expected': '0x3C030000', 'replacement': '0x3C020000', 'expected_relocations': 'R_MIPS_HI16:D_800D154C', 'replacement_relocations': 'R_MIPS_HI16:D_800D154C', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x00C', 'expected': '0x8C630000', 'replacement': '0x8C430000', 'expected_relocations': 'R_MIPS_LO16:D_800D154C', 'replacement_relocations': 'R_MIPS_LO16:D_800D154C', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x018', 'expected': '0x90620065', 'replacement': '0x90640065', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x01C', 'expected': '0x3C190000', 'replacement': '0x3C190000', 'expected_relocations': 'R_MIPS_HI16:D_800D2104', 'replacement_relocations': 'R_MIPS_HI16:D_800D1891', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x020', 'expected': '0x3C0D0000', 'replacement': '0x3C080000', 'expected_relocations': 'R_MIPS_HI16:D_800D1893', 'replacement_relocations': 'R_MIPS_HI16:D_800D2104', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x024', 'expected': '0x1040000B', 'replacement': '0x1080000B', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x028', 'expected': '0x00027080', 'replacement': '0x00047080', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x02C', 'expected': '0x01C27023', 'replacement': '0x01C47023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x034', 'expected': '0x01C27021', 'replacement': '0x01C47021', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x03C', 'expected': '0x01C27023', 'replacement': '0x01C47023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x044', 'expected': '0x01C27023', 'replacement': '0x01C47023', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x054', 'expected': '0x9068013F', 'replacement': '0x9069013F', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x058', 'expected': '0x8F390000', 'replacement': '0x8D080000', 'expected_relocations': 'R_MIPS_LO16:D_800D2104', 'replacement_relocations': 'R_MIPS_LO16:D_800D2104', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x05C', 'expected': '0x906B021E', 'replacement': '0x906D021E', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x060', 'expected': '0x00084880', 'replacement': '0x00095080', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x064', 'expected': '0x03295021', 'replacement': '0x3C180000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_HI16:D_800D1893', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x068', 'expected': '0x8D420000', 'replacement': '0x010A5821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x06C', 'expected': '0x91AD0000', 'replacement': '0x8D6C0000', 'expected_relocations': 'R_MIPS_LO16:D_800D1893', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x070', 'expected': '0x000B60C0', 'replacement': '0x93180000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800D1893', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x074', 'expected': '0x004C1021', 'replacement': '0x000D70C0', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x078', 'expected': '0x000D70C0', 'replacement': '0x018E7821', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x07C', 'expected': '0x004E1021', 'replacement': '0x001848C0', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x080', 'expected': '0x3C0F0000', 'replacement': '0x01E94021', 'expected_relocations': 'R_MIPS_HI16:D_800D1891', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x084', 'expected': '0x91EF0000', 'replacement': '0x950A0006', 'expected_relocations': 'R_MIPS_LO16:D_800D1891', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x088', 'expected': '0x94580006', 'replacement': '0x93390000', 'expected_relocations': '-', 'replacement_relocations': 'R_MIPS_LO16:D_800D1891', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x094', 'expected': '0x15F80004', 'replacement': '0x172A0004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x09C', 'expected': '0x90480000', 'replacement': '0x904B0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x0A0', 'expected': '0x39190001', 'replacement': '0x396D0001', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x0A4', 'expected': '0xA0590000', 'replacement': '0xA04D0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x0B0', 'expected': '0x90490000', 'replacement': '0x904C0000', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}, {'filename': 'game_A28B0', 'function': 'func_1507B974', 'offset': '0x0B4', 'expected': '0x51200004', 'replacement': '0x51800004', 'expected_relocations': '-', 'replacement_relocations': '-', 'note': 'Normalize closed path-node gate register allocation and independent address scheduling', 'insert_after': '', 'insert_after_relocations': '', 'omit': 'false'}]

def guard_manifest(before):
    if sha(before)!='65c9328a853ce794c22026870f8b38fc55eabfe2e58856edf652f053882ee113':raise ValueError('Inherited guard prefix changed')
    return before+b'game_A28B0,func_1507B974,0x008,0x3C030000,0x3C020000,R_MIPS_HI16:D_800D154C,R_MIPS_HI16:D_800D154C,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x00C,0x8C630000,0x8C430000,R_MIPS_LO16:D_800D154C,R_MIPS_LO16:D_800D154C,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x018,0x90620065,0x90640065,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x01C,0x3C190000,0x3C190000,R_MIPS_HI16:D_800D2104,R_MIPS_HI16:D_800D1891,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x020,0x3C0D0000,0x3C080000,R_MIPS_HI16:D_800D1893,R_MIPS_HI16:D_800D2104,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x024,0x1040000B,0x1080000B,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x028,0x00027080,0x00047080,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x02C,0x01C27023,0x01C47023,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x034,0x01C27021,0x01C47021,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x03C,0x01C27023,0x01C47023,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x044,0x01C27023,0x01C47023,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x054,0x9068013F,0x9069013F,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x058,0x8F390000,0x8D080000,R_MIPS_LO16:D_800D2104,R_MIPS_LO16:D_800D2104,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x05C,0x906B021E,0x906D021E,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x060,0x00084880,0x00095080,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x064,0x03295021,0x3C180000,-,R_MIPS_HI16:D_800D1893,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x068,0x8D420000,0x010A5821,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x06C,0x91AD0000,0x8D6C0000,R_MIPS_LO16:D_800D1893,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x070,0x000B60C0,0x93180000,-,R_MIPS_LO16:D_800D1893,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x074,0x004C1021,0x000D70C0,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x078,0x000D70C0,0x018E7821,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x07C,0x004E1021,0x001848C0,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x080,0x3C0F0000,0x01E94021,R_MIPS_HI16:D_800D1891,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x084,0x91EF0000,0x950A0006,R_MIPS_LO16:D_800D1891,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x088,0x94580006,0x93390000,-,R_MIPS_LO16:D_800D1891,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x094,0x15F80004,0x172A0004,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x09C,0x90480000,0x904B0000,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x0A0,0x39190001,0x396D0001,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x0A4,0xA0590000,0xA04D0000,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x0B0,0x90490000,0x904C0000,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\ngame_A28B0,func_1507B974,0x0B4,0x51200004,0x51800004,-,-,Normalize closed path-node gate register allocation and independent address scheduling,,,false\r\n'






def normalized_payload(raw,bindings):
    checked_payload(raw,bindings);result=bytearray(raw);relocations=dict(bindings)
    parse=lambda text:[]if text=='-'else[tuple(v.split(':',1))for v in text.split(';')]
    for row in NEW_GUARDS:
        at=int(row['offset'],0)
        if struct.unpack_from('>I',result,at)[0]!=int(row['expected'],0)or bindings.get(at,[])!=parse(row['expected_relocations']):raise ValueError('Path-node gate expected word or binding changed')
        struct.pack_into('>I',result,at,int(row['replacement'],0));relocations.pop(at,None)
        if row['replacement_relocations']!='-':relocations[at]=parse(row['replacement_relocations'])
    if sha(result)!='6fdf051ebcccc24a319c68dc04ab94926023612351cc32aa6e888dc54dbaa81e'or relocations!=ORIGINAL_BINDINGS:raise ValueError('Path-node gate normalized body/bindings changed')
    return bytes(result),relocations



ARTIFACTS=('before-padded.o','qualified-padded.o','proposed-owner.c','selected.o','original-func_1507B974.o','first-linked.elf')
EVIDENCE=('proposed-guards.csv', 'before-owner.c', 'before-owner-processed.c', 'before-owner.o', 'before-owner-diagnostics.txt', 'after-owner.c', 'after-owner-processed.c', 'after-owner.o', 'after-owner-diagnostics.txt', 'selected.c', 'selected-processed.c', 'selected.o', 'selected-diagnostics.txt', 'selected-best-input.c', 'make-shadow/src/game_A28B0.c.o.compact', 'actual-Make-plan.txt', 'Make-commands.json', 'actual-Make-diagnostics.txt', 'make-shadow/src/game_A28B0.c.o', 'make-shadow/src/game_A28B0.c.o.padded.s')

def verify_prepared(output):
    rows=json.loads((output/'artifact-fingerprint.json').read_text())
    if set(rows)!=set(ARTIFACTS):raise ValueError('Path-node gate artifact set changed')
    for name,wanted in rows.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Path-node gate artifact changed: '+name)
    for name,wanted in json.loads((output/'frozen-raw.json').read_text()).items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Path-node gate raw evidence changed: '+name)
    extra=json.loads((output/'canonical-prepared-fingerprint.json').read_text())
    if set(extra)!=set(EVIDENCE):raise ValueError('Path-node gate evidence set changed')
    for name,wanted in extra.items():
        if sha((output/name).read_bytes())!=wanted:raise ValueError('Path-node gate Make/diagnostics evidence changed: '+name)
    if(output/'selected-diagnostics.txt').read_bytes():raise ValueError('Unexpected selected diagnostics')
    for n in('before-owner','after-owner','actual-Make'):check_owner_diagnostics((output/(n+'-diagnostics.txt')).read_text(),(output/('before-owner.c'if n=='before-owner'else'after-owner.c')).read_text())
    if(output/'make-shadow/src/game_A28B0.c.o').read_bytes()!=(output/'qualified-padded.o').read_bytes():raise ValueError('Path-node gate Make object differs')
    q=json.loads((output/'preparation.json').read_text())
    if not q['complete'] or q['matching_credit']!=0 or q['guards']!=31 or q['exclusions']!=0:raise ValueError('Path-node gate private qualification changed')
    return dict(rows,**extra)

def audit(root,output):
    values=check_inputs(root,output,True);old=values['conker/build/conker.us.elf'];actual=(root/'conker/build/conker.us.elf').read_bytes();check_image(old,actual,values['conker/conker.us.bin'][ROM:ROM+SIZE])
    a,_,aa=load_elf_functions(str(output/'before-conker_build_conker.us.elf'),'mips-linux-gnu-objdump');b,_,bb=load_elf_functions(str(root/'conker/build/conker.us.elf'),'mips-linux-gnu-objdump')
    if a.keys()!=b.keys()or aa!=bb or[n for n in a if a[n]!=b[n]]!=[FUNCTION]:raise ValueError('Path-node gate changed another linked body/address')
    data=audit_layout(root/'conker/build/conker.us.elf',root/'conker')
    if(data['exact'],data['bytes'],data['owner_count'],data['different_bytes'])!=(True,189088,720,0):raise ValueError('Path-node gate protected data changed')
    q=dict(functions=len(a),other_bodies_fixed=len(a)-1,all_addresses_fixed=True,target_words=53,frame=24,alignment_words=0,slot_words=53,strict_first_link_reproduced=True,guards=31,game_data=data);(output/'installed-audit.json').write_text(json.dumps(q,indent=2)+'\n');return q
