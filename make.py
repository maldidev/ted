#!/bin/python3
from os import *
o = input("Do you have linux or WIN32_NT? (l=linux, w=win) ")
if o == "l":
    system("sudo cp ./ted.conf /etc")
    system("cp ./ted.py ./ted")
    system("chmod 775 ./ted")
    system("sudo mv ./ted /usr/bin")
    print("Done! just type 'ted <filename>.<filetype>'")
elif o == "w":
    system('pyinstaller --onefile --name "ted" ted-win.py')
    print("Go to dist/ and just type 'ted' or 'ted <filename>.<filetype>'")