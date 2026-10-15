#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import tkinter as tk
from PIL import Image
import os
from time import sleep

class PopupManager:
    def __init__(self):
        self.root = None
        
    def show_image_popup(self, image_path, fullscreen=False, duree=5000):
        """
        Affiche une image en popup
        """
        try:
            temp_path = "/tmp/_resized_popup_temp.png"
            
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            
            if fullscreen:
                self.root.attributes("-fullscreen", True)
            
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            if fullscreen:
                img = Image.open(image_path)
            if fullscreen and img.size == (screen_width, screen_height):
                # Already made at the size of the screen by the game (see ccamera.popup_picture)
                photo = tk.PhotoImage(file=image_path)
                max_width = int(screen_width)
                max_height = int(screen_height)
            elif fullscreen:
                scale = min(screen_width / img.width, screen_height / img.height)
                new_w = int(img.width * scale)
                new_h = int(img.height * scale)
                resized_img = img.resize((new_w, new_h), Image.ANTIALIAS if hasattr(Image, 'ANTIALIAS') else Image.LANCZOS)
                
                fond = Image.new("RGB", (screen_width, screen_height), (0, 0, 0))
                x = (screen_width - new_w) // 2
                y = (screen_height - new_h) // 2
                fond.paste(resized_img, (x, y))
                
                fond.save(temp_path)
                photo = tk.PhotoImage(file=temp_path)
                max_width = int(screen_width)
                max_height = int(screen_height)
            else:
                max_width = screen_width // 3
                max_height = screen_height // 3
                photo = tk.PhotoImage(file=image_path)

            image_width = photo.width()
            image_height = photo.height()
            
            facteur = max(
                image_width // max_width if image_width > max_width else 1,
                image_height // max_height if image_height > max_height else 1,
            )
            
            if facteur > 1:
                facteur = int(facteur + 0.5)
                photo = photo.subsample(facteur, facteur)
            
            image_width = photo.width()
            image_height = photo.height()
            
            label = tk.Label(self.root, image=photo)
            label.pack()
            
            if fullscreen:
                pos_x = (screen_width - image_width) // 2
                pos_y = (screen_height - image_height) // 2
            else:
                pos_x = screen_width - image_width
                pos_y = 0
            
            self.root.geometry(f"{image_width}x{image_height}+{pos_x}+{pos_y}")
            self.root.after(duree, self.root.destroy)
            label.image = photo
            
            self.root.mainloop()
            
            if fullscreen and os.path.exists(temp_path):
                os.remove(temp_path)
                
        except Exception as ex:
            print(f"Error in popup_manager show_image_popup(): {ex}")
            if self.root:
                self.root.destroy()
    
    def show_qr_popup(self, qr_image_path, duree=30000):
        """
        Affiche un QR code en popup
        """
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)
            self.root.attributes("-topmost", True)
            
            frame = tk.Frame(self.root)
            frame.pack(expand=True, fill='both', padx=10, pady=10)
            
            label_text = tk.Label(
                frame,
                text="Vos souvenirs sont disponibles ici",
                font=("Arial", 14)
            )
            label_text.pack(pady=(5, 2))
            
            label_arrow = tk.Label(frame, text="↓", font=("Arial", 24))
            label_arrow.pack(pady=(0, 5))
            
            qr_photo = tk.PhotoImage(file=qr_image_path)
            qr_label = tk.Label(frame, image=qr_photo)
            qr_label.image = qr_photo
            qr_label.pack()
            
            self.root.update_idletasks()
            w = self.root.winfo_reqwidth()
            h = self.root.winfo_reqheight()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = sw - w
            y = int(sh * 0.05)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
            
            # Animation de couleurs
            gradient_colors = ["#ffffff", "#f0f8ff", "#e6f2ff", "#d9ecff", 
                             "#cce6ff", "#d9ecff", "#e6f2ff", "#f0f8ff"]
            color_index = [0]
            
            def cycle_colors():
                try:
                    new_color = gradient_colors[color_index[0]]
                    self.root.configure(bg=new_color)
                    for widget in self.root.winfo_children():
                        widget.configure(bg=new_color)
                        for subwidget in widget.winfo_children():
                            try:
                                subwidget.configure(bg=new_color)
                            except Exception:
                                pass
                    color_index[0] = (color_index[0] + 1) % len(gradient_colors)
                    self.root.after(300, cycle_colors)
                except Exception:
                    pass
            
            self.root.after(100, cycle_colors)
            self.root.after(duree, self.root.destroy)
            self.root.mainloop()
            
        except Exception as ex:
            print(f"Error in popup_manager show_qr_popup(): {ex}")
            if self.root:
                self.root.destroy()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: popup_manager.py <type> <path> [fullscreen] [duree]")
        sys.exit(1)
    
    popup_type = sys.argv[1]
    path = sys.argv[2]
    
    manager = PopupManager()
    
    if popup_type == "image":
        fullscreen = sys.argv[3].lower() == "true" if len(sys.argv) > 3 else False
        duree = int(sys.argv[4]) if len(sys.argv) > 4 else 5000
        manager.show_image_popup(path, fullscreen, duree)
    
    elif popup_type == "qr":
        duree = int(sys.argv[3]) if len(sys.argv) > 3 else 30000
        manager.show_qr_popup(path, duree)
