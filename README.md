dain+waifu2x+ffmpeg



mkdir dainfux
cd dainfux

git clone https://github.com/amadeok/Dainfux


FFMPEG:
wget https://ffmpeg.org/releases/ffmpeg-4.3.2.tar.xz

tar -xf ffmpeg-4.3.2.tar.xz

cp Dainfux/ffmpeg-4.3.2/libavfilter/vf_photosensitivity.c ffmpeg-4.3.2/libavfilter/vf_photosensitivity.c

cd ffmpeg-4.3.2 

./configure

make -j4



WAIFU2X:
cd ..

wget https://github.com/nihui/waifu2x-ncnn-vulkan/archive/refs/tags/20210210.tar.gz

tar -xf 20210210.tar.gz




git clone https://github.com/nihui/waifu2x-ncnn-vulkan.git

rm -r waifu2x-ncnn-vulkan/src
rm -r waifu2x-ncnn-vulkan/models
rm -r waifu2x-ncnn-vulkan/images


cp -a waifu2x-ncnn-vulkan-20210210/. waifu2x-ncnn-vulkan/

cd waifu2x-ncnn-vulkan

git submodule update --init --recursive

mkdir build

cp -R ../Dainfux/waifu2x-ncnn-vulkan-20210210/src .

cmake ../src

cmake --build . -j 4



DAIN:


conda env create -f Dainfux/environment.yml

conda activate pytorch1.0.0

pip install torch==1.4.0+cu100 torchvision==0.5.0+cu100 -f https://download.pytorch.org/whl/torch_stable.html
pip install scipy==1.1.0

git clone -b colab-compatibility --depth 1 https://github.com/AlphaGit/DAIN DAIN

cd DAIN/my_package/

./build.sh

cd ../PWCNet/correlation_package_pytorch1_0

./build.sh

cd ../../

mkdir model_weights
wget -O model_weights/best.pth http://vllab1.ucmerced.edu/~wenbobao/DAIN/best.pth
!sudo apt-get install imagemagick imagemagick-doc


cp -a ../Dainfux/DAIN/. .


