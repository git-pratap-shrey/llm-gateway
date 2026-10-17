#!/usr/bin/env python3
"""
One-off script: republish the 5 stuck 'processing' jobs from data/result_db.db to RabbitMQ.
Resets their DB status to 'queued' and re-publishes the original payload.
"""

import ast
import json
import logging
import os
import pika
from sqlmodel import Session, create_engine, select, col
from result_store.results_db import Result

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s %(message)s")

JOB_IDS = [
    "01a143c8-cae5-7737-b05e-6c4159ed3acb",
    "01a143c8-cc2f-7abb-ad3f-19c59f69a3e2",
    "01a143c8-d0bc-732f-b8fc-26c5a89ad228",
    "01a143c8-d703-7043-9c89-4ae3e27d75ba",
    "01a143c8-d804-7199-b173-efff8edb7e29",
]

DB_PATH  = os.getenv("RESULT_DB_PATH", "data/result_db.db")
MQ_HOST  = os.getenv("RABBITMQ_HOST", "localhost")

engine = create_engine(f"sqlite:///{DB_PATH}")

connection = pika.BlockingConnection(pika.ConnectionParameters(host=MQ_HOST))
channel = connection.channel()
channel.queue_declare(queue="tasks", durable=True)

republished = 0
with Session(engine) as session:
    for job_id in JOB_IDS:
        row = session.exec(select(Result).where(col(Result.job_id) == job_id)).first()
        if row is None:
            logging.warning(f"  {job_id}: NOT FOUND in DB — skipping.")
            continue

        # 'data' column stores the input dict as a Python repr string
        try:
            input_data = ast.literal_eval(row.data)
        except Exception as e:
            logging.error(f"  {job_id}: Failed to parse data field: {e} — skipping.")
            continue

        payload = {
            "job_id":         job_id,
            "input":          input_data,
            "status":         "queued",
            "output":         None,
            "retry_count":    0,
            "fallback_index": 0,
        }

        # Reset DB status first
        row.status   = "queued"
        row.response = None
        session.add(row)

        # Publish to RabbitMQ
        channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
        )
        logging.info(f"  {job_id}: republished (provider={input_data.get('provider')}, model={input_data.get('model')}).")
        republished += 1

    session.commit()

connection.close()
logging.info(f"Done. {republished}/{len(JOB_IDS)} job(s) republished to RabbitMQ.")
