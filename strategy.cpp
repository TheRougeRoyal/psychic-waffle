#include "strategy.hpp"
#include <cmath>
#include <numeric>
#include <algorithm>

BollingerStrategy::BollingerStrategy(int window, double std_dev_multiplier)
    : window(window), std_dev_multiplier(std_dev_multiplier) {}

double BollingerStrategy::calculate_sma(const std::vector<double>& prices, int end_idx) {
    double sum = 0.0;
    for (int i = end_idx - window + 1; i <= end_idx; ++i) {
        sum += prices[i];
    }
    return sum / window;
}

double BollingerStrategy::calculate_stddev(const std::vector<double>& prices, int end_idx, double sma) {
    double sum_sq_diff = 0.0;
    for (int i = end_idx - window + 1; i <= end_idx; ++i) {
        sum_sq_diff += std::pow(prices[i] - sma, 2);
    }
    return std::sqrt(sum_sq_diff / window);
}

std::vector<Signal> BollingerStrategy::run_backtest(const std::vector<PriceData>& data) {
    int n = data.size();
    std::vector<double> close_prices;
    for (const auto& d : data) close_prices.push_back(d.close);

    std::vector<Signal> results;
    int current_position = 0;

    for (int i = 0; i < n; ++i) {
        if (i < window - 1) {
            results.push_back({0, 0, 0, 0, 0, 0, 0});
            continue;
        }

        double sma = calculate_sma(close_prices, i);
        double stddev = calculate_stddev(close_prices, i, sma);
        double upper = sma + (std_dev_multiplier * stddev);
        double lower = sma - (std_dev_multiplier * stddev);

        double prev_close = close_prices[i - 1];
        double prev_sma = calculate_sma(close_prices, i - 1);
        double prev_stddev = calculate_stddev(close_prices, i - 1, prev_sma);
        double prev_lower = prev_sma - (std_dev_multiplier * prev_stddev);
        double prev_upper = prev_sma + (std_dev_multiplier * prev_stddev);

        if (close_prices[i] < lower && prev_close >= prev_lower) {
            current_position = 1;
        } else if (close_prices[i] > upper && prev_close <= prev_upper) {
            current_position = -1;
        }

        double daily_ret = 0;
        if (i > 0) {
            daily_ret = std::log(close_prices[i] / close_prices[i - 1]);
        }

        results.push_back({close_prices[i], sma, upper, lower, current_position, daily_ret, 0});
    }

    for (int i = 1; i < results.size(); ++i) {
        results[i].strategy_return = results[i-1].position * results[i].daily_return;
    }

    return results;
}

// C-API implementations
extern "C" {
    void* create_strategy(int window, double std_dev_multiplier) {
        return new BollingerStrategy(window, std_dev_multiplier);
    }

    void destroy_strategy(void* strategy) {
        delete static_cast<BollingerStrategy*>(strategy);
    }

    int run_strategy(void* strategy, double* prices, int n, Signal* results) {
        BollingerStrategy* strat = static_cast<BollingerStrategy*>(strategy);
        std::vector<PriceData> data;
        for (int i = 0; i < n; ++i) {
            data.push_back({prices[i]});
        }

        std::vector<Signal> res = strat->run_backtest(data);

        int output_size = std::min((int)res.size(), n);
        for (int i = 0; i < output_size; ++i) {
            results[i] = res[i];
        }
        return output_size;
    }
}
