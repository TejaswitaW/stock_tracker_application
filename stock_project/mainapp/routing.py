from django.urls import re_path

from . import consumers
# StockConsumer: A Django Channels consumer that handles WebSocket connections.
# .as_asgi(): Converts the consumer into an ASGI application, allowing it to handle WebSocket connections in an ASGI server.
websocket_urlpatterns = [
    re_path(r'ws/stock/(?P<room_name>\w+)/$', consumers.StockConsumer.as_asgi()),
]