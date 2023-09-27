from llama import Llama
from torch.multiprocessing import Process, Queue
import torch.distributed as dist
import torch
import os
import logging
import gc
import sys
import datetime

# don't remove even though we should use gunicorn.error as log
logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
model_log = logging.getLogger('model.error')
model_log.setLevel(logging.DEBUG)
# log.debug("MODEL: llama distributed logging is configured.")

cfg = {
    "ckpt_dir": "llama-2-13b-chat",
    "tokenizer_path": "tokenizer.model",
    "temperature": 0.6,
    "top_p": 0.9,
    "max_seq_len": 1024,
    "max_batch_size": 8,
    "max_gen_len": None,
    "world_size":2,
    "backend":'nccl',
    "llama_addr":'127.0.0.1',
    "llama_port":9000,
    "timeout": datetime.timedelta(seconds=20)
}

class Distributed_Loader(object):
    def __init__(self, initialize=True, cfg=cfg, log=model_log):
        model_log.debug("MODEL: new model instance created.")
        self.check_for_logs()
        # clear GPU memory
        self.clear_mem()
        self.cfg = cfg
        # initialize queues
        self.request_queues = [Queue() for _ in range(cfg["world_size"])]
        self.response_queues = [Queue() for _ in range(cfg["world_size"])]
        self.processes = []
        self.response = None
        if initialize:
            self.initialize()

    def run(self, rank, request_queue, response_queue):
        os.environ['LOCAL_RANK'] = str(rank)

        # initialize Llama 2
        self.generator = Llama.build(
            ckpt_dir=cfg["ckpt_dir"],
            tokenizer_path=cfg["tokenizer_path"],
            max_seq_len=cfg["max_seq_len"],
            max_batch_size=cfg["max_batch_size"],
        )
        model_log.debug('MODEL: Llama initialized...')

        while True:
            # load messages from queue
            dialogs = [request_queue.get() for i in range(request_queue.qsize())]

            # replace Llama 2 default system message
            if dialogs[0][0]["role"] != "system":
                dialogs[0] = [
                    {
                        "role": "system",
                        "content": "You are an Optician. Always give brief answers that relate to subjective refractions.",
                    }
                ] + dialogs[0]
            model_log.debug(f'MODEL: Processing messages...\n {dialogs}')
            # send messages to Llama 2
            with torch.no_grad():
                results = self.generator.chat_completion(
                    dialogs,  # type: ignore
                    max_gen_len=cfg["max_gen_len"],
                    temperature=cfg["temperature"],
                    top_p=cfg["top_p"],
                )

            # get response from Llama 2
            response = results[0]['generation']
    
            response_queue.put(response)
            self.response = dict(response.items())
            model_log.debug('Responses queued...')
            # model_log.debug(f'RESPONSE:{response}')
            break

    def init_process(self, rank, fn, request_queue, response_queue, backend=cfg["backend"]):
        os.environ['MASTER_ADDR'] = cfg["llama_addr"]
        os.environ['MASTER_PORT'] = str(cfg["llama_port"])
        os.environ['WORLD_SIZE'] = str(cfg["world_size"])
        dist.init_process_group(backend, rank=rank, world_size=cfg["world_size"], timeout=cfg["timeout"])
        fn(rank, request_queue, response_queue)

    def initialize(self):
        # logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
        # log = logging.getLogger('gunicorn.error')
        # initialize all Llama 2 processes
        for rank in range(cfg["world_size"]):

            p = Process(target=self.init_process, args=(rank, self.run, self.request_queues[rank], self.response_queues[rank]))
            p.start()
            self.processes.append(p)

        # # wait for Llama 2 initialization
        # for rank in range(cfg["world_size"]):
        #     response = self.response_queues[rank].get()
        for p in self.processes:
            p.join()
        self.check_for_logs()
    
    def clear_mem(self):
        gc.collect()
        torch.cuda.empty_cache()
    def cleanup(self):
        dist.destroy_process_group()
    def check_for_logs(self):
        # get root logger
        root_logger = logging.getLogger()
        # get handlers
        handlers = root_logger.handlers
        for handler in handlers:
            if isinstance(handler, logging.FileHandler):
                root_logger.debug(f'MODEL: {handler.baseFilename}')

if __name__ == "__main__":
    llama_chat = Distributed_Loader(cfg)
