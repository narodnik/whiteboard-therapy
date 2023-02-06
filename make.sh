g++ -O3 -Wall -shared -std=c++11 -fPIC -Ipybind11/include/ -I/usr/include/python3.11/ bindy.cpp -linput -o python_libinput$(python3-config --extension-suffix)
