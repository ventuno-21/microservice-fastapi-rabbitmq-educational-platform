import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Optional, Optionalfrom typing import Annotated

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


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    registration_id: int
    amount: float
    status: str = "pending"
    



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


# ----------------------------
# Message handler
# ----------------------------
async def handle_message(message):
    async with message.process():
        payload = json.loads(message.body.decode())
        reg = RegistrationNew(**payload)

        async with async_session() as session:
            amount = 49.99

            # create new payment record
            payment = Payment(
                registration_id=reg.registration_id,
                amount=amount,
                status="paid",
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)

            # publish paid event (after saving in DB)
            paid = RegistrationPaid(
                registration_id=reg.registration_id,
                user_id=reg.user_id,
                user_email=reg.user_email,
                course_id=reg.course_id,
                amount=amount,
            )
            await publish("registrations", "registration.paid", paid.model_dump())

# ----------------------------
# Consumer
# ----------------------------
async def consumer():
    conn, queue = await setup_queue_bindings(
        "course_queue", "registrations", ["registration.paid"]
    )
    async with conn:
        async for message in queue:
            await handle_message(message)


@app.get("/")
async def root():
    return {"status": "payment ok"}
