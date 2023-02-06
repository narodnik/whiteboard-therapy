import pygame, time
import python_libinput

def main():
    li = python_libinput.libinput()
    li.start()

    pygame.init()

    screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)

    wacom_x, wacom_y = 0, 0

    origin_x, origin_y = 0, 0

    keydown_up = False
    keydown_down = False
    keydown_right = False
    keydown_left = False

    stopped = False
    down = False
    last_time = time.time()
    mouse_track = []
    while not stopped:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Received quit!")
                stopped = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                print("dddd")
                down = True
                # Start a new segment
                mouse_track.append([])
            elif event.type == pygame.MOUSEBUTTONUP:
                down = False
            elif event.type == pygame.MOUSEMOTION:
                print("motion")
                if down:
                    mouse_track[-1].append(event.pos)                
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
            origin_y -= 20
        if keydown_down:
            origin_y += 20
        if keydown_left:
            origin_x -= 20
        if keydown_right:
            origin_x += 20

        events = li.poll()
        for event in events:
            # tip up / down
            if event.type == 0:
                if event.tip_is_down:
                    print("down")
                    down = True
                    mouse_track.append([])
                else:
                    print("up")
                    down = False
            elif event.type == 1:
                x, y = event.x, event.y
                dim = screen.get_rect()
                w, h = dim.w, dim.h
                x *= w
                y *= h
                wacom_x, wacom_y = x, y
                if down:
                    print(x, y)
                    x -= origin_x
                    y -= origin_y
                    mouse_track[-1].append((x, y))                

        screen.fill(pygame.Color("black"))

        #print(mouse_track)
        for segment in mouse_track:
            if not segment:
                continue
            start = segment[0]
            for end in segment[1:]:
                start_x, start_y = start
                end_x, end_y = end

                start_x += origin_x
                start_y += origin_y
                end_x += origin_x
                end_y += origin_y

                start = (start_x, start_y)
                adj_end = (end_x, end_y)

                pygame.draw.line(screen, (255, 0, 0),
                                 start, adj_end, width=1)
                start = end

        pygame.draw.circle(screen, (255, 255, 255), (wacom_x, wacom_y), 8)

        pygame.display.flip()

        current_time = time.time()
        duration = current_time - last_time
        remaining_time = 0.02 - duration
        if remaining_time > 0:
            time.sleep(remaining_time)
        last_time = current_time

if __name__ == "__main__":
    main()

