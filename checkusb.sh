lsusb -t | sed -e 's/ Dev [0-9]\+,//' > json/usb_current.txt
diff -s json/usb_current.txt json/usb_expected.txt

