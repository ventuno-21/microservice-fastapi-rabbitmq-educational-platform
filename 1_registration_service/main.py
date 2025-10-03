from fastapi import FastAPI, BackgroundTasks
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import SQLModel, Field
from typing import Optional
import asyncio, os
from contextlib import asynccontextmanager

from shared.rabbitmq import publish
from shared.schemas import RegistrationNew

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://user:password@postgres_reg:5432/reg_db"
)

from sqlmodel.ext.asyncio.engine import create_async_engine

engine = create_async_engine(DATABASE_URL, echo=False)


class Registration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    user_email: str
    course_id: int
    status: str = "pending"


# ✅ lifespan instead of on_event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # shutdown
    await engine.dispose()


app = FastAPI(title="registration", lifespan=lifespan)


async def publish_registration(payload: RegistrationNew):
    # async def publish(exchange_name: str, routing_key: str, payload: dict):
    await publish("registrations", "registration.new", payload.model_dump())


@app.post("/register")
async def register(
    user_id: int, user_email: str, course_id: int, background_tasks: BackgroundTasks
):
    async with AsyncSession(engine) as session:
        reg = Registration(user_id=user_id, user_email=user_email, course_id=course_id)
        session.add(reg)
        await session.commit()
        await session.refresh(reg)

        payload = RegistrationNew(
            registration_id=reg.id,
            user_id=user_id,
            user_email=user_email,
            course_id=course_id,
        )

        background_tasks.add_task(asyncio.create_task, publish_registration(payload))

        return {"status": "ok", "registration_id": reg.id}
