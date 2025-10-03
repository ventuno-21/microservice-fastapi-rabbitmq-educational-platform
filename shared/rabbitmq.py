# shared/rabbitmq.py
import json
from aio_pika import connect_robust, Message, ExchangeType

RABBIT_URL = "amqp://guest:guest@rabbitmq/"

async def get_connection():
    return await connect_robust(RABBIT_URL)

async def publish(exchange_name: str, routing_key: str, payload: dict):
    conn = await get_connection()
    async with conn:
        channel = await conn.channel()
        exchange = await channel.declare_exchange(exchange_name, ExchangeType.TOPIC)
        msg = Message(json.dumps(payload).encode())
        await exchange.publish(msg, routing_key=routing_key)

async def setup_queue_bindings(queue_name: str, exchange_name: str, routing_keys: list):
    conn = await get_connection()
    channel = await conn.channel()
    exchange = await channel.declare_exchange(exchange_name, ExchangeType.TOPIC)
    queue = await channel.declare_queue(queue_name, durable=True)
    for rk in routing_keys:
        await queue.bind(exchange, rk)
    return conn, queue
