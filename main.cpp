#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <iomanip>
#include "strategy.hpp"

std::vector<PriceData> read_csv(const std::string& filename) {
    std::vector<PriceData> data;
    std::ifstream file(filename);
    std::string line, word;

    if (!file.is_open()) {
        std::cerr << "Could not open file " << filename << std::endl;
        return data;
    }

    // Skip header
    std::getline(file, line);

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::vector<std::string> row;
        while (std::getline(ss, word, ',')) {
            row.push_back(word);
        }
        // Assuming CSV format: Date, Open, High, Low, Close, Adj Close, Volume
        if (row.size() >= 5) {
            data.push_back({row[0], std::stod(row[4])}); // Use Close price (index 4)
        }
    }
    return data;
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " <csv_file>" << std::endl;
        return 1;
    }

    std::string filename = argv[1];
    std::vector<PriceData> data = read_csv(filename);

    if (data.empty()) {
        return 1;
    }

    BollingerStrategy strategy(20, 2.0);
    std::vector<Signal> results = strategy.run_backtest(data);

    double total_return = 0;
    for (const auto& s : results) {
        total_return += s.strategy_return;
    }

    std::cout << std::fixed << std::setprecision(4);
    std::cout << "Backtest results for: " << filename << std::endl;
    std::cout << "Total Strategy Return: " << total_return * 100 << "%" << std::endl;
    std::cout << "Final Signal Position: " << results.back().position << std::endl;

    return 0;
}
