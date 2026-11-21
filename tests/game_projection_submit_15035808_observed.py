from tools.tests import game_projection_submit_15035808_oracle as g
class Observed(g.Oracle):
    def __init__(self,*args):super().__init__(*args);self.actual_calls=[];self.frames=[]
    def frame(self):return tuple(self.memory[g.STACK+self.c.phase+i]for i in range(-216,40))
    def record_call(self,target):
        super().record_call(target);self.actual_calls.append((target,self.actual_args));self.frames.append(self.frame())
    def hook(self,target):
        super().hook(target)
