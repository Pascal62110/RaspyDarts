#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import tempfile
import pygame
from pygame.locals import *
import pygame.camera
import pygame.font
import datetime
import time
import subprocess
from PIL import Image
import threading
from operator import itemgetter
import random
from time import sleep

from include import cpaths
from include import cvideos

#resolution_width_ex = [ 320, 320, 640, 720, 854, 768, 800, 1024, 1280, 1280, 1280, 1400, 1680, 1600, 1920, 1920, 2048, 2048, 2560, 2560, 2560, 2560, 3440, 3840, 4096, 7680 ]
#resolution_height_ex= [ 200, 240, 480, 480, 480, 576, 600, 768 , 720 ,  800, 1024, 1050, 1050, 1200, 1080, 1200, 1080, 1536, 1080, 1440, 1600, 2048, 1440, 2160, 2160, 4320 ]
resolution_width_ex = [ 320, 640, 720, 768, 800, 1024, 1280, 1280, 1280, 1400, 1600, 1920, 2048, 2560, 3440, 3840, 7680 ]
resolution_height_ex= [ 240, 480, 480, 576, 600, 768 , 720 ,  800, 1024, 1050, 1200, 1080, 1536, 1440, 1440, 2160, 4320 ]

#
# Start of Camera Class
#
class Camera:
    def __init__(self, config, display, log, show_in_parametrage=False):
        self.camera = None
        self.update_filter = 0
        self.logs = log
        self.userDirectory = f"{config.user_dir}"
        self.photo_filter_directory = "images/photo_filter"
        self.theme = str(config.get_value('SectionGlobals', 'colorset'))
        try:
            pygame.camera.init()
        except Exception as ex:
            self.logs.Log("ERROR", f"Error in ccamera __init__ : {ex}")
        self.display = display
        self.path_of_filter = None
        self.incr_filter = 0
        self.path_of_filters_directory = None
        self.list_of_filter = []
        # Filters already read and scaled, see filter_layer()
        self._filter_layers = {}
        self.init_list_of_filters()
        self.init_var(config.read_file("Camera"), show_in_parametrage)
        self.work_in_progress = False
        self._capture_lock = threading.Lock()
        self.showing_in_progress = False
        self.qrPopThread = None
        self.qrPopWindow = None
        self.runningQRPop = False
        self.credentialsPath = os.path.join(self.userDirectory, "credentials.json")
        self._uploadToGoogleDrive = None
        try:
            if os.path.exists(self.credentialsPath) and self.upload_cloud:
                from include import ccamera_upload_GoogleDrive
                self._uploadToGoogleDrive = ccamera_upload_GoogleDrive.CameraUploadGoogleDrive(config, self.logs, self.credentialsPath)
            else:
                self.logs.debug(f"No credentials found to upload via Google Drive")
        except Exception as ex:
            self.logs.error(f"Error in ccamera __init__() : {ex}")
        
    def init_var(self, config_camera, show_in_parametrage=False):
        self.camera_id = str(config_camera['camera_id'])
        self.picture_path = cpaths.usable_dir(config_camera['picture_path'], os.path.join(cpaths.user_home(), 'Pictures'))
        self.video_path = cpaths.usable_dir(config_camera['video_path'], os.path.join(cpaths.user_home(), 'Videos'))
        self.directory_order = int(config_camera['directory_order'])
        self.choice_of_memories = int(config_camera['choice_of_memories'])
        self.pict_res_width = int(config_camera['picture_res_width'])
        self.pict_res_height = int(config_camera['picture_res_height'])
        self.vid_res_width = int(config_camera['video_res_width'])
        self.vid_res_height = int(config_camera['video_res_height'])
        self.flip_horizontal = bool(config_camera['flip_horizontal'] == '1')
        self.flip_vertical = bool(config_camera['flip_vertical'] == '1')
        self.nb_picture = int(config_camera['nb_picture'])
        self.video_duration = int(config_camera['video_duration'])
        self.fps = int(config_camera['fps'])
        self.events = str(config_camera['events'])
        self.upload_cloud = bool(config_camera['upload_cloud'] == '1')
        self.fullscreen = bool(config_camera['fullscreen_pop'] == '1')
        self.duree = int(config_camera['duree_ms'])
        if self.is_connected():
            if show_in_parametrage:
                # On bride sinon l'interface rame
                self.camera = pygame.camera.Camera(f"/dev/video{self.camera_id}", (800, 600))
            else:
                self.camera = pygame.camera.Camera(f"/dev/video{self.camera_id}", (self.pict_res_width, self.pict_res_height))
    
    def init_list_of_filters(self):
        try:
            files = []
            if self.theme in ('', 'clear', 'dark'):
                self.path_of_filters_directory = f"{self.userDirectory}/{self.photo_filter_directory}"
            else:
                self.path_of_filters_directory = f"{self.userDirectory}/themes/{self.theme}/{self.photo_filter_directory}"
            if os.path.exists(self.path_of_filters_directory):
                files = os.listdir(self.path_of_filters_directory)
                if files:
                    self.list_of_filter = []
                    for f in files:
                        self.list_of_filter.append((f, False))
            else:
                self.list_of_filter = None
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera init_list_of_filters() : {ex}")
        
    def is_connected(self):
        try:
            if(self.camera_id != '-1'):
                camera_list = pygame.camera.list_cameras()
                if camera_list :
                    return f"/dev/video{self.camera_id}" in camera_list
            return False
        except Exception as ex:
            self.logs.error(f"Error in ccamera is_connected() : {ex}")
    
    def camera_start(self):
        '''
        We start the USB camera, to be done before each use        
        '''
        try:
            if self.is_connected():
                self.camera.start()
        except Exception as ex:
            self.logs.error(f"Error in ccamera camera_start() : {ex}")
        
    def camera_stop(self): 
        '''
        We stop the USB camera, to be done after each use        
        '''
        try:
            if self.is_connected():
                self.camera.stop()
        except Exception as ex:
            self.logs.error(f"Error in ccamera camera_stop() : {ex}")
    
    def find_camera(self):
        '''
        We will browse v4l2-ctl to find the information of our USB camera
        There is "pygame.camera.list_cameras() but the responses don't tell us enough
        Return None if not find
        '''
        fd_all, all_cam_file = tempfile.mkstemp(suffix='_allcam.txt')
        os.close(fd_all)
        fd_cam, cam_file = tempfile.mkstemp(suffix='_cam.txt')
        os.close(fd_cam)
        try:
            cam_with_resolution = {}

            # On va recuperer les id des "USB Camera"
            os.system(f"v4l2-ctl --list-devices 2>/dev/null | grep '(usb-' -A1 | grep '/dev/video' | sed -e 's/^[ \\t]*//' | sort > {all_cam_file}")

            lines = []
            with open(all_cam_file, "r") as file:
                lines = file.readlines()

            for cam in lines:
                cam_id = cam.strip()[-1:]
                # On en a trouve un, on va recuperer ses resolutions et faire le tri dans les doublons (OSEF les FPS)
                os.system(f"v4l2-ctl -d {cam_id} --list-formats-ext | grep 'Size: Discrete' > {cam_file}")
                cam_lines = []
                with open(cam_file, "r") as file:
                    cam_lines = file.readlines()

                if cam_lines:
                    resolutions = []
                    resolutions_returned = []
                    for resFind in cam_lines:
                        resFindClean = resFind.strip().replace("Size: Discrete ", "")
                        parts = resFindClean.split('x')
                        if len(parts) == 2:
                            w, h = int(parts[0]), int(parts[1])
                            if not any(r[0] == w and r[1] == h for r in resolutions):
                                resolutions.append((w, h))
                    resolutions = sorted(resolutions, key=itemgetter(0, 1), reverse=True)
                    for good_width, good_height in resolutions:
                        resolutions_returned.append((f"{good_width}x{good_height}", f"{good_width}x{good_height}"))
                    cam_with_resolution[cam_id] = resolutions_returned

            return cam_with_resolution

        except Exception as ex:
            self.logs.error(f"Error in ccamera find_camera() : {ex}")
        finally:
            for f in (all_cam_file, cam_file):
                if os.path.exists(f):
                    os.remove(f)
    
    def resolutions_only_width(self, resolution):
        return int(resolution.split('x')[0])
    
    def resolutions_only_height(self, resolution):
        return int(resolution.split('x')[1])
    
    def resize_camera_image(self, screen, posXecran, posYecran, resWcamera, resHcamera):
        '''
        Resize the image so that it does not overflow the screen
        '''
        try:
            indexWidthRes = -1
            screen_width, screen_height = screen.get_size()
            widthEnd = posXecran + resWcamera
            heightEnd = posYecran + resHcamera
            
            # si on detecte une largeur trop grande alors on reajuste et on modifiera la hauteur
            if widthEnd > screen_width:
                possibleWidth = screen_width - posXecran - 100
                possibleWidth = (possibleWidth - min((possibleWidth - a for a in resolution_width_ex), key = abs))
                indexWidthRes = resolution_width_ex.index(possibleWidth)
            else:
                possibleWidth = resWcamera
                
            # on a deja detecte une largeur trop grande
            if indexWidthRes != -1:
                possibleHeight = resolution_height_ex[indexWidthRes]
            # si on detecte une hauteur trop grande alors on reajuste et on modifiera la largeur
            elif heightEnd > screen_height:
                possibleHeight = screen_height - posYecran - 100
                possibleHeight = (possibleHeight - min((possibleHeight - a for a in resolution_height_ex), key = abs))
                possibleWidth = resolution_height_ex[resolution_height_ex.index(possibleHeight)]
            else:
                possibleHeight = resHcamera
            
            return possibleWidth, possibleHeight
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera resize_camera_image() : {ex}")     
    
    def get_photo_filter(self):
        try:
            path_of_filter = ""
            self.list_of_filters()
            
            if self.list_of_filter:   
                # Find not show
                nb_filter_not_show = list((file[0], file[1]) for file in self.list_of_filter if file[1] == False)
                nb_files = len(nb_filter_not_show)
                rand_file = random.randint(0, nb_files - 1)
                             
                # Test if path or directory always exist (change value dynamically)
                path_of_filter =f"{self.path_of_filters_directory}/{nb_filter_not_show[rand_file][0]}"
                
                # No surprise ?
                if not self.filter_always_exist(path_of_filter):
                    self.list_of_filter.remove(nb_filter_not_show[rand_file])
                    self.get_photo_filter()
                    
                # next(ind for ind, tup in enumerate(self.list_of_filter) if nb_filter_not_show[rand_file][0] in tup)
                self.list_of_filter = self.update_list_of_filter_value(self.list_of_filter, str(nb_filter_not_show[rand_file][0]), True)
                
                # Reinit if all show
                if sum(1 for file in self.list_of_filter if file[1] == False) == 0:
                    newList = []
                    for f, aff in self.list_of_filter:
                        newList.append((f, False))
                    self.list_of_filter = newList
                     
            return path_of_filter if self.list_of_filter else None
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera get_photo_filter() : {ex}")
    
    def list_of_filters(self):
        try:
            filter_finded = []
            if os.path.exists(self.path_of_filters_directory):
                filter_finded = os.listdir(self.path_of_filters_directory)
            #
            if (filter_finded and len(filter_finded) > 0) and not self.list_of_filter:
                self.init_list_of_filters()
            elif (filter_finded and len(filter_finded) > 0) and len(filter_finded) != len(self.list_of_filter):
                self.populate_list_of_filter(filter_finded, self.list_of_filter)
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera list_of_filters() : {ex}")
    
    def filter_always_exist(self, filter_path):
        try:
            return (filter_path != None and os.path.isfile(filter_path))
                
        except Exception as ex:
            self.logs.error(f"Error in ccamera filter_always_exist() : {ex}")
            
    def populate_list_of_filter(self, new_list_of_filter, list_of_filter):
        try:
            for filt in new_list_of_filter:
                list_of_filter.append((filt, False)) if (filt, True) not in list_of_filter and (filt, False) not in list_of_filter else None
                    
        
        except Exception as ex:
            self.logs.error(f"Error in ccamera populate_list_of_filter() : {ex}")
            
    def update_list_of_filter_value(self, list_of_filter, key, value):
        try:
            return [(ke,va) if (ke != key) else (ke, value) for (ke, va) in list_of_filter]
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera update_list_of_filter_value() : {ex}")
            
    def filter_layer(self, path, size):
        '''
        Filter read from its file and scaled only once (the preview used to read it
        again from the SD card for each of its pictures)
        '''
        key = (path, os.path.getmtime(path), int(size[0]), int(size[1]))
        layer = self._filter_layers.get(key)
        if layer is None:
            layer = pygame.transform.scale(pygame.image.load(path).convert_alpha(), (key[2], key[3]))
            if len(self._filter_layers) >= 8:
                self._filter_layers.clear()
            self._filter_layers[key] = layer
        return layer

    def show_camera(self, screen, posX=0, posY=0, resW=0, resH=0):
        '''
        Display camera
        '''
        try:
            screen_width, screen_height = screen.get_size()
            if resW == 0:
                resW = self.pict_res_width
            if resH == 0:
                resH = self.pict_res_height
            # centrage automatique si posX = 0 ou posY = 0
            if posX == 0:
                posX = ((screen_width - resW) / 2)
            if posY == 0:
                posY = ((screen_height - resH) / 2)
                
            # on va eviter tout debordement du preview
            resW, resH = self.resize_camera_image(screen, posX, posY, resW, resH)
            
            camera_picture = Rect(posX, posY, resW, resH)
                  
            if self.is_connected():
                # 
                if self.camera is None:
                    # On reinitialise
                    self.camera = pygame.camera.Camera(f"/dev/video{self.camera_id}")
                    self.camera_start()
                # get a preview picture
                image = self.camera.get_image()
                # upscale image
                image = pygame.transform.scale(image, (resW, resH))
                # flip 
                image = pygame.transform.flip(image, self.flip_horizontal, self.flip_vertical)
                
                if self.incr_filter == 0:
                    self.path_of_filter = self.get_photo_filter()
                    
                self.incr_filter += 1
                if self.incr_filter == 30:
                    self.incr_filter = 0                    
                
                # certains aiment supprimer les filtres en cours
                if not self.filter_always_exist(self.path_of_filter):
                    self.path_of_filter = self.get_photo_filter()
                
                #path_of_filter = self.get_photo_filter()
                #if path_of_filter is not None:
                if self.path_of_filter is not None:
                    # Le calque, a la taille de l'apercu
                    calque = self.filter_layer(self.path_of_filter, (resW, resH))
                    # On applique le calque
                    image.blit(calque,(0, 0))
                    
                # display the preview
                screen.blit(image,(posX, posY))
                
            else:
                pygame.draw.rect(screen, pygame.Color(100, 100, 100), camera_picture)
                pygame.draw.line(screen, (255, 255, 255), (posX, posY), (posX + resW, posY + resH), 10)
                pygame.draw.line(screen, (255, 255, 255), (posX , posY + resH), (posX + resW, posY), 10)
                
            # refresh
            pygame.display.update(camera_picture)                    
                
        except Exception as ex:
            self.logs.error(f"Error in ccamera show_camera() : {ex}")             
     
    def folder_tree(self, directory_name, game):
        try:
            if self.directory_order == 0:
                # /home/pi/Pictures_Videos/Date/Jeux/Photos_Videos
                return f"{directory_name}/{game}"
            elif self.directory_order == 1:                
                # /home/pi/Pictures_Videos/Jeux/Date/Photos_Videos
                return f"{game}/{directory_name}"
                
        except Exception as ex:
            self.logs.error(f"Error in ccamera folder_tree() : {ex}")
                
    def action(self, directory_name_of_game, file_name):
        try:
            with self._capture_lock:
                if self.work_in_progress:
                    return
                if self.choice_of_memories == 0:
                    return
                self.work_in_progress = True
                choice = self.choice_of_memories

            filename = f"{file_name}"
            directory_game_name = f"{directory_name_of_game}"

            if choice == 3:
                choice = random.randint(1, 2)

            if choice == 1:
                # Cheeeeeeze
                self.take_shot(game=directory_game_name, picture_name=filename)
            elif choice == 2:
                # Lights... Camera... ...aaaaannnnnddd Action !
                self.take_video(game=directory_game_name, video_name=filename)

        except Exception as ex:
            self.work_in_progress = False
            self.logs.error(f"Error in ccamera action() : {ex}")
    
    def take_shot(self, start_stop=True, game="Test", picture_name=None):
        '''
        Here we take a shot in thread mode
        '''
        try:
            threading.Thread(target=self.take_a_shot, args=(start_stop,game,picture_name,), daemon=True).start()
        except Exception as ex:
            self.logs.error(f"Error in ccamera take_shot() : {ex}") 
        
    def take_a_shot(self, start_stop=True, game="Test", picture_name=None):
        '''
        Here we take a shot of the current event
        '''
        try:
            if self.is_connected():
                # Create folder in Google Drive if it not exists
                if self._uploadToGoogleDrive is not None:
                    if self._uploadToGoogleDrive.get_folder_id() is None:
                        self._uploadToGoogleDrive.create_new_folder_in_google_drive(game)
                # start engine...
                if start_stop:
                    self.camera_start()
                nbCapture = 0
                while nbCapture < self.nb_picture:
                    # get a preview picture
                    picture_shot = self.camera.get_image().convert_alpha()
                    picture_shot = pygame.transform.scale(picture_shot, (1024, 765))
                    nbCapture += 1
                    # flip
                    picture_shot = pygame.transform.flip(picture_shot, self.flip_horizontal, self.flip_vertical)
                    # name and other
                    now = datetime.datetime.now()
                    if picture_name is None:
                        pictureName = now.strftime("%H:%M:%S.%f")
                    else:
                        pictureName = picture_name
                    directory_name = now.strftime("%d_%m_%Y")
                    directory_default_name = f"{self.picture_path}/{self.folder_tree(directory_name, game)}"
                    if not os.path.exists(directory_default_name):
                        os.makedirs(directory_default_name)

                    path_of_filter = self.get_photo_filter()
                    if path_of_filter is not None:
                        calque = self.filter_layer(path_of_filter, (1024, 765))
                        picture_shot.blit(calque, (0, 0))

                    # save
                    pygame.image.save(picture_shot, f"{directory_default_name}/{pictureName}.png")

                    # Load picture in Google Drive
                    if self._uploadToGoogleDrive is not None:
                        if self._uploadToGoogleDrive.get_folder_id() is not None:
                            self._uploadToGoogleDrive.upload_one_picture_video_to_google_drive(f"{directory_default_name}/{pictureName}.png")

                    # Look at me !
                    self.show_image_popup(f"{directory_default_name}/{pictureName}.png", fullscreen=self.fullscreen, duree=self.duree)

                # ...stop engine
                if start_stop:
                    self.camera_stop()

        except Exception as ex:
            self.logs.error(f"Error in ccamera take_a_shot() : {ex}")
        finally:
            self.work_in_progress = False
           
    def take_video(self, game="Test", video_name=None):
        '''
        Here we take a video in thread mode
        '''
        try:
            threading.Thread(target=self.take_a_video, args=(None,False,game,video_name,), daemon=True).start()
        except Exception as ex:
            self.logs.error(f"Error in ccamera take_video() : {ex}") 
            
    def take_a_video(self, screen_with_all_information=None, stop_start=True, game="Test", video_name=None):
        '''
        Here we take a video of the current event
        '''
        # screen_with_all_information : (screen, defaultfontpath, posX_camera, posY_camera, resW, resH)
        try:
            if self.is_connected():
                # Create folder in Google Drive if it not exists
                if self._uploadToGoogleDrive is not None:
                    if self._uploadToGoogleDrive.get_folder_id() is None:
                        self._uploadToGoogleDrive.create_new_folder_in_google_drive(game)
                # stop engine...
                if stop_start:
                    self.camera_stop()
                # warn user (for exemple : parameters screen)
                if screen_with_all_information is not None:
                    resW, resH = self.resize_camera_image(screen_with_all_information[0], screen_with_all_information[2], screen_with_all_information[3],
                                                          self.vid_res_width, self.vid_res_height)
                    camera_picture = Rect(screen_with_all_information[2], screen_with_all_information[3], resW, resH)
                    pygame.draw.rect(screen_with_all_information[0], pygame.Color(100, 100, 100), camera_picture)
                    font = pygame.font.Font(screen_with_all_information[1], 30)
                    text = font.render("Recording in progress..", True, (255, 255, 255))
                    screen_with_all_information[0].blit(text, (screen_with_all_information[2] + 100, screen_with_all_information[3] + 100))
                    pygame.display.update(camera_picture)
                # name and other
                now = datetime.datetime.now()
                if video_name is None:
                    video_name = now.strftime("%H:%M:%S.%f")
                directory_name = now.strftime("%d_%m_%Y")
                directory_default_name = f"{self.video_path}/{self.folder_tree(directory_name, game)}"
                if not os.path.exists(directory_default_name):
                    os.makedirs(directory_default_name)
                output_path = f"{directory_default_name}/{video_name}.mp4"

                # Build flip filters
                flip_filters = []
                if self.flip_horizontal:
                    flip_filters.append('hflip')
                if self.flip_vertical:
                    flip_filters.append('vflip')

                path_of_filter = self.get_photo_filter()

                # Base command (with audio)
                cmd = [
                    'ffmpeg', '-v', 'quiet',
                    '-f', 'alsa', '-ac', '1', '-i', 'default',
                    '-f', 'v4l2',
                    '-video_size', f'{self.vid_res_width}x{self.vid_res_height}',
                    '-vsync', 'vfr',
                    '-i', f'/dev/video{self.camera_id}'
                ]

                if path_of_filter is not None:
                    # PNG overlay filter: input[2]=png, input[1]=video
                    cmd.extend(['-i', path_of_filter])
                    scale_part = f'[2]scale={self.vid_res_width}:{self.vid_res_height}[png]'
                    if flip_filters:
                        flip_str = ','.join(flip_filters)
                        complex_filter = f'{scale_part};[1:v]{flip_str}[video];[video][png]overlay'
                    else:
                        complex_filter = f'{scale_part};[1][png]overlay'
                    cmd.extend(['-filter_complex', complex_filter])
                elif flip_filters:
                    cmd.extend(['-vf', ','.join(flip_filters)])

                cmd.extend(['-t', f'00:00:{self.video_duration:02d}', output_path])

                subprocess.run(cmd)

                # Load video in Google Drive
                if self._uploadToGoogleDrive is not None:
                    if self._uploadToGoogleDrive.get_folder_id() is not None:
                        self._uploadToGoogleDrive.upload_one_picture_video_to_google_drive(output_path)

                # Tadaaaa
                self.show_action_video(output_path)

                # ...start engine
                if stop_start:
                    self.camera_start()

        except Exception as ex:
            self.logs.error(f"Error in ccamera take_a_video() : {ex}")
        finally:
            self.work_in_progress = False
            
    def show_action_video(self, video_path):
        try:
            # on cherche la resolution de l'ecran
            screen_size = os.popen("xrandr | head -n1 | cut -d, -f2 | cut -d' ' -f3-5")
            screen_size_width, screen_size_height = screen_size.read().split('x')
            
            right_corner_x = int(screen_size_width.strip()) - self.vid_res_width
            right_corner_y = int(screen_size_height.strip()) - self.vid_res_height
            
            player = cvideos.find_player()
            if player == 'omxplayer':
                command = ['omxplayer', '--win', f'{right_corner_x},-{right_corner_y},{int(screen_size_width.strip())},{int(screen_size_height.strip())}',
                           '--aspect-mode','letterbox','-o', 'alsa', f'{video_path}']
            elif player is not None:
                # Top right corner of the screen, at the size of the recorded video
                command = cvideos.player_command(player, video_path,
                                                 window=(right_corner_x, 0, self.vid_res_width, self.vid_res_height))
            else:
                self.logs.warning("No video player found : recorded video is not shown")
                return

            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
        except Exception as ex:
            self.logs.error(f"Error in ccamera show_action_photo() : {ex}")

    def show_qr_code(self):   
            try:
                if self._uploadToGoogleDrive is not None:
                    if self._uploadToGoogleDrive.get_folder_id() is not None:
                        qrPop = self._uploadToGoogleDrive.get_qrcode_to_new_google_drive_folder()
                        if qrPop is not None:
                            self.show_qr_popup(qrPop)
                        
            except Exception as ex:
                self.logs.error(f"Error in ccamera show_qr_code() : {ex}") 

    def show_qr_code_for_pictures_videos(self):
            try:
                threading.Thread(target=self.show_qr_code, daemon=True).start()

            except Exception as ex:
                self.logs.error(f"Error in ccamera get_qr_code_for_pictures_videos() : {ex}")
       
    def show_image_popup(self, image_path, fullscreen=False, duree=5000):
        """
        Affiche une image en popup via subprocess
        """
        try:
            if not os.path.exists(image_path):
                self.logs.error(f"Image path does not exist: {image_path}")
                return
            
            popup_script = None
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'cpopup_manager.py'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cpopup_manager.py'),
                os.path.join(cpaths.ROOT_DIR, 'include', 'cpopup_manager.py')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    popup_script = path
                    break
            
            if not popup_script:
                self.logs.error("cpopup_manager.py not found")
                return
            
            cmd = [
                'python3',
                popup_script,
                'image',
                image_path,
                'true' if fullscreen else 'false',
                str(duree)
            ]
            
            # Lancer en arrière-plan (non-bloquant)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera show_image_popup() : {ex}")

    def close_qr_popup(self):
        """
        Ferme le popup QR code
        """
        try:
            if self._uploadToGoogleDrive is not None:
                self._uploadToGoogleDrive.reinit_folder_id()
        except Exception as ex:
            self.logs.error(f"Error in ccamera close_qr_popup() : {ex}")

    def show_qr_popup(self, qr_img):
        """
        Affiche le QR code en popup via subprocess
        """
        try:
            # Sauvegarder le QR code temporairement
            tmp_path = "/tmp/temp_qr_popup.png"
            qr_display_size = 200
            resized_qr = qr_img.resize((qr_display_size, qr_display_size), resample=Image.BICUBIC)
            resized_qr.save(tmp_path)
            
            popup_script = None
            possible_paths = [
                os.path.join(os.path.dirname(__file__), 'cpopup_manager.py'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cpopup_manager.py'),
                os.path.join(cpaths.ROOT_DIR, 'include', 'cpopup_manager.py')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    popup_script = path
                    break
            
            if not popup_script:
                self.logs.error("cpopup_manager.py not found")
                return
            
            cmd = [
                'python3',
                popup_script,
                'qr',
                tmp_path,
                '30000'
            ]
            
            # Lancer en arrière-plan (non-bloquant)
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        except Exception as ex:
            self.logs.error(f"Error in ccamera show_qr_popup(): {ex}")

