# user_service/kafka_producer.py
from kafka import KafkaProducer
import json
import os

KAFKA_BOOTSTRAP_SERVERS = os.environ.get(
    'KAFKA_BOOTSTRAP_SERVERS', 'kafka-user:9092'
)
TOPIC = 'user-events'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8') if k else None,
)

def send_user_created_event(user_data: dict):
    """Envia evento de criação de usuário para o Kafka."""
    future = producer.send(
        TOPIC,
        key=str(user_data['id']),
        value=user_data
    )
    # opcional: esperar confirmação
    future.get(timeout=10)