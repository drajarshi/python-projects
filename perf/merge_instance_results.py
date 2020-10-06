__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2020 Rajarshi Das"

# Given a set of result csv files generated by the run_netperf.py wrapper,
# merge them, and either a) group the run instances by start time or 
# b) map the number of instances running by timestamp
# c) compute the mean latency, mean transaction rate and 90th pct latency
# output files: 1. merged.csv (all result files merged),
# 2. grouped_by_start_time.csv (instance count by start time)
# 3. map_ts_instance_count.csv (instance count by run timestamp) 
# 4. tps_and_latency.csv (mean, 90pct latency and mean tps)

import pandas as pd
import sys
import time
import datetime
import csv
import os
import numpy as np

MERGE_DATA_FILE = "merged.csv"
INSTANCE_GROUP_BY_START_TIME_FILE = "grouped_by_start_time.csv"
TIMESTAMP_INSTANCE_COUNT_MAP_FILE = "map_ts_instance_count.csv"
TPS_AND_LATENCY_FILE = "tps_and_latency.csv"

def merge_results(file_list):
    df_files = [];

    for i in range(len(file_list)):
        print(file_list[i]);
        #df_files.append(pd.DataFrame(pd.read_csv(file_list[i])));
        print("i: ",i);
        if (i==0):
            df = pd.DataFrame(pd.read_csv(file_list[i]));
        else:
            df = df.append(pd.DataFrame(pd.read_csv(file_list[i])),\
                    ignore_index=True);

    print(df);
    df.to_csv("merged.csv");
    #print(df_files);
    return df;

def fetch_tps_and_latency(df,start_time=0,end_time=0):
    # 90th percentile of the 90th percentile latency times of all instances
    p90_latency_microsecs = np.percentile(df['p90_latency(microseconds)'],90);

    # Average of the mean latency times of all instances
    mean_latency_microsecs = df['mean_latency(microseconds)'].mean();

    # Mean Transaction rate of all instances
    start_time = int(time.mktime(time.strptime(df["start_time"][0],\
                "%d-%m-%Y_%H:%M:%S")));
    end_time = int(time.mktime(time.strptime(df["end_time"][len(df.index)-1],\
                "%d-%m-%Y_%H:%M:%S")));
    total_duration = end_time - start_time;

    mean_transaction_rate = (df['transaction_rate(trans/sec)']*\
            df['duration(seconds)'][0]).sum()/total_duration;

    output_line = "mean_latency," + str(mean_latency_microsecs) + \
            ",microsecs,mean_tps," + str(mean_transaction_rate) + \
            ",90th_percentile_latency," + str(p90_latency_microsecs) + \
            ",microsecs";

    print(output_line);

    perf_data_file = open(TPS_AND_LATENCY_FILE,"w");
    perf_data_file.write(output_line);
    perf_data_file.close();

def group_by_start_time(df):
    df.groupby("start_time").size().to_csv(INSTANCE_GROUP_BY_START_TIME_FILE);

def open_merged_result_file():
    df = pd.DataFrame(pd.read_csv("test.csv"));
    return df;

# Through the run, how many instances were running at a given time
def group_running_instances_by_timestamp(df):
    map_ts_instance_count = {}

    # first get a map of timestamp to instance count
    for i in range(len(df["start_time"])):
        timeiter = int(time.mktime(time.strptime(df["start_time"][i],\
                "%d-%m-%Y_%H:%M:%S")));
        endtime = int(time.mktime(time.strptime(df["end_time"][i],\
                "%d-%m-%Y_%H:%M:%S")));

        while (timeiter <= endtime):
            if timeiter in map_ts_instance_count:
                map_ts_instance_count[timeiter] += 1;
            else:
                map_ts_instance_count[timeiter] = 1;
            timeiter += 1;

    print(map_ts_instance_count);

    # now get an equivalent map of time strings to instance count
    map_ts_instance_count2 = {};

    for k in map_ts_instance_count.keys():
        k_str = datetime.datetime.fromtimestamp(k).\
                strftime("%d-%m-%Y_%H:%M:%S");
        map_ts_instance_count2[k_str] = map_ts_instance_count[k];

    print(map_ts_instance_count2);

    map_ts_instance_count2_file = open(TIMESTAMP_INSTANCE_COUNT_MAP_FILE,"w");
    cols = ["timestamp","number_of_instances"];
    writer = csv.DictWriter(map_ts_instance_count2_file, fieldnames=cols);
    writer.writeheader();

    for key in map_ts_instance_count2.keys():
        writer.writerow({"timestamp":key,"number_of_instances":\
                map_ts_instance_count2[key]});

if __name__ == "__main__":
    file_list = [];

    # 3 ways to provide input:
    # a. specify the file names space separated
    if (len(sys.argv) < 2):
        print("enter the file names (space separated) to be merged");
        file_list = input().split(' ');
    # b. specify the absolute path of the folder containing all the result \
    # files
    elif ((len(sys.argv) == 2) and ("csv" not in sys.argv[1])):
        for summ_file in os.listdir(sys.argv[1]):
            if (os.path.isfile(summ_file) and ("csv" in summ_file)\
                    and ("netperf_summary" in summ_file)):
                file_list.append(summ_file);
    # c. specify the files space separated in the command line itself
    else:
        print(len(sys.argv));
        for i in range(len(sys.argv)):
            if i == 0:
                continue;
            file_list.append(sys.argv[i]);

    print("file_list: ",file_list);
    df = merge_results(file_list);
#    df= open_merged_result_file(); # temporary bypass

    group_by_start_time(df);
    group_running_instances_by_timestamp(df);
    fetch_tps_and_latency(df);