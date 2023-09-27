from flask import (Flask, request, jsonify)
import argparse, logging
from llama_distributed import Distributed_Loader

model = Distributed_Loader(initialize=False)
# lists to keep track of conversation
request_queues = [list() for _ in range(model.cfg["world_size"])]
# flask setup
app = Flask(__name__)

# For Gunicorn: sets flask logger to the same settings as gunicorn logger
log = logging.getLogger('gunicorn.error')
app.logger.handlers = log.handlers
app.logger.setLevel(log.level)
log.debug("API: Flask logging is configured.")


def response_json(response, key="message"):
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "choices": [{
            "index": 0,
            key: response,
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }

def check_messages(messages):
    if not isinstance(messages, list):
        return jsonify({
            "error": {
                "message": "'messages' must be a list",
                "code": "invalid_message_list"
            }
        }), 400

    for message in messages:
        if not isinstance(message, dict) or 'role' not in message or 'content' not in message:
            return jsonify({
                "error": {
                    "message": "Each message must have a 'role' and a 'content'",
                    "code": "invalid_message"
                }
            }), 400

    return None       

@app.route("/chat", methods=['POST'])
def chat():
    # get messages from request
    messages = dict(request.json)
    log.debug(f'messages: {messages}')
    # validate message format
    errors = check_messages(messages["message"])
    if errors:
        return errors
    # add messages to queue for Llama 2
    for rank in range(model.cfg["world_size"]):
        # store running conversation
        for message in messages["message"]:
            log.debug(message)
            request_queues[rank].append(message)

        model.request_queues[rank].put(request_queues[rank])
        # model.request_queues[rank].put(messages["message"])
        log.debug(f"message queue length: {model.request_queues[rank].qsize()}")
    # model must be initialized after messages are loaded into the queue.
    model.initialize()
    # wait for response        
    for rank in range(model.cfg["world_size"]):
        response = model.response_queues[rank].get()
        request_queues[rank].append(response)
        log.debug(request_queues[rank])
    # return regular JSON response
    return jsonify(response)


@app.route('/', methods=['GET'])
def is_running():
    return "<h1>Chat server is running!</h1>"

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-p','--port',type=int,default=8080, help="Running port")
    parser.add_argument("-H","--host",type=str,default='0.0.0.0', help="Address to broadcast")
    parser.add_argument("-d","--debug",type=bool,default=True, help="enable logging for debugging")
    args = parser.parse_args()
    app.run(host=args.host,port=args.port, debug=args.debug)