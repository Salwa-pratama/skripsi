Hallo hari ini saya akan belajar mengenai computer vision menggunakan mobilenet-SSD, dan media pipe



Dibawah ini merupakan model MobileNetSSD yang saya pakai
``` bash
# MobileNetSSD_deploy.prototxt
wget https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/voc/MobileNetSSD_deploy.prototxt

# MobileNetSSD_deploy.caffemodel
wget -O MobileNetSSD_deploy.caffemodel https://raw.githubusercontent.com/djmv/MobilNet_SSD_opencv/master/MobileNetSSD_deploy.caffemodel

```

Dan dibawah ini merupakan model COCO-SSD yang saya pakai
``` bash
wget http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz
tar -xvf ssd_mobilenet_v2_coco_2018_03_29.tar.gz
# extraksi jika menggunakan containerisasi
tar --no-same-owner -xvf ssd_mobilenet_v2_coco_2018_03_29.tar.gz
wget https://raw.githubusercontent.com/opencv/opencv_extra/master/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt

```


1. Download kategori tertentu 

- Untuk hanya abjad saja 

python3 scrape_sibi.py --category abjad


- Hanya angka 

python3 scrape_sibi.py --category angka


- Hanya Kata Dasar Tertentu (Misal awalan huruf A dan B)

python3 scrape_sibi.py --category kata_dasar --letters ab


2. Mengumpulkan Metadata Dulu

python3 scrape_sibi.py --metadata-only

3. Download Semua Data (Abjad, Angka, Imbuhan, & Kata Dasar A-Z)

python3 scrape_sibi.py --category all

4. Ekstrasi Otomatis Frame Citra 

python3 scrape_sibi.py --category kata_dasar --extract-frames --fps 5

