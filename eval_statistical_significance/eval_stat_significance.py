__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2023 Rajarshi Das"

# Given a set of data points for multiple linear regression, evaluate the statistical
# significance of these features in relation to the output variable.
# run the program as <.py> 1 [data_model_file] e.g.
# <.py> 1 ./lcytek1_data_model_constp_deg7.txt
# The option 2 is to calculate a linear regression model and identify the coefficients.
# Run as <.py> 2 [data model file]
# Additionally the 'validation_set_ratio' variable can be set to identify the percentage
# of the data that will be used for validation: defaults to 0.2. This splits the data
# into 5 sets and will iterate through each of the 5 sets as a validation set using the 
# other 4 for the model. Further set the last parameter 'modeltype' in the second call to 
# get_linear_regr_model() (either of 1/ 2/ 3 for now) to select the appropriate model to get
# the output for (defaults to 1).
# 1: P = Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G and 2: P = Bf + Dp + Es + Bf*Dp + Bf*Es + 
# F(num_gpu_sets-1) + G.
# 3. P = Bf + F(num_gpu_sets-1) + G
# 4. P = Bf + Dp + Es + F(num_gpu_sets-1) + G. 'modeltype' can take 1/2/3/4 now.
# 5. P = Bf + C(l-1) + Dp + Es + F(num_gpu_sets-1) + G. 'modeltype' = 1/2/3/4/5
# Modified (4-apr):
# Replaced 'lcytek1_evaluation' flag with 'extra_evaluations' flag. Always set to 1.
# 'evaluate_gpuset_data' flag replaces 'lcytek1_evaluation' in command line
# 4-apr:
# Added 2 new tests :Bf + F(num_gpu_sets) + G, and Af^3 + Bf + F(num_gpu_sets) + G
#  in stat significance (method = 1).
# 5-apr: Under method = 1, add new model:
# 6. P = Bf + D(p+s) + G for data = 1 gpuset. This model corresponds to modeltype=6
# 8-apr: Added a 4th parameter (optional) if method = 2. This specifies num_groups.
# This is the number of folds in the validation. Allowed range : 1-20. default=3
# 7-jun: added 2 new testcases under extra_evaluation() for Af^3+Bf+C(g-1)+D and
# Af^3+C(g-1)+D
# 10-jun: add new model for method=2
# P = Af^3 + B(num_gpu_sets - 1) + C. This corresponds to modeltype=7. 
# 'modeltype' = 1/2/3/4/5/6/7
# add new model for method=1 (get statistical significance)
# P = Af^3 + B(p+s) + C.
# 11-jun: add new model for method=1 and method=2
# P = Af^3 + B(p+s) + C(num_gpu_sets-1) + D
# for method=2, this is 'modeltype' = 8
# 12-jun: add new model for method=1 and method=2
# P = Af^3 + B(l-1) + C(p+s) + D(num_gpu_sets-1) + E. modeltype=9
# 13-jun: add 2 new models for method=1
# P = Af^3 + Bf + C(p+s) + D(gpusets-1) + E
# P = Af^3 + Bf + C(l-1) + D(p+s) + E(gpusets-1) + F
# 13-jun: add existing model P=Af^3 + B(p+s) + C to method=2
# this model now corresponds to modeltype=10
# 11-jul: comment: <.py> 1 <data txt file> 1: the second parameter (optional) 1 indicates
# that evaluate for gpuset data as well.
# 11-jul: add model P = Af^3 + Bf + C(l-1) + D(p+s) + E(num_gpu_sets-1) + F
# to method=2, since we find this model to be statistically significant over
# enhanced data (incl. variation by (p+s) and (l) for Sobol): modeltype=11
# 14-jul: add model P = Af^3 + B(num_gpu_sets-1) + C to method=1, based on 
# our correlation analysis cols W:AP in P2200-all-kernel*benchmark-all_data 
# (multi-kernel_gpu_runs.ods)
# add model P = Af^3 + B(l-1) + C(num_gpu_sets-1) + D to method=1. This removes
# -ve multicollinearity from the data: W1:AA6
# 16-jul: fixed the high condition number issue, by reducing the f^3 by a factor
# of 1e9 before checking the stat significance (method=1).
# 19-jul: Add new model P = A(log(f)) + B(l-1) + C(num_gpu_sets-1) + D to method=1
# 20-jul: Add the log(f) model to method=2
# 21-jul: Introduce scaling_factor=1e9 as a variable. This can be used to scale
# down f^3 values by an appropriate factor (e.g. 1e6 or 1e9). In order to scale
# down by 1e9 set scaling_factor=1e9.
# 25-jul: Add model E = A*f^3 + B*fansp + C, where fansp is the GPU fan speed
# and E is the energy consumed, to method=1. Also, add model T = Af + Bfansp + C
# where T is the peak temperature, to method=1. fan speed data evaluation is 
# done by passing 2 (instead of 1 for evaluating gpuset data): this evaluates
# the energy (E) model. Passing 3 evaluates the temperature and fanspeed data. 
# <.py> 1 <file.txt> 2/3, the 3rd optional parameter is set to 2/3.
# 25-jul: Add model P = A*f^3 + B*fansp + C where f and fansp are as above in the
# model for energy E. This will also get included when 2 is passed instead of 1,
# to method=1. modify the input .txt data to include measured_power as well.

import statsmodels.api as sm
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import math
import sys
import copy
import matplotlib.pyplot as plt
from itertools import combinations

extra_evaluations = 1; # this is valid only if there is gpuset data and evaluate_gpuset_data=1. 
			#Extra set of tests within gpuset data. 

evaluate_gpuset_data = 0; # pass 1 in command line if gpuset data also needs to be evaluated
		 	# we do not have gpuset data for the initial power model.

evaluate_energy_fanspeed_data = 0; # pass 2 in command line if fanspeed data also needs to be 
			# evaluated with energy data. Note that, if 2 is passed, gpuset data
			    # will not be evaluated. 
evaluate_temp_fanspeed_data = 0; # pass 3 instead to evaluated temperature and fanspeed data

scaling_factor = 1e9;
#scaling_factor = 1e6;

def split_dataset(num_values, num_groups):
	
	all_groups = [];

	group = [];
	for group_id in range(num_groups):
		for j in range(num_values):
			if (j%num_groups==group_id):
				group.append(j);
		all_groups.append(copy.deepcopy(group));
		group = [];

	print("debug: all_groups: ",all_groups);
	return all_groups;

def get_mape_and_rmse(predictions, meas_power):
	ape = [];
	diff_squared = [];
	for i in range(len(predictions)):
		diff = predictions[i] - meas_power[i];
		ape.append(float(abs(predictions[i]-meas_power[i])/meas_power[i])*100.0);
		diff_squared.append(pow(diff,2));

	mape = np.average(ape);
	rmse = np.sqrt(np.average(diff_squared));

	return mape,rmse;

def get_linear_regr_model_core(core_freq_model, core_freq_val, \
	active_lanes_minus1_model, active_lanes_minus1_val, primary_PB_model\
	, primary_PB_val, non_primary_PB_model, non_primary_PB_val\
	, core_freq_primary_PB_model, core_freq_primary_PB_val\
	, core_freq_non_primary_PB_model, core_freq_non_primary_PB_val\
	, num_gpusets_minus1_model, num_gpusets_minus1_val, meas_power_model\
	, meas_power_val, modeltype=1):

	lr = LinearRegression();

	if (modeltype == 1): # Bf*Dp + Bf*Es + F(num_gpusets-1) + G
		X_data_model = np.column_stack((core_freq_primary_PB_model,\
			core_freq_non_primary_PB_model, num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_primary_PB_val,\
			core_freq_non_primary_PB_val, num_gpusets_minus1_val));
	elif (modeltype == 2): 
		X_data_model = np.column_stack((core_freq_model, primary_PB_model,\
			non_primary_PB_model, core_freq_primary_PB_model,\
			core_freq_non_primary_PB_model, num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_val, primary_PB_val,\
			non_primary_PB_val, core_freq_primary_PB_val,\
			core_freq_non_primary_PB_val, num_gpusets_minus1_val));
	elif (modeltype == 3):
		X_data_model = np.column_stack((core_freq_model,\
						num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_val,\
						num_gpusets_minus1_val));
	elif (modeltype == 4): # Bf + Dp + Es + F(num_gpu_sets-1) + G
		X_data_model = np.column_stack((core_freq_model, primary_PB_model,\
			non_primary_PB_model, num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_val, primary_PB_val,\
			non_primary_PB_val, num_gpusets_minus1_val));
	elif (modeltype == 5): # Bf + C(l-1) + Dp + Es + F(num_gpu_sets-1) + G
		X_data_model = np.column_stack((core_freq_model, active_lanes_minus1_model,\
					primary_PB_model,non_primary_PB_model, \
					num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_val, active_lanes_minus1_val,\
					primary_PB_val, non_primary_PB_val, \
					num_gpusets_minus1_val));
	elif (modeltype == 6): # Bf + D(p+s) + G
		all_PB_model = [];
		all_PB_val = [];
		for i in range(len(primary_PB_model)):
			all_PB_model.append(primary_PB_model[i]+non_primary_PB_model[i]);
		for i in range(len(primary_PB_val)):
			all_PB_val.append(primary_PB_val[i]+non_primary_PB_val[i]);
		X_data_model = np.column_stack((core_freq_model, all_PB_model));
		X_data_val = np.column_stack((core_freq_val, all_PB_val));
	elif (modeltype == 7): #Af^3 + B(num_gpu_sets-1) + C
		core_freq_cubed_model = [];
		core_freq_cubed_val = [];

		for i in range(len(core_freq_model)):
			core_freq_cubed_model.append(pow(core_freq_model[i],3));
		for i in range(len(core_freq_val)):
			core_freq_cubed_val.append(pow(core_freq_val[i],3));

		# we reduce the value to fix the condition number issue in method=1
		core_freq_cubed_model = np.array(core_freq_cubed_model)/scaling_factor;
		core_freq_cubed_val = np.array(core_freq_cubed_val)/scaling_factor;
	
		X_data_model = np.column_stack((core_freq_cubed_model,\
						num_gpusets_minus1_model));
		X_data_val = np.column_stack((core_freq_cubed_val,\
						num_gpusets_minus1_val));
	elif ((modeltype == 8) #Af^3 + B(p+s) + C(num_gpu_sets-1) + D
		or (modeltype == 9) #Af^3 + B(l-1) + C(p+s) + D(gpu_sets-1) + E
		or (modeltype == 10) #Af^3 + B(p+s) + C for <=1 gpuset
		or (modeltype == 11) #Af^3 + Bf + C(l-1) + D(p+s) + E(gpu_sets-1) + F
		or (modeltype == 12)): #Alog10(f) + B(l-1) + C(p+s) + D(gpu_sets-1) + E
		core_freq_cubed_model = [];
		core_freq_cubed_val = [];
		log_core_freq_model = [];
		log_core_freq_val = [];
		all_PB_model = [];
		all_PB_val = [];

		for i in range(len(primary_PB_model)):
			all_PB_model.append(primary_PB_model[i]+non_primary_PB_model[i]);
		for i in range(len(primary_PB_val)):
			all_PB_val.append(primary_PB_val[i]+non_primary_PB_val[i]);
		for i in range(len(core_freq_model)):
			core_freq_cubed_model.append(pow(core_freq_model[i],3));
			log_core_freq_model.append(np.log10(core_freq_model[i]));
		for i in range(len(core_freq_val)):
			core_freq_cubed_val.append(pow(core_freq_val[i],3));
			log_core_freq_val.append(np.log10(core_freq_val[i]));

		#print("debug. core_freq_cubed_val before reducing by ratio 1e9: ",core_freq_cubed_model);
		#print("debug. core_freq_cubed_val before reducing by ratio 1e9: ",core_freq_cubed_val);

		# we reduce the value to fix the condition number issue in method=1
		core_freq_cubed_model = np.array(core_freq_cubed_model)/scaling_factor;
		core_freq_cubed_val = np.array(core_freq_cubed_val)/scaling_factor;

		#print("debug. core_freq_cubed_val after reducing by ratio 1e9: ",core_freq_cubed_model);
		#print("debug. core_freq_cubed_val after reducing by ratio 1e9: ",core_freq_cubed_val);

		#exit(-1);
	
		if (modeltype == 8):
			X_data_model = np.column_stack((core_freq_cubed_model, all_PB_model,\
						num_gpusets_minus1_model));
			X_data_val = np.column_stack((core_freq_cubed_val, all_PB_val,\
						num_gpusets_minus1_val));
		elif (modeltype == 9): #Af^3 + B(l-1) + C(p+s) + D(gpusets-1) + E
			X_data_model = np.column_stack((core_freq_cubed_model, \
						active_lanes_minus1_model, \
						all_PB_model,\
						num_gpusets_minus1_model));
			X_data_val = np.column_stack((core_freq_cubed_val, \
						active_lanes_minus1_val,\
						all_PB_val,\
						num_gpusets_minus1_val));
		elif (modeltype == 10):
			X_data_model = np.column_stack((core_freq_cubed_model, \
						all_PB_model));
			X_data_val = np.column_stack((core_freq_cubed_val, \
						all_PB_val));
		elif (modeltype == 11):
			X_data_model = np.column_stack((core_freq_cubed_model, \
						core_freq_model,active_lanes_minus1_model, \
						all_PB_model,\
						num_gpusets_minus1_model));
			X_data_val = np.column_stack((core_freq_cubed_val, \
						core_freq_val,active_lanes_minus1_val,\
						all_PB_val,\
						num_gpusets_minus1_val));
		elif (modeltype == 12): #Alog10(f) + B(l-1) + C(p+s) + D(gpusets-1) + E
			X_data_model = np.column_stack((log_core_freq_model, \
						active_lanes_minus1_model, \
						all_PB_model,\
						num_gpusets_minus1_model));
			X_data_val = np.column_stack((log_core_freq_val, \
						active_lanes_minus1_val,\
						all_PB_val,\
						num_gpusets_minus1_val));
	else:
		print("unsupported model type! Choose either 1 or 2. Exiting");
		exit(-4);

	lr.fit(X_data_model,meas_power_model);
	print("Linear Regr model coeffs: ", lr.coef_);
	print("Linear Regr model intercept: ", lr.intercept_);

	predictions = lr.predict(X_data_val);

	mape,rmse = get_mape_and_rmse(predictions, meas_power_val);

	return mape,rmse;

# https://towardsdatascience.com/the-complete-guide-to-linear-regression-in-python-3d3f8f06bf8
def get_linear_regr_model(meas_power, core_freq, active_lanes_minus1, \
	primary_PB, non_primary_PB, num_gpusets_minus1, group_indices = [], modeltype = 1):

	core_freq_temp = copy.deepcopy(core_freq);
	core_freq = [];

	for i in range(len(core_freq_temp)):
		core_freq.append(core_freq_temp[i]/1e6);

	core_freq_primary_PB = [];
	core_freq_non_primary_PB = [];
	for i in range(len(core_freq)):
		core_freq_primary_PB.append(core_freq[i]*primary_PB[i]);
		core_freq_non_primary_PB.append(core_freq[i]*primary_PB[i]);

	if (group_indices): # the data set split is specified
		num_groups = len(group_indices);

		print(num_groups,"-fold validation:");
		print("##################");

		test_combinations = combinations(range(num_groups), num_groups-1);
		
		for comb in list(test_combinations):
			model_indices = [];
			for i in range(num_groups-1):
				model_indices = model_indices + group_indices[comb[i]];
			
			val_list = [1]*num_groups;
			val_indices = [];
			# isolate the group not in the combination: this is the val group
			for i in range(num_groups-1):
				val_list[comb[i]] = 0;

			for i in range(len(val_list)):
				if (val_list[i] == 1):
					print("debug: val index: ",i);
					val_indices = group_indices[i];
					break;

			core_freq_model = [];
			active_lanes_minus1_model = [];
			primary_PB_model = [];
			non_primary_PB_model = [];
			num_gpusets_minus1_model = [];
			core_freq_primary_PB_model = [];
			core_freq_non_primary_PB_model = [];
			meas_power_model = [];

			for model_idx in model_indices:
				core_freq_model.append(core_freq[model_idx]);
				active_lanes_minus1_model.append(active_lanes_minus1[model_idx]);
				primary_PB_model.append(primary_PB[model_idx]);
				non_primary_PB_model.append(non_primary_PB[model_idx]);
				num_gpusets_minus1_model.append(num_gpusets_minus1[model_idx]);
				core_freq_primary_PB_model.append(core_freq_primary_PB[model_idx]);
				core_freq_non_primary_PB_model.append(core_freq_non_primary_PB[model_idx]);
				meas_power_model.append(meas_power[model_idx]);

			core_freq_val = [];
			active_lanes_minus1_val = [];
			primary_PB_val = [];
			non_primary_PB_val = [];
			num_gpusets_minus1_val = [];
			core_freq_primary_PB_val = [];
			core_freq_non_primary_PB_val = [];
			meas_power_val = [];

			for val_idx in val_indices:
				core_freq_val.append(core_freq[val_idx]);
				active_lanes_minus1_val.append(active_lanes_minus1[val_idx]);
				primary_PB_val.append(primary_PB[val_idx]);
				non_primary_PB_val.append(non_primary_PB[val_idx]);
				num_gpusets_minus1_val.append(num_gpusets_minus1[val_idx]);
				core_freq_primary_PB_val.append(core_freq_primary_PB[val_idx]);
				core_freq_non_primary_PB_val.append(core_freq_non_primary_PB[val_idx]);
				meas_power_val.append(meas_power[val_idx]);

			if (modeltype == 1):
				model = "P = Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G";
			elif (modeltype == 2):
				model = "P = Bf + Dp + Es + Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G";
			elif (modeltype == 3):
				model = "P = Bf + F(num_gpu_sets-1) + G";
			elif (modeltype == 4):
				model = "P = Bf + Dp + Es + F(num_gpu_sets-1) + G";
			elif (modeltype == 5):
				model = "P = Bf + C(l-1) + Dp + Es + F(num_gpu_sets-1) + G";
			elif (modeltype == 6):
				model = "P = Bf + D(p+s) + G";
			elif (modeltype == 7):
				model = "P = Af^3 + B(num_gpu_sets-1) + C";
			elif (modeltype == 8):
				model = "P = Af^3 + B(p+s) + C(num_gpu_sets-1) + D";
			elif (modeltype == 9):
				model = "P = Af^3 + B(l-1) + C(p+s) + D(num_gpu_sets-1) + E";
			elif (modeltype == 10):
				model = "P = Af^3 + B(p+s) + C";
			elif (modeltype == 11):
				model = "P = Af^3 + Bf + C(l-1) + D(p+s) + E(num_gpu_sets-1) + F";
			elif (modeltype == 12):
				model = "P = Alog10(f) + B(l-1) + C(p+s) + D(num_gpu_sets-1) + E";

			mape,rmse = get_linear_regr_model_core(core_freq_model, core_freq_val, \
			active_lanes_minus1_model, active_lanes_minus1_val, primary_PB_model\
			, primary_PB_val, non_primary_PB_model, non_primary_PB_val\
			, core_freq_primary_PB_model, core_freq_primary_PB_val\
			, core_freq_non_primary_PB_model, core_freq_non_primary_PB_val\
			, num_gpusets_minus1_model, num_gpusets_minus1_val, meas_power_model\
			, meas_power_val, modeltype);

			print(model," MAPE: ",mape," RMSE: ", rmse);
		
		return; # with specified group indices. 

	# If group indices are  not specified
	# use the entire data set for model and validation.
	print("full dataset for both modelling and validation:");
	print("###############################################");

	lr = LinearRegression();

	core_freq_cubed = [];
	for i in core_freq:
		core_freq_cubed.append(math.pow(i,3));

#	X_data = np.column_stack((core_freq_cubed, core_freq, active_lanes_minus1,\
#					primary_PB, non_primary_PB, num_gpusets_minus1));

	# P = Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G
	X_data = np.column_stack((core_freq_primary_PB, \
					core_freq_non_primary_PB, num_gpusets_minus1));

	lr.fit(X_data,meas_power);
	print("Linear Regr model coeffs: ", lr.coef_);
	print("Linear Regr model intercept: ", lr.intercept_);

	predictions = lr.predict(X_data);

	mape,rmse = get_mape_and_rmse(predictions, meas_power);
	print("P = Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G: MAPE: ",mape," RMSE: ", rmse);

	# P = Bf + Dp + Es + Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G
	X_data = np.column_stack((core_freq,primary_PB, non_primary_PB,\
					core_freq_primary_PB, \
					core_freq_non_primary_PB, num_gpusets_minus1));

	lr.fit(X_data,meas_power);
	print("Linear Regr model coeffs: ", lr.coef_);
	print("Linear Regr model intercept: ", lr.intercept_);

	predictions = lr.predict(X_data);

	mape,rmse = get_mape_and_rmse(predictions, meas_power);
	print("P = Bf + Dp + Es + Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G: MAPE: ",mape," RMSE: ", rmse);

	X_data = np.column_stack((core_freq,primary_PB, non_primary_PB,\
					 num_gpusets_minus1));

	lr.fit(X_data,meas_power);
	print("Linear Regr model coeffs: ", lr.coef_);
	print("Linear Regr model intercept: ", lr.intercept_);

	predictions = lr.predict(X_data);

	mape,rmse = get_mape_and_rmse(predictions, meas_power);
	print("P = Bf + Dp + Es + F(num_gpu_sets-1) + G: MAPE: ",mape," RMSE: ", rmse);

def lcytek1_extra_evaluations(meas_power, core_freq_cubed, core_freq,\
        active_lanes_minus1, primary_PB, non_primary_PB, num_gpusets_minus1):
	# For lcyte_k1, remove the C and D coefficients both of which show a P value
	# > 0.05.

		log_core_freq = [];
		for freq in core_freq:
			log_core_freq.append(math.log(freq,10));

		X_data = np.column_stack((core_freq,\
							non_primary_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + E(s) + F(num_gpusets_minus1) + G\
		 all rows:");
		print(est2.summary());

	# check multi-collinearity
	# Start with Bf and C(l-1)
		core_freq_active_lanes_minus1 = [];
		core_freq_primary_PB = [];
		core_freq_non_primary_PB = [];
		active_lanes_minus1_primary_PB = [];
		active_lanes_minus1_non_primary_PB = [];
		primary_PB_non_primary_PB = [];

		for i in range(len(core_freq)):
			core_freq_active_lanes_minus1.append(core_freq[i]*active_lanes_minus1[i]);
			core_freq_primary_PB.append(core_freq[i]*primary_PB[i]);
			core_freq_non_primary_PB.append(core_freq[i]*non_primary_PB[i]);

			active_lanes_minus1_primary_PB.append(active_lanes_minus1[i]*primary_PB[i]);
			active_lanes_minus1_non_primary_PB.append(active_lanes_minus1[i]*\
										non_primary_PB[i]);

			primary_PB_non_primary_PB.append(primary_PB[i]*non_primary_PB[i]);

		# check multi-collinearity
		##########################
		X_data = np.column_stack((core_freq,core_freq_active_lanes_minus1,\
			active_lanes_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*C(l-1) + C(l-1) + G\
		 all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,core_freq_primary_PB,\
			primary_PB));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*Dp + Dp + G\
		 all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,core_freq_non_primary_PB,\
			non_primary_PB));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*Es + Es + G\
		 all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,active_lanes_minus1,\
						active_lanes_minus1_primary_PB,\
						primary_PB));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + C(l-1) + C(l-1)*Dp + Dp + G\
		 all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,active_lanes_minus1,\
						active_lanes_minus1_non_primary_PB,\
						non_primary_PB));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + C(l-1) + C(l-1)*Es + Es + G\
		 all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,active_lanes_minus1,\
						core_freq_primary_PB,\
						non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + C(l-1) + Bf*Dp + Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,\
						core_freq_primary_PB,\
						non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*Dp + Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,\
						core_freq_primary_PB,core_freq_non_primary_PB,\
						non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*Dp + Bf*Es + Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq,\
						core_freq_primary_PB,core_freq_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Bf*Dp + Bf*Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq, primary_PB,\
						core_freq_primary_PB,core_freq_non_primary_PB,\
						non_primary_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Dp + Bf*Dp + Bf*Es + Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_primary_PB,\
						core_freq_non_primary_PB,\
						non_primary_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf*Dp + Bf*Es + Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_primary_PB,\
						core_freq_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf*Dp + Bf*Es + F(gpu_sets-1) +\
		 	G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_cubed, core_freq, \
						primary_PB, core_freq_primary_PB,\
						non_primary_PB, core_freq_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + Dp + Bf*Dp + Es + \
				Bf*Es + F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_cubed, core_freq, \
						primary_PB, non_primary_PB,\
						primary_PB_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + Dp + Es + Dp*Es\
				+ F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_cubed, core_freq, \
					 	non_primary_PB,\
						primary_PB_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + Es + Dp*Es\
				+ F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq, \
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		num_gpusets = [];
		for i in range(len(num_gpusets_minus1)):
			num_gpusets.append(num_gpusets_minus1[i]+1);

		print("num_gpusets: ",num_gpusets);

		X_data = np.column_stack((core_freq, \
						num_gpusets));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + F(gpu_sets) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq_cubed, core_freq, \
						num_gpusets));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + F(gpu_sets) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq, \
					 	primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Dp + F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((core_freq, \
					 	primary_PB, non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + Dp + Es + F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		X_data = np.column_stack((\
						primary_PB, core_freq_primary_PB,\
						non_primary_PB, core_freq_non_primary_PB,\
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Dp + Bf*Dp + Es + \
				Bf*Es + F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		# new models below: introduced for evaluation without gpusets as well
		# attempt to model with total PB
		total_PB = [];
		for i in range(len(primary_PB)):
			PB = primary_PB[i] + non_primary_PB[i];
			total_PB.append(PB);	

		# Af^3 + Bf + C(l-1) + D(p+s) + E(gpu_sets-1) + F
		X_data = np.column_stack((core_freq_cubed, core_freq,\
						active_lanes_minus1,\
						total_PB, num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + C(l-1) + D(p+s) + E(gpu_sets-1)\
				+ F [new]:");
		print(est2.summary());

		# Bf + C(l-1) + D(p+s) + E(gpu_sets-1) + F
		X_data = np.column_stack((core_freq,\
						active_lanes_minus1,\
						total_PB, num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + C(l-1) + D(p+s) + E(gpu_sets-1) + \
				F [new]:");
		print(est2.summary());

		# Bf + D(p+s) + E(gpu_sets-1) + F
		X_data = np.column_stack((core_freq,\
						total_PB, num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + D(p+s) + E(gpu_sets-1) + F [new]: ");
		print(est2.summary());

		# Af^3 + Bf + F(gpu_sets-1) + G
		X_data = np.column_stack((core_freq_cubed, core_freq, \
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + \
				+ F(gpu_sets-1) + G all rows:");
		print(est2.summary());

		# Af^3 + F(gpu_sets-1) + G
		X_data = np.column_stack((core_freq_cubed, \
						num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + F(gpu_sets-1) \
				+ G all rows:");
		print(est2.summary());

		# Af^3 + B(p+s) + C
		X_data = np.column_stack((core_freq_cubed, \
						total_PB));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(p+s) + C all rows:");
		print(est2.summary());

		# Af^3 + B(p+s) + C(num_gpu_sets-1) + D
		X_data = np.column_stack((core_freq_cubed, \
					total_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(p+s) + C(num_gpu_sets-1) \
				+ D all rows:");
		print(est2.summary());

		# Af^3 + B(p+s) + C(num_gpu_sets-1) + D
		X_data = np.column_stack((core_freq_cubed, \
					total_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(p+s) + C(num_gpu_sets-1) \
				+ D all rows:");
		print(est2.summary());

		# Af^3 + B(l-1) + C(p+s) + D(num_gpu_sets-1) + E
		X_data = np.column_stack((core_freq_cubed, active_lanes_minus1,\
					total_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(l-1) + C(p+s) + \
				D(num_gpu_sets-1) + E all rows:");
		print(est2.summary());

		# Af^3 + Bf + C(p+s) + D(num_gpu_sets-1) + E
		X_data = np.column_stack((core_freq_cubed, core_freq,\
					total_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + C(p+s) + \
				D(num_gpu_sets-1) + E all rows:");
		print(est2.summary());

		# Af^3 + Bf + C(l-1) + D(p+s) + E(num_gpu_sets-1) + F
		X_data = np.column_stack((core_freq_cubed, core_freq,\
					active_lanes_minus1,total_PB,\
					num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + C(l-1) + D(p+s) + \
				E(num_gpu_sets-1) + F all rows:");
		print(est2.summary());

		# Af^3 + B(num_gpu_sets-1) + C
		X_data = np.column_stack((core_freq_cubed,\
					num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(num_gpu_sets-1) + C\
				all rows:");
		print(est2.summary());

		# Af^3 + B(l-1) + C(num_gpu_sets-1) + D
		X_data = np.column_stack((core_freq_cubed,\
					active_lanes_minus1,\
					num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + B(l-1) + C(num_gpu_sets-1) \
					+ D all rows:");
		print(est2.summary());

		# Alog_10(f) + B(l-1) + C(p+s) + D(num_gpu_sets-1) + E
		X_data = np.column_stack((log_core_freq, active_lanes_minus1,\
					total_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Alog_10(f) + B(l-1) + C(p+s) + \
			D(num_gpu_sets-1) + E");

		print(est2.summary());

# credit: https://stats.stackexchange.com/questions/243000/cause-of-a-high-condition-number-in-a-python-statsmodels-regression
def centre_data(X):
	X -= np.average(X);

	return X;

# use this routine for method=1, and either the Energy or the Temperature
# model.
def get_significance_energy_temp(meas_energy_or_temp, core_freq, fan_speed\
				,meas_power,meas_runtime):
	core_freq_temp = copy.deepcopy(core_freq);

	core_freq = [];

	# need to take just the freq values without the 1e6
	for i in core_freq_temp:
		core_freq.append(i/1e6);

	if (evaluate_energy_fanspeed_data == 1):
		meas_energy = copy.deepcopy(meas_energy_or_temp);

		meas_energy_or_temp = [];
		for i in range(len(core_freq)):
			meas_energy_or_temp.append(meas_energy[i]*1e6);
		
		core_freq_cubed = [];
		for i in core_freq:
			core_freq_cubed.append(math.pow(i,3)/scaling_factor);

		# E = Af + Bfansp + C: all rows
		X_data = np.column_stack((core_freq, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_energy_or_temp, X_const);
		est2 = est.fit();

		print("Measured energy as Af + Bfansp + C all rows:");
		print(est2.summary());

		# E = Af^3 + Bfansp + C: all rows
		X_data = np.column_stack((core_freq_cubed, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_energy_or_temp, X_const);
		est2 = est.fit();

		print("Measured energy as Af^3 + Bfansp + C all rows:");
		print(est2.summary());

		# E = Af^3 + B: all rows
		#X_data = np.column_stack((core_freq_cubed, fan_speed));

		#X_const = sm.add_constant(X_data);
		X_const = sm.add_constant(core_freq_cubed);
		est = sm.OLS(meas_energy_or_temp, X_const);
		est2 = est.fit();

		print("Measured energy as Af^3 + B all rows:");
		print(est2.summary());

		# P = Af^3 + Bfansp + C: all rows
		X_data = np.column_stack((core_freq_cubed, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bfansp + C all rows:");
		print(est2.summary());

		# Rt = Af^3 + Bfansp + C: all rows
		X_data = np.column_stack((core_freq_cubed, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_runtime, X_const);
		est2 = est.fit();

		print("Measured runtime as Af^3 + Bfansp + C all rows:");
		print(est2.summary());

		# Rt = Af + Bfansp + C: all rows
		X_data = np.column_stack((core_freq, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_runtime, X_const);
		est2 = est.fit();

		print("Measured runtime as Af + Bfansp + C all rows:");
		print(est2.summary());

		# Rt = Af^3 + B: all rows
		#X_data = np.column_stack((core_freq_cubed));

		#X_const = sm.add_constant(X_data);
		X_const = sm.add_constant(core_freq_cubed);
		est = sm.OLS(meas_runtime, X_const);
		est2 = est.fit();

		print("Measured runtime as Af^3 + B all rows:");
		print(est2.summary());

		# Rt = Af + B: all rows
		#X_data = np.column_stack((core_freq));

		#X_const = sm.add_constant(X_data);
		X_const = sm.add_constant(core_freq);
		est = sm.OLS(meas_runtime, X_const);
		est2 = est.fit();

		print("Measured runtime as Af + B all rows:");
		print(est2.summary());

	elif (evaluate_temp_fanspeed_data == 1):
		# T = Af + Bfansp + C: all rows
		X_data = np.column_stack((core_freq, fan_speed));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_energy_or_temp, X_const);
		est2 = est.fit();

		print("Measured temp as Af + Bfansp + C all rows:");
		print(est2.summary());

	else:
		print("only energy or temp model evaluation possible ... retry\n");
		exit(-1);

def get_significance(meas_power, core_freq, active_lanes_minus1, \
	primary_PB, non_primary_PB, num_gpusets_minus1):

	#core_freq_temp = copy.deepcopy(core_freq);

	#core_freq = [];

	#for i in core_freq_temp:
	#	core_freq.append(i*1e6);

	#X_const = sm.add_constant(core_freq_cubed);
	#X_const = sm.add_constant(core_freq);
	#est = sm.OLS(meas_power, X_const);
	#print("Measured power against core_frequency^3");

	core_freq_temp = copy.deepcopy(core_freq);

	core_freq = [];

	# need to take just the freq values without the 1e6
	for i in core_freq_temp:
		core_freq.append(i/1e6);

	core_freq_cubed = [];
	for i in core_freq:
		core_freq_cubed.append(math.pow(i,3));

	# attempt to model with total PB
	total_PB = [];
	for i in range(len(primary_PB)):
		PB = primary_PB[i] + non_primary_PB[i];
		total_PB.append(PB);	

	# we now center all the data in order to avoid the high condition number
	# reported by statsmodel OLS
	#print("debug: before centering : core_freq: ",core_freq);
	#core_freq = centre_data(core_freq);
	#print("debug: centered data: core_freq: ",core_freq);

	print("debug: before centering : core_freq_cubed: ",core_freq_cubed);
	# not useful, since the range of values after centering is still from
	# e-8 to e8
	#core_freq_cubed = centre_data(core_freq_cubed);
	#print("debug: centered data: core_freq_cubed: ",core_freq_cubed);

	# works with the ratio of min value e.g. 999^3/139^3 = 371.23. With this
	# condition number issue is solved. But we need to compute a similar ratio
	# on the validation GPU (e.g. Ampere) too..
	#core_freq_cubed = np.array(core_freq_cubed)/min(core_freq_cubed);
	#print("debug: reduced by ratio of min value: core_freq_cubed: ",core_freq_cubed);
	#exit(-1);

	# works well. We now have the condition number solved. Also, it is simple to
	# do f^3/1e9 on the validation GPU data, since we still retain the same values
	# but only reduced by a constant factor of 1e9.
	core_freq_cubed = np.array(core_freq_cubed)/scaling_factor;

	#active_lanes_minus1 = centre_data(active_lanes_minus1);
	#print("debug: centered data: active_lanes_minus1: ",active_lanes_minus1);
	#primary_PB = centre_data(primary_PB);
	#print("debug: centered data: primary_PB: ",primary_PB);
	#non_primary_PB = centre_data(non_primary_PB);
	#print("debug: centered data: non_primary_PB: ",non_primary_PB);
	#total_PB = centre_data(total_PB);
	#print("debug: centered data: total_PB: ",total_PB);
	#num_gpusets_minus1 = centre_data(num_gpusets_minus1);
	#print("debug: centered data: num_gpusets_minus1: ",num_gpusets_minus1);

	# Af + B: 1st 9 rows
	X_const = sm.add_constant(core_freq[0:9]); # all freqs with 1 lane only
	print("debug: input core_freq: ", core_freq[0:9]);
	est = sm.OLS(meas_power[0:9], X_const);
	est2 = est.fit();

	print("Measured power against core_frequency");
	print(est2.summary());

	# Af^3 + Bf + C: 1st 9 rows
	X_data = np.column_stack((core_freq_cubed[0:9], core_freq[0:9]));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[0:9], X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C 1st 9 rows:");
	print(est2.summary());

	#  P = Af^3 + Bf + C(l-1) + D(p) + E(s) + F
	# using data from 1st 9 rows
	X_data = np.column_stack((core_freq_cubed[0:9], core_freq[0:9], active_lanes_minus1[0:9],\
					primary_PB[0:9], non_primary_PB[0:9]));
	
	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[0:9], X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + D(p) + E(s) + F from 1st 9 rows:");
	print(est2.summary());

	# P = Af^3 + Bf + C(l-1) + F. All rows
	X_data = np.column_stack((core_freq_cubed, core_freq, active_lanes_minus1));
	
	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power, X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + F from all rows:");
	print(est2.summary());

	# Af^3 + Bf + C: all rows
	X_data = np.column_stack((core_freq_cubed, core_freq));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power, X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C all rows:");
	print(est2.summary());

	# Af^3 + Bf + C(l-1) + D(p) + F: all rows
	X_data = np.column_stack((core_freq_cubed, core_freq,active_lanes_minus1,\
							primary_PB));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power, X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + D(p) + F all rows:");
	print(est2.summary());

	# Af^3 + Bf + C(l-1) + D(p) + E(s) + F: all rows
	X_data = np.column_stack((core_freq_cubed, core_freq,active_lanes_minus1,\
							primary_PB,non_primary_PB));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power, X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + D(p) + E(s) + F all rows:");
	print(est2.summary());

	# Af^3 + Bf + C(l-1) + D(p) + E(s) + F: [first 72 rows of prev 6-term model]
	X_data = np.column_stack((core_freq_cubed[:72], core_freq[:72],\
							active_lanes_minus1[:72],\
							primary_PB[:72], non_primary_PB[:72]));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[:72], X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + D(p) + E(s) + F (first 72 rows\
			of previous 6-term model):");
	print(est2.summary());

	# Af^3 + Bf + C(l-1) + D(p+s) + F
	X_data = np.column_stack((core_freq_cubed[:72], core_freq[:72],\
							active_lanes_minus1[:72],\
							total_PB[:72]));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[:72], X_const);
	est2 = est.fit();

	print("Measured power as Af^3 + Bf + C(l-1) + D(p+s) + F (first 72 rows\
			of previous 6-term model) [new]:");
	print(est2.summary());

	# Bf + C(l-1) + D(p+s) + F
	X_data = np.column_stack((core_freq[:72],active_lanes_minus1[:72],\
					total_PB[:72]));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[:72], X_const);
	est2 = est.fit();

	print("Measured power as Bf + C(l-1) + D(p+s) + F (first 72 rows\
			of previous 6-term model) [new]:");
	print(est2.summary());

	# Bf + D(p+s) + F
	X_data = np.column_stack((core_freq[:72], total_PB[:72]));

	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power[:72], X_const);
	est2 = est.fit();

	print("Measured power as Bf + D(p+s) + F (first 72 rows\
			of previous 6-term model) [new]:");
	print(est2.summary());

	# Af^3 + B(p+s) + C # ensure all data points are for 1 gpuset only
	X_data = np.column_stack((core_freq_cubed, total_PB));
	X_const = sm.add_constant(X_data);
	est = sm.OLS(meas_power, X_const);
	est2 = est.fit();

	# we do not have gpuset data for the initial power model
	if (evaluate_gpuset_data):

		# Af^3 + Bf + C(l-1) + D(p) + E(s) + F(gpu_sets-1) + G : all rows
		X_data = np.column_stack((core_freq_cubed, core_freq,active_lanes_minus1,\
					primary_PB,non_primary_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Af^3 + Bf + C(l-1) + D(p) + E(s) + F(gpu_sets) + G\
			 all rows:");
		print(est2.summary());

		# Excluding A (dynamic power coefficient) since the P value > 0.05 and hence
		# it is statistically insignificant
		# Bf + C(l-1) + D(p) + E(s) + F(gpu_sets) + G : all rows
		X_data = np.column_stack((core_freq,active_lanes_minus1,\
				primary_PB,non_primary_PB,num_gpusets_minus1));

		X_const = sm.add_constant(X_data);
		est = sm.OLS(meas_power, X_const);
		est2 = est.fit();

		print("Measured power as Bf + C(l-1) + D(p) + E(s) + F(gpu_sets) + G\
				 all rows:");
		print(est2.summary());

		if (extra_evaluations):
			lcytek1_extra_evaluations(meas_power, core_freq_cubed, core_freq, \
				active_lanes_minus1, primary_PB, non_primary_PB,\
				num_gpusets_minus1);
	
def get_data_from_file(file,option):
	data_f = open(file,"r");

	for line in data_f:
		var = line.split(' = ')[0];
		# print("debug: var: ",var);

		value = line.split(' = ')[1].split(";\n")[0];
		# print("debug: ",value);

		if (var == 'power'):
			measured_power = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				measured_power.append(float(values[i]));
			print("debug: ",measured_power);
		elif ((var == 'core_frequency') or (var == 'norm_core_frequency')):
			core_freq = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			if (var == 'core_frequency'):
				for i in range(len(values)):
					core_freq.append(float(values[i])*1e6);
			else:
				for i in range(len(values)):
					core_freq.append(float(values[i]));
			print("debug: ",core_freq);
		elif ((var == 'active_lanes') or (var == 'norm_active_lanes_minus1')):
			active_lane_count_minus1 = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			if (var == 'norm_active_lanes_minus1'):
				for i in range(len(values)):
					active_lane_count_minus1.append(float(values[i]));
			else:
				for i in range(len(values)):
					active_lane_count_minus1.append(int(values[i])-1);
			print("debug: ",active_lane_count_minus1);
		elif ((var == 'active_primary_PB') or (var == 'norm_active_primary_PB')):
			active_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			if (var == 'active_primary_PB'):
				for i in range(len(values)):
					active_primary_PB.append(int(values[i]));
			else:
				for i in range(len(values)):
					active_primary_PB.append(float(values[i]));
			print("debug: ",active_primary_PB);
		elif ((var == 'active_non_primary_PB') or 
					(var == 'norm_active_non_primary_PB')):
			active_non_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			if (var == 'active_non_primary_PB'):
				for i in range(len(values)):
					active_non_primary_PB.append(int(values[i]));
			else:
				for i in range(len(values)):
					active_non_primary_PB.append(float(values[i]));
			print("debug: ",active_non_primary_PB);
		elif (var == 'extra_TB'): # used in option '17' for GICOV
			extra_TB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				extra_TB.append(int(values[i]));
			print("debug: ",extra_TB);
		elif (var == 'num_gpu_repetitions_for_TB'): # used in option '18'
			num_gpu_repetitions_for_TB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				num_gpu_repetitions_for_TB.append(int(values[i]));
			print("debug: ",num_gpu_repetitions_for_TB);
		elif ((var == 'GPU_sets') or (var == 'norm_GPU_sets_minus1')):
			num_GPU_sets_minus1 = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			if (var == 'norm_GPU_sets_minus1'):
				for i in range(len(values)):
					num_GPU_sets_minus1.append(float(values[i]));
			else:
				for i in range(len(values)):
					num_GPU_sets_minus1.append(int(values[i])-1);
			print("debug: gpu sets: ",num_GPU_sets_minus1);
		elif (var == 'energy'): 
			measured_energy = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				measured_energy.append(float(values[i]));
			print("debug: ",measured_energy);
		elif (var == 'temp'): 
			measured_temp = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				measured_temp.append(int(values[i]));
			print("debug: ",measured_temp);
		elif (var == 'fan_speed'): 
			fan_speed = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				fan_speed.append(int(values[i]));
			print("debug: ",fan_speed);
		elif (var == 'runtime'): 
			measured_runtime = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				measured_runtime.append(float(values[i]));
			print("debug: ",measured_runtime);
		elif (var == 'deg6_num_data_points'):
			deg6_num_data_points = int(value);
		elif (var == 'deg6_model_indices'):
			deg6_model_indices = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				deg6_model_indices.append(int(values[i]));
		else:
			print("unknown variable in data file.. exiting");
			exit(-1);

	if ((option == 1) or (option == 2)):
		if (evaluate_energy_fanspeed_data == 1):
			return measured_power,measured_runtime,measured_energy,\
				core_freq,fan_speed;
		elif (evaluate_temp_fanspeed_data == 1):
			return measured_temp,core_freq,fan_speed;
		else:		
			return measured_power,core_freq,\
			active_lane_count_minus1,active_primary_PB,\
			active_non_primary_PB,num_GPU_sets_minus1;

if __name__ == "__main__":

		method = int(sys.argv[1]);
	
		modeltype = 1; # default for method = 2.

		if ((method == 1) or (method == 2)):
			if (len(sys.argv) <= 2):
				if (method == 1):
					print("To evaluate statistical significance ");
					print("specify .py <method> <data file name >");
					print("<optional 3rd param: evaluate_gpuset_data=1/0>");
					print("default is set to 0");
					exit(-2);
				else:
					print("To prepare the model: ");
					print("specify .py <method> <data file name >");
					print("<optional 3rd param: model type=1/2/3/4/5>");
					print("1: P = Bf*Dp + Bf*Es + F(num_gpu_sets-1) + G");
					print("2: P = Bf+Dp+Es+Bf*Dp+Bf*Es+F(num_gpu_sets-1)+G");
					print("3: P = Bf + F(num_gpu_sets-1) + G");
					print("4: P = Bf + Dp + Es + F(num_gpu_sets-1) + G"); 
					print("5: P = Bf+C(l-1)+Dp+Es+F(num_gpu_sets-1)+G");
					print("6: P = Bf+C(p+s)+D");
					print("7: P = Af^3+F(num_gpu_sets-1)+G");
					print("8: P = Af^3+B(p+s)+C(num_gpu_sets-1)+D");
					print("default model type is 1");
					print("<optional 4th param: number of folds in validation (groups):");
					print("1 - 20> default: 3");
					exit(-2);
			else:
				data_file = sys.argv[2];

			# set default num_groups value
			if (method == 2):
				# validation_set_ratio = 0.2; # for a 80:20 split
				# validation_set_ratio = 0.25; # for a 75:25 split of 4 different workload data
								# namely GICOV, srad_v1_k4, sobolQRNG_k1 and backprop_k1
				# validation_set_ratio = 0.33; # for a 66:33 split of 3 different workload data
								# namely srad_v1_k4, sobolQRNG_k1 and backprop_k1
				num_groups = 3; # equivalent to validation_set_ratio = 0.33
				# validation_set_ratio = 0.25; # for a 75:25 split of 3 different workload data
								# namely srad_v1_k4, sobolQRNG_k1 and backprop_k1. 

			# The 3rd (optional) parameter if set to 1
			# implies that gpuset data is to be evaluated: default = 0
			# For method = 2, the optional parameter selects the model type.
			if (len(sys.argv) >= 4):
				if (method == 1): # evaluate statistical significance
					if (int(sys.argv[3]) == 1):
						evaluate_gpuset_data = 1;
					elif (int(sys.argv[3]) == 2):
						evaluate_energy_fanspeed_data = 1;
					elif (int(sys.argv[3]) == 3):
						evaluate_temp_fanspeed_data = 1;
				else: # prepare model (method = 2)
					modeltype = int(sys.argv[3]);

			# for method = 2, the next optional parameter sets the num_groups
			if (len(sys.argv) == 5):
				if (method == 2):
					num_groups = int(sys.argv[4]);
					if ((num_groups > 20) or \
						(num_groups < 2)):
						print("num_groups: allowed range: 1-20");
						exit(-4);

			if (method == 2):
				print("debug: set number of groups to ",num_groups);

			if (method == 1):
				if (evaluate_energy_fanspeed_data == 1):
					measured_power,measured_runtime,measured_energy,\
					core_freq,fan_speed = get_data_from_file(data_file,\
								method);
				elif (evaluate_temp_fanspeed_data == 1):
					measured_temp,core_freq,fan_speed = \
						get_data_from_file(data_file,method);
				else:
					measured_power,core_freq,active_lane_count_minus1,\
					active_primary_PB_count,active_non_primary_PB_count,\
					num_GPU_sets_minus1 = get_data_from_file(data_file,method);
	
			# 72 data points: tab 'INT_ADD_100-1-32_16_4_8_12_20_24_28_constp-deg6-models'
			if (method == 1):
				if (evaluate_energy_fanspeed_data == 1):
					get_significance_energy_temp(\
					measured_energy, core_freq, fan_speed, measured_power, \
					measured_runtime);
				elif (evaluate_temp_fanspeed_data == 1):
					get_significance_energy_temp(measured_temp, core_freq, fan_speed\
					, measured_power, measured_runtime);
				else:
					get_significance(measured_power, core_freq, \
					active_lane_count_minus1, active_primary_PB_count,\
					active_non_primary_PB_count, num_GPU_sets_minus1);	

			# get_coeffs_gpusets(core_freq,active_lane_count_minus1,active_primary_PB_count,\
            		#    active_non_primary_PB_count,measured_power,num_GPU_sets_minus1,7,\
			#	deg6_num_points,deg6_model_indices,val_by_unique_freq);

			elif (method == 2):
				# use entire dataset for model and validation
				get_linear_regr_model(measured_power, core_freq, active_lane_count_minus1, \
				active_primary_PB_count, active_non_primary_PB_count, num_GPU_sets_minus1);
				print("\n\n");

				# num_groups = int(1/validation_set_ratio);
				all_groups = split_dataset(len(measured_power), num_groups);

				get_linear_regr_model(measured_power, core_freq, active_lane_count_minus1, \
				active_primary_PB_count, active_non_primary_PB_count, num_GPU_sets_minus1,\
				# all_groups,1); # Set the last parameter to 1/ 2 to select the model type.
				all_groups,modeltype);
		else:
			print("Only methods 1/2 supported. .. exiting");
			exit(1);

