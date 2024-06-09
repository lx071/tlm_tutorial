import simpy
from utils import *

class Initiator(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.socket = Socket(self)
        self.env.process(self.thread_process())
        pass

    def thread_process(self):
        delay = SC_NS(10)
        trans = Generic_Payload()
        trans.set_data_ptr(12)
        trans.set_response_status(tlm_response_status.TLM_INCOMPLETE_RESPONSE, self.socket)
        # self.socket.b_transport(trans, delay)
        yield self.env.process(self.socket.b_transport(trans, delay))
        yield self.env.timeout(delay)
        pass

class Memory(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.socket = Socket(self)
        self.socket.register_b_transport(self.b_transport)

    def b_transport(self, trans: Generic_Payload, delay):
        print("Memory::b_transport")
        data = trans.get_data_ptr()
        print("data:", data)
        trans.set_response_status(tlm_response_status.TLM_OK_RESPONSE, self.socket.other_socket)
        yield self.env.timeout(0)
        pass

class Top(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.initiator = Initiator(env, "initiator")
        self.memory = Memory(env, "memory")
        self.initiator.socket.bind(self.memory.socket)


if __name__ == '__main__':
    env = simpy.Environment()
    top = Top(env, 'top')
    env.run()
