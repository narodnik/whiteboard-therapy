#!/usr/bin/env python3
import asyncio
import time
from argparse import ArgumentParser

import pygame
import zmq
import zmq.asyncio

class Appointment:
    def __init__(self, name, topic, frontend, backend):
        self.frontend = frontend
        self.backend = backend
        self.ctx = zmq.asyncio.Context()

        self.topic = topic
        self.name = name

        self.pub = self.ctx.socket(zmq.PUB)
        self.pub.connect(self.backend)

        self.sub = self.ctx.socket(zmq.SUB)
        self.sub.connect(self.frontend)
        self.sub.setsockopt_string(zmq.SUBSCRIBE, self.topic)

        self.stopped = False

        self.patients = {}

        self.screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        self.wacom_x = 0
        self.wacom_y = 0
        self.origin_x = 0
        self.origin_y = 0
        self.down = False
        self.mouse_track = []

    async def subscribe(self):
        print("Start subscriber")

        while not self.stopped:
            msg = await self.sub.recv_string()
            print(f"Sub got msg: {msg}")
            sp = msg.split(":")
            topic = sp[0]
            name = sp[1]
            event = sp[2]

            if name == self.name:
                continue

            patient_data = self.patients.get(name, {
                                             "wacom_x": 0,
                                             "wacom_y": 0,
                                             "origin_x": 0,
                                             "origin_y": 0,
                                             "mouse_track": [],
                                             "down": False,
                                             })

            if event == "MouseMotion":
                x, y = sp[3], sp[4]
                patient_data["wacom_x"] = int(x)
                patient_data["wacom_y"] = int(y)
                if patient_data["down"]:
                    patient_data["mouse_track"][-1].append((int(x), int(y)))

            elif event == "MouseButtonDown":
                patient_data["down"] = True
                patient_data["mouse_track"].append([])

            elif event == "MouseButtonUp":
                patient_data["down"] = False

            elif event == "OriginY":
                patient_data["origin_y"] += int(sp[3])

            elif event == "OriginX":
                patient_data["origin_x"] += int(sp[3])

            for segment in patient_data["mouse_track"]:
                if not segment:
                    continue
                start = segment[0]
                for end in segment[1:]:
                    start_x, start_y = start
                    end_x, end_y = end

                    start_x += patient_data["origin_x"]
                    start_y += patient_data["origin_y"]
                    end_x += patient_data["origin_x"]
                    end_y += patient_data["origin_y"]

                    start = (start_x, start_y)
                    adj_end = (end_x, end_y)

                    pygame.draw.line(self.screen, (255,0,0), start, adj_end, width=1)
                    start = end

            pygame.draw.circle(self.screen, (255,255,255),
                               (patient_data["wacom_x"], patient_data["wacom_y"]),
                               8)
            pygame.display.flip()

            self.patients[name] = patient_data

    async def draw(self):
        keydown_up = False
        keydown_down = False
        keydown_right = False
        keydown_left = False

        last_time = time.time()

        while not self.stopped:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    print("Received quit!")
                    self.stopped = True
                    break
                elif event.type == pygame.MOUSEMOTION:
                    print("MouseMotion")
                    self.wacom_x, self.wacom_y = pygame.mouse.get_pos()
                    msg = f"{self.topic}:{self.name}:MouseMotion:{self.wacom_x}:{self.wacom_y}"
                    await self.pub.send_string(msg)
                    if self.down:
                        self.mouse_track[-1].append(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    print("MouseButtonDown")
                    self.down = True
                    self.mouse_track.append([])
                    msg = f"{self.topic}:{self.name}:MouseButtonDown"
                    await self.pub.send_string(msg)
                elif event.type == pygame.MOUSEBUTTONUP:
                    print("MouseButtonUp")
                    self.down = False
                    msg = f"{self.topic}:{self.name}:MouseButtonUp"
                    await self.pub.send_string(msg)

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        keydown_up = True
                    elif event.key == pygame.K_DOWN:
                        keydown_down = True
                    elif event.key == pygame.K_RIGHT:
                        keydown_right = True
                    elif event.key == pygame.K_LEFT:
                        keydown_left = True
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_UP:
                        keydown_up = False
                    elif event.key == pygame.K_DOWN:
                        keydown_down = False
                    elif event.key == pygame.K_RIGHT:
                        keydown_right = False
                    elif event.key == pygame.K_LEFT:
                        keydown_left = False

            if keydown_up:
                self.origin_y += 20
                msg = f"{self.topic}:{self.name}:OriginY:{self.origin_y}"
                await self.pub.send_string(msg)
            if keydown_down:
                self.origin_y -= 20
                msg = f"{self.topic}:{self.name}:OriginY:{self.origin_y}"
                await self.pub.send_string(msg)
            if keydown_left:
                self.origin_x += 20
                msg = f"{self.topic}:{self.name}:OriginX:{self.origin_x}"
                await self.pub.send_string(msg)
            if keydown_right:
                self.origin_x -= 20
                msg = f"{self.topic}:{self.name}:OriginX:{self.origin_x}"
                await self.pub.send_string(msg)

            self.screen.fill(pygame.Color("black"))

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

                    pygame.draw.line(self.screen, (255,0,0), start, adj_end, width=1)
                    start = end

            pygame.draw.circle(self.screen, (255,255,255),
                               (self.wacom_x, self.wacom_y), 8)
            pygame.display.flip()

            current_time = time.time()
            duration = current_time - last_time
            remaining_time = 0.02 - duration
            if remaining_time > 0:
                await asyncio.sleep(remaining_time)
            last_time = current_time

async def main():
    parser = ArgumentParser()
    parser.add_argument("-f", "--frontend", default="tcp://127.0.0.1:5559")
    parser.add_argument("-b", "--backend", default="tcp://127.0.0.1:5560")
    parser.add_argument("-p", "--patient", required=True, type=str)
    parser.add_argument("-t", "--topic", default="Therapy")
    args = parser.parse_args()

    pygame.init()

    appt = Appointment(args.patient, args.topic, args.frontend, args.backend)

    await asyncio.gather(
        appt.subscribe(),
        appt.draw(),
    )

if __name__ == "__main__":
    asyncio.run(main())
