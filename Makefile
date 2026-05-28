CXX = g++
CXXFLAGS = -std=c++17 -Wall -O3 -shared -fPIC $(shell ./venv/bin/pybind11-config --includes)

TARGET = bb_strategy.so
OBJS = strategy.o bindings.o

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

strategy.o: strategy.cpp strategy.hpp
	$(CXX) $(CXXFLAGS) -c strategy.cpp

bindings.o: bindings.cpp strategy.hpp
	$(CXX) $(CXXFLAGS) -c bindings.cpp

clean:
	rm -f $(TARGET) $(OBJS)
