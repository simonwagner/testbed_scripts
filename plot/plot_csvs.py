#!/usr/bin/env python

import argparse
import csv
import re

import numpy as np
import pandas as pd
import matplotlib

import matplotlib
matplotlib.use("pgf")
pgf_with_pdflatex = {
    "pgf.texsystem": "pdflatex",
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": [],
    "axes.labelsize": 10,
    "font.size": 10,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "pgf.preamble": [
             r"\usepackage[utf8x]{inputenc}",
             r"\usepackage[T1]{fontenc}",
             r"\usepackage{cmbright}",
             ]
}
matplotlib.rcParams.update(pgf_with_pdflatex)
import matplotlib.pyplot as plt

from matplotlib2tikz import save as tikz_save

argparser = argparse.ArgumentParser()

argparser.add_argument("input_csvs", nargs="*", metavar="CSV")
argparser.add_argument("-o", "--output")
argparser.add_argument("-f", "--format", choices=["pdf", "pgf", "png", "tikz", "tex"])
argparser.add_argument("--max-speed-mbit", type=float, default=1000)

CSV_FILENAME_RE = re.compile(r".*cores_(\d+)_conn_(\d+)_sndbuff_(\d+)\.csv$")

def main():
    args = argparser.parse_args()

    cores_measurements = read_data(args.input_csvs)
    percentiles_cores_measurements = {}
    
    for cores, measurements in cores_measurements.iteritems():
        percentile_measurements = [(connections, calc_percentiles(connection_measurements)) for (connections, connection_measurements) in measurements]
        percentiles_cores_measurements[cores] = percentile_measurements
    
    f = plt.figure(figsize=(5, 2.5))
    ax = f.add_subplot(111)
    
    plot_connections_per_core(ax, percentiles_cores_measurements)
    
    #set linerate marker
    plt.axhline(y=args.max_speed_mbit, linestyle="dotted", color="grey")
    ax.annotate("line rate", color="grey", xy=(0, args.max_speed_mbit), xycoords=("axes pixels", "data"), xytext=(1, 5), textcoords='offset pixels').set_fontsize(8)
    
    if args.output.endswith(args.format):
        output_fname = args.output
    else:
        output_fname = args.output + "." + args.format
    
    ax.legend()
    ax.set_ylim(ymin=0.0, ymax=args.max_speed_mbit*1.1) # 10% over line rate
    ax.set_ylabel("throughput [Mbit/s]")
    ax.set_xlabel("connections")
    
    if args.format == "tikz" or args.format == "tex":
        tikz_save(output_fname, figure=f, figureheight='4.5cm', figurewidth='10cm')
    else:
        f.savefig(output_fname)
    
    
def read_data(input_csvs):
    cores_measurements = {}
    
    for input_csv in input_csvs:
        print "%s..." % input_csv
        filename_match = CSV_FILENAME_RE.match(input_csv)
        cores = int(filename_match.group(1))
        connections = int(filename_match.group(2))
        sndbuff = int(filename_match.group(3))
        
        measurements_per_thread = pd.read_csv(input_csv, delimiter=";", header=None, names=["thread", "connection", "bytes", "count_connections", "start", "end"])
        measurements = combine_measurements_from_threads(measurements_per_thread)
        #drop the first 10 sec of measurements, as that has the slow start up phase
        measurements.drop(measurements[measurements.start < 5.0].index, inplace=True)
        #drop all measurements where we have not yet reached the maximum number of connections
        max_connections = measurements["count_connections"].max()
        measurements.drop(measurements[measurements.count_connections < max_connections].index, inplace=True)
        #now calculate the speed
        measurements["speed"] = measurements.apply(lambda row: speed(row), axis=1)
        #only get the bytes column as that has the sweet, sweet data
        speed_measurements = measurements.ix[:, "speed"]
        
        cores_measurements[cores] = cores_measurements.get(cores, []) + [(max_connections, speed_measurements)]
    return cores_measurements

def combine_measurements_from_threads(measurements_per_thread):
    threads = measurements_per_thread["thread"].unique()
    
    #group measurements in a similar time range together
    #upper bound is 5.1sec
    measurements = pd.DataFrame(columns=["bytes", "connection", "start", "end"])
    for (thread_measurement_index, thread_measurement) in measurements_per_thread.iterrows():
        matching_measurement_ix = None
        for (measurment_index, measurement) in measurements.iterrows():
            if max(measurement["end"], thread_measurement["end"]) - min(measurement["start"], thread_measurement["start"]) < 5.1:
                matching_measurement_ix = measurment_index
                break
        if matching_measurement_ix is None:
            measurements = measurements.append({
                "connection": 0,
                "bytes": 0,
                "count_connections": 0,
                "start": thread_measurement["start"],
                "end": thread_measurement["end"],
            }, ignore_index=True)
            matching_measurement_ix = measurements.iloc[-1].name
        
        matching_measurement = measurements.iloc[matching_measurement_ix]
        measurements.loc[matching_measurement_ix, "start"] = min(matching_measurement["start"], thread_measurement["start"])
        measurements.loc[matching_measurement_ix, "end"] = max(matching_measurement["end"], thread_measurement["end"])
        measurements.loc[matching_measurement_ix, "bytes"] += thread_measurement["bytes"] * 8
        measurements.loc[matching_measurement_ix, "count_connections"] += thread_measurement["count_connections"]
    
    return measurements

def speed(row):
    return row["bytes"]/(row["end"] - row["start"])

def calc_percentiles(measurements):
    return [measurements.quantile(p) for p in (0.25, 0.5, 0.75)]

def plot_connections_per_core(ax, percentiles_cores_measurements):
    for core, percentiles_core_measurements in percentiles_cores_measurements.iteritems():
        measurements = sorted(percentiles_core_measurements, key=lambda item: item[0])
        xs = [item[0] for item in measurements]
        ys = [item[1][1]/1e6 for item in measurements]
        yerr = [
                 [(item[1][1] - item[1][0])/1e6 for item in measurements],
                 [(item[1][2] - item[1][1])/1e6 for item in measurements]
               ]
        
        plt.errorbar(xs, ys, yerr=yerr, marker='x', label="%d cores" % core)

if __name__ == "__main__":
    main()