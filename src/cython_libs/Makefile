VERSION := 9.5.2237

# Boost is included in utils
BOOST_ROOT := $(shell pwd)/../utils/boost_1_81_0/

##############
##  SOURCE  ##
##############
.PHONY: build # Build a C++ program.
.PHONY: clean

build:
	cmake . -Bbuild -DCMAKE_PREFIX_PATH=$(shell pwd) -DBOOST_ROOT=$(BOOST_ROOT)
	cmake --build build

clean:
	-rm -rf build
	-rm *.o
	cmake . -Bbuild -DCMAKE_PREFIX_PATH=$(shell pwd) -DBOOST_ROOT=$(BOOST_ROOT)
	cmake --build build
	-mv build/kirschtorte.so ./
