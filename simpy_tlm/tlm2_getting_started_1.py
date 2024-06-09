import simpy
from utils import *
import random

# Shows the generic payload, sockets, and blocking transport interface.
# Shows the responsibilities of initiator and target with respect to the generic payload.
# Has only dummy implementations of the direct memory and debug transaction interfaces.
# Does not show the non-blocking transport interface.

class ResponseError(Exception):
    pass

# Initiator module generating generic payload transactions
class Initiator(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.socket = Socket(self)  # Construct and name socket
        self.env.process(self.thread_process())
        # Internal data buffer used by initiator with generic payload
        self.data = [None]

    def thread_process(self):
        # TLM-2 generic payload transaction, reused across calls to b_transport
        trans = Generic_Payload()
        delay = 10
        # delay = SC_NS(10)
        
        # Generate a random sequence of reads and writes
        for i in range(32, 96, 4):
            cmd = random.randint(0, 1)
            if(cmd == tlm_command.TLM_WRITE_COMMAND):
                self.data = [0xFF000000 | i]

            # Initialize 8 out of the 10 attributes, byte_enable_length and extensions being unused
            trans.set_command( cmd )
            trans.set_address( i )
            trans.set_data_ptr( self.data )
            trans.set_data_length( 4 )
            trans.set_streaming_width( 4 )  # = data_length to indicate no streaming
            trans.set_byte_enable_ptr( 0 )  # 0 indicates unused
            trans.set_dmi_allowed( False )  # Mandatory initial value
            trans.set_response_status( tlm_response_status.TLM_INCOMPLETE_RESPONSE, self.socket ); # Mandatory initial value

            # self.socket.b_transport(trans, delay)
            yield self.env.process(self.socket.b_transport(trans, delay))   # Blocking transport call
            
            # Initiator obliged to check response status and delay
            if ( trans.is_response_error() ):
                print("TLM-2", "Response error from b_transport")
                raise ResponseError("Response error from b_transport")
            
            # print("trans = { %s, %#x }, data = %#x at time %d delay = %d" % ('W' if cmd == 1 else 'R', i, self.data[0], self.env.now, delay))
            print("trans = ( {}, {} ), data = {} at time {} delay = {}"
                  .format('W' if cmd == 1 else 'R',
                          hex(i),
                          hex(self.data[0]),
                          self.env.now,
                          delay))
            
            # Realize the delay annotated onto the transport call
            yield self.env.timeout(delay)


# Target module representing a simple memory
class Memory(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        self.socket = Socket(self)
        # Register callback for incoming b_transport interface method call
        self.socket.register_b_transport(self.b_transport)
        
        # Initialize memory with random data
        self.mem = [0] * 256
        for i in range(256):
            self.mem[i] = 0xAA000000 | random.randint(0, 256)

    # TLM-2 blocking transport method
    def b_transport(self, trans: Generic_Payload, delay):

        # print("Memory::b_transport")
        
        cmd = trans.get_command()
        adr = trans.get_address()
        ptr = trans.get_data_ptr()
        len = trans.get_data_length()
        byt = trans.get_byte_enable_ptr()
        wid = trans.get_streaming_width()

        # Obliged to check address range and check for unsupported features,
        #   i.e. byte enables, streaming, and bursts
        # Can ignore DMI hint and extensions
        # Using the SystemC report handler is an acceptable way of signalling an error

        if (adr >= 256 or byt != 0 or len > 4 or wid < len):
            print("TLM-2", "Target does not support given generic payload transaction")

        if adr >= 256:
            trans.set_response_status(tlm_response_status.TLM_ADDRESS_ERROR_RESPONSE);
            # raise ValueError("Target does not support given generic payload transaction")
            return

        # Obliged to implement read and write commands
        if ( cmd == tlm_command.TLM_READ_COMMAND ):
            ptr[0] = self.mem[adr]
            # print("read mem[%0d] = %#x" % (adr, self.mem[adr]))
            pass
        elif ( cmd == tlm_command.TLM_WRITE_COMMAND ):
            self.mem[adr] = ptr[0]
            # print("write mem[%0d] = %#x" % (adr, ptr))
            pass

        # Obliged to set response status to indicate successful completion
        trans.set_response_status(tlm_response_status.TLM_OK_RESPONSE, self.socket.other_socket)
        yield self.env.timeout(0)


class Top(Module):
    def __init__(self, env, name):
        super().__init__(env, name)
        
        # Instantiate components
        self.initiator = Initiator(env, "initiator")
        self.memory = Memory(env, "memory")

        # One initiator is bound directly to one target with no intervening bus

        # Bind initiator socket to target socket
        self.initiator.socket.bind(self.memory.socket)


if __name__ == '__main__':
    env = simpy.Environment()
    top = Top(env, 'top')
    env.run()
