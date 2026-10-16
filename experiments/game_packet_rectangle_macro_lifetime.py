"""Inspect the selected rectangle's macro homes before another source decision."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from types import SimpleNamespace
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_middle as engine
from tools.experiments import game_packet_rectangle_flip_capture as selected
from tools.experiments import game_packet_rectangle_compiler_trace as compiler
from tools.tests import packet_rectangle_flip_capture_checkpoint as checkpoint
from tools.experiments.game_packet_rectangle_lifetime import shape

BUILD='conker/build/game-packet-rectangle-macro-lifetime'
OWNER,FUNCTION,ENTRY,ROM,WORDS=selected.OWNER,selected.FUNCTION,selected.ENTRY,selected.ROM,selected.WORDS
PATHS=selected.PATHS
BASELINE=dict(selected.BASELINE,**checkpoint.AFTER)
INITIAL=SELECTED=selected.SELECTED
build=selected.build
FRAME_SCRIPT=compiler.debugger_script
TEMP_POINTS={0x4174D0:'gettemp',0x450490:'spilltemps',0x450902:'spill-selected'}
TEMP_OBSERVERS=r'''
macro_sequence=0
macro_owned=[]

def macro_pool(mem):
    result=[]
    cursor=u32(mem,0x1001c4b8)
    seen=set()
    while cursor:
        if not 0<cursor<0x80000000 or cursor in seen or len(result)>=64:
            raise gdb.GdbError('Unbounded UOPT macro temporary pool')
        seen.add(cursor)
        raw=bytes(gdb.selected_inferior().read_memory(mem+cursor,20))
        result.append(dict(pointer=cursor,raw=raw.hex()))
        cursor=int.from_bytes(raw[16:20],'little')
    return result

def macro_record(event,mem,**extra):
    global macro_sequence
    if Path(gdb.current_progspace().filename)!=compiler_dir/'uopt' or macro_sequence>=1000:
        raise gdb.GdbError('Wrong macro compiler ownership/event bound')
    macro_sequence+=1
    gdb.write('RECT_TEMP '+json.dumps(dict(sequence=macro_sequence,event=event,
        inferior=gdb.selected_inferior().num,pid=gdb.selected_inferior().pid,
        host_pc=int(gdb.parse_and_eval('$pc')),extent=u32(mem,0x1001c4b4),
        head=u32(mem,0x1001c4b8),tail=u32(mem,0x1001c4bc),
        count=u32(mem,0x1001e680),pool=macro_pool(mem),**extra),sort_keys=True)+'\n')

class MacroReturned(gdb.FinishBreakpoint):
    def __init__(self,event,mem,extra):
        self.event,self.mem,self.extra=event,mem,extra
        super().__init__(gdb.newest_frame(),internal=True)
    def stop(self):
        extra=dict(self.extra)
        if self.event=='gettemp':
            extra['result']=u32(self.mem,extra['destination'])
        macro_record(self.event+'-return',self.mem,**extra)
        return False

class MacroObserve(gdb.Breakpoint):
    def __init__(self,address,event):
        self.event=event
        super().__init__('*0x%x'%address,internal=True)
    def stop(self):
        event=self.event
        mem=int(gdb.parse_and_eval('$r14' if event=='spill-selected' else '$rdi'))
        if event=='spill-selected':
            frame=int(gdb.parse_and_eval('$ebp'))&0xffffffff
            ichain=u32(mem,frame+0xa0)
            macro_record(event,mem,index=u32(mem,frame+0xbc),temporary=u32(mem,frame+0x94),
                ichain=ichain,ichain_raw=bytes(gdb.selected_inferior().read_memory(mem+ichain,40)).hex())
        else:
            extra=dict(caller=int(gdb.newest_frame().older().pc()))
            if event=='gettemp':
                extra.update(destination=int(gdb.parse_and_eval('$edx'))&0xffffffff,
                    size=int(gdb.parse_and_eval('$ecx'))&0xffffffff)
            macro_record(event,mem,**extra)
            MacroReturned(event,mem,extra)
        return False
'''


def debugger_script(root,work):
    script=FRAME_SCRIPT(root,work)
    anchor='class FrameChanged(gdb.Breakpoint):'
    install='capture()\nif gdb.current_progspace().filename == '
    cleanup="    Begin('f_readuinstr.constprop.0')"
    if any(script.count(a)!=1 for a in (anchor,install,cleanup)):
        raise ValueError('Changed qualified macro observation anchors')
    script=script.replace(anchor,TEMP_OBSERVERS+'\n'+anchor,1)
    created=''.join('    macro_owned.append(MacroObserve(%d,%r))\n'%(a,e) for a,e in TEMP_POINTS.items())
    script=script.replace(install,"capture()\nif Path(gdb.current_progspace().filename)==compiler_dir/'uopt':\n"+
        created+"    gdb.write('RECT_TEMP_INSTALLED\\n')\nif gdb.current_progspace().filename == ",1)
    return script.replace(cleanup,"    for observer in macro_owned:\n        observer.delete()\n"
        "    gdb.write('RECT_TEMP_REMOVED\\n')\n"+cleanup,1)


def gate_script(root,work):
    script=debugger_script(root,work)
    anchor='def macro_record(event,mem,**extra):'
    call='temporary=u32(mem,frame+0x94),\n'
    if script.count(anchor)!=1 or script.count(call)!=1:
        raise ValueError('Changed qualified temporary-gate anchors')
    observer=r'''
def macro_forbidden(mem):
    blocks=u32(mem,0x1001e5c8)
    pointer=u32(mem,0x1001e5cc)
    if not 0<=blocks<=8 or blocks and not 0<pointer<0x80000000:
        raise gdb.GdbError('Unbounded UOPT temporary forbidden vector')
    raw=bytes(gdb.selected_inferior().read_memory(mem+pointer,blocks*16)) if blocks else b''
    return dict(blocks=blocks,pointer=pointer,raw=raw.hex())
'''
    return script.replace(anchor,observer+'\n'+anchor,1).replace(call,call.rstrip('\n')+
        'forbidden=macro_forbidden(mem),\n',1)


def freeze(root,out):
    with patch.object(engine,'BASELINE',BASELINE):
        engine.freeze(root,out)


def recovered_owner(before,body=None):
    lo,hi=build.function_span(before,FUNCTION)
    if before[lo:hi]!=INITIAL.split('\n',1)[1].rstrip():
        raise ValueError('Unknown rectangle macro-lifetime predecessor')
    return before[:lo]+(SELECTED if body is None else body).split('\n',1)[1].rstrip()+before[hi:]


def measure(root,out,label='selected',body=None):
    with patch.multiple(engine,BASELINE=BASELINE,recovered_owner=recovered_owner):
        return engine.measure(root,out,label,SELECTED if body is None else body)


def forms():
    yield 'predecessor',INITIAL
    corners=(('integerX','(s32)((u32)integerX << 2)'),
        ('integerY','(s32)((u32)integerY << 2)'),
        ('right','(s32)((u32)((s32)((f32)widthAdjust + width - 1.0f) + integerX) << 2)'),
        ('bottom','(s32)((u32)((s32)(height - 1.0f) + integerY) << 2)'))
    for label,roles in (('scales',('integerScaleX','integerScaleY')),
            ('dead-integers',('numerator','animationDelta'))):
        for order in ('XY','YX'):
            body=INITIAL
            assignments={}
            for role,(_,value) in zip(roles,corners[2:]):
                body=body.replace(value,role,1)
                assignments[role]='    '+role+' = '+value+';\n'
            low=''
            for role,value in corners[:2]:
                body=body.replace(value,role,1)
                low+='    '+role+' = '+value+';\n'
            high=''.join(assignments[role] for role in (roles if order=='XY' else roles[::-1]))
            body=body.replace('    gSPScisTextureRectangle',high+low+'    gSPScisTextureRectangle',1)
            yield 'phase-corners-'+label+'-'+order,body
    body=INITIAL
    assignments=''
    for role,value in corners[:2]:
        name='quarter'+role[-1]
        body=body.replace('    s32 animationDelta;', '    s32 '+name+';\n    s32 animationDelta;',1)
        body=body.replace(value,name,1)
        assignments+='    '+name+' = '+value+';\n'
    yield 'named-low-control',body.replace('    gSPScisTextureRectangle',assignments+'    gSPScisTextureRectangle',1)
    for kind in ('unsigned-product','wide-product','wide-shift'):
        for roles in (('integerX',),('integerY',),('integerX','integerY')):
            body=INITIAL
            for role,value in corners[:2]:
                if role not in roles:
                    continue
                if kind=='unsigned-product':
                    replacement='(s32)((u32)'+role+' * 4u)'
                elif kind=='wide-product':
                    replacement='(s32)((s64)'+role+' * 4)'
                else:
                    replacement='(s32)((u64)(s64)'+role+' << 2)'
                body=body.replace(value,replacement,1)
            yield 'low-'+kind+'-'+''.join(role[-1] for role in roles),body
    for roles in (('S',),('T',),('S','T')):
        body=INITIAL
        for role in roles:
            value='originalStepS' if role=='S' else 'stepT'
            body=body.replace('(u16)(0u - (u32)'+value+')',
                '(s32)((0u - (u32)'+value+') & 0xFFFFu)',1)
        yield 'flip-mask-'+''.join(roles),body
    pairs=(('integerX','integerY'),('textureS','textureT'),('fractionalT','animationDelta'))
    for mask in range(1,8):
        body=INITIAL
        for bit,(first,second) in enumerate(pairs):
            if mask&(1<<bit):
                old='    s32 '+first+';\n    s32 '+second+';'
                if body.count(old)!=1:
                    raise ValueError('Changed macro role declaration pair')
                body=body.replace(old,'    s32 '+second+';\n    s32 '+first+';',1)
        yield 'declarations-'+str(mask),body
    yield 'declarations-flag-before-fraction',INITIAL.replace('    s32 flipFlags;\n','').replace(
        '    s32 fractionalT;','    s32 flipFlags;\n    s32 fractionalT;',1)
    for roles in (('X',),('Y',),('X','Y')):
        body=INITIAL
        for role in roles:
            field='unk4' if role=='X' else 'unk6'
            body=body.replace('(packet->descriptor->'+field+' + 255) << 5',
                '((u32)packet->descriptor->'+field+' + 255u) << 5',1)
        yield 'dimension-unsigned-'+''.join(roles),body


def trace(root,out,label,temps=False,gates=False):
    adapter=SimpleNamespace(FUNCTION=FUNCTION,build=build,freeze=freeze,measure=measure,recovered_owner=recovered_owner)
    with patch.object(compiler,'source',adapter),patch.object(compiler,'SIGNATURES',dict(
            compiler.SIGNATURES,**selected.TRACE_SIGNATURE)):
        if temps:
            with patch.object(compiler,'debugger_script',gate_script if gates else debugger_script):
                result=compiler.trace(root,out,label,SELECTED)
        else:
            result=compiler.trace(root,out,label,SELECTED)
    return {k:result[k] for k in ('label','normal','code_unchanged','record_counts','installable')}


def allocation_trace(root,out,label):
    adapter=SimpleNamespace(FUNCTION=FUNCTION,build=build,freeze=freeze,measure=measure,recovered_owner=recovered_owner)
    with patch.object(compiler,'source',adapter),patch.object(compiler,'SIGNATURES',dict(
            compiler.SIGNATURES,**selected.TRACE_SIGNATURE)):
        result=compiler.trace_allocation(root,out,label,SELECTED,5)
    return {k:result[k] for k in ('label','mode','normal','code_unchanged','installable')}


def validate_capture(root,work,temps=False,gates=False):
    with patch.object(compiler,'SIGNATURES',dict(compiler.SIGNATURES,**selected.TRACE_SIGNATURE)):
        result=compiler.validate(root,work)
    script=(gate_script if gates else debugger_script)(root,work) if temps else FRAME_SCRIPT(root,work)
    if (work/'ugen-frame.gdb').read_text()!=script:
        raise ValueError('Changed macro observation script')
    receipt=json.loads((work/'receipt.json').read_text())
    expected=(346,136,18,'f95ee415f2eba533fa4076e5f6c42331367bf3444eb855a78b7816f598dc48c3',
        '9227400f8ff743be1839c55d4b574abd1b970397e83fd781fb8dacf7baf03f26',True)
    if tuple(receipt['baseline'][k] for k in ('words','frame','differences','raw_sha256',
            'source_sha256','isolated_matches_full_owner'))!=expected:
        raise ValueError('Wrong selected macro compiler body')
    return result


def decoded_pool(event):
    rows=[]
    for node in event['pool']:
        raw=bytes.fromhex(node['raw'])
        if len(raw)!=20 or not 0<node['pointer']<0x80000000:
            raise ValueError('Truncated/invalid UOPT temporary node')
        index,offset,size,flags,nxt=struct.unpack('<IiIII',raw)
        if flags not in (0,0x1000000):
            raise ValueError('Invalid UOPT temporary availability byte')
        rows.append(dict(pointer=node['pointer'],index=index,offset=offset,size=size,
            available=bool(flags),next=nxt))
    if (event['count']!=len(rows) or event['extent']!=120+4*len(rows) or len(rows)>6 or
            event['head']!=(rows[0]['pointer'] if rows else 0) or
            event['tail']!=(rows[-1]['pointer'] if rows else 0) or
            len({r['pointer'] for r in rows})!=len(rows)):
        raise ValueError('Broken UOPT temporary pool ownership/extent')
    for index,row in enumerate(rows):
        if (row['index'],row['offset'],row['size'],row['next'])!=(index,-124-index*4,4,
                rows[index+1]['pointer'] if index+1<len(rows) else 0):
            raise ValueError('Broken UOPT temporary chain/size/displacement')
    return rows


def checked_temp_events(events,constraints):
    selections=[(18,0),(73,0),(107,1),(135,2),(145,3),(156,0),(235,0),(262,0),
        (303,1),(316,1),(335,2),(347,2),(349,1),(354,3),(355,4),(357,1),
        (381,2),(389,2),(393,4),(401,5)]
    route=['spilltemps']+['spill-selected']*20+['spilltemps-return','gettemp','gettemp-return']
    if ([e['sequence'] for e in events]!=list(range(1,25)) or
            [e['event'] for e in events]!=route or len({(e['inferior'],e['pid']) for e in events})!=1):
        raise ValueError('Wrong UOPT temporary sequence/process route')
    for event in events:
        rows=decoded_pool(event)
        expected_pc={'spilltemps':0x450490,'spill-selected':0x450902,
            'spilltemps-return':0x48FC31,'gettemp':0x4174D0,'gettemp-return':0x438F1C}[event['event']]
        if event['host_pc']!=expected_pc:
            raise ValueError('Wrong UOPT temporary probe instruction')
        if event['event']=='spill-selected':
            index,temporary=selections[event['sequence']-2]
            raw=bytes.fromhex(event['ichain_raw'])
            if (event['index']!=index or event['temporary']!=rows[temporary]['pointer'] or len(raw)!=40 or
                    not 0<event['ichain']<0x80000000 or struct.unpack_from('<I',raw)[0]&65535!=index):
                raise ValueError('Wrong UOPT temporary expression assignment')
        elif event['event'].startswith('gettemp'):
            if event['size']!=4 or event['caller']!=0x438F1C or not 0<event['destination']<0x80000000:
                raise ValueError('Wrong UOPT gettemp call boundary')
        elif event['caller']!=0x48FC31:
            raise ValueError('Wrong UOPT spilltemps call boundary')
    before,after=events[-2:]
    old,new=decoded_pool(before),decoded_pool(after)
    if ([r['available'] for r in old]!=[True]*4+[False]*2 or
            [r['available'] for r in new]!=[False]+[True]*3+[False]*2 or
            before['destination']!=after['destination'] or after['result']!=new[0]['pointer']):
        raise ValueError('Wrong UOPT gettemp reuse observation')
    picked={row['expression']:row for row in constraints}
    members=[[] for _ in range(6)]
    blockers={}
    for index,slot in selections:
        conflicts=set(picked[index]['interference'])
        if any(member in conflicts for member in members[slot]):
            raise ValueError('UOPT temporary reuse contradicts interference')
        if index in (347,354):
            blockers[index]=[sorted(conflicts.intersection(group)) for group in members[:slot]]
            if not all(blockers[index]):
                raise ValueError('Missing first-fit UOPT temporary blocker')
        members[slot].append(index)
    if (blockers!={347:[[73,235],[107]],354:[[235],[107,349],[347]]} or
            [picked[i]['color'] for i in (18,73,107,135,145,347,354)]!=[29,3,6,12,0,0,0]):
        raise ValueError('Changed UOPT native/constraint correspondence')
    return dict(events=len(events),selected_expressions=len(selections),pool_count=6,
        intermediate_extent=144,emitted_M_extent=136,blockers=blockers,
        no_gettemp_absence_claim=True,installable=False)


def checked_gate_events(events,constraints):
    result=checked_temp_events(events,constraints)
    direct={}
    for event in events:
        if event['event']!='spill-selected':
            continue
        vector=event['forbidden']
        raw=bytes.fromhex(vector['raw'])
        if vector['blocks']!=4 or len(raw)!=64 or not 0<vector['pointer']<0x80000000 or any(raw[4:]):
            raise ValueError('Wrong native temporary forbidden-vector snapshot')
        bits=struct.unpack_from('<I',raw)[0]
        pool=decoded_pool(event)
        forbidden=[i for i in range(32) if bits&(0x80000000>>i)]
        if any(i>=len(pool) for i in forbidden):
            raise ValueError('Native forbidden bit is outside the temporary pool')
        free=next((r for r in pool if r['index'] not in forbidden),None)
        if free is None or free['pointer']!=event['temporary']:
            raise ValueError('Native first-fit temporary gate contradicts selected home')
        if event['index'] in (347,354):
            direct[event['index']]=dict(forbidden=forbidden,selected=free['index'],offset=free['offset'])
    if direct!={347:dict(forbidden=[0,1],selected=2,offset=-132),
            354:dict(forbidden=[0,1,2],selected=3,offset=-136)}:
        raise ValueError('Changed native macro temporary blockers')
    return dict(result,native_gates=direct)


def validate_temps(root,work,constraints,gates=False):
    parsed=validate_capture(root,work,True,gates)
    log=(work/'debugger.txt').read_text()
    lines=log.splitlines()
    if lines.count('RECT_TEMP_INSTALLED')!=1 or lines.count('RECT_TEMP_REMOVED')!=1:
        raise ValueError('Missing UOPT temporary lifecycle')
    positions=[i for i,line in enumerate(lines) if line.startswith('RECT_TEMP ')]
    if not positions:
        raise ValueError('UOPT temporary observer did not fire')
    events=[json.loads(lines[i][10:]) for i in positions]
    child=parsed['inputs'][0]['inferior']
    if (events[0]['inferior']!=child or events[0]['pid']<=0 or not
            lines.index('RECT_TEMP_INSTALLED')<min(positions)<=max(positions)<
            lines.index('TRACE_EXIT inferior=%d code=0'%child)<lines.index('RECT_TEMP_REMOVED')):
        raise ValueError('Misordered/unowned UOPT temporary lifetime')
    pid=events[0]['pid']
    if ('process %d is executing new program: %s'%(pid,(root/'ido/ido5.3_recomp/uopt').resolve()) not in lines or
            '[Inferior %d (process %d) exited normally]'%(child,pid) not in lines):
        raise ValueError('Wrong UOPT temporary child process')
    return (checked_gate_events if gates else checked_temp_events)(events,constraints)


def validate_all(root,out):
    freeze(root,out)
    plain=validate_capture(root,out/'compiler-selected-qualified')
    instrumented=validate_capture(root,out/'compiler-selected-temp-pool',True)
    gated=validate_capture(root,out/'compiler-selected-pool-gates',True,True)
    if plain['records']!=instrumented['records'] or plain['records']!=gated['records']:
        raise ValueError('Temporary probes changed compiler streams')
    with patch.object(compiler,'SIGNATURES',dict(compiler.SIGNATURES,**selected.TRACE_SIGNATURE)):
        allocation=compiler.validate_allocation(root,out/'allocation-selected-qualified-5')
    row=validate_temps(root,out/'compiler-selected-temp-pool',allocation['constraints'])
    row['gated_capture']=validate_temps(root,out/'compiler-selected-pool-gates',allocation['constraints'],True)
    row['record_counts']={k:len(v) for k,v in plain['records'].items()}
    (out/'qualified-evidence.json').write_text(json.dumps(row,indent=2)+'\n')
    return row


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    kind=parser.add_mutually_exclusive_group(required=True)
    kind.add_argument('--trace')
    kind.add_argument('--allocation')
    kind.add_argument('--screens',action='store_true')
    kind.add_argument('--validate',action='store_true')
    parser.add_argument('--temps',action='store_true')
    parser.add_argument('--gates',action='store_true')
    parser.add_argument('--filter',default='')
    args=parser.parse_args()
    if args.validate:
        print(json.dumps(validate_all(args.root,args.root/BUILD),indent=2))
        return
    if args.screens:
        for label,body in forms():
            if args.filter and args.filter not in label:
                continue
            row=measure(args.root,args.root/BUILD,label,body)[2]
            physical=shape(args.root/BUILD,label)
            print(json.dumps(dict({k:row[k] for k in ('label','words','frame','differences','diagnostics')},
                **{k:physical[k] for k in ('prefix','suffix','slot_suffix')})),flush=True)
        return
    if args.allocation:
        print(json.dumps(allocation_trace(args.root,args.root/BUILD,args.allocation),indent=2))
        return
    print(json.dumps(trace(args.root,args.root/BUILD,args.trace,args.temps or args.gates,args.gates),indent=2))


if __name__=='__main__':
    main()
