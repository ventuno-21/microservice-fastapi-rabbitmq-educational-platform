import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.engine import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from shared.rabbitmq import publish, setup_queue_bindings
from shared.schemas import RegistrationCompleted, RegistrationNew, RegistrationPaid

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@postgres_pay:5432/pay_db"
)
engine = create_async_engine(DATABASE_URL, echo=False)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    task = asyncio.create_task(consumer())

    yield

    task.cancel()

    # shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


async def handle_message(message):
    async with message.process():
        payload = json.loads(message.body.decode())
        reg = RegistrationCompleted(**payload)
        print(
            f"[NOTIFICATION] Send welcome email to {reg.user_email} for course {reg.course_id}"
        )


async def consumer():
    conn, queue = await setup_queue_bindings(
        "notif_queue", "registrations", ["registration.completed"]
    )
    async with conn:
        async for message in queue:
            await handle_message(message)


@app.get("/")
async def root():
    return {"status": "notification ok"}
