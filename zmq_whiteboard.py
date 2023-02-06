#!/usr/bin/env python3
import asyncio
import time
from queue import Queue

import pygame
import zmq
import zmq.asyncio

TOPIC = "Therapy"
Q = asyncio.Queue(maxsize=0)
CTX = zmq.asyncio.Context()


class Sub:
    def __init__(self, topic, frontend):
        self.topic = topic
        self.frontend = frontend
        self.loop = True

    async def subscribe(self):
        print("Start subscriber")
        subscriber = CTX.socket(zmq.SUB)
        subscriber.connect(self.frontend)
        subscriber.setsockopt_string(zmq.SUBSCRIBE, self.topic)
        while self.loop:
            msg = await subscriber.recv()
            print(f"Sub got msg: {msg}")
            await Q.put(msg)

    def stop(self):
        self.loop = False


class Board:
    def __init__(self, topic, backend):
        self.wacom_x, self.wacom_y = 0, 0
        self.origin_x, self.origin_y = 0, 0
        self.stopped = False
        self.pub = CTX.socket(zmq.PUB)
        self.pub.connect(backend)
        self.topic = topic
        self.mouse_track = []

    async def recv_queue(self):
        while not self.stopped:
            msg = await Q.get()
            print(f"Got msg from queue: {msg}")

    async def publish(self):
        print(f"Start publisher")

    async def draw(self):
        screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        last_time = time.time()

        while not self.stopped:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    print("motion")
                    self.pub.send_string(f"{self.topic}:motion")

            screen.fill(pygame.Color("black"))

            for segment in self.mouse_track:
                if not segment:
                    continue
                start = segment[0]
                for end in segment[1:]:
                    start_x, start_y = start
                    end_x, end_y = end

                    start_x += self.origin_x
                    start_y += self.origin_y
                    end_x += self.origin_x
                    end_y += self.origin_y

                    start = (start_x, start_y)
                    adj_end = (end_x, end_y)

                    pygame.draw.line(screen, (255, 0, 0), start, adj_end,
                                     width=1)

                    start = end

            pygame.draw.circle(screen, (255, 255, 255),
                               (self.wacom_x, self.wacom_y), 8)

            pygame.display.flip()

            current_time = time.time()
            duration = current_time - last_time
            remaining_time = 0.02 - duration
            if remaining_time > 0:
                time.sleep(remaining_time)
            last_time = current_time


async def main():
    pygame.init()

    sub = Sub(TOPIC, "tcp://127.0.0.1:5559")
    board = Board(TOPIC, "tcp://127.0.0.1:5560")

    await asyncio.gather(
        sub.subscribe(),
        board.recv_queue(),
        board.draw(),
    )

asyncio.run(main())
