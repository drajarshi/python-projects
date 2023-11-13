__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2022 Rajarshi Das"

# v1 of the script uses Polynomial.fit in order to get the coefficients.
# The second version solves a linear equation Ax = B with A containing 
# the 3rd order, 1st order and constant (1) values w.r.t. frequency,
# and B containing the measured power. x is the set of coefficients 
# which we obtain using np.linalg.
# Invoke as : 
# 1. python <.py>  # this will require the core_freq and measured_power lists hardcoded
# 2. python <.py> 2 [core_freq_list] [measured_power_list] # will invoke the linear equation solver
# 3. python <.py> 1 [core_freq_list] [measured_power_list] # 1 is the method type and will
# invoke the Polynomial fit code.
# 4. python <.py> 3 [core_freq_list] [measured_power_list] <const_power> # model static power. 
# If <const_power> is not supplied, it is assumed. Previous options model const power.
# 5. python <.py> 4 [lane_count_list] [measured_power_list] # model static power as a function
# of lane count. This is per freq. For this ensure that a measured_power_list is provided for 
# a specific frequency.
# 6. python <.py> 5 [core_freq_list] [measured_power_list] <const_power> # model static power.
# Same as option 3 above, except that it models p = Af^3 + Bf, whereas option 5 models p = Af^3 + B
# 7. python <.py> 6 [lane count list] [measured/target power list] # model static power variability
# using a sinusoidal fn. y = A*sin(Bx)
# 8. python <.py> 7 [core_freq_list] [measured_power_list] <const_power> # model static power.
# The modeled equation is p = Afcore^3 + Bf + C(fmem^3 + fmem). if fmem is fixed, the C term
# is fixed throughout. This generates one model per lane count.
# 9. python <.py> 8 [core_freq_list] [measured_power_list] <const_power> # model static power.
# From the measured power list, isolate one entry. Get the lowest RMSE and lowest_MAPE from the other data. 
# repeat this for all the data points in the measured power list. Get 2 models per frequency.
# Models p = Af^3 + Bf : same as eqn 3. This option is useful to get all the models per lane count (2
# per frequency) where the measured power has entries for all frequencies.
# 10. python <.py> 9 [n x n input A matrix] [n x 1 output B vector]. Solve Ax = B
# 11. python <.py> 10 [core_freq_list] [active_lane_count_list] [active_PB_list] [measured_power_list]
# Models the measured power as P = Af^3 + Bf + C*active_lanes + D*inactive_lanes + E*active_PB +
# F*inactive_PB. A,C and E correspond to dynamic power, while B, D and F correspond to static power.
# 12. python <.py> 11 [core_freq_list] [active_lane_count_list]  [active_primary_PB_list] 
# [active_non-primary_PB_list] [measured_power_list]
# Models the measured power as P = Af^3 + Bf + C*(active_lanes-1) + D*active_primary_PB +
# E*active_non-primary_PB. A,B corresponds to frequency specific dynamic and static power. C corresponds
# to active lane count (other than lane 1) specific dynamic and static power. D corresponds to
# lane 1's static and dynamic power for every active primary PB. E corresponds to the same power for every
# non primary PB that is active.
# 13. python <.py> 12 [non-primary PB count list] [measured_power list]. This assumes a fixed core 
# frequency, fixed lane count, and fixed number of primary PB. Models the power as ax^2+bx+c as a function
# of the number of non-primary PB.
# 14. python <.py> 13 [core_freq_list] [active_lane_count_list]  [active_primary_PB_list]
# [active_non-primary_PB_list] [measured_power_list]
# Models the measured power as P = Af^3 + Bf + C*(active_lanes-1) + D*active_primary_PB +
# E*active_non-primary_PB + F. A,B corresponds to frequency specific dynamic and static power. C corresponds
# to active lane count (other than lane 1) specific dynamic and static power. D corresponds to
# lane 1's static and dynamic power for every active primary PB. E corresponds to the same power for every
# non primary PB that is active, and F is the constant power.
# 15. python <.py> 14 [data file name]. The specified file contains [measured power] [core frequency] 
# [active_lane_count] [active_primary_PB] [active_non_primary_PB].  Identifies unique core frequencies
# for the model and validates against the other core frequencies. Models power as option 13 above.
# 16. python <.py> 15 [data file name] <validate_by_unique_freq>. The specified file contains [measured power] 
# [core_frequency] [active_lane_count]. Models as P = Af^3 + Bf + C(l-1) + D. Specify python <.py> 15 [filename]
# 1 to validate with data points whose frequency is different from the ones used for the model. A value of
# 0 validates against data points whose frequency may be same as the model data (but the data point itself
# is different). A value of 0 makes sense if there are other independent variables apart from frequency.
# The value of 0 is the default for option 15 (assumed if not specified).
# 17. python <.py> 16 [data file name]. Models constant power as option 2 above: P = AF^3 + Bf + C
# 18. python <.py> 17 [data file name]. Models total power as y = mx + c, where 'c' is the lumped power component
# corresponding to 596 TB and x is the extra_TB used above 596 (default). Applies to GICOV kernel. 
# 19. python <.py> 18 [data file name]. Models total power as y = mx + c, where 'c' is the lumped power as option
# 17 above and x represents num_gpu_repetitions_for_TB, i.e. the number of times we need to iterate to complete the 
# specified TB count once, e.g. with 596 TB, we need to iterate over 20 SMs 30 times. Applies to GICOV.
# 20. python <.py> 19 [data file name]. The specified file contains [measured power] [core frequency]
# [active_lane_count] [active_primary_PB_final_set] [active_non_primary_PB_final_set] [num_GPU_sets -1] 
# [deg6_num_data_points] and [deg6_model_indices]. The num_GPU_sets refers to the number : ceil((num_TB/20)).
# E.g. if num_TB = 40, num_GPU_sets = 2. If num_TB = 55, num_GPU_sets=3.
# Also, the active_primary_PB and active_non_primary_PB are for the final GPU set. This option models total
# power as P = Af^3 + Bf + C*(active_lanes-1) + D*active_primary_PB_final_set + E*active_non-primary_PB_final_set 
# + F*(num_GPU_sets-1) + G. This option is introduced to handle cases with TB count > max PB on the GPU. The 
# purpose of the deg6* data is to select non-deg6 specific data points for the model. This option assumes that
# a deg6 model is already available. Also, set 'gpuset_model_new_data_points' in get_coeffs_gpusets() routine
# to an appropriate value (< 7) to indicate the number of data points to use from the gpuset new data.
# The remaining (7 - this number) is taken from the deg6 model data (existing).
# Further, set 'validate_gpuset_data_only = 1' in get_coeffs_gpusets() routine if we need to validate
# the generated model against data points from the new gpuset data only (and none from the previous ones
# used while validating the deg6 model).
# 21. python <.py> 20 [data file name]. Same as option 14 except that the model is P = Bf + D(p+s) + F

import numpy as np
import pandas as pd
from itertools import combinations
import sys
from scipy import optimize

LINEAR=1
NON_LINEAR=2
STATIC_FIXED_PER_LANE_COUNT=3

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

# model Ax = B  e.g. as A11*x1 + A12*x2 + A13*x3 + A14*x4 = B11 where there
# are 4 unknowns. Similarly for A21..A44.
def get_coeffs8(A,B):
	A_data = [];
	B_data = [];

	num_unknowns = len(B);

	if (num_unknowns != len(A)):
		print("The input matrix data size does not match the output\
			vector size. Exiting");
		exit(-1);

	for i in range(len(A)):
		A_row = [];
		for j in range(len(A[i])):
			A_row.append(A[i][j]);
		A_data.append(A_row);
	
	for i in range(len(B)):
		B_data.append(B[i]);		

	print("A_data: ",A_data);
	print("B_data: ",B_data);

	x = np.linalg.solve(np.array(A_data),np.array(B_data));

	print("A: ",A);
	print("B: ",B);
	print("number of unknowns: ",num_unknowns);
	print("coefficients: ",x);	

# used in get_coeffs12 (option 14 or 15)
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
		elif (var == 'core_frequency'):
			core_freq = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				core_freq.append(float(values[i])*1e6);
			print("debug: ",core_freq);
		elif (var == 'active_lanes'):
			active_lane_count_minus1 = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_lane_count_minus1.append(int(values[i])-1);
			print("debug: ",active_lane_count_minus1);
		elif (var == 'active_primary_PB'):
			active_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_primary_PB.append(int(values[i]));
			print("debug: ",active_primary_PB);
		elif (var == 'active_non_primary_PB'):
			active_non_primary_PB = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				active_non_primary_PB.append(int(values[i]));
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
		elif (var == 'GPU_sets'):
			num_GPU_sets_minus1 = [];
			values = value.split(',');
			values[0] = values[0].split('[')[1];
			values[len(values)-1] = values[len(values)-1].split(']')[0];

			for i in range(len(values)):
				num_GPU_sets_minus1.append(int(values[i])-1);
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

	if ((option == 14) or (option == 20)):
		return measured_power,core_freq,active_lane_count_minus1,active_primary_PB,\
		active_non_primary_PB;
	elif (option == 15): # option = 15
		return measured_power,core_freq,active_lane_count_minus1;
	elif (option == 17): # option = 17
		return measured_power,extra_TB;
	elif (option == 18): # option = 18
		return measured_power,num_gpu_repetitions_for_TB;
	elif (option == 19): # deg 7. option = 19
		return measured_power,core_freq,active_lane_count_minus1,active_primary_PB,\
		active_non_primary_PB,num_GPU_sets_minus1,deg6_num_data_points,deg6_model_indices;
	else: # option = 16
		return measured_power,core_freq;

#def validate_model(model_coeffs,core_freq,measured_power,validation_list,\
#					num_unknown_coeffs,model_type=NON_LINEAR,active_lanes=[],\
#					active_primary_PB=[],active_non_primary_PB=[]):
def validate_model(model_coeffs,core_freq,measured_power,validation_list,\
					num_unknown_coeffs,model_type=NON_LINEAR,active_lanes_minus1=[],\
					active_primary_PB=[],active_non_primary_PB=[],\
					num_GPU_sets_minus1=[]):
	estimated_power = [];
	ape = [];
	diff_squared = [];

	for i in range(len(validation_list)):
		if (validation_list[i] == 1): # freq avl for validation
			if (model_type==LINEAR): # y=mx+c 
				if (num_unknown_coeffs == 2):
					est_pow = core_freq[i]*model_coeffs[0] +\
								model_coeffs[1];
				elif (num_unknown_coeffs == 3):
					est_pow = core_freq[i]*model_coeffs[0] +\
					 (active_primary_PB[i]+active_non_primary_PB[i])*\
						model_coeffs[1] + model_coeffs[2];
				else:
					print("unsupported linear type model. exiting..\n");
					exit(-1);

			else:
				if (num_unknown_coeffs == 7): # Af^3 + Bf + C(l-1) + D(pri_PB) +
											  # E(non_pri_PB) + F(num_GPU_sets-1) +
											  # G
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							core_freq[i]*model_coeffs[1] +\
							active_lanes_minus1[i]*model_coeffs[2] +\
							active_primary_PB[i]*model_coeffs[3] +\
							active_non_primary_PB[i]*model_coeffs[4] +\
							num_GPU_sets_minus1[i]*model_coeffs[5] +\
							model_coeffs[6];
				elif (num_unknown_coeffs == 6): # Af^3 + Bf + C(l-1) + D(pri_PB) +
											  # E(non_pri_PB) + F
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							core_freq[i]*model_coeffs[1] +\
							active_lanes_minus1[i]*model_coeffs[2] +\
							active_primary_PB[i]*model_coeffs[3] +\
							active_non_primary_PB[i]*model_coeffs[4] +\
							model_coeffs[5];
				elif (num_unknown_coeffs == 4): # Af^3 + Bf + C(l-1)+ D
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							core_freq[i]*model_coeffs[1] +\
							active_lanes_minus1[i]*model_coeffs[2] + \
							model_coeffs[3];
				elif (num_unknown_coeffs == 3): # Af^3 + Bf + C
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							core_freq[i]*model_coeffs[1] +\
							model_coeffs[2];
				elif ((model_type == STATIC_FIXED_PER_LANE_COUNT) and \
						(num_unknown_coeffs == 2)): # Af^3 + B
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							model_coeffs[1];
				elif (num_unknown_coeffs == 2): # Af^3 + Bf
					est_pow = pow(core_freq[i],3)*model_coeffs[0] + \
							core_freq[i]*model_coeffs[1];
				else:
					print("error: unsupported number of coeffs.. exiting.");
					exit(-2);

			estimated_power.append(est_pow);
		else:
			estimated_power.append(0);

	for i in range(len(measured_power)):
		if (estimated_power[i] != 0):
			diff = estimated_power[i] - measured_power[i];
			abs_percent_error =  abs((float)(diff/measured_power[i])*100.0);
			ape.append(abs_percent_error);
			
			diff_squared.append(pow(diff,2));

	rmse = np.sqrt(np.average(diff_squared));
	#rmse = np.sqrt(np.average(pow((np.array(estimated_power)-np.array(measured_power)),2)));

	print("MAPE: ",np.average(ape));
	print("rmse: ",rmse);
	print("estimated power: ",estimated_power);
	print("measured power: ",measured_power);

	return (np.average(ape),rmse);

def get_lowest_mape_and_rmse(results):

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

# P = Af^3 + Bf + C*(active_lane_count-1) + D*active_primary_PB
# + E*active_non_primary_PB + F*(num_GPU_sets-1) + G [option 19] for
# the INT_ADD/INT_STATIC ubenchmark.
# val_by_unique_freq = 0: implies use all data points other than the ones used
# for building the model (including similar frequency as the model
# data points). A value of 1 implies use only data points with frequency
# values other than the ones used to build the model (fewer validation
# points).
# Used by option 19. The data indices for the best (deg 6) model from option 14
# are fixed and modelled along with each of the additional data points for 
# TB > 20. The resulting model is validated against the other data points
# and the best model selected.
def get_coeffs_gpusets(core_freq,active_lane_count_minus1,active_primary_PB,\
         active_non_primary_PB,measured_power,num_GPU_sets_minus1,deg_of_poly,\
		 deg6_num_data_points,deg6_model_indices,val_by_unique_freq):

	gpuset_model_new_data_points = 2; # b/w index 72 and 80 # set this as desired.
	deg6_model_num_points = 7 - gpuset_model_new_data_points # use fewer data 
								# points from the deg6 model

	validate_gpuset_data_only = 1; # consider validation data points in the 
								   # new gpu set data only

	if (deg_of_poly != 7):
		print("unsupported degree ",deg_of_poly," of polynomial. Try 7!\n");
		exit(-1);

	print("debug: deg6 num points: ",deg6_num_data_points, " model: ",\
			deg6_model_indices);

	# 1/7 points to be selected from the data indexed 72:80 
	# tab 'INT_ADD_100-1-32_16_4_8_12_20_24_28_constp-deg7_incl-GPU-sets-models'
	#### new start
	list_deg6_combinations = combinations(range(6),deg6_model_num_points);

	results = [];

	for comb in list(list_deg6_combinations):
		# check that we do not have the same frequency more than once in the combination
		freq_list = [];
		index_list = [];
		skip_combination = 0;
		A = [];
		B = [];

		print("debug: existing deg6 model. comb: ",comb); # debug
		for i in range(deg6_model_num_points):
			idx = deg6_model_indices[comb[i]];
			if core_freq[idx] in freq_list:
				print("frequency: ",core_freq[idx]," more than once.. skip");
				skip_combination = 1;
				break;
			else:
				freq_list.append(core_freq[idx]);
				index_list.append(idx);
				A_row = [];
				A_row.append(pow(core_freq[idx],3)); #f^3
				A_row.append(core_freq[idx]); #f^1
				A_row.append(active_lane_count_minus1[idx]);
				A_row.append(active_primary_PB[idx]);
				A_row.append(active_non_primary_PB[idx]);
				A_row.append(num_GPU_sets_minus1[idx]); # new for deg 7
				A_row.append(1);

				A.append(A_row);
				B.append(measured_power[idx]);

		if (skip_combination):
			continue;

		print("debug: after existing index addition: ");
		print("debug: index_list: ",index_list);
		print("debug: A: ",A);
		print("debug: B: ",B);
		print("debug: freq_list: ",freq_list);

		list_deg7_new_combinations = combinations(range(len(measured_power)-\
						deg6_num_data_points),gpuset_model_new_data_points);

		for comb7 in list(list_deg7_new_combinations):
		# check that we do not have the same frequency more than once in the combination
			skip_combination7 = 0;

			print("debug: comb7: ",comb7); # debug
			for i in range(gpuset_model_new_data_points):
				idx = deg6_num_data_points+comb7[i];
				if core_freq[idx] in freq_list:
					print("frequency: ",core_freq[idx]," more than once.. skip");
					skip_combination7 = 1;
					break;
				else:
					freq_list.append(core_freq[idx]);
					index_list.append(idx);
					A_row = [];
					A_row.append(pow(core_freq[idx],3)); #f^3
					A_row.append(core_freq[idx]); #f^1
					A_row.append(active_lane_count_minus1[idx]);
					A_row.append(active_primary_PB[idx]);
					A_row.append(active_non_primary_PB[idx]);
					A_row.append(num_GPU_sets_minus1[idx]); # new for deg 7
					A_row.append(1);

					A.append(A_row);
					B.append(measured_power[idx]);

			if (skip_combination7):
				continue;

	### new end

	# the following commented code is optimized for using all 6 model points from
	# the deg6 best MAPE model and 1 data point from the new gpuset specific data points
	# the above nested combinations code handles this case as well.
	#results = [];

	#freq_list = [];
	#index_list = [];

	#A = [];
	#B = [];
	
	# add the existing indices first
	#for i in range(len(deg6_model_indices)):
	#	freq_list.append(core_freq[deg6_model_indices[i]]);
	#	index_list.append(deg6_model_indices[i]);
	#	A_row = [];
	#	A_row.append(pow(core_freq[deg6_model_indices[i]],3)); #f^3
	#	A_row.append(core_freq[deg6_model_indices[i]]); #f^1
	#	A_row.append(active_lane_count_minus1[deg6_model_indices[i]]);
	#	A_row.append(active_primary_PB[deg6_model_indices[i]]);
	#	A_row.append(active_non_primary_PB[deg6_model_indices[i]]);
	#	A_row.append(num_GPU_sets_minus1[deg6_model_indices[i]]); # new for deg 7
	#	A_row.append(1);

	#	A.append(A_row);
	#	B.append(measured_power[deg6_model_indices[i]]);

	#print("debug: after existing index addition: ");
	#print("debug: index_list: ",index_list);
	#print("debug: A: ",A);
	#print("debug: B: ",B);
	#print("debug: freq_list: ",freq_list);
#
	# repeat the model and validation for each of the 'deg 7' data points
	#for idx in range(len(measured_power)-deg6_num_data_points):
	#	if core_freq[deg6_num_data_points+idx] in freq_list:
	#		continue;
	#	freq_list.append(core_freq[deg6_num_data_points+idx]);
	#	index_list.append(deg6_num_data_points+idx);
#
	#	A_row = [];
	#	A_row.append(pow(core_freq[deg6_num_data_points+idx],3)); #f^3
	#	A_row.append(core_freq[deg6_num_data_points+idx]); #f^1
	#	A_row.append(active_lane_count_minus1[deg6_num_data_points+idx]);
	#	A_row.append(active_primary_PB[deg6_num_data_points+idx]);
	#	A_row.append(active_non_primary_PB[deg6_num_data_points+idx]);
	#	A_row.append(num_GPU_sets_minus1[deg6_num_data_points+idx]); # new for deg 7
	#	A_row.append(1);

	#	A.append(A_row);
	#	B.append(measured_power[deg6_num_data_points+idx]);

			val_freq_list = [1]*len(core_freq); # validation list of frequencies
			# solve Ax = B: B is the measured power

			# since we want to validate with data in the new gpuset data, 
			# mask out all previous indices
			if (validate_gpuset_data_only == 1):
				for l in range(len(core_freq)):
					if (l < deg6_num_data_points):
						val_freq_list[l] = 0;

			for k in range(len(index_list)):
			# set '0' for each occurrence of the validation frequency
				for j in range(len(core_freq)):
					if (val_by_unique_freq == 1):
						if (((j == index_list[k]) or (core_freq[j] == core_freq[index_list[k]]))\
							and (val_freq_list[j] == 1)):
							val_freq_list[j] = 0; # freq used for the model.
					# do not break since subsequent data points can also match
					else: # val_by_unique_freq = 0. Use all data points other than the model 
						if ((j == index_list[k]) and (val_freq_list[j] == 1)):
							val_freq_list[j] = 0;
							break; # since there's only one data point that will match

			print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation
			print("debug: final index_list: ",index_list);
			print("debug: final A: ",A);
			print("debug: final B: ",B);	

				# https://stackoverflow.com/questions/9155478/how-to-try-except-an-illegal-matrix-operation-due-to-singularity-in-numpy
			try:
				x = np.linalg.solve(np.array(A),np.array(B));
			except np.linalg.LinAlgError as err:
				print("Singular Matrix.. skip and continue");
				continue;
	
			print("A: ",np.array(A), "B: ",np.array(B));
			print("x: ",x);

			mape,rmse = validate_model(x,core_freq,measured_power,val_freq_list\
									,deg_of_poly,NON_LINEAR,active_lane_count_minus1,\
									active_primary_PB,active_non_primary_PB,\
									num_GPU_sets_minus1);
			result = [];
			result.append(x);
			result.append(mape);
			result.append(rmse);
			result.append(val_freq_list);
			results.append(result);

		# need to remove all new added elements for the current combination
		# so that we can then add for the next.
			for l in range(gpuset_model_new_data_points):
				A.remove(A[-1]);
				B.remove(B[-1]);
				freq_list.remove(freq_list[-1]);
				index_list.remove(index_list[-1]);

		# remove the last entries since we choose a new element next
		# specific to the optimized case of all elements from deg6 model and 1 from
		# new gpuset data points
		# freq_list.remove(freq_list[-1]);
		# index_list.remove(index_list[-1]);
		# A.remove(A[-1]);
		# B.remove(B[-1]);

	get_lowest_mape_and_rmse(results);	

# model constant power. Derived from get_coeffs2() with modifications
# P = Af^3 + Bf + C*(active_lane_count-1) + D*active_primary_PB
# + E*active_non_primary_PB + F [option 14] OR
# model power as P = Af^3 + Bf + C*(active_lane_count-1) + D, where 
# P is the total measured power for a kernel such as GICOV [option 15]
# or P = Bf + D(p+s) + F [option 20].
# val_by_unique_freq = 0: implies use all data points other than the ones used
# for building the model (including similar frequency as the model
# data points). A value of 1 implies use only data points with frequency
# values other than the ones used to build the model (fewer validation
# points).
def get_coeffs12(core_freq,active_lane_count_minus1,active_primary_PB,\
                active_non_primary_PB,measured_power,deg_of_poly,\
				val_by_unique_freq):
	#deg_of_poly = 6;

	if ((deg_of_poly != 6) and (deg_of_poly != 4) and (deg_of_poly != 3)):
		print("unsupported degree ",deg_of_poly," of polynomial. Try 3 or 4 or 6!\n");
		exit(-1);

	print("debug: total count of entries: ",len(measured_power));

	list_combinations = combinations(range(len(measured_power)),deg_of_poly);

	results = [];

	for comb in list(list_combinations):
		# check that we do not have the same frequency more than once in the combination
		freq_list = [];
		skip_combination = 0;

		print("debug: ",comb); # debug
		for i in range(deg_of_poly):
			if core_freq[comb[i]] in freq_list:
				print("frequency: ",core_freq[comb[i]]," more than once.. skip");
				skip_combination = 1;
				break;
			else:
				freq_list.append(core_freq[comb[i]]);

		if (skip_combination):
			continue;
			
		val_freq_list = [1]*len(core_freq); # validation list of frequencies
		#print(combination[2]);
		# solve Ax = B: B is the measured power
		A = [];
		B = [];
		for i in range(deg_of_poly):
			B.append(measured_power[comb[i]]);

			print("debug: comb[i]: ",comb[i]);
			A_row = [];
			if (deg_of_poly == 6):
					A_row.append(pow(core_freq[comb[i]],3)); #f^3
					A_row.append(core_freq[comb[i]]); #f^1
					A_row.append(active_lane_count_minus1[comb[i]]);
					A_row.append(active_primary_PB[comb[i]]);
					A_row.append(active_non_primary_PB[comb[i]]);
					A_row.append(1);
			elif (deg_of_poly == 3): # P = Bf + D(p+s) + F
					A_row.append(core_freq[comb[i]]); #f^1
					A_row.append(active_primary_PB[comb[i]] + \
						active_non_primary_PB[comb[i]]); # p + s
					A_row.append(1);
			else: # degree = 4
					A_row.append(pow(core_freq[comb[i]],3)); #f^3
					A_row.append(core_freq[comb[i]]); #f^1
					A_row.append(active_lane_count_minus1[comb[i]]);
					A_row.append(1);

			A.append(A_row);

			for j in range(len(core_freq)):
			# set '0' for each occurrence of the validation frequency
				if (val_by_unique_freq == 1):
					if (((j == comb[i]) or (core_freq[j] == core_freq[comb[i]]))\
							and (val_freq_list[j] == 1)):
						val_freq_list[j] = 0; # freq used for the model.
						# do not break since subsequent data points can also match
				else: # val_by_unique_freq = 0. Use all data points other than the model 
					if ((j == comb[i]) and (val_freq_list[j] == 1)):
						val_freq_list[j] = 0;
						break; # since there's only one data point that will match

		print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation

		# https://stackoverflow.com/questions/9155478/how-to-try-except-an-illegal-matrix-operation-due-to-singularity-in-numpy
		try:
			x = np.linalg.solve(np.array(A),np.array(B));
		except np.linalg.LinAlgError as err:
			print("Singular Matrix.. skip and continue");
			continue;
	
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		if (deg_of_poly == 3): # P = Bf + D(p+s) + F
			mape,rmse = validate_model(x,core_freq,measured_power,val_freq_list\
					,deg_of_poly,LINEAR,active_lane_count_minus1,\
					active_primary_PB,active_non_primary_PB);
		else:
			mape,rmse = validate_model(x,core_freq,measured_power,val_freq_list\
					,deg_of_poly,NON_LINEAR,active_lane_count_minus1,\
					active_primary_PB,active_non_primary_PB);

		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	get_lowest_mape_and_rmse(results);	

# model P = Ax^2 + Bx + C where x is the number of non-primary PB. This assumes that the data
# is for a fixed core frequency, fixed lane count, and fixed number of primary PB.
def get_coeffs11(active_non_primary_PB,measured_power,const_p):
	A = [];
	B = [];

	for i in range(len(measured_power)):
		A_row = [];

		A_row.append(pow(active_non_primary_PB[i],2));
		A_row.append(active_non_primary_PB[i]);
		A_row.append(1); 

		A.append(A_row);

		meas_power = measured_power[i] - const_p;
		B.append(meas_power);

	x = np.linalg.solve(np.array(A),np.array(B));
	print("A: ",np.array(A), "B: ",np.array(B));
	print("x: ",x);

# model P = Af^3 + Bf + C*(active_lane_count-1) + D*active_primary_PB
# + E*active_non_primary_PB
# if model_cp == 1 [model_constant_power == 1]
# then P = Af^3 + Bf + C*(active_lane_count-1) + D*active_primary_PB
# + E*active_non_primary_PB + F where F is the constant power
def get_coeffs10(core_freq,active_lane_count_minus1,active_primary_PB,\
				active_non_primary_PB,measured_power,const_p,model_cp=0):
	A = [];
	B = [];

	for i in range(len(measured_power)):
		A_row = [];

		A_row.append(pow(core_freq[i],3));
		A_row.append(core_freq[i]);
		A_row.append(active_lane_count_minus1[i]);
		A_row.append(active_primary_PB[i]);
		A_row.append(active_non_primary_PB[i]);
		if (model_cp == 1):
			A_row.append(1);

		A.append(A_row);
	
		if (model_cp == 1):
			meas_power = measured_power[i];
		else:	
			meas_power = measured_power[i] - const_power;

		B.append(meas_power);

	x = np.linalg.solve(np.array(A),np.array(B));
	print("A: ",np.array(A), "B: ",np.array(B));
	print("x: ",x);

# model P = Af^3 + Bf + C*active_lane_count + D*inactive_lane_count + 
# E*active_PB + F*inactive_PB
def get_coeffs9(core_freq,active_lane_count,active_PB,measured_power,\
				const_p):
	total_lanes = 32;
	total_PB = 20;

	A = [];
	B = [];

	for i in range(len(measured_power)):
		A_row = [];

		A_row.append(pow(core_freq[i],3));
		A_row.append(core_freq[i]);
		A_row.append(active_lane_count[i]);
		A_row.append(total_lanes - active_lane_count[i]);
		A_row.append(active_PB[i]);
		A_row.append(total_PB - active_PB[i]);

		A.append(A_row);
		
		meas_power = measured_power[i] - const_power;
		B.append(meas_power);

	x = np.linalg.solve(np.array(A),np.array(B));
	print("A: ",np.array(A), "B: ",np.array(B));
	print("x: ",x);

# model dyn_static_p = Afcore^3 + Bfcore + C(fmem^3 + fmem) # fmem is fixed
def get_coeffs7(core_freq,measured_power,const_p,num_unknown_coeffs=3,\
				mem_freq=5005e6):

	meas_power = 0;
	list_combinations = combinations(range(len(measured_power)),num_unknown_coeffs);
	print(list_combinations);

	results = [];

	for comb in list(list_combinations):
		val_freq_list = [1]*len(core_freq); # validation list of frequencies
		#print(combination[2]);
		# solve Ax = B: B is the measured power
		A = [];
		B = [];
		for i in range(num_unknown_coeffs):
			meas_power = measured_power[comb[i]] - const_power; # keep the f^3 and f terms
			B.append(meas_power);

			A_row = [];
			A_row.append(pow(core_freq[comb[i]],3)); #f^3
			A_row.append(core_freq[comb[i]]); #f^1
			A_row.append(pow(mem_freq,3)+mem_freq); #fmem^3+fmem^1

			A.append(A_row);

			for j in range(len(core_freq)):
				if ((j == comb[i]) and (val_freq_list[j] == 1)):
					val_freq_list[j] = 0; # freq used for the model. 
					break;
				
		print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation

		x = np.linalg.solve(np.array(A),np.array(B));
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		corrected_meas_power = []; # without const power

		for i in range(len(measured_power)):
			corrected_meas_power.append(measured_power[i] - const_power);

		mape,rmse = validate_model(x,core_freq,corrected_meas_power,val_freq_list\
									,num_unknown_coeffs);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	lowest_mape = abs(results[0][1]); # set the 1st combination's mape as reference.
	lowest_rmse = abs(results[0][2]); # set the 1st combination's rmse as reference.

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

# for modeling static power over lane counts at a fixed frequency. Sinusoidal curve.
# y = a*sin(bx)
# credit: https://scipy-lectures.org/intro/scipy/auto_examples/plot_curve_fit.html
def model_fn_coeffs6(x,A,B):
	y = A * np.sin(B*x); 
	return y;

def get_coeffs6(lane_counts, target_power):

	p,p_cov = optimize.curve_fit(model_fn_coeffs6,lane_counts,target_power);
	print("coeffs: A: ",p[0]," B: ",p[1]);
	
	return 0;

# for static power. dyn_static_p = Af^3 + B # B is static power and constant per lane count
def get_coeffs5(core_freq,measured_power,const_p): # A is dyn power coefficient
	meas_power = 0;
	list_combinations = combinations(range(len(measured_power)),2); # A and B are unknowns
	print(list_combinations);
	results = [];

	for comb in list(list_combinations):
		val_freq_list = [1]*len(core_freq); # validation list of frequencies
		#print(combination[2]);
		# solve Ax = B: B is the measured power 
		A = [];
		B = [];
		for i in range(2):
			meas_power = measured_power[comb[i]] - const_p;
			B.append(meas_power);

			A_row = [];
			A_row.append(pow(core_freq[comb[i]],3)); #f^3
			A_row.append(1); # for constant term

			A.append(A_row);

			for j in range(len(core_freq)):
				if ((j == comb[i]) and (val_freq_list[j] == 1)):
					val_freq_list[j] = 0; # freq used for the model. 
					break;
				
		print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation

		x = np.linalg.solve(np.array(A),np.array(B));
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		corrected_meas_power = []; # without const power

		for i in range(len(measured_power)):
			corrected_meas_power.append(measured_power[i] - const_p);

		mape,rmse = validate_model(x,core_freq,corrected_meas_power,val_freq_list\
									,num_unknown_coeffs,STATIC_FIXED_PER_LANE_COUNT);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	lowest_mape = abs(results[0][1]); # set the 1st combination's mape as reference.
	lowest_rmse = abs(results[0][2]); # set the 1st combination's rmse as reference.

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

	

	return 0;

# At a fixed freq, Pdyn and Pconst are fixed. Therefore, the measured power should vary directly
# by lane count only (static power)
# For static power per freq [measured_power mapped by lane count]
def get_coeffs4_linear(lane_counts,measured_power,num_unknown_coeffs=2):
	meas_power = 0;
	list_combinations = combinations(range(len(lane_counts)),num_unknown_coeffs);
	print(list_combinations);
	results = [];

	for comb in list(list_combinations):
		val_lane_list = [1]*len(lane_counts); # validation list of lane counts
		# solve y = mx + c. y is measured power and x is lane count. m and c are unknowns

		A = [];
		B = [];

		dup_found = 0; # to check if the same measured power is used twice
		for i in range(num_unknown_coeffs):
			A_row  = [];
			
			if (len(A) > 0):
				# skip combinations with the same input twice
				# useful when we model num_GPU_repetitions against power
				# based on changing TB count
				for j in range(len(A)):
					if (A[j][0] == lane_counts[comb[i]]):
						dup_found = 1;
						break;
			A_row.append(lane_counts[comb[i]]);
			A_row.append(1); 

			A.append(A_row);

			if (len(B) > 0):
				for j in range(len(B)):
					if (B[j] == measured_power[comb[i]]):
						dup_found = 1;
						break;
			B.append(measured_power[comb[i]]);

			for j in range(len(lane_counts)):
			# check whether the element index matches or 
			# the value at the element index matches=> we should not
			# be validating with the same input that we built with, 
			# even though they are two separate data points.
				if (((j == comb[i]) or (lane_counts[j] == \
					lane_counts[comb[i]])) and (val_lane_list[j] == 1)):
					val_lane_list[j] = 0; # freq used for the model. 
					# break; # since multiple elements may match the 2nd
					# condition

		# if duplicate data found, skip this combination
		# and skip this combination.
		if (dup_found == 1):
				print("duplicate input variable or measured power found. skipping combination:",\
						comb);
				continue;
				
		print("validation list of lane counts: ",val_lane_list); # 1 implies lane count for 
																# validation

		x = np.linalg.solve(np.array(A),np.array(B));
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		mape,rmse = validate_model(x,lane_counts,measured_power,val_lane_list\
									,num_unknown_coeffs,LINEAR);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_lane_list);
		results.append(result);

	lowest_mape = abs(results[0][1]); # set the 1st combination's mape as reference.
	lowest_rmse = abs(results[0][2]); # set the 1st combination's rmse as reference.

	for i in range(len(results)):
		if (abs(results[i][1]) < lowest_mape):
			lowest_mape = abs(results[i][1]);
	for i in range(len(results)):
		if (abs(results[i][2]) < lowest_rmse):
			lowest_rmse = abs(results[i][2]);

	for res in results:
		if (lowest_mape == abs(res[1])):
			print("lowest mape: ",lowest_mape);
			print("validation lane list: ",res[3]);
			break;

	for res in results:
		if (lowest_rmse == res[2]):
			print("lowest rmse: ",lowest_rmse);
			print("validation lane list: ",res[3]);

# Given a list of data points for measured_power, mark one as the validation data
# and run get_coeffs3() over the remaining data points. Repeat this for all the
# data points.
def wrap_get_coeffs(core_freq,measured_power,num_unknown_coeffs,const_power,method=3):
	validation_index = -1;
	
	for i in range(len(measured_power)):
		train_meas_power = [];
		train_core_freq = [];
		validation_data = measured_power[i];
		validation_index = i;

		print("excluding index: ",validation_index);

		# prepare the list of training data excl the validation data
		for j in range(len(measured_power)):
			if (validation_index == j):
				continue;
			train_meas_power.append(measured_power[j]);
			train_core_freq.append(core_freq[j]);
		
		if (method == 3):
			print("validation frequency: ",core_freq[validation_index]\
				," MHz");
			get_coeffs3(train_core_freq,train_meas_power,num_unknown_coeffs,\
				const_power);

# For static power per lane count [measured power mapped by core_freq]
# P_static_and_dyn = Af^3 + Bf [both dyn and static component vary by frequency]
def get_coeffs3(core_freq,measured_power,num_unknown_coeffs,const_power):

	meas_power = 0;
	list_combinations = combinations(range(len(measured_power)),num_unknown_coeffs);
	print(list_combinations);

	print("debug RD. core_freq list: ",core_freq);
	print("debug RD. meas_power list: ",measured_power);

	results = [];

	for comb in list(list_combinations):
		val_freq_list = [1]*len(core_freq); # validation list of frequencies

		#print(combination[2]);
		# solve Ax = B: B is the measured power
		A = [];
		B = [];
		for i in range(num_unknown_coeffs):
			meas_power = measured_power[comb[i]] - const_power; # keep the f^3 and f terms
			B.append(meas_power);

			A_row = [];
			A_row.append(pow(core_freq[comb[i]],3)); #f^3
			A_row.append(core_freq[comb[i]]); #f^1

			A.append(A_row);

			for j in range(len(core_freq)):
				if ((j == comb[i]) and (val_freq_list[j] == 1)):
					val_freq_list[j] = 0; # freq used for the model. 
					break;
				
		#print("validation list of freq indices: ",val_freq_list); # 1 implies freq for validation

		x = np.linalg.solve(np.array(A),np.array(B));
		print("A: ",np.array(A), "B: ",np.array(B));
		print("x: ",x);

		corrected_meas_power = []; # without const power

		for i in range(len(measured_power)):
			corrected_meas_power.append(measured_power[i] - const_power);

		mape,rmse = validate_model(x,core_freq,corrected_meas_power,val_freq_list\
									,num_unknown_coeffs);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	lowest_mape = abs(results[0][1]); # set the 1st combination's mape as reference.
	lowest_rmse = abs(results[0][2]); # set the 1st combination's rmse as reference.

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

# credit: https://www.geeksforgeeks.org/permutation-and-combination-in-python/
# credit: https://stackoverflow.com/questions/3459098/create-list-of-single-item-repeated-n-times
# For const power.
def get_coeffs2(core_freq,measured_power,deg_of_poly=3):
	list_combinations = combinations(range(len(measured_power)),deg_of_poly);
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

		mape,rmse = validate_model(x,core_freq,measured_power,val_freq_list\
									,deg_of_poly);
		result = [];
		result.append(x);
		result.append(mape);
		result.append(rmse);
		result.append(val_freq_list);
		results.append(result);

	get_lowest_mape_and_rmse(results);	

if __name__ == "__main__":
#       core_freq = [139,278,417,556,607];
#        core_freq = [139e-3,278e-3,417e-3,556e-3,607e-3]; # in GHz
#        core_freq = [139e6,278e6,417e6,556e6,607e6]; # Hz
		core_freq = [139e6,278e6,417e6,556e6,607e6,696e6,797e6,898e6,999e6]; # Hz
		lane_counts = [1,4,8,12,16,20,24,28,32];  # for static power model per freq
#       measured_power = [19.6394202898551,20.282972972973,20.6770909090909,22.449375,22.7490909090909];
#       measured_power = [22.1232842410137,23.7798811423158,23.830277367614,29.5205741597036,30.3766110748561,32.0287801665763,33.986431347592,35.8388156452346,37.720811318817]; # GICOV
#       measured_power = [20.9055913230182,21.020133884283,21.028433542617,21.4059189906608,21.4562637975061,21.5599600704549,21.713204686488,21.9007672911003,22.0876557279796]; # INT_STATIC ubenchmark. 1 lane. steady state temp
#       measured_power = [20.913991507075,21.0317739655406,21.0726404619449,21.4968251827684,21.5057893158111,21.5988264025789,21.7946179694907,22.0016364156284,22.163310583803]; # INT_STATIC ubenchmark, 32 lanes. steady state temp
#	measured_power = [20.63,20.82,20.82,21.12,21.21,21.3,21.41,21.69,21.88]; # INT_STATIC ubenchmark. 1 lane at 0.632t (0.632 of max normalized temp)
#	measured_power = [20.73,20.81,20.82,21.21,21.31,21.41,21.6,21.8,21.98]; # INT_STATIC ubenchmark. 32 lanes at 0.632t (0.632 of max norm temp)
#       measured_power = [20.63,20.73,20.82,21.12,21.12,21.21,21.31,21.51,21.7]; # INT_ADD. 1 lane at 0.632t
#       measured_power = [20.63,20.82,20.82,21.21,21.21,21.31,21.49,21.69,21.88]; # INT_ADD. 32 lanes at 0.632tNT_ADD. 32 lanes at 0.632t
#       measured_power = [20.63,20.73,20.73,21.21,21.21,21.3,21.51,21.69,21.9]; # INT_MUL. 1 lane at 0.632t
#       measured_power = [20.73,20.82,20.82,21.2,21.3,21.39,21.59,21.88,21.99]; # INT_MUL. 32 lanes at .632t
#       measured_power = [20.63,20.73,20.73,21.12,21.12,21.21,21.31,21.51,21.7]; # FP_ADD. 1 lane at 0.632t
#       measured_power = [20.73,20.82,20.82,21.2,21.2,21.39,21.59,21.69,21.88]; # FP_ADD. 32 lanes at 0.632t
#       measured_power = [20.63,20.73,20.73,21.12,21.21,21.31,21.41,21.59,21.79]; # FP_MUL. 1 lane at 0.632t
#       measured_power = [20.63,20.82,20.82,21.2,21.3,21.39,21.59,21.69,21.98]; # FP_MUL. 32 lanes at 0.632t
#       measured_power = [21.41,22.08,22.09,23.93,24.12,24.6,25.28,25.86,26.45]; # INT_MEM. 100-20-1-512 (100 iters, 20 TBs, 1 lane, 512 tb size) at 0.632t
#       measured_power = [22.27,23.93,23.93,28.28,28.77,29.54,30.91,32.35,33.61]; # INT_MEM. 100-20-32-512 (100 iters, 20 TBs, 32 lanes, 512 tb size) at 0.632t

#	All max power values below
#		measured_power = [21.02,21.12,21.12,21.51,21.51,21.6,21.8,21.99,22.19]; # INT_STATIC. Steady state. Max average power. 1 lane
#		measured_power = [20.82,21.02,21.02,21.41,21.51,21.6,21.8,21.9,22.09]; # INT_STATIC. Max avg power. 8 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.41,21.6,21.8,21.99,22.09]; # INT_STATIC. Steady state. Max average power. 16 lanes
#		measured_power = [20.82,20.92,21.02,21.51,21.51,21.6,21.8,21.99,22.19]; # INT_STATIC. Max avg power. 24 lanes
#		measured_power = [20.92,21.12,21.12,21.51,21.51,21.7,21.8,22.09,22.19]; # INT_STATIC. Steady state. Max average power. 32 lane
#		measured_power = [20.92,21.02,21.02,21.41,21.51,21.6,21.8,21.99,22.18]; # INT_FP_STATIC. Steady state. Max average power. 1 lane
#		measured_power = [20.92,21.02,21.02,21.51,21.6,21.7,21.9,22.09,22.29]; # INT_FP_STATIC. Steady state. Max average power. 32 lanes
#		measured_power = [20.92,21.02,21.02,21.31,21.31,21.41,21.6,21.8,21.99]; # Max average power reached. INT_ADD. 1 lane.
#		measured_power = [20.92,21.02,21.12,21.51,21.51,21.6,21.8,21.99,22.09]; # Max average power reached. INT_ADD. 32 lanes.
#		measured_power = [20.82,21.02,21.02,21.51,21.51,21.7,21.8,21.99,22.19]; # INT_MUL. Max Avg Power. 1 lane
#		measured_power = [20.92,21.12,21.12,21.51,21.6,21.7,21.9,22.18,22.29]; # INT_MUL. Max Avg Power. 32 lanes
#		measured_power = [20.92,21.02,20.92,21.31,21.41,21.51,21.6,21.8,21.99]; # FP_ADD. Max Avg Power. 1 lane
#		measured_power = [20.92,21.12,21.12,21.51,21.51,21.6,21.88,21.99,22.19]; # FP_ADD. Max Avg Power. 32 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.51,21.6,21.8,21.9,22.09]; # FP_MUL. Max Avg Power. 1 lane
		measured_power = [20.92,21.12,21.12,21.51,21.6,21.6,21.9,21.99,22.19]; # FP_MUL. Max Avg Power. 32 lanes
#		measured_power = [21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15,26.74]; # INT_MEM. Max Avg Power. 100-20-1-512
#		measured_power = [22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.56,33.8]; # INT_MEM. Max Avg Power. 100-20-32-512

#	All max power values below per frequency for INT_STATIC. Lane counts 1,4,8,12,16,20,24,28,32
#		measured_power = [21.02,20.82,20.82,20.82,20.82,20.82,20.82,20.82,20.92]; # @139MHz
#		measured_power = [21.12,21.02,21.02,20.92,21.02,20.92,20.92,21.02,21.12]; # 278
#		measured_power = [21.12,21.02,21.02,21.02,21.02,20.92,21.02,21.02,21.12]; # 417
#		measured_power = [21.51,21.41,21.41,21.41,21.41,21.41,21.51,21.51,21.51]; # 556
#		measured_power = [21.51,21.51,21.51,21.41,21.41,21.51,21.51,21.51,21.51]; # 607
#		measured_power = [21.6,21.6,21.6,21.51,21.6,21.6,21.6,21.7,21.7]; # 696
#		measured_power = [21.8,21.7,21.8,21.7,21.8,21.7,21.8,21.8,21.8]; # 797
#		measured_power = [21.99,21.9,21.9,21.9,21.99,21.9,21.99,22.09,22.09]; # 898
#		measured_power = [22.19,22.19,22.09,22.09,22.09,22.19,22.19,22.29,22.19]; # 999

#	All max power values per lane count. INT_STATIC only.
#		measured_power = [21.02,21.12,21.12,21.51,21.51,21.6,21.8,21.99,22.19]; # 1 lane
#		measured_power = [20.82,21.02,21.02,21.41,21.51,21.6,21.7,21.9,22.19]; # 4 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.51,21.6,21.8,21.9,22.09]; # 8 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.41,21.51,21.7,21.9,22.09]; # 12 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.41,21.6,21.8,21.99,22.09]; # 16 lanes
#		measured_power = [20.82,20.92,20.92,21.41,21.51,21.6,21.7,21.9,22.19]; # 20 lanes
#		measured_power = [20.82,20.92,21.02,21.51,21.51,21.6,21.8,21.99,22.19]; # 24 lanes
#		measured_power = [20.82,21.02,21.02,21.51,21.51,21.7,21.8,22.09,22.29]; # 28 lanes
#		measured_power = [20.92,21.12,21.12,21.51,21.51,21.7,21.8,22.09,22.19]; # 32 lanes

#	All max power values per lane count except at 999 MHz. INT_STATIC. Validate model at 999 MHz
#		measured_power = [21.02,21.12,21.12,21.51,21.51,21.6,21.8,21.99]; # 1 lane
#		measured_power = [20.82,21.02,21.02,21.41,21.51,21.6,21.7,21.9]; # 4 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.51,21.6,21.8,21.9]; # 8 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.41,21.51,21.7,21.9]; # 12 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.41,21.6,21.8,21.99]; # 16 lanes
#		measured_power = [20.82,20.92,20.92,21.41,21.51,21.6,21.7,21.9]; # 20 lanes
#		measured_power = [20.82,20.92,21.02,21.51,21.51,21.6,21.8,21.99]; # 24 lanes
#		measured_power = [20.82,21.02,21.02,21.51,21.51,21.7,21.8,22.09]; # 28 lanes
#		measured_power = [20.92,21.12,21.12,21.51,21.51,21.7,21.8,22.09]; # 32 lanes

#	All max power values per lane count. INT_MEM
#		measured_power = [21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15,26.74]; # 100-20-1-512
#		measured_power = [21.6,22.48,22.58,24.51,24.9,25.29,25.98,26.56,27.32]; # 100-20-4-512
#		measured_power = [21.7,22.66,22.68,24.9,25.2,25.68,26.46,27.23,27.91]; # 100-20-8-512
#		measured_power = [21.99,23.16,23.16,26.07,26.46,26.95,27.81,28.78,29.86]; # 100-20-12-512
#		measured_power = [21.99,23.25,23.16,26.17,26.56,27.05,28,28.98,29.95]; # 100-20-16-512
#		measured_power = [22.19,23.64,23.65,27.15,27.61,28.49,29.47,30.71,31.78]; # 100-20-20-512
#		measured_power = [22.48,23.93,23.95,27.81,28.1,28.98,30.23,31.39,32.66]; # 100-20-24-512
#		measured_power = [22.29,23.85,23.85,27.91,28.49,29.37,30.61,31.88,33.24]; # 100-20-28-512
#		measured_power = [22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.46,33.8]; # 100-20-32-512

#	All max power values per lane count except at 999 MHz. INT_MEM. Validate model at 999 MHz
#		measured_power = [21.6,22.29,22.29,24.22,24.51,24.9,25.59,26.15]; # 100-20-1-512
#		measured_power = [21.6,22.48,22.58,24.51,24.9,25.29,25.98,26.56]; # 100-20-4-512
#		measured_power = [21.7,22.66,22.68,24.9,25.2,25.68,26.46,27.23]; # 100-20-8-512
#		measured_power = [21.99,23.16,23.16,26.07,26.46,26.95,27.81,28.78]; # 100-20-12-512
#		measured_power = [21.99,23.25,23.16,26.17,26.56,27.05,28,28.98]; # 100-20-16-512
#		measured_power = [22.19,23.64,23.65,27.15,27.61,28.49,29.47,30.71]; # 100-20-20-512
#		measured_power = [22.48,23.93,23.95,27.81,28.1,28.98,30.23,31.39]; # 100-20-24-512
#		measured_power = [22.29,23.85,23.85,27.91,28.49,29.37,30.61,31.88]; # 100-20-28-512
#		measured_power = [22.58,24.32,24.32,28.49,29.06,29.86,31.2,32.46]; # 100-20-32-512

#	All max power values per lane count. INT_ADD with 1 add instruction. 
#	const_power is excluded within get_coeffs routine
#		measured_power = [20.82,21.02,20.92,21.31,21.41,21.41,21.6,21.8,21.99]; # 1 lane
#		measured_power = [20.82,20.92,20.92,21.31,21.41,21.51,21.6,21.8,21.99]; # 4 lanes
#		measured_power = [20.82,20.92,20.92,21.31,21.41,21.51,21.51,21.8,21.99]; # 8 lanes
#		measured_power = [20.82,20.92,20.92,21.41,21.41,21.51,21.7,21.8,21.99]; # 12 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.41,21.41,21.6,21.8,21.99]; # 16 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9,22.09]; # 20 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9,22.09]; # 24 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.31,21.51,21.6,21.9,22.09]; # 28 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9,22.09]; # 32 lanes

#	All max power values per lane count. INT_ADD with 1 add. Excluding 999 MHz.
#		measured_power = [20.82,21.02,20.92,21.31,21.41,21.41,21.6,21.8]; # 1 lane
#		measured_power = [20.82,20.92,20.92,21.31,21.41,21.51,21.6,21.8]; # 4 lanes
#		measured_power = [20.82,20.92,20.92,21.31,21.41,21.51,21.51,21.8]; # 8 lanes
#		measured_power = [20.82,20.92,20.92,21.41,21.41,21.51,21.7,21.8]; # 12 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.41,21.41,21.6,21.8]; # 16 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9]; # 20 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9]; # 24 lanes
#		measured_power = [20.82,21.02,21.02,21.41,21.31,21.51,21.6,21.9]; # 28 lanes
#		measured_power = [20.82,20.92,21.02,21.41,21.31,21.51,21.6,21.9]; # 32 lanes
#	Modeled static power values for lane counts: 1,4,8,12,16,20,24,28,32. INT_STATIC. 999 MHz
#		target_static_power = [1.43102160594,1.2668061258,1.36112664087,1.16324796762,1.36112664087,1.066189743,1.32576088203,1.36026867969,1.54572306966]; # corresponding to model obtained with lowest RMSE for both A and B in Af^3 + Bf: column 'modeled_static_power_999MHz_AB_lowest-RMSE' in accelwattch-ubench-gpu-runs-power_STATIC_power.ods
		target_static_power = [0.98295201405,1.2668061258,1.18954144782,1.50286108455,1.18954144782,1.066189743,1.18954144782,1.49375311164,1.79417425977]; # corresponding to model with lowest MAPE for A and B in Af^3 + Bf.

#	All max power values for each combination. Data below for modeling. Option 10.
#	P = A*f^3 + B*f + C*active_lanes + D*inactive_lanes + E*active_PB + F*inactive_PB	
#		core_freq = [139e6,999e6,278e6,556e6,696e6,797e6];
#		active_lane_count = [1,28,16,32,8,12];
#		active_PB_count = [20,10,1,10,1,20];
#		measured_power = [21.31,26.93,21.02,24.22,21.6,25.49];

#	All max power values for each combination. Data below for modeling. Option 11.
#	P = A*f^3 + B*f + C*(active_lanes-1) + D*active_primary_PB + E*active_non-primary_PB	
		#core_freq = [139e6,999e6,278e6,556e6,696e6,797e6];
		#active_lane_count_minus1 = [0,27,15,31,7,11];
		#active_primary_PB_count = [10,10,1,10,1,10];
		#active_non_primary_PB_count = [10,0,0,0,0,10];
		
		# we have 5 unknowns. So, 5 data points suffice
#		core_freq = [139e6,999e6,278e6,556e6,696e6];
#		active_lane_count_minus1 = [0,27,15,31,7];
#		active_primary_PB_count = [10,10,1,10,1];
#		active_non_primary_PB_count = [10,0,0,0,0];

		#measured_power = [21.31,26.93,21.02,24.22,21.6,25.49];
#		measured_power = [21.31,26.93,21.02,24.22,21.6];

# 	Option 12. INT_STATIC. Model measured power against num non primary PB.
#	P = A*num_non-pr_PB^2 + B*num_non-pr_PB + C. 3 unknowns. 3 data points.
#		active_non_primary_PB_count = [0,2,5];
#		measured_power = [26.95,25.68,26.56];

#   Option 13. INT_ADD. Model measured power as:
#   P = A*f^3 + B*f + C*(active_lanes-1) + D*active_primary_PB + E*active_non-primary_PB
#	+ F, where F is constant power

		#core_freq = [139e6,139e6,999e6,999e6,999e6,139e6];
		#active_lane_count_minus1 = [0,0,15,31,31,15]; # generates singular matrix
		#active_primary_PB_count = [1,10,1,10,10,10];
		#active_non_primary_PB_count = [0,0,0,10,0,10];
		#measured_power = [20.92,21.12,22.09,26.37,25.2,21.31];

		# source: sheet 'INT_ADD_100-1-32_100-1-16_constp-models' in CONST_power.ods cell CI48
#		core_freq = [139e6,999e6,278e6,898e6,696e6,556e6];
#		active_lane_count_minus1 = [0,31,15,3,27,7];
#		active_primary_PB_count = [1,10,5,10,10,10];
#		active_non_primary_PB_count = [0,0,0,5,8,10];
#		measured_power = [20.92,25.2,21.31,23.93,24.22,23.25];

		# modeling p_L2,p_icache,p_other_SM_components, and p_idle-L1-shdmem-tex
		# for INT_STATIC as part of per SM power/idle power. 
		# 32 lanes and 999 MHz data below.
		# The following input matrix fails to generate an output.
		input_matrix = [[1,1,1,1],
				[1,2,2,2],
				[1,10,10,10],
				[1,10,20,10]
				];

		output_SM_power_vector = [1.58,2.26,6.34,7.39];

		method = 2; # model const power
		num_unknown_coeffs = 2; # const_power is known
		val_by_unique_freq = 0; # default for option 14/19/15

		if ((len(sys.argv) == 2) or (len(sys.argv) == 3)\
				or (len(sys.argv) == 4)):
			method = int(sys.argv[1]);

			if ((method == 14) or (method == 15) \
					or (method == 16) or (method == 17) \
					or (method == 18) or (method == 19) \
					or (method == 20)):
				if (len(sys.argv) == 2):
					print("specify .py <method> <data file name>");
					exit(-2);
				else:
					data_file = sys.argv[2];

			if ((method == 14) or (method == 15) or (method == 19)\
				or (method == 20)):
				if (len(sys.argv) == 4):
					val_by_unique_freq = int(sys.argv[3]);

		if (len(sys.argv) == 4):
			core_freq = sys.argv[1];
			measured_power = sys.argv[2];
	
		if (method == 4):
			print("modeling static power (linear) by lane count..");	
		elif (method == 3):
			print("modeling static power..");
		elif (method == 6):
			print("modeling static power variability by lane count based on existing modeled static power");
		elif (method == 2):
			print("modeling const power..");

		#const_power = 20.5673255 # Modeled using INT_ADD/MUL, FP_ADD/MUL and INT_MEM. 0.632t
		#const_power = 20.3989245 # Modeled using INT_ADD/MUL and FP_ADD/MUL. 0.632t
		#const_power = 20.7689687 # Modeled using INT_ADD/MUL and FP_ADD/MUL and INT_MEM. Max average power.
		const_power = 20.6122793 # Modeled using INT_ADD/MUL and FP_ADD/MUL. Max average power. Lowest MAPE
		#const_power = 20.670338 # Modeled using INT_ADD/MUL and FP_ADD/MUL. Max average power. Lowest RMSE

		if (method != 2):
			print("setting constant power: ",const_power);

		print("core_freq list set to: ",core_freq);
		if (method == 6):
			print("target static power list set to: ",target_static_power);
		else:
			print("measured_power list set to: ",measured_power);

		if (method == 1):
			coeffs = get_coeffs(core_freq,measured_power);
#        get_MAPE(core_freq,measured_power,coeffs);
		elif (method == 2):	
			get_coeffs2(core_freq,measured_power);
		elif (method == 3): # method = 3
			get_coeffs3(core_freq,measured_power,num_unknown_coeffs,const_power);
		elif (method == 4): # method = 4
			get_coeffs4_linear(lane_counts,measured_power);
		elif (method == 5): # method = 5
			get_coeffs5(core_freq,measured_power,const_power);
		elif (method == 6): # method = 6
			get_coeffs6(lane_counts,target_static_power);
		elif (method == 7):# method = 7
			get_coeffs7(core_freq,measured_power,const_power);
		elif (method == 8): # method = 8
			wrap_get_coeffs(core_freq,measured_power,num_unknown_coeffs,const_power);
		elif (method == 9): # method = 9
			get_coeffs8(input_matrix, output_SM_power_vector);
		elif (method == 10): # method = 10
			get_coeffs9(core_freq,active_lane_count,active_PB_count,measured_power\
				,const_power);
		elif (method == 11): # method = 11
			get_coeffs10(core_freq,active_lane_count_minus1,active_primary_PB_count,\
				active_non_primary_PB_count,measured_power,const_power);
		elif (method == 12): # method = 12
			get_coeffs11(active_non_primary_PB_count,measured_power,const_power);
		elif (method == 13): # method = 13. Model constant power as well, hence send a
			  # placeholder of -1 in the parameter const_power.
			get_coeffs10(core_freq,active_lane_count_minus1,active_primary_PB_count,\
				active_non_primary_PB_count,measured_power,-1,1);
		elif ((method == 14) or (method == 20)): # method = 14 or 20
			measured_power,core_freq,active_lane_count_minus1,active_primary_PB_count,\
			active_non_primary_PB_count = get_data_from_file(data_file,method);
		
			deg_poly = 6;
			if (method == 20):
				deg_poly = 3;

			get_coeffs12(core_freq,active_lane_count_minus1,active_primary_PB_count,\
                	active_non_primary_PB_count,measured_power,deg_poly,val_by_unique_freq);
		elif (method == 15): 
			measured_power,core_freq,active_lane_count_minus1 = \
					get_data_from_file(data_file,method);
		
			# specify placeholders for primary and non-primary PB counts as they are 
			# unused
			get_coeffs12(core_freq,active_lane_count_minus1,-1,-1,measured_power,4\
						,val_by_unique_freq);
		elif (method == 16):
			measured_power,core_freq = get_data_from_file(data_file,method);	
			get_coeffs2(core_freq,measured_power);
		elif (method == 17):
			measured_power,extra_TB = get_data_from_file(data_file,method);
			get_coeffs4_linear(extra_TB,measured_power);	
		elif (method == 18):
			measured_power,num_gpu_repetitions_by_TB = get_data_from_file(data_file,\
										method);
			get_coeffs4_linear(num_gpu_repetitions_by_TB,measured_power);	
		elif (method == 19):
			measured_power,core_freq,active_lane_count_minus1,active_primary_PB_count,\
			active_non_primary_PB_count,num_GPU_sets_minus1,deg6_num_points,\
			deg6_model_indices = get_data_from_file(data_file,method);
		
			# 72 data points: tab 'INT_ADD_100-1-32_16_4_8_12_20_24_28_constp-deg6-models'
			get_coeffs_gpusets(core_freq,active_lane_count_minus1,active_primary_PB_count,\
                		active_non_primary_PB_count,measured_power,num_GPU_sets_minus1,7,\
				deg6_num_points,deg6_model_indices,val_by_unique_freq);

		else:
			print("unsupported method type.. exiting");
