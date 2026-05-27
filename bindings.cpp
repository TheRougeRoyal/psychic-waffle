#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "strategy.hpp"

namespace py = pybind11;

PYBIND11_MODULE(bb_strategy, m) {
    py::class_<PriceData>(m, "PriceData")
        .def(py::init<std::string, double>())
        .def_readwrite("date", &PriceData::date)
        .def_readwrite("close", &PriceData::close);

    py::class_<Signal>(m, "Signal")
        .def_readwrite("date", &Signal::date)
        .def_readwrite("price", &Signal::price)
        .def_readwrite("ma", &Signal::ma)
        .def_readwrite("upper_band", &Signal::upper_band)
        .def_readwrite("lower_band", &Signal::lower_band)
        .def_readwrite("position", &Signal::position)
        .def_readwrite("daily_return", &Signal::daily_return)
        .def_readwrite("strategy_return", &Signal::strategy_return);

    py::class_<BollingerStrategy>(m, "BollingerStrategy")
        .def(py::init<int, double>(), py::arg("window") = 20, py::arg("std_dev_multiplier") = 2.0)
        .def("run_backtest", &BollingerStrategy::run_backtest);
}
