"""
A module that wraps queuing to be able to use
different queue backends
"""

from collections import namedtuple

class QueueWrapper(object):
    """
    Module provides interface to queue and offers alternate backends
    """
    def __init__(self, queue_name, kind, backend):
        """
        Setup view with backend
        """
        self.queue_name = queue_name
        self.kind = kind
        if self.kind == 'sqs':
            self.queue = backend.get_queue_by_name(QueueName=queue_name)
        elif self.kind == 'redis':
            self.queue = backend

    def send_message(self, message):
        """
        send message to queue
        """
        if self.kind == 'redis':
            self.queue.rpush(self.queue_name, message)
            return {'MessageId': 'n/a'}
        elif self.kind == 'sqs':
            return self.queue.send_message(MessageBody=message)

    def receive_messages(self, **kwargs):
        """
        receive messages
        """
        if self.kind == 'redis':
            def delete_stub():
                """ to mimic sqs message object """
            msg = self.queue.lpop(self.queue_name)
            messages = []
            if msg:
                message = namedtuple('Message', ['body', 'delete'])
                msg = message(str(msg, 'utf-8'), delete_stub)
                messages.append(msg)
            return messages
        elif self.kind == 'sqs':
            return self.queue.receive_messages(**kwargs)
