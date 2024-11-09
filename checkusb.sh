lsusb -t | sed -e 's/ Dev [0-9]\+,//' > usb_current.txt
diff usb_current.txt usb_expected.txt

