import asyncio
import socket
import pyppeteer.connection
import logging
from ipaddress import ip_address
from pyppeteer.network_manager import NetworkManager, Response

def _customOnResponseReceived(self, event: dict) -> None:
        """
        Pyppeteer doesn't expose the remoteIPAddress and remotePort attributes from the received
        Response object from Chrome. This is a hack that adds those attribute to it manually so that we can
        access them in the screenshot function. This is a much more elegant approach as socket.gethostbyaddr() 
        is a blocking call so it would slow things down somewhat significantly.

        Let the browser handle everything! :)

        Original function https://github.com/miyakogi/pyppeteer/blob/1aa0221f4fda21d59b18373e0f09071f2cd7402b/pyppeteer/network_manager.py#L255-L268
        """

        request = self._requestIdToRequest.get(event['requestId'])
        # FileUpload sends a response without a matching request.
        if not request:
            return
        _resp = event.get('response', {})
        response = Response(self._client, request,
                            _resp.get('status', 0),
                            _resp.get('headers', {}),
                            _resp.get('fromDiskCache'),
                            _resp.get('fromServiceWorker'),
                            _resp.get('securityDetails'))

        # Add the remoteIPAddress and remotePort attributes to the Response object
        response.remoteIPAddress = _resp.get('remoteIPAddress')
        response.remotePort = _resp.get('remotePort')

        request._response = response
        self.emit(NetworkManager.Events.Response, response)

def patch_pyppeteer():
    """
    There's a bug in pyppeteer currently (https://github.com/miyakogi/pyppeteer/issues/62) which closes the websocket connection to Chromium after ~20s.
    This is a hack to fix that. Taken from https://github.com/miyakogi/pyppeteer/pull/160

    Additionally this hooks the _onResponseReceived method with our own above.
    """
    original_method = pyppeteer.connection.websockets.client.connect

    def new_method(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return original_method(*args, **kwargs)

    pyppeteer.connection.websockets.client.connect = new_method
    # Hook the onResponseReceived event
    pyppeteer.network_manager.NetworkManager._onResponseReceived = _customOnResponseReceived

async def resolve_host(host):
    try:
        return socket.gethostbyaddr(host)[0]
    except Exception as e:
        logging.debug(f"Error resolving IP {host}: {e}")

def is_ipaddress(host):
    try:
        ip_address(host)
        return True
    except ValueError:
        return False
