# This implementation was copied from the Fabric project directly:
# https://github.com/fabric/fabric/blob/master/fabric/context_managers.py#L486
# The purpose was to remove the rtunnel creation printouts here:
# https://github.com/fabric/fabric/blob/master/fabric/context_managers.py#L547


from contextlib import contextmanager
import socket
import select

from fabric import api as fabric_api
from fabric.state import connections
from fabric.thread_handling import ThreadHandler

from cloudify.exceptions import NonRecoverableError


def documented_contextmanager(func):
    wrapper = contextmanager(func)
    wrapper.undecorated = func
    return wrapper


@documented_contextmanager
def remote(local_port, remote_port=0, local_host="localhost",
           remote_bind_address="127.0.0.1"):
    """
    Create a tunnel forwarding a locally-visible port to the remote target.
    """
    sockets = []
    channels = []
    threads = []

    def accept(channel, (src_addr, src_port), (dest_addr, dest_port)):
        channels.append(channel)
        sock = socket.socket()
        sockets.append(sock)

        try:
            sock.connect((local_host, local_port))
        except Exception as e:
            try:
                channel.close()
            except Exception as e2:
                close_error = ' (While trying to close channel: {0})'.format(
                    e2)
            else:
                close_error = ''
            raise NonRecoverableError(
                '[{0}] rtunnel: cannot connect to {1}:{2} ({3}){4}'.format(
                    fabric_api.env.host_string, local_host,
                    local_port, e, close_error))

        th = ThreadHandler('fwd', _forwarder, channel, sock)
        threads.append(th)

    transport = connections[fabric_api.env.host_string].get_transport()
    remote_port = transport.request_port_forward(
        remote_bind_address, remote_port, handler=accept)

    try:
        yield remote_port
    finally:
        for sock, chan, th in zip(sockets, channels, threads):
            sock.close()
            chan.close()
            th.thread.join()
            th.raise_if_needed()
        transport.cancel_port_forward(remote_bind_address, remote_port)


def _forwarder(chan, sock):
    # Bidirectionally forward data between a socket and a Paramiko channel.
    while True:
        r, w, x = select.select([sock, chan], [], [])
        if sock in r:
            data = sock.recv(1024)
            if len(data) == 0:
                break
            chan.send(data)
        if chan in r:
            data = chan.recv(1024)
            if len(data) == 0:
                break
            sock.send(data)
    chan.close()
    sock.close()
