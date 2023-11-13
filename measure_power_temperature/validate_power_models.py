__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2023 Rajarshi Das"

# Given a set of power models of the form:
# [a b c] where a,b and c are the 3rd order, 1st order and constant
# coefficients of a 3rd degree polynomial, and multiple sets of [freq,measured_power]
# values, identify which of the power models gives the lowest MAPE and (or)
# RMSE. Note that each of the power models has been derived from one among
# the multiple sets of values.
# Invoke as:
# python <.py> . # Skips the data points which were used to generate the model. Specify
# python <.py> 1 to indicate that all data points should be used to get the MAPE and RMSE.
# Added an option in order to read an input file containing the data and then, find
# the MAPE and RMSE based on a 6-term model and the accelwattch static power model for
# the data.This new option is invoked as:
# python <.py> 0 <txt file containing the data>
# e.g. python <.py> 0 INT_ADD_data_validate_constp_model.txt
# If all the data needs to be used (including the points used to generate the model), then
# specify python <.py> 1 INT_ADD_data_validate_constp_model.txt
# Another option to validate across all benchmarks:
# python <.py> <use_all_flag> <data_file> <all_bench_flag>
# python <.py> 0 consolidated_data_validate_constp_model2.txt 1
# The '0' indicates do not use all data for validation. The '1' at the end indicates that
# the model generated for each of the benchmarks specified in the data file should be 
# validated against the data for the other benchmarks, and the model with lowest MAPE
# and lowest RMSE generated. Any value other than '1' for the 3rd parameter is invalid.
# python <.py> 2 consolidated_data_validate_constp_model2.txt 1
# The value of 2 for <use_all_flag> implies do NOT use all data AND the architecture > PASCAL
# A value of 0 implies do NOT use all data and architecture <= PASCAL.
# This is used to estimate the accelwattch power differently (compared to the PASCAL case).
# A value of 1 or 3 in <use_all_flag> implies USE all data. 1: <= PASCAL. 3: > PASCAL.
# The <all_bench_flag> stays as is.
# 5-apr-23: all_bench = 3 implies a three term model is to be used instead of a 6-term model.
# this is the last parameter. specify as python <.py> 0 <data file> 3
# 6-apr-23: all_bench = 4 implies use a three term model and behave like all_bench=1 (validate
# across all the data). all_bench = 1 uses a 6-term model and validates across all data.
# 6-apr-23: Remove INT_MUL from comparison_header. We want to build the best model using
# the other three with all_bench_flag = 4, and use it to evaluate INT_MUL on A4000.
# 6-apr-23: Also remove INT_MUL models and data from power_model_grid and measured_power_grid
# in order to get the best model over 1 and 32 lanes of INT_ADD/FP_ADD/MUL: identify constant
# power using 3 ubenchmarks. See measured_power_grid/power_model_grid_4_ubenchmarks.
# 6-apr-23: Added microbenchmark name to lowest MAPE and lowest RMSE models in const power
# estimation output: printing this using all_bench_comparison_header.
# 7-apr-23: For all_bench_flag = 1/4, now one or more of parameters (core_freq/lanes/PB/power
# /models) can be specified for each microbenchmark. e.g. core_frequency specific to INT_ADD
# should be specified as core_frequency_INT_ADD. If core_frequency_FP_ADD is not found, then
# the core frequency for FP_ADD is set to the generic variable core_frequency. Ditto for others.
# Currently, per ubenchmark models (6-term/3-term) are always assumed though its possible to
# allow generic models as well.
# 8-apr-23: Add all_bench_flag=5. e.g. This uses INT_ADD's model to estimate power for
# FP_ADD and then compute a MAPE across all of FP_ADD,FP_MUL and INT_FP_SFU_STATIC. Repeats
# for all the other combinations.
# 11-apr-23: Fixed the INT_ADD lowest MAPE/32 lane, INT_MUL lowest MAPE/1 lane lowest MAPE/
# 32 lane, FP_ADD lowest MAPE/1 lane, FP_MUL lowest MAPE/1 and 32 lanes

import numpy as np
import pandas as pd
from itertools import combinations
import sys

all_bench_flag = -1; # setting it global since we need it for 3-term model power estimation

def get_coeffs(core_freq,measured_power):
        coeffs = np.polynomial.Polynomial.fit(core_freq,measured_power,deg=3,window=[0,1]);
#        coeffs = np.polynomial.Polynomial.fit(core_freq,measured_power,deg=1,window=[0,1]);
        print(coeffs);
#        print(coeffs.tolist());
        return coeffs;

def get_MAPE(core_freq,measured_power,coeffs):
        estimated_power = [];
        for i in range(len(core_freq)):
            # we do not have the 2nd order term in the Ptotal equation.
            est_power = coeffs[0] + coeffs[1]*pow(core_freq[i],1) + coeffs[3]*pow(core_freq[i],3);
            estimated_power.append(est_power);

        ape = [];
        for i in range(len(measured_power)):
            diff = estimated_power[i] - measured_power[i];
            abs_percent_error =  (float)(diff/measured_power[i])*100.0;
            ape.append(abs_percent);

        print("MAPE: {0}".format(np.average(ape)));

def validate_model(model_coeffs,core_freq,measured_power,validation_list):
	estimated_power = [];
	ape = [];
	diff_squared = [];

	for i in range(len(validation_list)):
		if (validation_list[i] == 1): # freq avl for validation
			est_pow = pow(core_freq[i],3)*model_coeffs[0] + core_freq[i]*model_coeffs[1] +\
				model_coeffs[2];
			estimated_power.append(est_pow);
		else:
			estimated_power.append(0);

	for i in range(len(measured_power)):
		if (estimated_power[i] != 0):
			diff = estimated_power[i] - measured_power[i];
			abs_percent_error =  (float)(diff/measured_power[i])*100.0;
			ape.append(abs_percent_error);
			
			diff_squared.append(pow(diff,2));

	rmse = np.sqrt(np.average(diff_squared));
	#rmse = np.sqrt(np.average(pow((np.array(estimated_power)-np.array(measured_power)),2)));

	print("MAPE: ",np.average(ape));
	print("rmse: ",rmse);
	print("estimated power: ",estimated_power);
	print("measured power: ",measured_power);

	return (np.average(ape),rmse);

# credit: https://www.geeksforgeeks.org/permutation-and-combination-in-python/
# credit: https://stackoverflow.com/questions/3459098/create-list-of-single-item-repeated-n-times
def get_coeffs2(core_freq,measured_power,deg_of_poly=3):
	list_combinations = combinations(range(len(core_freq)),deg_of_poly);
	print(list_combinations);

	results = [];

	for comb in list(list_combinations):
		val_freq_list = [1]*len(core_freq); # validation list of frequencies
		#print(combination[2]);
		# solve Ax = B: B is the measured power
		A = [];
		B = [];
		for i in range(deg_of_poly):
			B.append(measured_power[comb[i]]);

			A_row = [];
			A_row.append(pow(core_freq[comb[i]],3)); #f^3
			A_row.append(core_freq[comb[i]]); #f^1
			A_row.append(1);

			A.append(A_row);

			for j in range(len(core_freq)):
				if ((j == comb[i]) and (val_freq_list[j] == 1)):
					val_freq_list[j] = 0; # freq used for the model. 
					break;
				
		print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation

		x = np.linalg.solve(np.array(A),np.array(B));
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		mape,rmse = validate_model(x,core_freq,measured_power,val_freq_list);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	lowest_mape = abs(results[0][1]); # set the 1st combination's mape as reference.
	lowest_rmse = abs(results[0][2]); # set the 1st combination's mape as reference.

	for i in range(len(results)):
		if (abs(results[i][1]) < lowest_mape):
			lowest_mape = abs(results[i][1]);
	for i in range(len(results)):
		if (abs(results[i][2]) < lowest_rmse):
			lowest_rmse = abs(results[i][2]);

	for res in results:
		if (lowest_mape == abs(res[1])):
			print("lowest mape: ",lowest_mape);
			print("validation freq list: ",res[3]);
			break;

	for res in results:
		if (lowest_rmse == res[2]):
			print("lowest rmse: ",lowest_rmse);
			print("validation freq list: ",res[3]);
			break;
		
		#exit(-1);

# for use with six term power and accelwattch power
# validation
def get_mape_and_rmse2(meas_p,est_p,val_indices,use_all=0):
	mape_rmse_values = [];
	ape_values = [];
	rmse_values = [];

	for est_p_index in range(len(est_p)):
		if ((use_all == 0) or (use_all == 2)): # skip the ones used for the model
			if (est_p[est_p_index] != -1): # '-1' is a dummy est_p for
						# the data points used to build the model
				diff = est_p[est_p_index] - \
						meas_p[est_p_index];
				ape = abs((float)(diff/meas_p[est_p_index])*100.0);

				# print("debug: index: ",est_p_index," meas_p: ",\
				#	meas_p[est_p_index]," est_p: ",\
				#	est_p[est_p_index]," ape: ",ape);
				ape_values.append(ape);
				rmse_values.append(pow(diff,2));
		else: # 1 or 3 (<= Pascal and > Pascal respectively)
			# print("debug: est_p_index: ",est_p_index);
			diff = est_p[est_p_index] - \
					meas_p[est_p_index];
			ape = abs((float)(diff/meas_p[est_p_index])*100.0);

			ape_values.append(ape);
			rmse_values.append(pow(diff,2));
	
	mape = np.average(ape_values);
	rmse = np.sqrt(np.average(rmse_values));
	mape_rmse_values = mape,rmse;

	return mape_rmse_values;

# used in the original estimation of constant power with 
# hard coded measured power values [meas_p_grid] 2 per ubenchmark (1lane,32lane)
# and 4 models per ubenchmark (lowest MAPE,RMSE for 1lane and 32 lane)
def get_mape_and_rmse(meas_p_grid,est_p_grid,use_all=0):
    mape_rmse_values = [];
    skip_meas_power_index = -1;

    for est_p_model_index in range(len(est_p_grid)): # per model. 16 x 9 grid
        if (use_all == 0):
             if (est_p_model_index %2 == 0):
                 skip_meas_power_index += 1;
        ape = []; # per est_p_model
        diff_squared = [];
        for meas_p_grid_index in range(len(meas_p_grid)): # 8 x 9 grid
            if (use_all == 0):
                if (skip_meas_power_index == meas_p_grid_index): # skip the data which 
                                                          # was used to build the model
                 #print("skipped debug:",skip_meas_power_index," ",meas_p_grid[meas_p_grid_index]);
                 continue; 
            for freq_index in range(len(est_p_grid[est_p_model_index])): # per freq
                diff = est_p_grid[est_p_model_index][freq_index] - meas_p_grid\
                          [meas_p_grid_index][freq_index];
                abs_percent_error =  abs((float)(diff/(meas_p_grid[meas_p_grid_index]\
                                        [freq_index]))*100.0);
                ape.append(abs_percent_error);
                diff_squared.append(pow(diff,2));

        rmse = np.sqrt(np.average(diff_squared));
        mape = np.average(ape);

        mape_rmse = [mape,rmse];

        mape_rmse_values.append(mape_rmse);
          
    return mape_rmse_values; 

def get_data_from_file(file,option):
	aw_1lane_model = [];
	aw_32lane_model = [];

	data_f = open(file,"r");

	if (option == 1): # consolidated data
		all_data = {};

	for line in data_f:
		var = line.split(' = ')[0];
		# print("debug: var: ",var);

		value = line.split(' = ')[1].split(";\n")[0];

		#if (var == 'power'):
		if ('power' in var): # match power_INT_ADD, power_INT_MUL..
				
			measured_power = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				measured_power.append(float(values[i]));
			print("debug: ",var,": ",measured_power);
			
			# The suffix '_' indicates ubenchmark specific data.
			if (option == 1) and ('power_' in var): 
				ubench_suffix = var.split("power_")[1];
				# Add if this is the first data for this ubenchmark
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['power'] = measured_power;
				
		elif ('core_frequency' in var):
			core_freq = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				core_freq.append(float(values[i])*1e6);
			print("debug: ",core_freq);

			if (option == 1) and ('core_frequency_' in var): 
				ubench_suffix = var.split("core_frequency_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['core_frequency'] = core_freq;

		elif ('active_lanes' in var):
			active_lane_count_minus1 = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_lane_count_minus1.append(int(values[i])-1);
			print("debug: ",active_lane_count_minus1);

			if (option == 1) and ('active_lanes_' in var): 
				ubench_suffix = var.split("active_lanes_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['active_lanes_minus1'] = \
					active_lane_count_minus1;

		elif ('active_primary_PB' in var):
			active_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_primary_PB.append(int(values[i]));
			print("debug: ",active_primary_PB);

			if (option == 1) and ('active_primary_PB_' in var): 
				ubench_suffix = var.split("active_primary_PB_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['active_primary_PB'] = \
					active_primary_PB;

		elif ('active_non_primary_PB' in var):
			active_non_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_non_primary_PB.append(int(values[i]));
			print("debug: ",active_non_primary_PB);

			if (option == 1) and ('active_non_primary_PB_' in var): 
				ubench_suffix = var.split("active_non_primary_PB_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['active_non_primary_PB'] = \
						active_non_primary_PB;

		elif ('validation_indices' in var):
			validation_indices = [];

			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				validation_indices.append(int(values[i]));
			print("debug: validation_indices: ",validation_indices);

			if (option == 1) and ('validation_indices_' in var): 
				ubench_suffix = var.split("validation_indices_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['validation_indices'] = \
						validation_indices;

		elif (('accelwattch_1lane_model' in var) or\
			 ('accelwattch_32lane_model' in var)): # Af^3 + Bf + C

			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				if ('accelwattch_1lane_model' in var):
					aw_1lane_model.append(float(values[i]));
				else:
					aw_32lane_model.append(float(values[i]));
		
			if (option == 1) and ('lane_model_' in var): 
				ubench_suffix = var.split("lane_model_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				if ('accelwattch_1lane_model' in var):
					all_data[ubench_suffix]['accelwattch_1lane_model'] \
						 = aw_1lane_model;
				else: # 32 lane
					all_data[ubench_suffix]['accelwattch_32lane_model'] \
						 = aw_32lane_model;

			if ('accelwattch_1lane_model' in var):
				print("debug: aw_1lane_model: ",aw_1lane_model);
			else:
				print("debug: aw_32lane_model: ",aw_32lane_model);

		elif ('six_term_model' in var):
			six_term_model = [];

			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				six_term_model.append(float(values[i]));

			if (option == 1) and ('six_term_model_' in var): 
				ubench_suffix = var.split("six_term_model_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['six_term_model'] = \
						six_term_model;

			print("debug: six_term_model: ",six_term_model);

		elif ('three_term_model' in var):
			three_term_model = [];

			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				three_term_model.append(float(values[i]));

			if (option == 1) and ('three_term_model_' in var): 
				ubench_suffix = var.split("three_term_model_")[1];
				if not ubench_suffix in all_data:
					all_data[ubench_suffix] = {}; 
				all_data[ubench_suffix]['three_term_model'] = \
						three_term_model;

			print("debug: three_term_model: ",three_term_model);
		else:
			print("unknown variable in data file.. exiting");
			exit(-1);
	
	if (option == 1): # use this for for both 6-term and 3-term models (consolidated)
		return all_data,core_freq,active_lane_count_minus1,\
		active_primary_PB,active_non_primary_PB,\
		validation_indices;
	elif (option == 3):
		return three_term_model,aw_1lane_model,aw_32lane_model,\
		core_freq,active_lane_count_minus1,active_primary_PB,\
		active_non_primary_PB,measured_power,validation_indices;
	else:
		return six_term_model,aw_1lane_model,aw_32lane_model,\
		core_freq,active_lane_count_minus1,active_primary_PB,\
		active_non_primary_PB,measured_power,validation_indices;

def get_best_fit_model(mape_rmse_array):
     lowest_mape = abs(mape_rmse_array[0][0]);
     lowest_rmse = abs(mape_rmse_array[0][1]);

     lowest_mape_model_index = -1;
     lowest_rmse_model_index = -1;

     for model_index in range(len(mape_rmse_array)):
         print("debug: model index: ",model_index);
         print("debug: mape: ",mape_rmse_array[model_index][0]);
         print("debug: rmse: ",mape_rmse_array[model_index][1]);

     for model_index in range(len(mape_rmse_array)):
         if (abs(mape_rmse_array[model_index][0]) < lowest_mape):
             lowest_mape = abs(mape_rmse_array[model_index][0]);
             lowest_mape_model_index = model_index;
             #print("debug: lowest mape index: ",lowest_mape_model_index);
         if (abs(mape_rmse_array[model_index][1]) < lowest_rmse):
             lowest_rmse = abs(mape_rmse_array[model_index][1]);
             lowest_rmse_model_index = model_index;
             #print("debug: lowest rmse index: ",lowest_rmse_model_index);

     return lowest_mape_model_index,lowest_rmse_model_index;

def get_six_term_est_power(six_term_model,core_freq_list,active_lanes_minus1,\
			num_active_pri_PB,num_active_non_pri_PB,power_index):
	i = power_index;

	six_term_est_power = six_term_model[0]*pow(core_freq_list[i],3) +\
		six_term_model[1]*core_freq_list[i] + \
		six_term_model[2]*active_lanes_minus1[i] + \
		six_term_model[3]*num_active_pri_PB[i] + \
		six_term_model[4]*num_active_non_pri_PB[i] +\
		six_term_model[5];

	#print("debug: 6-term model. run index: ",i," estimated power: ",six_term_est_power);

	return six_term_est_power;

def get_three_term_est_power(three_term_model,core_freq_list,active_lanes_minus1,\
			num_active_pri_PB,num_active_non_pri_PB,power_index):
	i = power_index;

	three_term_est_power = three_term_model[0]*core_freq_list[i] +\
		three_term_model[1]*(num_active_pri_PB[i]+\
		num_active_non_pri_PB[i]) +\
		three_term_model[2];

	#print("debug: 3-term model. run index: ",i," estimated power: ",three_term_est_power);

	return three_term_est_power;

def get_accelwattch_est_power(accelwattch_1l_model,accelwattch_32l_model,\
		core_freq_list,active_lanes_minus1,power_index,arch_higher_than_pascal=0):
	i = power_index;

	#print("debug: validation index: i",i);

	lanes1_static_power = accelwattch_1l_model[1]*core_freq_list[i];

	lanes32_static_power = accelwattch_32l_model[1]*core_freq_list[i];

	per_add_lane_static_power = float((lanes32_static_power - \
							lanes1_static_power)/31); # per additional lane

	if (arch_higher_than_pascal == 1):
		if (active_lanes_minus1[i] <= 15): # active lanes <= 16
			accelwattch_est_power = accelwattch_32l_model[0]*pow(core_freq_list[i],3)\
			+ lanes1_static_power + per_add_lane_static_power*active_lanes_minus1[i] + \
			accelwattch_32l_model[2];
		else:
			accelwattch_est_power = accelwattch_32l_model[0]*pow(core_freq_list[i],3)\
			+ lanes1_static_power + (0.5*per_add_lane_static_power*15) + \
			(0.5*per_add_lane_static_power*(active_lanes_minus1[i]-16)) + \
			accelwattch_32l_model[2];

			#print("debug: validation index: ",i," aw est power: ",accelwattch_est_power," lanes: ",
			#active_lanes_minus1[i]+1," per add lane power: ",per_add_lane_static_power,
			#" 1 lane power: ",lanes1_static_power, " 32 lane power: ",lanes32_static_power,
			#" core freq: ",core_freq_list[i]);

	else: # PASCAL and below
		accelwattch_est_power = accelwattch_32l_model[0]*pow(core_freq_list[i],3)\
			+ lanes1_static_power + per_add_lane_static_power*active_lanes_minus1[i] + \
			accelwattch_32l_model[2];

	# print("debug: aw model. run index: ",i," per_lane_power: ",per_add_lane_static_power,\
	#				" estimated power: ",accelwattch_est_power," 1 lane st power: ",\
	#				lanes1_static_power," active additional lanes: ",active_lanes_minus1[i]);

	return accelwattch_est_power;

# def get_est_power_data(six_term_model,accelwattch_1l_model,\
def get_est_power_data(term_model,accelwattch_1l_model,\
		accelwattch_32l_model,core_freq_list,active_lanes_minus1,\
		num_active_pri_PB,num_active_non_pri_PB,validation_indices,use_all_flag):

	term_est_power_data = []; # to imply both 6-term and 3-term as the case may be
	accelwattch_power_data = [];

	for i in range(len(validation_indices)):
		if ((use_all_flag == 0) or (use_all_flag == 2)): # use_all_flag = 0 implies
			# do not use all data for validation on arch <= PASCAL. use_all_flag = 2
			# implies do not use all data for validation on arch > PASCAL.
			if (validation_indices[i] == 1):
				if ((all_bench_flag == 3) or (all_bench_flag == 4) or\
					(all_bench_flag == 5)): # 3-term model
					term_est_power = get_three_term_est_power(term_model,\
					core_freq_list,active_lanes_minus1,num_active_pri_PB,\
					num_active_non_pri_PB,i);
				else:
					term_est_power = get_six_term_est_power(term_model,\
					core_freq_list,active_lanes_minus1,num_active_pri_PB,\
					num_active_non_pri_PB,i);

				term_est_power_data.append(term_est_power);
				if (use_all_flag == 2): # > PASCAL and do not use all
					accelwattch_est_power = get_accelwattch_est_power(\
					accelwattch_1l_model,accelwattch_32l_model,core_freq_list\
					,active_lanes_minus1,i,1); # arch_higher_than_pascal = 1
				else:
					accelwattch_est_power = get_accelwattch_est_power(\
					accelwattch_1l_model,accelwattch_32l_model,core_freq_list\
					,active_lanes_minus1,i,0);

				accelwattch_power_data.append(accelwattch_est_power);
			else:
				term_est_power_data.append(-1);
				accelwattch_power_data.append(-1);

		elif ((use_all_flag == 1) or (use_all_flag == 3)):
			if ((all_bench_flag == 3) or (all_bench_flag == 4) or\
					(all_bench_flag == 5)): # 3-term model
				term_est_power = get_three_term_est_power(term_model,\
				core_freq_list,active_lanes_minus1,num_active_pri_PB,\
				num_active_non_pri_PB,i);
			else:
				term_est_power = get_six_term_est_power(term_model,\
				core_freq_list,active_lanes_minus1,num_active_pri_PB,\
				num_active_non_pri_PB,i);

			term_est_power_data.append(term_est_power);
			if (use_all_flag == 3): # arch_higher_than_pascal = 1
				accelwattch_est_power = get_accelwattch_est_power(\
					accelwattch_1l_model,accelwattch_32l_model,core_freq_list\
					,active_lanes_minus1,i,1);
			else:
				accelwattch_est_power = get_accelwattch_est_power(\
					accelwattch_1l_model,accelwattch_32l_model,core_freq_list\
					,active_lanes_minus1,i,0);
			accelwattch_power_data.append(accelwattch_est_power);
		else:
			print("Error: unknown value for <use_all_flag>. Specify one in 0,1,2,3");
			exit(-1);

	#print("debug: aw power data: ",accelwattch_power_data," 6 term power data: ",
	#		six_term_est_power_data);
	return term_est_power_data,accelwattch_power_data;	

if __name__ == "__main__":
	core_freq = [139e6,278e6,417e6,556e6,607e6,696e6,797e6,898e6,999e6]; # Hz
		#       measured_power = [22.1232842410137,23.7798811423158,23.830277367614,29.5205741597036,30.3766110748561,32.0287801665763,33.986431347592,35.8388156452346,37.720811318817]; # GICOV
		#       measured_power = [20.9055913230182,21.020133884283,21.028433542617,21.4059189906608,21.4562637975061,21.5599600704549,21.713204686488,21.9007672911003,22.0876557279796]; # INT_STATIC ubenchmark. 1 lane. steady state temp
		#       measured_power = [20.913991507075,21.0317739655406,21.0726404619449,21.4968251827684,21.5057893158111,21.5988264025789,21.7946179694907,22.0016364156284,22.163310583803]; # INT_STATIC ubenchmark, 32 lanes. steady state temp
		#       measured_power = [20.63,20.82,20.82,21.12,21.21,21.3,21.41,21.69,21.88]; # INT_STATIC ubenchmark. 1 lane at 0.632t (0.632 of max normalized temp)
		#       measured_power = [20.73,20.81,20.82,21.21,21.31,21.41,21.6,21.8,21.98]; # INT_STATIC ubenchmark. 32 lanes at 0.632t (0.632 of max norm temp)

	# measured_power_grid_header = ['INT_ADD','INT_MUL','FP_ADD','FP_MUL','INT_MEM'];
		# measured power at 0.632t
	measured_power_grid_0_632t = [
		[20.63,20.73,20.82,21.12,21.12,21.21,21.31,21.51,21.7], # INT_ADD. 1 lane at 0.632t
		[20.63,20.82,20.82,21.21,21.21,21.31,21.49,21.69,21.88], # INT_ADD. 32 lanes at 0.632t
		[20.63,20.73,20.73,21.21,21.21,21.3,21.51,21.69,21.9], # INT_MUL. 1 lane at 0.632t
		[20.73,20.82,20.82,21.2,21.3,21.39,21.59,21.88,21.99], # INT_MUL. 32 lanes at .632t
		[20.63,20.73,20.73,21.12,21.12,21.21,21.31,21.51,21.7], # FP_ADD. 1 lane at 0.632t
		[20.73,20.82,20.82,21.2,21.2,21.39,21.59,21.69,21.88], # FP_ADD. 32 lanes at 0.632t
		[20.63,20.73,20.73,21.12,21.21,21.31,21.41,21.59,21.79], # FP_MUL. 1 lane at 0.632t
		[20.63,20.82,20.82,21.2,21.3,21.39,21.59,21.69,21.98], # FP_MUL. 32 lanes at 0.632t
		#[21.41,22.08,22.09,23.93,24.12,24.6,25.28,25.86,26.45], # INT_MEM.100-20-1-512 at .632t
		#[22.27,23.93,23.93,28.28,28.77,29.54,30.91,32.35,33.61] # INT_MEM.100-20-32-512 at .632t
		];

		# power models for 0.632t
	power_model_grid_0_632t = [
		[1.40028451e-28,1.09936579e-09,2.04213678e+01], #INT_ADD_1lane_model1
		[3.37443941e-28,8.38663964e-10,2.05125195e+01], #INT_ADD_1lane_model2
		[-2.84766809e-28,1.55693312e-09,2.03932908e+01], #INT_ADD_32lanes_model1
		[3.74798502e-28,1.02015272e-09,2.04871922e+01],
		[3.38495910e-28,1.16475885e-09,2.03989245e+01], #INT_MUL_1lane_model1
		[3.38495910e-28,1.16475885e-09,2.03989245e+01], #INT_MUL_1lane_model2 # same as model1
		[3.32079005e-28,1.17344097e-09,2.04866487e+01],
		[6.70796200e-28,8.57059123e-10,2.05673255e+01],
		[3.97355909e-28,8.07728349e-10,2.04969143e+01], #FP_ADD
		[3.29578546e-28,8.99431596e-10,2.04728770e+01],
		[5.44620509e-28,7.47134743e-10,2.06246856e+01],
		[3.04788887e-28,1.05779881e-09,2.05193836e+01],
		[4.28710712e-28,8.57312453e-10,2.05096822e+01], #FP_MUL
		[3.78211134e-28,9.58457993e-10,2.04554228e+01],
		[3.63890166e-29,1.36198497e-09,2.04405864e+01],
		[3.69469640e-28,1.14259292e-09,2.04701873e+01],
		#[6.68186836e-27,7.67738243e-10,2.12853394e+01], #INT_MEM
		#[1.80000369e-28,5.89277402e-09,2.04379415e+01],
		#[-5.59324332e-27,1.86733595e-08,1.88589766e+01],
		#[-2.62251485e-28,1.40034538e-08,1.98820152e+01]
		];

	measured_power_grid = [ # max average power # excluding INT_MUL, incl. INT_FP_SFU_STATIC
		[20.92,21.02,21.02,21.31,21.31,21.41,21.6,21.8,21.99], # Max average power reached. INT_ADD. 1 lane.
		[20.92,21.02,21.12,21.51,21.51,21.6,21.8,21.99,22.09], # Max average power reached. INT_ADD. 32 lanes.
#		[20.82,21.02,21.02,21.51,21.51,21.7,21.8,21.99,22.19], # INT_MUL. Max Avg Power. 1 lane
#		[20.92,21.12,21.12,21.51,21.6,21.7,21.9,22.18,22.29], # INT_MUL. Max Avg Power. 32 lanes
		[20.92,21.02,20.92,21.31,21.41,21.51,21.6,21.8,21.99], # FP_ADD. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.51,21.6,21.88,21.99,22.19], # FP_ADD. Max Avg Power. 32 lanes
		[20.82,20.92,21.02,21.41,21.51,21.6,21.8,21.9,22.09], # FP_MUL. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.6,21.6,21.9,21.99,22.19], # FP_MUL. Max Avg Power. 32 lanes
		#[21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15,26.74], # INT_MEM. Max Avg Power. 100-20-1-512
		#[22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.56,33.8], # INT_MEM. Max Avg Power. 100-20-32-512
		[20.92,21.02,21.02,21.41,21.51,21.6,21.8,21.9,22.09], # INT_FP_SFU_STATIC. Max power 1 lane
		[20.92,21.12,21.12,21.51,21.6,21.8,21.9,22.09,22.29], # INT_FP_SFU_STATIC. Max power 32 lane
		];

	measured_power_grid_3_ubenchmarks = [ # max average power # excluding INT_MUL
		[20.92,21.02,21.02,21.31,21.31,21.41,21.6,21.8,21.99], # Max average power reached. INT_ADD. 1 lane.
		[20.92,21.02,21.12,21.51,21.51,21.6,21.8,21.99,22.09], # Max average power reached. INT_ADD. 32 lanes.
#		[20.82,21.02,21.02,21.51,21.51,21.7,21.8,21.99,22.19], # INT_MUL. Max Avg Power. 1 lane
#		[20.92,21.12,21.12,21.51,21.6,21.7,21.9,22.18,22.29], # INT_MUL. Max Avg Power. 32 lanes
		[20.92,21.02,20.92,21.31,21.41,21.51,21.6,21.8,21.99], # FP_ADD. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.51,21.6,21.88,21.99,22.19], # FP_ADD. Max Avg Power. 32 lanes
		[20.82,20.92,21.02,21.41,21.51,21.6,21.8,21.9,22.09], # FP_MUL. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.6,21.6,21.9,21.99,22.19], # FP_MUL. Max Avg Power. 32 lanes
		#[21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15,26.74], # INT_MEM. Max Avg Power. 100-20-1-512
		#[22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.56,33.8], # INT_MEM. Max Avg Power. 100-20-32-512
		];

	measured_power_grid_4_ubenchmarks = [ # max average power
		[20.92,21.02,21.02,21.31,21.31,21.41,21.6,21.8,21.99], # Max average power reached. INT_ADD. 1 lane.
		[20.92,21.02,21.12,21.51,21.51,21.6,21.8,21.99,22.09], # Max average power reached. INT_ADD. 32 lanes.
		[20.82,21.02,21.02,21.51,21.51,21.7,21.8,21.99,22.19], # INT_MUL. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.6,21.7,21.9,22.18,22.29], # INT_MUL. Max Avg Power. 32 lanes
		[20.92,21.02,20.92,21.31,21.41,21.51,21.6,21.8,21.99], # FP_ADD. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.51,21.6,21.88,21.99,22.19], # FP_ADD. Max Avg Power. 32 lanes
		[20.82,20.92,21.02,21.41,21.51,21.6,21.8,21.9,22.09], # FP_MUL. Max Avg Power. 1 lane
		[20.92,21.12,21.12,21.51,21.6,21.6,21.9,21.99,22.19], # FP_MUL. Max Avg Power. 32 lanes
		#[21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15,26.74], # INT_MEM. Max Avg Power. 100-20-1-512
		#[22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.56,33.8], # INT_MEM. Max Avg Power. 100-20-32-512
		];

	power_model_grid_incl_FP_SFU_STATIC = [ # max average power # including INT_FP_SFU_STATIC. corrected
		[6.00626737e-28,5.49751624e-10,2.08419715e+01], # INT_ADD
		[6.00626737e-28,5.49751624e-10,2.08419715e+01],
		[-7.19237656e-30,1.49378127e-09,2.06048833e+01],
		[4.23320336e-29,1.46334956e-09,2.06122793e+01],
#		[1.73475647e-28,1.39245366e-09,2.06259831e+01], # INT_MUL
#		[2.50546011e-28,1.30334622e-09,2.06381620e+01],
#		[2.37400292e-28,1.31854507e-09,2.07360847e+01],
#		[5.39959690e-28,1.07612353e-09,2.07689687e+01],
		[4.11669720e-28,7.68220515e-10,2.08121118e+01], # FP_ADD
		[5.39673531e-28,6.46435234e-10,2.08286961e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[8.24528485e-29,1.38141360e-09,2.06277621e+01], # FP_MUL
		[-6.77140158e-30,1.63190794e-09,2.04664751e+01],
		[8.24528485e-29,1.38141360e-09,2.07277621e+01],
		[3.25791765e-28,1.10006929e-09,2.07662154e+01],
		#[6.96661493e-27,7.32188817e-10,2.14795161e+01], # INT_MEM
		#[-4.81633641e-29,6.28039153e-09,2.05450859e+01],
		#[-4.91714142e-27,1.61677477e-08,2.03458886e+01],
		#[-5.24502969e-28,1.41455215e-08,2.01915551e+01],
		[2.47061284e-28,1.07481706e-09,2.07699369e+01], # INT_FP_SFU_STATIC
		[1.61403572e-28,1.26566977e-09,2.06646761e+01],
		[2.37400292e-28,1.31854507e-09,2.07360847e+01],
		[2.81483281e-28,1.27393889e-09,2.07421665e+01]
		];

	power_model_grid = [ # max average power # excluding INT_MUL. corrected
		[6.00626737e-28,5.49751624e-10,2.08419715e+01], # INT_ADD
		[6.00626737e-28,5.49751624e-10,2.08419715e+01],
		[-7.19237656e-30,1.49378127e-09,2.06048833e+01],
		[4.23320336e-29,1.46334956e-09,2.06122793e+01],
#		[1.73475647e-28,1.39245366e-09,2.06259831e+01], # INT_MUL
#		[2.50546011e-28,1.30334622e-09,2.06381620e+01],
#		[2.37400292e-28,1.31854507e-09,2.07360847e+01],
#		[5.39959690e-28,1.07612353e-09,2.07689687e+01],
		[4.11669720e-28,7.68220515e-10,2.08121118e+01], # FP_ADD
		[5.39673531e-28,6.46435234e-10,2.08286961e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[8.24528485e-29,1.38141360e-09,2.06277621e+01], # FP_MUL
		[-6.77140158e-30,1.63190794e-09,2.04664751e+01],
		[8.24528485e-29,1.38141360e-09,2.07277621e+01],
		[3.25791765e-28,1.10006929e-09,2.07662154e+01],
		#[6.96661493e-27,7.32188817e-10,2.14795161e+01], # INT_MEM
		#[-4.81633641e-29,6.28039153e-09,2.05450859e+01],
		#[-4.91714142e-27,1.61677477e-08,2.03458886e+01],
		#[-5.24502969e-28,1.41455215e-08,2.01915551e+01]
		];

	power_model_grid_4_ubenchmarks = [ # max average power	  
		[6.00626737e-28,5.49751624e-10,2.08419715e+01], # INT_ADD
		[6.00626737e-28,5.49751624e-10,2.08419715e+01],
		[3.09253916e-28,1.21402877e-09,2.06758557e+01],
		[4.23320336e-29,1.46334956e-09,2.06122793e+01],
		[2.86088041e-28,1.23566706e-09,2.06703380e+01], # INT_MUL
		[2.50546011e-28,1.30334622e-09,2.06381620e+01],
		[4.19789256e-29,1.43317140e-09,2.07206764e+01],
		[5.39959690e-28,1.07612353e-09,2.07689687e+01],
		[5.39185397e-28,6.20789057e-10,2.08322623e+01], # FP_ADD
		[5.39673531e-28,6.46435234e-10,2.08286961e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[3.15859344e-28,1.11155298e-09,2.07646459e+01],
		[-5.76712548e-28,2.23425195e-09,2.03112686e+01], # FP_MUL
		[-6.77140158e-30,1.63190794e-09,2.04664751e+01],
		[-2.71051428e-28,2.03984395e-09,2.04224350e+01],
		[3.25791765e-28,1.10006929e-09,2.07662154e+01],
		#[6.96661493e-27,7.32188817e-10,2.14795161e+01], # INT_MEM
		#[-4.81633641e-29,6.28039153e-09,2.05450859e+01],
		#[-4.91714142e-27,1.61677477e-08,2.03458886e+01],
		#[-5.24502969e-28,1.41455215e-08,2.01915551e+01]
		];

	# all_bench_comparison_header = ['INT_ADD','INT_MUL','FP_ADD','FP_MUL'];
	all_bench_comparison_header = ['INT_ADD','FP_ADD','FP_MUL']; # use INT_MUL for A4000 eval
	#all_bench_comparison_header = ['INT_ADD','FP_ADD','FP_MUL','INT_FP_SFU_STATIC']; 
						# use INT_MUL for A4000 eval

	use_all_flag = 0;
	compare_6term_accelwattch = 0;
	compare_3term_accelwattch = 0;
	# all_bench_flag = -1;

	if (len(sys.argv)==2):
		use_all_flag = int(sys.argv[1]); # Use all the data points including the ones that generated
									   # the model to get the MAPE. Default is to skip the data points
									   # that generated the model.

	if (len(sys.argv)>2): # specify use_all flag, compare 6-term and accelwattch models
			try:
				use_all_flag = int(sys.argv[1]);
				compare_6term_accelwattch = 1; 
				data_file = sys.argv[2];
				if (len(sys.argv) == 4): # do a consolidated comparison
					all_bench_flag = int(sys.argv[3]);
					if ((all_bench_flag == 3) or (all_bench_flag == 4)\
						or (all_bench_flag == 5)):
						compare_6term_accelwattch = 0;
						compare_3term_accelwattch = 1;
			except TypeError:
				print("Incorrect data entered.");
				if (len(sys.argv)==3):
					print("Specify <.py> <use_all_flag> <data file>");
				else: # len = 4. 
					print("Specify <.py> <use_all_flag> <data file> <all_bench_flag>");

	if ((len(sys.argv) == 4) and (all_bench_flag != 1) and (all_bench_flag != 3)\
			and (all_bench_flag != 4) and (all_bench_flag != 5)):
		print("Specify 1 for the all_bench_flag parameter at the end");
		print("A value of 3 for the all_bench flag indicates that ");
		print("a three term model is specified. A value of 4 indicates ");
		print("that a three term model is specified for validation across");
		print("all the data (equivalent to all_bench=1 and 6-term model)");
		print("all_bench=5 means use a 3-term model from INT_ADD, and estimate");
		print("power for other 3 ubenchmarks and compute MAPE");
		print("e.g. python <.py> 0 <data_file> 1/3/4/5");
		exit(-1);

	if ((compare_6term_accelwattch == 1) or (compare_3term_accelwattch == 1)):
			est_power_grid_6term_model = [];
			est_power_grid_3term_model = [];
			est_power_grid_accelwattch_model = [];
			six_term_model = [];
			three_term_model = [];
			accelwattch_1l_model = [];
			accelwattch_32l_model = [];

			all_data = {}; # consolidated comparison

			# fetch 'all_data' if we are doing a consolidated review.
			if ((all_bench_flag == 1) or (all_bench_flag == 4)\
				or (all_bench_flag == 5)):
				all_data,core_freq_list,active_lanes_minus1\
				,num_active_pri_PB,num_active_non_pri_PB\
				,validation_indices = get_data_from_file(data_file,1);
				print("all_data: ",all_data);
			elif (all_bench_flag == 3): # 3 term model for a single ubenchmark
				three_term_model,accelwattch_1l_model,accelwattch_32l_model,\
				core_freq_list,active_lanes_minus1,num_active_pri_PB,\
				num_active_non_pri_PB,measured_power,validation_indices =\
					get_data_from_file(data_file,3); # 3 term model
			else:
				six_term_model,accelwattch_1l_model,accelwattch_32l_model,\
				core_freq_list,active_lanes_minus1,num_active_pri_PB,\
				num_active_non_pri_PB,measured_power,validation_indices =\
					get_data_from_file(data_file,0);

			if ((all_bench_flag == 1) or (all_bench_flag == 4)\
					or (all_bench_flag == 5)):
				mape_and_rmse_term_all = []; # 6-term/ 3-term
				mape_and_rmse_aw_all = [];

				for bench_name in all_bench_comparison_header:
					term_est_power_data_all = []; # 6-term/ 3-term
					accelwattch_power_data_all = [];
					measured_power_data_all = [];

					# bench specific models available
					if (all_bench_flag == 1):
						term_model = all_data[bench_name]\
									['six_term_model'];
					else: # all_bench_flag = 4 or 5
						term_model = all_data[bench_name]\
									['three_term_model'];
					accelwattch_1l_model = all_data[bench_name]\
								['accelwattch_1lane_model'];
					accelwattch_32l_model = all_data[bench_name]\
								['accelwattch_32lane_model'];

					# set bench specific data if available
					if ((all_bench_flag == 1) or (all_bench_flag == 4)):
						if bench_name in all_data:
							if 'core_frequency' in all_data[bench_name]:
								core_freq_list = all_data[bench_name]\
									['core_frequency'];
							if 'active_lanes_minus1' in all_data[bench_name]:
								active_lanes_minus1 = all_data[bench_name]\
									['active_lanes_minus1'];
							if 'active_primary_PB' in all_data[bench_name]:
								num_active_pri_PB = all_data[bench_name]\
									['active_primary_PB'];
							if 'active_non_primary_PB' in all_data[bench_name]:
								num_active_non_pri_PB = all_data[bench_name]\
									['active_non_primary_PB'];
							if 'validation_indices' in all_data[bench_name]:
								validation_indices = all_data[bench_name]\
									['validation_indices'];
					
						term_est_power_data,accelwattch_power_data = \
						get_est_power_data(term_model,accelwattch_1l_model,\
						accelwattch_32l_model,core_freq_list,active_lanes_minus1,\
						num_active_pri_PB,num_active_non_pri_PB,validation_indices\
						,use_all_flag);

					#print("debug: six_term_est_data: ",six_term_est_power_data,\
					#	" aw_est_data: ",accelwattch_power_data);
					# compare the est power for INT_ADD against measured power for
					# INT_MUL/FP_ADD/FP_MUL. Repeat the other 3 combinations.

					if (all_bench_flag == 5):
						core_freq_list_generic = core_freq_list;
						active_lanes_minus1_generic = active_lanes_minus1;
						num_active_pri_PB_generic = num_active_pri_PB;
						num_active_non_pri_PB_generic = num_active_non_pri_PB;
						validation_indices_generic = validation_indices;

					for data_bench_key in all_data:
						if (bench_name == data_bench_key): # compare against others
							continue;
						measured_power = all_data[data_bench_key]['power'];
						for i in range(len(measured_power)):
							measured_power_data_all.append(measured_power[i]);

					# for all_bench_flag = 5, get ubenchmark specific data if available
					# and apply the 'bench_name' model to get est power for the validation
					# ubenchmark, and compare against the meas power to get MAPE.

						if (all_bench_flag == 5):
							if 'core_frequency' in all_data[data_bench_key]:
								core_freq_list = all_data[data_bench_key]\
									['core_frequency'];
							else:
								core_freq_list = core_freq_list_generic;
							if 'active_lanes_minus1' in all_data[data_bench_key]:
								active_lanes_minus1 = all_data[data_bench_key]\
									['active_lanes_minus1'];
							else:
								active_lanes_minus1 = active_lanes_minus1_generic;
							if 'active_primary_PB' in all_data[data_bench_key]:
								num_active_pri_PB = all_data[data_bench_key]\
									['active_primary_PB'];
							else:
								num_active_pri_PB = num_active_pri_PB_generic;
							if 'active_non_primary_PB' in all_data[data_bench_key]:
								num_active_non_pri_PB = all_data[data_bench_key]\
									['active_non_primary_PB'];
							else:
								num_active_non_pri_PB = num_active_non_pri_PB_generic;
							if 'validation_indices' in all_data[data_bench_key]:
								validation_indices = all_data[data_bench_key]\
									['validation_indices'];
							else:
								validation_indices = validation_indices_generic;

							term_est_power_data,accelwattch_power_data = \
							get_est_power_data(term_model,accelwattch_1l_model,\
							accelwattch_32l_model,core_freq_list,\
							active_lanes_minus1,num_active_pri_PB,\
							num_active_non_pri_PB,validation_indices\
								,use_all_flag);

							for i in range(len(term_est_power_data)):
								term_est_power_data_all.append\
										(term_est_power_data[i]);
							for i in range(len(accelwattch_power_data)):
								accelwattch_power_data_all.append\
										(accelwattch_power_data[i]);
							print("debug: appended bench: ",data_bench_key," upto :", \
								len(term_est_power_data_all));

					# for all_bench_flag = 1 or 4, use the 'bench_name' 's est power and
					# compare against measured power of the other 3 validation ubenchmarks
					# to get MAPE

						else:
							for i in range(len(term_est_power_data)):
								term_est_power_data_all.append\
										(term_est_power_data[i]);
							for i in range(len(accelwattch_power_data)):
								accelwattch_power_data_all.append\
										(accelwattch_power_data[i]);

							#print("debug: appended bench: ",data_bench_key," upto :", \
							#	len(term_est_power_data_all));

					# regardless of whether arch <= Pascal or > Pascal, pass '1' in the
					# use_all_flag variable, since the effect of using 1 or 3 for computing
					# mape/ rmse is the same. 
					print("debug: bench_name: ",bench_name);
					mape_and_rmse_term = get_mape_and_rmse2(measured_power_data_all,\
								 term_est_power_data_all,validation_indices,1);
					mape_and_rmse_term_map = {};
					mape_and_rmse_term_map[bench_name] = mape_and_rmse_term;
					# mape_and_rmse_term_all.append(mape_and_rmse_term);
					mape_and_rmse_term_all.append(mape_and_rmse_term_map);
					mape_and_rmse_aw = get_mape_and_rmse2(measured_power_data_all,\
								accelwattch_power_data_all,validation_indices,1);
					mape_and_rmse_aw_map = {};
					mape_and_rmse_aw_map[bench_name] = mape_and_rmse_aw;
					# mape_and_rmse_aw_all.append(mape_and_rmse_aw);
					mape_and_rmse_aw_all.append(mape_and_rmse_aw_map);

				if ((all_bench_flag == 4) or (all_bench_flag == 5)):
					print("aw: ",mape_and_rmse_aw_all," 3-term: ",mape_and_rmse_term_all);
				else:
					print("aw: ",mape_and_rmse_aw_all," 6-term: ",mape_and_rmse_term_all);

			else: # single ubench estimation
				six_term_est_power_data = [];
				three_term_est_power_data = [];
				accelwattch_power_data = [];
				if (compare_6term_accelwattch == 1):
					six_term_est_power_data,accelwattch_power_data = \
					get_est_power_data(six_term_model,accelwattch_1l_model,\
							accelwattch_32l_model,core_freq_list,active_lanes_minus1,\
							num_active_pri_PB,num_active_non_pri_PB,validation_indices\
							,use_all_flag);

					mape_and_rmse_six_term = get_mape_and_rmse2(measured_power,six_term_est_power_data\
									,validation_indices,use_all_flag);
					mape_and_rmse_aw = get_mape_and_rmse2(measured_power,accelwattch_power_data\
									,validation_indices,use_all_flag);
					print("mape and rmse: six term model: ",mape_and_rmse_six_term[0],\
									mape_and_rmse_six_term[1]);
					print("mape and rmse: accelwattch model: ",mape_and_rmse_aw[0],mape_and_rmse_aw[1]);
				elif (compare_3term_accelwattch == 1):
					three_term_est_power_data,accelwattch_power_data = \
					get_est_power_data(three_term_model,accelwattch_1l_model,\
							accelwattch_32l_model,core_freq_list,active_lanes_minus1,\
							num_active_pri_PB,num_active_non_pri_PB,validation_indices\
							,use_all_flag);

					mape_and_rmse_three_term = get_mape_and_rmse2(measured_power,three_term_est_power_data\
									,validation_indices,use_all_flag);
					mape_and_rmse_aw = get_mape_and_rmse2(measured_power,accelwattch_power_data\
									,validation_indices,use_all_flag);
					print("mape and rmse: three term model: ",mape_and_rmse_three_term[0],\
									mape_and_rmse_three_term[1]);
					print("mape and rmse: accelwattch model: ",mape_and_rmse_aw[0],mape_and_rmse_aw[1]);
	else:
			est_power_grid = []; # 16 x 9 grid [16 models x 9 freqs]

        #for power_model_idx in range(len(power_model_grid)):
        #    print("debug: power_model_idx: ",power_model_idx,power_model_grid[power_model_idx]);

			for power_model_idx in range(len(power_model_grid)):
				est_power_line = []; # per power model
				for freq_index in range(len(core_freq)):
					est_power = power_model_grid[power_model_idx][0]*pow(core_freq[freq_index],3) + \
								power_model_grid[power_model_idx][1]*core_freq[freq_index] + \
								power_model_grid[power_model_idx][2];
					est_power_line.append(est_power);
				est_power_grid.append(est_power_line);

        #print("debug: est_power_grid: ",est_power_grid);
        
			mape_and_rmse_vals = get_mape_and_rmse(measured_power_grid,est_power_grid,use_all_flag);

			mape_model_idx,rmse_model_idx=get_best_fit_model(mape_and_rmse_vals);

			# add ubenchmark name for best fit also. 4 models per ubenchmark.
			print("best fit model with mape: ",power_model_grid[mape_model_idx], "with mape: ",\
				mape_and_rmse_vals[mape_model_idx][0], " index: ", mape_model_idx,\
				" microbenchmark: ", all_bench_comparison_header[int(mape_model_idx/4)]);
			print("best fit model with rmse: ",power_model_grid[rmse_model_idx], "with rmse: ",\
				mape_and_rmse_vals[rmse_model_idx][1], " index: ", rmse_model_idx, \
				" microbenchmark: ", all_bench_comparison_header[int(rmse_model_idx/4)]);
