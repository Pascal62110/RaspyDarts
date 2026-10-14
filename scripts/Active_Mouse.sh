#!/bin/sh
# Show the mouse cursor again (effective after a reboot)
sudo sed -i -- '/^xserver-command=/s/ -nocursor//' /etc/lightdm/lightdm.conf
