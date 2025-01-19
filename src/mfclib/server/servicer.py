import logging
import threading
from concurrent import futures

import grpc


from ..models.configuration import Config, ServerConfig
from .proto import service_pb2, service_pb2_grpc

logger = logging.getLogger(__name__)


class MFCControllerServicer(service_pb2_grpc.EurothermServicer):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.stop_event = threading.Event()
        # self.io = EurothermIO(cfg.devices)
        # self.io.start()

    def StopServer(
        self,
        request: service_pb2.StopRequest,
        context: grpc.ServicerContext,
    ):
        logger.info('[Request] StopServer')
        self.io.stop()  # stop data acquisition
        self.stop_event.set()
        return service_pb2.Empty()

    def ServerHealthCheck(
        self,
        request: service_pb2.Empty,
        context: grpc.ServicerContext,
    ):
        logger.info('[Request] ServerHealthCheck')
        return service_pb2.Empty()


class MFCControllerClient:
    def __init__(self, channel: grpc.Channel, cfg: ServerConfig) -> None:
        self._client = service_pb2_grpc.EurothermStub(channel)
        self._cfg = cfg

    @property
    def timeout(self):
        return self._cfg.timeout.m_as('s')

    def stop_server(self):
        self._client.StopServer(service_pb2.StopRequest())

    def is_alive(self):
        self._client.ServerHealthCheck(service_pb2.Empty(), timeout=self.timeout)


def is_alive(cfg: Config | ServerConfig):
    logger.info('Checking server health.')
    if isinstance(cfg, Config):
        cfg = cfg.server
    client = connect(cfg)
    try:
        client.is_alive()
        return True
    except grpc.RpcError:
        return False


def serve(cfg: Config):
    executor = futures.ThreadPoolExecutor()
    server = grpc.server(executor)
    servicer = MFCControllerServicer(cfg)
    service_pb2_grpc.add_EurothermServicer_to_server(servicer, server)

    server_address = f'{cfg.server.ip}:{cfg.server.port}'
    server.add_insecure_port(server_address)

    logger.info(f'Starting TCLogger server at {server_address}')
    server.start()

    def wait_for_termination():
        logger.info('Waiting for server to terminate...')
        servicer.stop_event.wait()

        logger.info(f'Stopping server at {server_address}')
        token = server.stop(30.0)
        token.wait(30.0)

        if not token.is_set():
            logger.error('Server did not terminate')
        else:
            logger.info('Server stopped')

    return executor.submit(wait_for_termination)


def connect(cfg: Config | ServerConfig):
    if isinstance(cfg, Config):
        cfg = cfg.server
    server_address = f'{cfg.ip}:{cfg.port}'

    logger.info(f'Connecting client to server at {server_address}')
    channel = grpc.insecure_channel(server_address)

    return MFCControllerClient(channel, cfg)
