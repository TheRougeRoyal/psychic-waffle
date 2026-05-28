#ifndef STRATEGY_HPP
#define STRATEGY_HPP

#include <vector>
#include <string>

struct PriceData {
    std::string date;
    double close;
};

struct Signal {
    std::string date;
    double price;
    double ma;
    double upper_band;
    double lower_band;
    int position;
    double daily_return;
    double strategy_return;
};

class BollingerStrategy {
public:
    BollingerStrategy(int window = 20, double std_dev_multiplier = 2.0);
    std::vector<Signal> run_backtest(const std::vector<PriceData>& data);
    Signal update(const std::string& date, double price);

private:
    int window;
    double std_dev_multiplier;
    std::vector<double> price_history;
    int current_position = 0;

    double calculate_sma(const std::vector<double>& prices, int end_idx);
    double calculate_stddev(const std::vector<double>& prices, int end_idx, double sma);
};

// C-API for ctypes bridge
extern "C" {
    void* create_strategy(int window, double std_dev_multiplier);
    void destroy_strategy(void* strategy);
    int run_strategy(void* strategy, double* prices, int n, Signal* results);
}

#endif
