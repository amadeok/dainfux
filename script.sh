#!/bin/bash

pip install torch==1.4.0+cu100 torchvision==0.5.0+cu100 -f https://download.pytorch.org/whl/torch_stable.html
pip install scipy==1.1.0
pip install ffmpeg-python
pip install gputil
pip install distro


wget -qO - https://packages.lunarg.com/lunarg-signing-key-pub.asc | sudo apt-key add -
sudo wget -qO /etc/apt/sources.list.d/lunarg-vulkan-1.2.154-bionic.list https://packages.lunarg.com/vulkan/1.2.154/lunarg-vulkan-1.2.154-bionic.list
sudo apt update
sudo apt install vulkan-sdk

cd /content/dainfux
wget https://github.com/nihui/waifu2x-ncnn-vulkan/archive/refs/tags/20210210.tar.gz
tar -xf 20210210.tar.gz
git clone https://github.com/nihui/waifu2x-ncnn-vulkan.git

cd /content/dainfux/
cp -a waifu2x-ncnn-vulkan-20210210/. waifu2x-ncnn-vulkan/



cd /content/dainfux/

rm -r waifu2x-ncnn-vulkan/src
rm -r waifu2x-ncnn-vulkan/models
rm -r waifu2x-ncnn-vulkan/images
cp -a waifu2x-ncnn-vulkan-20210210/. waifu2x-ncnn-vulkan/
cd /content/dainfux/waifu2x-ncnn-vulkan

cp -R ../Dainfux/waifu2x-ncnn-vulkan-20210210/src .


cd /content/dainfux/
git clone -b colab-compatibility --depth 1 https://github.com/AlphaGit/DAIN /content/dainfux/DAIN
cd /content/dainfux/DAIN
git log -1

cd /content/dainfux/DAIN
mkdir model_weights
wget -O model_weights/best.pth http://vllab1.ucmerced.edu/~wenbobao/DAIN/best.pth

CUDA_VISIBLE_DEVICES=0
sudo apt-get install imagemagick imagemagick-doc

cd /content/dainfux/DAIN
cp -a ../Dainfux/DAIN/. .

chmod 755 "/content/dainfux/Dainfux/waifu2x-ncnn-vulkan-20210210/build/ubuntu18.04/waifu2x-ncnn-vulkan"
chmod 755 "/content/dainfux/Dainfux/ffmpeg-4.3.2/ubuntu18.04/ffmpeg"







