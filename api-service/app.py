import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import router
from src.database.dependency.session import async_session_fabric
from src.tools.rabbit_client import rabbitmq_client
from src.tools.worker import OutboxWorker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rabbitmq_client.start()

    worker = OutboxWorker(rabbitmq_client, async_session_fabric)
    worker_task = asyncio.create_task(worker.start())
    app.state.outbox_worker = worker

    yield

    await worker.stop()

    try:
        await asyncio.wait_for(worker_task, timeout=5.0)
    except asyncio.TimeoutError:
        print("Воркер не успел завершиться принудительно")

    await rabbitmq_client.stop()


app = FastAPI(
    title="Payment service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
