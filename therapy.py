#!/usr/bin/env python3
import asyncio
import time
from argparse import ArgumentParser

import pygame
import zmq
import zmq.asyncio

FPS = 60

class Patient:
    def __init__(self):
        self.down = False
        self.mouse_track = []
        self.wacom_x = 0
        self.wacom_y = 0
        self.origin_x = 0
        self.origin_y = 0


async def handle_events(name, patients, sub):
    while True:
        msg = await sub.recv_string()
        msg = msg.split(":")

        _topic = msg[0]
        patient = msg[1]
        event = msg[2]

        # Skip ourselves
        if name == patient:
            continue

        print(f"sub recv: {msg}")

        if not patients.get(patient):
            patients[patient] = Patient()

        if event == "MouseMotion":
            w_x, w_y = int(msg[3]), int(msg[4])
            patients[patient].wacom_x = w_x
            patients[patient].wacom_y = w_y
            if patients[patient].down:
                patients[patient].mouse_track[-1].append((w_x, w_y))
        elif event == "MouseButtonDown":
            patients[patient].down = True
            patients[patient].mouse_track.append([])
        elif event == "MouseButtonUp":
            patients[patient].down = False
        elif event == "OriginX":
            patients[patient].origin_x += int(msg[3])
        elif event == "OriginY":
            patients[patient].origin_y += int(msg[3])


async def pygame_event_loop(name, patients, pub, topic):
    keydown_up = False
    keydown_down = False
    keydown_right = False
    keydown_left = False

    while True:
        await asyncio.sleep(0)
        event = pygame.event.wait()

        if event.type == pygame.QUIT:
            break

        if event.type == pygame.MOUSEMOTION:
            w_x, w_y = event.pos
            patients[name].wacom_x = w_x
            patients[name].wacom_y = w_y
            if patients[name].down:
                patients[name].mouse_track[-1].append(event.pos)
            msg = f"{topic}:{name}:MouseMotion:{w_x}:{w_y}"
            await pub.send_string(msg)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            patients[name].down = True
            patients[name].mouse_track.append([])
            msg = f"{topic}:{name}:MouseButtonDown"
            await pub.send_string(msg)

        elif event.type == pygame.MOUSEBUTTONUP:
            patients[name].down = False
            msg = f"{topic}:{name}:MouseButtonUp"
            await pub.send_string(msg)

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
            patients[name].origin_y += 20
            msg = f"{topic}:{name}:OriginY:{patients[name].origin_y}"
            await pub.send_string(msg)
        if keydown_down:
            patients[name].origin_y -= 20
            msg = f"{topic}:{name}:OriginY:{patients[name].origin_y}"
            await pub.send_string(msg)
        if keydown_left:
            patients[name].origin_x += 20
            msg = f"{topic}:{name}:OriginX:{patients[name].origin_x}"
            await pub.send_string(msg)
        if keydown_right:
            patients[name].origin_x -= 20
            msg = f"{topic}:{name}:OriginX:{patients[name].origin_x}"
            await pub.send_string(msg)


async def whiteboard(screen, patients):
    current_time = 0

    while True:
        last_time, current_time = current_time, time.time()
        #print("sleep:", 1/FPS - (current_time-last_time))
        await asyncio.sleep(1 / FPS - (current_time - last_time))

        screen.fill(pygame.Color("black"))

        for patient in patients.values():
            for segment in patient.mouse_track:
                if not segment:
                    continue
                start = segment[0]
                for end in segment[1:]:
                    start_x, start_y = start
                    end_x, end_y = end

                    start_x += patient.origin_x
                    start_y += patient.origin_y
                    end_x += patient.origin_x
                    end_y += patient.origin_y

                    start = (start_x, start_y)
                    adj_end = (end_x, end_y)

                    pygame.draw.line(screen, (255,0,0), start, adj_end, width=1)
                    start = end

            pygame.draw.circle(screen, (255,255,255),
                               (patient.wacom_x, patient.wacom_y), 8)

        pygame.display.flip()



async def main(frontend, backend, patient, topic):
    pygame.init()

    pygame.display.set_caption("Therapy session")
    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)

    ctx = zmq.asyncio.Context()
    pub = ctx.socket(zmq.PUB)
    pub.connect(backend)

    sub = ctx.socket(zmq.SUB)
    sub.connect(frontend)
    sub.setsockopt_string(zmq.SUBSCRIBE, topic)

    patients = {}
    patients[patient] = Patient()

    await asyncio.gather(
        whiteboard(screen, patients),
        pygame_event_loop(patient, patients, pub, topic),
        handle_events(patient, patients, sub),
    )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-f", "--frontend", default="tcp://192.168.1.56:5559")
    parser.add_argument("-b", "--backend", default="tcp://192.168.1.56:5560")
    parser.add_argument("-p", "--patient", required=True, type=str)
    parser.add_argument("-t", "--topic", default="Therapy")
    args = parser.parse_args()

    asyncio.run(main(args.frontend, args.backend, args.patient, args.topic))
