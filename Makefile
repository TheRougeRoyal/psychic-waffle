CXX = g++
CXXFLAGS = -std=c++17 -Wall -O3 -shared -fPIC

TARGET = libbb_strategy.so
OBJS = strategy.o

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS)

strategy.o: strategy.cpp strategy.hpp
	$(CXX) $(CXXFLAGS) -c strategy.cpp

clean:
	rm -f $(TARGET) $(OBJS)
