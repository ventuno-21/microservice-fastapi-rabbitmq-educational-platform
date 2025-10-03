# FastAPI Async Microservices (Education) - ZIP

This package contains a minimal example of 4 FastAPI async microservices using SQLModel (async) and RabbitMQ (aio-pika).

Services:
- registration_service (port 8001)
- payment_service (port 8002)
- course_service (port 8003)
- notification_service (port 8004)

Run with: `docker-compose up --build`

or

▶️ Run the project

## Run RabbitMQ:

```
docker run -d --hostname rabbit --name rabbit -p 5672:5672 -p 15672:15672 rabbitmq:3-management
# Management: http://localhost:15672 (guest/guest)
```

## Run the worker:
```
python worker.py
```

## Run Django:
```
python manage.py runserver
```

Then POST to registration service:
`POST http://localhost:8001/register?user_id=1&user_email=test@example.com&course_id=10`

# Notes
1st)  
SessionDep = Annotated[AsyncSession, Depends(get_session)]  
This is specifically for dependency injection in FastAPI.  

FastAPI itself resolves dependencies only when a **request** hits an **endpoint** (like @app.post, @app.get).  like below:
```
@app.get("/payments/{payment_id}")
async def get_payment(payment_id: int, session: SessionDep):
    return await session.get(Payment, payment_id) 
```

Dependency Injection in FastAPI works such that when an endpoint is called, FastAPI checks which parameters are defined with Depends().

Then FastAPI automatically creates an instance of the dependency and passes it to the endpoint function.

This only happens when a real HTTP request hits that endpoint.

If your function is executed outside the context of FastAPI (for example, a function triggered by RabbitMQ or Celery), FastAPI cannot resolve the dependency because there is no request for the DI system to act upon.

But functions like consumer() or handle_message() are called directly by RabbitMQ, outside of FastAPI’s context, so dependency injection does not work there.  

2nd) Workflow Diagram 
[User] 
   |
   | 1. Register for a course
   v
[Registration Service]
   |
   | --> publish("registrations", "registration.created")
   v
[RabbitMQ Exchange: registrations]
   |
   |---(routing_key="registration.created")---> [Payment Service]
   |
   v
------------------------------------------------------------
[Payment Service]
   |
   | 2. Verify payment (e.g., payment gateway)
   | --> publish("registrations", "registration.paid")
   v
[RabbitMQ Exchange: registrations]
   |
   |---(routing_key="registration.paid")---> [Course Service]
   |
   v
------------------------------------------------------------
[Course Service]
   |
   | 3. Activate user access to the course
   | --> publish("registrations", "registration.completed")
   v
[RabbitMQ Exchange: registrations]
   |
   |---(routing_key="registration.completed")---> [Notification Service]
   |
   v
------------------------------------------------------------
[Notification Service]
   |
   | 4. Send welcome email or SMS to the user
   v
[User gets access + notification ✅]


3rd) Message flow in RabbitMQ
The producer publishes a message to an exchange. When creating an exchange, the type must be specified. This topic will be covered later on.  
The exchange receives the message and is now responsible for routing the message. The exchange takes different message attributes into account, such as the routing key, depending on the exchange type.  
Bindings must be created from the exchange to queues. In this case, there are two bindings to two different queues from the exchange. The exchange routes the message into the queues depending on message attributes.  
The messages stay in the queue until they are handled by a consumer  
The consumer handles the message.  
![RabbitMQ Exchanges](https://www.cloudamqp.com/img/blog/exchanges-topic-fanout-direct.png)

Some important concepts need to be described before we dig deeper into RabbitMQ. The default virtual host, the default user, and the default permissions are used in the examples, so let’s go over the elements and concepts:

**Producer**: Application that sends the messages.  
**Consumer**: Application that receives the messages.  
**Queue**: Buffer that stores messages.  
**Message**: Information that is sent from the producer to a consumer through RabbitMQ.  
**Connection**: A TCP connection between your application and the RabbitMQ broker.  
**Channel**: A virtual connection inside a connection. When publishing or consuming messages from a queue - it's all done over a channel.  
**Exchange**: Receives messages from producers and pushes them to queues depending on rules defined by the exchange type. To receive messages, a queue needs to be bound to at least one exchange.  
**Binding**: A binding is a link between a queue and an exchange.  
**Routing key**: A key that the exchange looks at to decide how to route the message to queues. Think of the routing key like an address for the message.  
**AMQP**: Advanced Message Queuing Protocol is the protocol used by RabbitMQ for messaging.  
**Users**: It is possible to connect to RabbitMQ with a given username and password. Every user can be assigned permissions such as rights to read, write and configure privileges within the instance. Users can also be assigned permissions for specific virtual hosts.  
**Vhost, virtual host**: Provides a way to segregate applications using the same RabbitMQ instance. Different users can have different permissions to different vhost and queues and exchanges can be created, so they only exist in one vhost.  