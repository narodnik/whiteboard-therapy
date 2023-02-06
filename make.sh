g++ -O3 -Wall -shared -std=c++11 -fPIC -I./ -I/usr/include/python3.11/ bindy.cpp -linput -o python_libinput$(python3-config --extension-suffix)
