"""Observe the pinned rectangle allocator without steering colors or emitted code."""
import argparse
import json
from pathlib import Path
import struct
from unittest.mock import patch

from tools.experiments import game_packet_rectangle_compiler_trace as previous

BUILD='conker/build/game-packet-rectangle-allocator'
ALLOCATION_SCRIPT=previous.allocation_script
POINTS={0x47FE70:'global-entry',0x480212:'initialized',0x480DA0:'rank',
    0x480FC0:'chosen',0x48041A:'unconstrained',0x41DE10:'compute-save',
    0x480384:'unconstrained-evaluate',0x4648F0:'needsplit',0x434130:'local-entry'}
OBSERVERS=r'''
rect_sequence=0

def rect_word(mem,address):
    return int.from_bytes(gdb.selected_inferior().read_memory(mem+address,4),'little')

def rect_row(mem,index,units=False):
    count=rect_word(mem,0x1001cb38)
    table=rect_word(mem,0x1001cc30)
    if not 0<=index<count<10000 or not 0<table<0x80000000:
        raise gdb.GdbError('Invalid rectangle allocation table')
    read=lambda address,size:bytes(gdb.selected_inferior().read_memory(mem+address,size))
    slot=read(table+index*8,8)
    ichain=int.from_bytes(slot[:4],'little')
    live=int.from_bytes(slot[4:],'little')
    if not 0<ichain<0x80000000 or not 0<live<0x80000000:
        raise gdb.GdbError('Missing rectangle allocation row')
    head=read(live,60)
    result=dict(index=index,table_entry=slot.hex(),ichain=ichain,
        ichain_prefix=read(ichain,16).hex(),live=live,head=head.hex())
    if units:
        seen=set()
        cursor=int.from_bytes(head[8:12],'little')
        result['units']=[]
        while cursor:
            if cursor in seen or len(seen)>=128:
                raise gdb.GdbError('Unbounded rectangle live units')
            seen.add(cursor)
            raw=read(cursor,24)
            node=int.from_bytes(raw[:4],'little')
            result['units'].append(dict(address=cursor,raw=raw.hex(),node=node,
                node_prefix=read(node,48).hex()))
            cursor=int.from_bytes(raw[4:8],'little')
    return result

def rect_record(event,mem,index=None,**extra):
    global rect_sequence
    inferior=gdb.selected_inferior()
    if gdb.current_progspace().filename!=RECT_PROGRAM or rect_sequence>=3000:
        raise gdb.GdbError('Rectangle allocator ownership/event bound failed')
    rect_sequence+=1
    units=event=='initialized' or event.endswith('-return')
    rows=[rect_row(mem,i,units) for i in (123,137)]
    active=None if index is None else rect_row(mem,index)
    record=dict(sequence=rect_sequence,event=event,inferior=inferior.num,pid=inferior.pid,
        host_pc=int(gdb.parse_and_eval('$pc')),count=rect_word(mem,0x1001cb38),
        table=rect_word(mem,0x1001cc30),rows=rows,active=active,**extra)
    gdb.write('RECT_COLOR '+json.dumps(record,sort_keys=True)+'\n')

class RectReturned(gdb.FinishBreakpoint):
    def __init__(self,event,mem,index=None):
        self.event,self.mem,self.index=event,mem,index
        super().__init__(gdb.newest_frame(),internal=True)
    def stop(self):
        extra=dict(eax=int(gdb.parse_and_eval('$eax'))&0xffffffff) if self.event=='needsplit' else {}
        rect_record(self.event+'-return',self.mem,self.index,**extra)
        return False

class RectObserve(gdb.Breakpoint):
    def __init__(self,address,event):
        self.event=event
        super().__init__('*0x%x'%address,internal=True)
    def stop(self):
        event=self.event
        if event in ('global-entry','local-entry','compute-save','needsplit'):
            mem=int(gdb.parse_and_eval('$rdi'))
        elif event.startswith('unconstrained'):
            mem=int(gdb.parse_and_eval('$r15'))
        else:
            mem=int(gdb.parse_and_eval('$r14'))
        if event in ('global-entry','local-entry'):
            rect_record(event,mem)
            RectReturned(event,mem)
        elif event=='initialized':
            rect_record(event,mem)
        elif event in ('compute-save','needsplit'):
            live=int(gdb.parse_and_eval('$edx' if event=='compute-save' else '$esi'))&0xffffffff
            matches=[i for i in (123,137) if rect_row(mem,i)['live']==live]
            if matches:
                rect_record(event,mem,matches[0])
                RectReturned(event,mem,matches[0])
        else:
            index=rect_word(mem,0xfffff5c if event=='chosen' else 0xfffff60)
            if event=='chosen' or index in (123,137):
                extra=dict(best_bits=bytes(gdb.selected_inferior().read_memory(0x4b0ac0,4)).hex()) if event in ('rank','unconstrained-evaluate') else {}
                if event=='unconstrained-evaluate':
                    extra.update(gain_bits=bytes(gdb.selected_inferior().read_memory(0x4b0ad8,4)).hex(),
                        chosen_reg=rect_word(mem,0xfffff2c),eflags=int(gdb.parse_and_eval('$eflags')))
                rect_record(event,mem,index,**extra)
        return False
'''


def allocation_script(root):
    script=ALLOCATION_SCRIPT(root)
    anchor='import json\ndef trace_exit(event):'
    install="    gdb.execute('set follow-fork-mode parent')"
    cleanup="('*0x422830', '*0x484590')"
    if any(script.count(item)!=1 for item in (anchor,install,cleanup)):
        raise ValueError('Changed qualified allocator observation anchors')
    program=json.dumps(str((root/'ido/ido5.3_recomp/uopt').resolve()))
    script=script.replace(anchor,'import json\nRECT_PROGRAM='+program+'\n'+OBSERVERS+'\ndef trace_exit(event):',1)
    created=''.join('    RectObserve(%d,%r)\n'%(address,event) for address,event in POINTS.items())
    marker="    gdb.write('RECT_COLOR_INSTALLED\\n')\n"
    script=script.replace(install,created+marker+install,1)
    locations=tuple(['*0x422830','*0x484590']+['*0x%x'%address for address in POINTS])
    script=script.replace(cleanup,repr(locations),1)
    return script.replace("gdb.write('RECT_ALLOC_REMOVED\\n')", "gdb.write('RECT_COLOR_REMOVED\\n')\ngdb.write('RECT_ALLOC_REMOVED\\n')",1)


def decode(row):
    head=bytes.fromhex(row['head'])
    slot=bytes.fromhex(row['table_entry'])
    ichain=bytes.fromhex(row['ichain_prefix'])
    if len(head)!=60 or len(slot)!=8 or len(ichain)!=16:
        raise ValueError('Truncated allocator row')
    words=struct.unpack('<15I',head)
    expression=struct.unpack_from('<I',ichain)[0]&65535
    if (struct.unpack('<II',slot)!=(row['ichain'],row['live']) or words[0]!=row['ichain'] or
            words[1]!=row['index'] or row['index'] in (123,137) and expression!=row['index']):
        raise ValueError('Allocator table/range/ichain identity mismatch')
    assigned=words[8]>>24
    return dict(index=row['index'],expression=expression,assigned=assigned if assigned<128 else assigned-256,
        regsleft=(words[8]>>16)&255,hasstore=(words[8]>>8)&255,save_state=words[8]&255,
        divisor=words[7],interference=words[9],save_bits='%08x'%words[12],
        forbidden=[i for i in range(64) if words[10+i//32]&(0x80000000>>(i&31))])


def checked_units(row):
    cursor=struct.unpack_from('<I',bytes.fromhex(row['head']),8)[0]
    seen=set()
    for unit in row['units']:
        raw=bytes.fromhex(unit['raw'])
        node=bytes.fromhex(unit['node_prefix'])
        if (len(raw)!=24 or len(node)!=48 or not cursor or cursor in seen or
                unit['address']!=cursor or len(seen)>=128):
            raise ValueError('Broken allocator live-unit chain')
        seen.add(cursor)
        pointer,cursor,owner=struct.unpack_from('<III',raw)
        if pointer!=unit['node'] or not 0<pointer<0x80000000 or owner!=row['live']:
            raise ValueError('Broken allocator unit/node ownership')
    if cursor:
        raise ValueError('Truncated allocator live-unit chain')


def checked_events(lines,events,constraints):
    installed=json.loads(next(line[21:] for line in lines if line.startswith('RECT_ALLOC_INSTALLED ')))
    begin,end=lines.index('RECT_COLOR_INSTALLED'),lines.index('RECT_COLOR_REMOVED')
    positions=[i for i,line in enumerate(lines) if line.startswith('RECT_COLOR ')]
    child='TRACE_EXIT inferior=%d code=0'%installed['inferior']
    if not begin<min(positions)<=max(positions)<lines.index(child)<end<lines.index('RECT_ALLOC_REMOVED'):
        raise ValueError('Misordered allocator probe lifecycle')
    if len({(e['inferior'],e['pid'],e['table']) for e in events})!=1:
        raise ValueError('Changed allocator process/table ownership')
    if events[0]['inferior']!=installed['inferior'] or events[0]['pid']<=0:
        raise ValueError('Wrong allocator child ownership')
    returns={0x48FC16:'local-entry-return',0x4813A1:'needsplit-return',
        0x4825AD:'compute-save-return',0x48FC86:'global-entry-return'}
    addresses=POINTS.copy()
    addresses.update(returns)
    critical={row['index']:(row['ichain'],row['live']) for row in events[0]['rows']}
    for event in events:
        if addresses.get(event['host_pc'])!=event['event']:
            raise ValueError('Wrong allocator probe instruction')
        for row in event['rows']:
            if (row['ichain'],row['live'])!=critical[row['index']]:
                raise ValueError('Changed critical allocator pointers')
            if event['event']=='initialized' or event['event'].endswith('-return'):
                checked_units(row)
        if event['active'] and event['active']['index'] in critical:
            snapshot=next(r for r in event['rows'] if r['index']==event['active']['index'])
            if event['active']!={k:v for k,v in snapshot.items() if k!='units'}:
                raise ValueError('Inconsistent active allocator row')
        if event['event']=='needsplit' and (event['sequence']>=len(events) or
                events[event['sequence']]['event']!='needsplit-return'):
            raise ValueError('Missing allocator needsplit return')
        if event['event']=='needsplit-return':
            before=events[event['sequence']-2]
            if before['event']!='needsplit' or before['active']['index']!=event['active']['index'] or event.get('eax')!=0:
                raise ValueError('Wrong allocator needsplit return')
    route=[(e['event'],e['active']['index'] if e['active'] else None) for e in events]
    tail=[(name,index) for index in (123,137) for name in
        ('unconstrained','compute-save','compute-save-return','unconstrained-evaluate')]
    if (len(events)!=75 or route[:4]!=[(n,None) for n in
            ('local-entry','local-entry-return','global-entry','initialized')] or
            route[-9:]!=tail+[('global-entry-return',None)] or
            sum(e['event']=='chosen' for e in events)!=18 or any(e['event']=='rank' for e in events)):
        raise ValueError('Changed observed allocator ordinal route')
    for index,save,gain,cost,color,flags in ((123,'40000000','00008040','00000000',12,514),
            (137,'3fc00000','00004040','00006c41',14,515)):
        endrow=next(e for e in events if e['event']=='unconstrained-evaluate' and e['active']['index']==index)
        active=decode(endrow['active'])
        if (endrow['gain_bits'],endrow['best_bits'],endrow['chosen_reg'],endrow['eflags'],
                active['save_bits'],active['divisor'])!=(gain,cost,color,flags,save,2):
            raise ValueError('Changed allocator cost-gate operands')
        gain_value=struct.unpack('<f',bytes.fromhex(gain))[0]
        cost_value=struct.unpack('<f',bytes.fromhex(cost))[0]
        if bool(endrow['eflags']&1)!=(gain_value<cost_value):
            raise ValueError('Inconsistent allocator cost-gate comparison')
        initial=decode(next(e for e in events if e['event']=='unconstrained' and e['active']['index']==index)['active'])
        final=decode(next(r for r in events[-1]['rows'] if r['index']==index))
        printed=next(r for r in constraints if r['expression']==index)
        expected_forbidden=list(range(1,12 if index==123 else 13))
        if (initial['forbidden'],initial['regsleft'],final['assigned'],printed['color'],printed['forbidden'])!=(
                expected_forbidden,11 if index==123 else 10,12 if index==123 else 0,
                12 if index==123 else 0,expected_forbidden):
            raise ValueError('Allocator native/printed constraints disagree')


def validate(root,work):
    allocation=previous.validate_allocation(root,work)
    log=(work/'debugger.txt').read_text()
    lines=log.splitlines()
    if any(marker in log for marker in ('Python Exception','Error in sourced','RECT_COLOR_ERROR')):
        raise ValueError('Allocator probe error')
    if (work/'compiler-child.gdb').read_text()!=allocation_script(root):
        raise ValueError('Changed allocator observer script')
    if lines.count('RECT_COLOR_INSTALLED')!=1 or lines.count('RECT_COLOR_REMOVED')!=1:
        raise ValueError('Missing allocator probe lifecycle')
    events=[json.loads(line[11:]) for line in lines if line.startswith('RECT_COLOR ')]
    if not events or [e['sequence'] for e in events]!=list(range(1,len(events)+1)):
        raise ValueError('Missing/reordered allocator sequence')
    for event in events:
        if [row['index'] for row in event['rows']]!=[123,137] or not 137<event['count']<10000:
            raise ValueError('Missing allocator critical rows')
        for row in event['rows']+([event['active']] if event['active'] else []):
            decode(row)
    names=[e['event'] for e in events]
    for name in ('global-entry','initialized','global-entry-return','local-entry','local-entry-return'):
        if names.count(name)!=1:
            raise ValueError('Incomplete allocator stage: '+name)
    for index in (123,137):
        for stage in ('unconstrained','compute-save','compute-save-return','unconstrained-evaluate'):
            if sum(e['event']==stage and e['active']['index']==index for e in events)!=1:
                raise ValueError('Allocator ordinal/cost probe did not fire')
    checked_events(lines,events,allocation['constraints'])
    return dict(events=events,constraints=allocation['constraints'],installable=False)


def trace(root,out,label):
    with patch.object(previous,'allocation_script',allocation_script):
        previous.trace_allocation(root,out,label,previous.source.SELECTED,5)
    work=out/('allocation-'+label+'-5')
    result=validate(root,work)
    (work/'allocator-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    result=trace(args.root,args.root/BUILD,args.name)
    for event in result['events']:
        if event['event'] in ('rank','unconstrained','unconstrained-evaluate','global-entry-return'):
            print(json.dumps(dict(sequence=event['sequence'],event=event['event'],
                active=decode(event['active']) if event['active'] else None,
                critical=[decode(row) for row in event['rows']],
                gates={k:event[k] for k in ('best_bits','gain_bits','chosen_reg','eflags') if k in event})),flush=True)


if __name__=='__main__':
    main()
