set -v

sudo ls > /dev/null
./build-web.sh
sudo dpkg -i omogenjudge-web.deb
sudo service omogenjudge-web restart
