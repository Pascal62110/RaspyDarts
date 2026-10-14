#!/bin/sh
# Hide the mouse cursor (effective after a reboot)
CONF=/etc/lightdm/lightdm.conf

if grep -q '^xserver-command=' $CONF
then
	# Keep the other options of the X server
	sudo sed -i -- '/^xserver-command=/{/-nocursor/!s/$/ -nocursor/}' $CONF
else
	sudo sed -i -- 's/^#xserver-command=X.*/xserver-command=X -nocursor/' $CONF
fi
