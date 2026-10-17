"""Ordered ISA accesses and complete modeled state, including real factory/copy code."""
from tools.tests import game_transition_completion_oracle as previous
from tools.tests import game_view_point_projection_oracle as point


class BurstOracle(previous.CompletionOracle):
    def __init__(self,*args,**kwargs):
        self.io=[]
        super().__init__(*args,**kwargs)

    def get(self,address,size):
        value=super().get(address,size)
        if self.own_instruction:self.io.append(('R',address,size,value))
        return value

    def put(self,address,value,size):
        super().put(address,value,size)
        if self.recording and self.own_instruction:self.io.append(('W',address,size,value&((1<<(size*8))-1)))


def state(machine):
    return (point.state(machine),machine.io,machine.rng,machine.floats,machine.hi,machine.lo,
        machine.condition,machine.active_descriptor,machine.dispatched_word)
