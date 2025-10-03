import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from rabbitmq import publish_message, setup_queue_bindings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel

from shared.rabbitmq import publish, setup_queue_bindings
from shared.schemas import RegistrationCompleted, RegistrationPaid

# ----------------------------
# Database setup (SQLAlchemy async)
# ----------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@postgres_course:5432/course_db"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# ----------------------------
# Model (based on SQLModel)
# ----------------------------
class Enrollment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registration_id: int
    user_id: int
    course_id: int
    active: bool = False


# ----------------------------
# Message handler
# ----------------------------
async def handle_message(message):
    async with message.process():
        payload = json.loads(message.body.decode())
        reg = RegistrationPaid(**payload)

        async with AsyncSessionLocal() as session:
            enroll = Enrollment(
                registration_id=reg.registration_id,
                user_id=reg.user_id,
                course_id=reg.course_id,
                active=True,
            )
            session.add(enroll)
            await session.commit()
            await session.refresh(enroll)

        # New message after registration
        completed = RegistrationCompleted(
            registration_id=reg.registration_id,
            user_id=reg.user_id,
            user_email=reg.user_email,
            course_id=reg.course_id,
        )

        # Publishing a message to RabbitMQ
        await publish_message(
            exchange_name="registrations",
            routing_key="registration.completed",
            message=completed.dict(),
        )


# ----------------------------
# Consumer
# ----------------------------
async def consumer():
    # async def setup_queue_bindings(queue_name: str, exchange_name: str, routing_keys: list):
    conn, queue = await setup_queue_bindings(
        "course_queue", "registrations", ["registration.paid"]
    )
    async with conn:
        async for message in queue:
            await handle_message(message)


# ----------------------------
# Lifespan (instead of on_event which is obsolete)
# ----------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    asyncio.create_task(consumer())

    yield

    # Shutdown
    await engine.dispose()


# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="course", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "course ok"}
