__author__ = "Rajarshi Das"
__copyright__ = "Copyright (C) 2023 Rajarshi Das"

from enum import Enum

class Stage(Enum):
	ISSUE = 1
	START_EX = 2
	EX_COMPLETE = 3
	WRITEBACK = 4
	COMMIT = 5

Stage_mapping_for_cycle_table = {
	Stage.ISSUE:"Issue",
	Stage.START_EX:"Start_EX",
	Stage.EX_COMPLETE:"EX_Complete",
	Stage.WRITEBACK:"Writeback",
	Stage.COMMIT:"Commit"
}

NUM_LOAD_BUFFERS = 2
NUM_ADDSUB_RS = 3
NUM_MULDIV_RS = 2

# Mimic that effective address 0(R2)
# contains the content of R3
Memory = {16:45}

ARF = {"R1":12,
	"R2":16,
	"R3":45,
	"R4":5,
	"R5":3,
	"R6":4,
	"R7":1,
	"R8":2,
	"R9":2,
	"R10":3
};

RAT = {"R1":"--",
	"R2":"--",
	"R3":"--",
	"R4":"--",
	"R5":"--",
	"R6":"--",
	"R7":"--",
	"R8":"--",
	"R9":"--",
	"R10":"--"
};

stage_success=0
instr_not_at_head=99 # used in commit stage. Instr not at head of ROB

ready_for_ex=1 #  used to start ex
not_ready_for_ex=0

overall_cycles_completed = [0] # used to update cycle table

ROB_Entry_Header = ["ROB_Name",
	     "Instruction_Type",
	     "Destination",
	     "Value"
];

ROB = []; # Array of ROB entries
ROB_Master = {};

# Initialize the ROB
def init_ROB(num_ROB_entries):
	ROB = [];
	for i in range(0,num_ROB_entries):
		ROB_Name = "ROB" + str(i+1);
		ROB_Entry = {"ROB_Name":ROB_Name,
				"Instruction_Type":"",
				"Destination":"",
				"Value":""
		};

		ROB.append(ROB_Entry);

	ROB_Master = {"Head":0, # head is at the first entry
			"Entries":ROB,
			"Tail":0
	}

	return ROB_Master;

def init_ARF(values):
	reg_name = "";

	for i in range(len(values)):
		reg_name = "R"+ str(i+1); # R1 maps to 0th value
		ARF[reg_name] = values[i];

def init_RAT(num_RAT_entries):
	RAT = {};
	for i in range(num_RAT_entries):
		reg_name = "R" + str(i+1);
		RAT[reg_name] = "--";

	return RAT;

Load_Buffer_Header = ["Instruction",
			"Busy",
			"Destination_Tag",
			"Address_Offset",
			"Source_Register"
];

LB_entry_pending = 1;

RS_Header = ["Instruction",
		"Busy",
		"Destination_Tag",
		"Source1_Tag",
		"Source2_Tag",
		"Value_Source1",
		"Value_Source2"
];

LB = [];

type_LB=1;
type_RS=2;

def init_Load_Buffers(num_Load_Buffers):
	for i in range(num_Load_Buffers):
		LB_entry = {
		"Instruction": "",
		"Busy": "",
		"Destination_Tag": "",
		"Address_Offset": "",
		"Source_Register": "",
		}

		LB.append(LB_entry);

	#print("debug: LB:",LB);
	return LB;

def init_RS(num_RS):
	RS = [];
	for i in range(num_RS):
		RS_entry = {
		"Instruction": "",
		"Busy": "",
		"Destination_Tag": "",
		"Source1_Tag": "",
		"Source2_Tag": "",
		"Value_Source1": "",
		"Value_Source2": "",
		}

		RS.append(RS_entry);
	
	return RS;

addsub_RS = [];
muldiv_RS = [];

def init_all_RS(num_addsub_RS,num_muldiv_RS):
	#print("debug: num_addsub_RS:",num_addsub_RS);
	addsub_RS = init_RS(num_addsub_RS);
	#print("debug: init addsub_RS:",addsub_RS);

	#print("debug: num_muldiv_RS:",num_muldiv_RS);
	muldiv_RS = init_RS(num_muldiv_RS);
	#print("debug: init muldiv_RS:",muldiv_RS);
	return addsub_RS,muldiv_RS;

RS_entry_pending = 2;

instruction_cycle_table_header = ["Instruction",
				"Issue",
				"Start_EX",
				"EX_Complete",
				"Writeback",
				"Commit"
				]

instruction_cycle_table_entry = {"Instruction":"",
				 "Issue":0,
				 "Start_EX":0,
				 "EX_Complete":0,
				 "Writeback":0,
				 "Commit":0
				}

instruction_cycle_table = []

alu_instruction_header = ["funct7_31_25",
			"rs2_24_20",
			"rs1_19_15",
			"funct3_14_12",
			"rd_11_7",
			"opcode_6_0"
];

lw_instruction_header = ["imm_31_20",
			"rs1_19_15",
			"funct3_14_12",
			"rd5_11_7",
			"opcode_6_0"
];


cycles_count = {"LW":2,
		"ADD":2,
		"SUB":2,
		"MUL":10,
		"DIV":40
};

opcode_map = {"LW":3,
	      "ALU":51
};

instr_store = []; # to store mapped instructions
instr_completed_store = []; # store completed instructions

flag_start_ex = []; # if start_ex should not happen, corresponding instruction
		   # index should be 1. Else 0.

# LW R3, 0(R2): 0x00012183
# lw:imm[11:0], rs1[5], funct3[3], rd[5], opcode[7]
# alu: funct7,rs2[5],rs1[5],funct3[3],rd[5],op[7]
# output: the instruction type, destination reg, source regs, cycles
# required for the instruction

def parse_instruction(instruction):
	type = "";
	src1_reg = "";
	src2_reg = "";
	imm_value = "";
	dest_reg = "";
	funct7 = "";
	funct3 = "";
	total_execution_cycles = 0;

	# first identify the instruction type
	# Get the opcode ( & 0b1111111 or & 127)
	opcode_mask = 127; # mask bits 31-8: opcode bits: 7-0
	opcode = int(instruction) & opcode_mask;

	for map_instr in opcode_map.keys():
		if (opcode == opcode_map[map_instr]):
			type = map_instr;

	if (type == ""):
		print("Unable to find matching type for instruction: ",instruction);
		exit(-1);
	
	instruction_entry = {};

	if (type == "LW"): # LW. Find the immediate, source and destination
		# rsh by 20 bits
		imm_value = instruction >> 20; # top 12 bits are imm value
		
		mask_src1 = 31; # 2^5 - 1 (for the rightmost 5 bits)
		shift_src1 = 15; # bit 19-15 we have src1

		src1_reg = (instruction >> shift_src1) & mask_src1; 

		mask_dest = mask_src1; # 5 bits
		shift_dest = 7; # bit 11-7 we have dest

		dest_reg = (instruction >> shift_dest) & mask_dest;

		total_execution_cycles = cycles_count[type];

	elif (type == "ALU"): # covers ADD, SUB, MUL, DIV
		shift_funct7 = 25; # bits 31-25 are funct7
		funct7 = instruction >> shift_funct7;	

		shift_funct3 = 12; # bits 14-12 are funct3
		mask_funct3 = 7; # 3 bits

		funct3 = (instruction >> shift_funct3) & mask_funct3;

		# MUL* and DIV* grouping
		if (funct7 == 1):
			if (funct3 == 0):
				type = "MUL";
			elif (funct3 == 4):
				type = "DIV";
		# ADD/SUB
		elif (funct3 == 0):
			if (funct7 == 0):
				type = "ADD";
			elif (funct7 == 32):
				type = "SUB";

		#print("debug: ALU instruction type: ",type," instruction\
		#		: ",hex(instruction));

		if (type == "ALU"): # unknown instruction!
			print("Unknown instruction type. instruction: ",instruction);
			exit(-1);

		mask_src1 = 31; # 2^5 - 1 (for the rightmost 5 bits)
		shift_src1 = 15; # bit 19-15 we have src1

		src1_reg = (instruction >> shift_src1) & mask_src1; 
		
		mask_src2 = 31; # 2^5 - 1 (5 bits)	
		shift_src2 = 20; # bits 24-20 are src2

		src2_reg = (instruction >> shift_src2) & mask_src2;

		mask_dest = mask_src1; # 5 bits
		shift_dest = 7; # bit 11-7 we have dest

		dest_reg = (instruction >> shift_dest) & mask_dest;

		total_execution_cycles = cycles_count[type];

	if (type == "LW"):
		readable_form = type + " " + "R" + str(dest_reg) + "," \
			+ str(imm_value) + "(" + "R" + str(src1_reg) + ")";
	else:
		readable_form = type + " " + "R" + str(dest_reg) + "," \
			+ "R" + str(src1_reg) + "," + "R" + str(src2_reg);

	instruction_entry = {"type":type,
			     "src1_reg":src1_reg,
			     "src2_reg":src2_reg,
			     "dest_reg":dest_reg,
			     "imm_value":imm_value,
			     "total_execution_cycles":total_execution_cycles,
			     "readable_form":readable_form,
			     "current_stage":"",
			     "dest_value":0, # hold the result to pass to RS and ROB
			     "dest_tag":"",
			     "cycles_completed":0,
			     "execution_cycles_completed":0
			    }

	instr_store.append(instruction_entry);
	flag_start_ex.append(0);

def init_instruction_cycle_table():
	for instr in instr_store:
		instruction_cycle_table_entry = {};
		instruction_cycle_table_entry["Instruction"] = instr\
							["readable_form"];
		instruction_cycle_table_entry["Issue"] = 0;
		instruction_cycle_table_entry["Start_EX"] = 0;
		instruction_cycle_table_entry["EX_Complete"] = 0;
		instruction_cycle_table_entry["Writeback"] = 0;
		instruction_cycle_table_entry["Commit"] = 0;
	
		instruction_cycle_table.append(instruction_cycle_table_entry);

	#print("debug: in init_instruction_cycle_table()");
	print_instruction_cycle_table();

def update_instruction_cycle_table(instr):
	current_stage = Stage_mapping_for_cycle_table[instr["current_stage"]];

	for i in range(len(instruction_cycle_table)):
		if (instruction_cycle_table[i]["Instruction"]== \
			instr["readable_form"]):
			instruction_cycle_table[i][current_stage] =\
					overall_cycles_completed[0] + 1;
			break;

# Check if the source reg is in the ROB. If yes, return the destn reg
# If the src and destn regs are the same, then ensure we do not take 
# the ROB assigned for the destn. dest_ROB is for the destn.
def check_src_reg_in_ROB(src_reg,dest_ROB):
	src_tag = "";

	#print("debug: check source reg: ",src_reg);
	for i in range(len(ROB_Master["Entries"])):
		# continue the loop even if the ROB entry is found,
		# since we need to take the latest ROB entry.
		if ((ROB_Master["Entries"][i]["Destination"] == src_reg) and
			(ROB_Master["Entries"][i]["ROB_Name"] != \
					dest_ROB)):
			src_tag = ROB_Master["Entries"][i]["ROB_Name"];
			#print("debug: src_tag found: ",src_tag);
	
	return src_tag;

# fetch value for the source register from the ARF
def fetch_value_from_ARF(src_reg):
	return ARF[src_reg];

def fetch_value_from_memory(address):
	return Memory[address];

# common routine to add an entry in a RS
def add_RS_entry(instr,RS):
	check_reg = "";
	src1_tag = "";
	src2_tag = "";
	src1_val = "";
	src2_val = "";
	RS_entry_success = False;

	# check if the source reg is a destination in the ROB
	check_reg = "R" + str(instr["src1_reg"]);
	src1_tag = check_src_reg_in_ROB(check_reg,instr["dest_tag"]);

	# if it isn't, get the value from the ARF
	if (src1_tag == ""):
		src1_val = fetch_value_from_ARF(check_reg);

	check_reg = "R" + str(instr["src2_reg"]);
	src2_tag = check_src_reg_in_ROB(check_reg,instr["dest_tag"]);
	if (src2_tag == ""):
		src2_val = fetch_value_from_ARF(check_reg);
			
	#print("debug: len(RS): ",len(RS));

	#print("debug: before adding: RS",RS);
	#debug start
	#for i in range(len(RS)):
	#	print("i: ",i," RS: ",RS[i]);
	#debug end
	for i in range(len(RS)):
		if (RS[i]["Busy"] == "Y"): # Occupied
			continue;
		#print("debug: adding RS entry at i: ",i);
		RS[i]["Instruction"] = instr["readable_form"];
		RS[i]["Busy"] = "Y";			
		#RS[i]["Destination_Tag"] = ROB_assigned;
		RS[i]["Destination_Tag"] = instr["dest_tag"];

		if (src1_tag != ""):
			RS[i]["Source1_Tag"] = src1_tag;
		else:
			RS[i]["Value_Source1"] = src1_val;

		if (src2_tag != ""):
			RS[i]["Source2_Tag"] = src2_tag;
		else:
			RS[i]["Value_Source2"] = src2_val;

		#print("debug: iteration: ",i," done.");
		RS_entry_success = True;
		break;

	#print("debug: after adding: RS",RS);	
	#print("debug: RS_entry_success:",RS_entry_success);

	if (not RS_entry_success): # RS full. need to wait.
		print("RS full. Wait for next chance\n");
		return RS,RS_entry_pending;

	return RS,RS_entry_success;

def instruction_issue(instr,LB,addsub_RS,muldiv_RS):
# create a RoB entry
# create a corresponding RAT entry
# create a LB/RS entry

	ROB_assigned = "";
	LB_entry_success = False;
	addsub_RS_entry_success = False;
	muldiv_RS_entry_success = False;

	RS = []; # temporary placeholder

	ROB_Master["Entries"][ROB_Master["Tail"]]["Instruction_Type"] = instr["type"];
	ROB_Master["Entries"][ROB_Master["Tail"]]["Destination"] = "R"+str(instr["dest_reg"]);
	ROB_assigned = ROB_Master["Entries"][ROB_Master["Tail"]]["ROB_Name"];
	instr["dest_tag"] = ROB_assigned;
	ROB_Master["Tail"] += 1; # move the tail one step ahead

	dest_reg_str = "R" + str(instr["dest_reg"]);

	for reg_name in RAT.keys():
		if (reg_name == dest_reg_str):
			RAT[reg_name] = ROB_assigned;
			break;	

	if (instr["type"] == "LW"): # need a load buffer entry
		for i in range(len(LB)):
			if (LB[i]["Busy"] == "Y"): # Occupied
				continue;
			LB[i]["Instruction"] = instr["readable_form"];
			LB[i]["Busy"] = "Y";
			LB[i]["Destination_Tag"] = ROB_assigned;
			Source_Register = "R" + str(instr["src1_reg"]);
			Source_Register_Value = fetch_value_from_ARF(\
						Source_Register);
					
			LB[i]["Address_Offset"] = int(instr["imm_value"]) + \
					int(Source_Register_Value);
			LB[i]["Source_Register"] = "R"+str(instr["src1_reg"]);
			LB_entry_success = True;
			#print("debug: After adding LB entry,LB: ",LB);
			break;
		if (not LB_entry_success): # no free space. Need to wait
			print("Load Buffer full. Wait for next chance\n");
			return LB_entry_pending,LB,addsub_RS,muldiv_RS;
		
	elif ((instr["type"]=="ADD") or (instr["type"]=="SUB")):
		#print("debug: adding instruction: ",instr," to RS");
		RS = addsub_RS;
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			addsub_RS = RS;
		#print("debug: added RS entry: addsub_RS:",addsub_RS);
	elif ((instr["type"]=="MUL") or (instr["type"]=="DIV")):
		#print("debug: adding instruction: ",instr," to RS");
		RS = muldiv_RS;
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			muldiv_RS = RS;
		#print("debug: added RS entry: muldiv_RS:",muldiv_RS);

	instr["current_stage"] = Stage.ISSUE;
	instr["cycles_completed"] += 1;
	update_instruction_cycle_table(instr);

	#print("debug: ROB_Master: ",ROB_Master);
	#print("debug: Issue stage complete. instruction: ",instr);

	return stage_success,LB,addsub_RS,muldiv_RS;

def instruction_ready_for_ex_type_load(instr,LB,ROB_Master):
	for i in range(len(LB)):
		if (LB[i]["Instruction"]==instr["readable_form"]):
			if ("ROB" in LB[i]["Source_Register"]):
				print(instr["type"]," not yet ready..");
				return not_ready_for_ex;
			break;	

	return ready_for_ex;

def instruction_ready_for_ex_type_alu(instr,RS,ROB_Master):
	for i in range(len(RS)):
		if (RS[i]["Instruction"] == \
				instr["readable_form"]):
			if ((RS[i]["Value_Source1"]=="") or
				(RS[i]["Value_Source2"]=="")):
				print(instr["type"]," not yet ready..");
				return not_ready_for_ex;
			break;

	return ready_for_ex;

# check if conditions for starting EX are met. If not, return
# check the LB and RS

# need to redo the logic here. E.g. when does the LB entry show busy=N?
# and when does it change from Y to N?
# If it does not change and is always Y when it exists, then why do we
# need Busy?
def instruction_start_ex_type_load(instr):
	Effective_Address = 0;
	for i in range(len(LB)):
		if (LB[i]["Busy"] == "Y"): # Occupied
			# Ready to start EX
			# The eff. address must be available at this stage
			if (LB[i]["Instruction"] == instr["readable_form"]):
				instr["dest_value"] = \
					fetch_value_from_memory(LB[i]\
							["Address_Offset"]);	

				# clear LB entry
				LB[i]["Instruction"] = "";
				LB[i]["Busy"] = "";
				LB[i]["Destination_Tag"] = "";
				LB[i]["Address_Offset"] = "";
				LB[i]["Source_Register"] = "";
				
				instr["current_stage"] = Stage.START_EX;
				instr["cycles_completed"] += 1;
				update_instruction_cycle_table(instr);
				
				return stage_success;

def instruction_compute_result(type,src1,src2):
	result = 0;

	#print("debug: src1: ",src1," src2:",src2);

	if (type == "ADD"):
		result = int(src1) + int(src2);
	elif (type == "SUB"):
		result = int(src1) - int(src2);
	elif (type == "MUL"):
		result = int(src1) * int(src2);
	elif (type == "DIV"):
		result = int(int(src1) / int(src2));
	else:
		print("unknown instruction type	: ",type," exiting..");
		exit(-1);
	
	return result;

def instruction_start_ex_type_alu(instr,RS):
	for i in range(len(RS)):
		if (RS[i]["Instruction"] == instr["readable_form"]):
			if (RS[i]["Busy"] == "Y"):
				# ready to START_EX
				#if ((RS[i]["Value_Source1"] != "") and
				#(RS[i]["Value_Source2"] != "")):
					#print("debug: start ex: RS:",RS);
					#print("debug: src1 val:",\
					#RS[i]["Value_Source1"]);
					#print("debug: src2 val:",\
					#RS[i]["Value_Source2"]);
				instr["dest_value"] = \
					instruction_compute_result(instr["type"]\
						,RS[i]["Value_Source1"]\
						,RS[i]["Value_Source2"]);
				# clear RS entry
				RS[i]["Instruction"] = "";	
				RS[i]["Busy"] = "";	
				RS[i]["Destination_Tag"] = "";	
				RS[i]["Source1_Tag"] = "";	
				RS[i]["Source2_Tag"] = "";	
				RS[i]["Value_Source1"] = "";	
				RS[i]["Value_Source2"] = "";

				instr["current_stage"] = Stage.START_EX;
				instr["cycles_completed"] += 1;
				update_instruction_cycle_table(instr);
					
				return stage_success;

def instruction_start_ex(instr):
	return_value = -1;

	if (instr["type"] == "LW"):
		return_value = instruction_start_ex_type_load(instr);
	elif ((instr["type"] == "MUL") or (instr["type"] == "DIV")):
		return_value = instruction_start_ex_type_alu(instr,muldiv_RS);
	elif ((instr["type"] == "ADD") or (instr["type"] == "SUB")):
		return_value = instruction_start_ex_type_alu(instr,addsub_RS);

	#print("debug: started EX. instruction: ",instr);

	return return_value;

# Result is computed in START_EX since we lose the LB / RS context
def instruction_ex_complete(instr):
	instr["current_stage"] = Stage.EX_COMPLETE;
	instr["cycles_completed"] += instr["execution_cycles_completed"];
	# instr["cycles_completed"] += 1;

	#print("debug: completed EX. instruction: ",instr);
	update_instruction_cycle_table(instr);

# also set the donot_start_ex flag for the dependent instructions
# if they are 'AFTER' the instruction that is writing back.
def instruction_set_donot_start_ex(instr,type_LB_RS,LB_or_RS,\
#				updated_instr_index,instr_store):
				updated_instr_index):
	current_instr_index = 9999;

	if (type_LB_RS == type_LB):
		for j in range(len(instr_store)):
			if (instr_store[j]["readable_form"] == \
				instr["readable_form"]):
				current_instr_index = j;
				continue;
			# LB_or_RS is actually LB below
			if (instr_store[j]["readable_form"] == \
				LB_or_RS[updated_instr_index]["Instruction"]):
				if (j > current_instr_index):
					#instr_store[j]["donot_start_ex"]=1;
					flag_start_ex[j] = 1; 
					break;

	# LB_or_RS is actually RS below
	elif ((LB_or_RS[updated_instr_index]["Value_Source1"] != "") and \
		(LB_or_RS[updated_instr_index]["Value_Source2"] != "")):
		for j in range(len(instr_store)):
			if (instr_store[j]["readable_form"] == \
				instr["readable_form"]):
				current_instr_index = j;
				continue;
			if (instr_store[j]["readable_form"] == \
				LB_or_RS[updated_instr_index]["Instruction"]):
				if (j > current_instr_index):
					#instr_store[j]["donot_start_ex"]=1;
					flag_start_ex[j] = 1;
					break;
					
	#return instr_store;

#def instruction_writeback_LB(instr,LB,instr_store):
def instruction_writeback_LB(instr,LB):
	for i in range(len(LB)):
		#print_flag_ex();

		Source_set = 0;

		# LB entry has the source register waiting for the result.
		if (LB[i]["Busy"] == "Y") and (LB[i]["Source_Register"] == \
					instr["dest_tag"]):
			LB[i]["Source_Register"] = instr["dest_value"];
			Source_set = 1;

		#instr_store = instruction_set_donot_start_ex(\
		# check and set flag_start_ex only if we updated the LB
		# for the instruction in this iteration. Otherwise, we
		# end up checking for all instructions that have source_reg
		# available.
		if (Source_set == 1):
			instruction_set_donot_start_ex(\
#				instr,type_LB,LB,i,instr_store);
				instr,type_LB,LB,i);

		#return instr_store;

	print_LB();

#def instruction_writeback_RS(instr,RS,instr_store):
def instruction_writeback_RS(instr,RS):
	instruction_ready_index = []; #index of instructions which will now
					#be ready to run
	for i in range(len(RS)):
		#print_flag_ex();

		Source1_set = False;
		Source2_set = False;

		if (RS[i]["Source1_Tag"] == instr["dest_tag"]):
			RS[i]["Source1_Tag"] = "";
			RS[i]["Value_Source1"] = instr["dest_value"];
			Source1_set = True;
			
		if (RS[i]["Source2_Tag"] == instr["dest_tag"]):
			RS[i]["Source2_Tag"] = "";
			RS[i]["Value_Source2"] = instr["dest_value"];
			Source2_set = True;

		#instr_store = instruction_set_donot_start_ex(\
		# check and set flag_start_ex only if we updated the RS
		# for the instruction in this iteration.
		if ((Source1_set == True) or (Source2_set == True)):
			instruction_set_donot_start_ex(\
#				instr,type_RS,RS,i,instr_store);
				instr,type_RS,RS,i);
		#return instr_store;

	print_RS(RS);
		
#def instruction_writeback_ROB(instr,ROB_Master):
def instruction_writeback_ROB(instr):
	dest_reg_str = "";

	for i in range(len(ROB_Master["Entries"])):
		dest_reg_str = "R" + str(instr["dest_reg"]);

		if ((ROB_Master["Entries"][i]["ROB_Name"] == \
				instr["dest_tag"]) and \
		   (ROB_Master["Entries"][i]["Destination"] == \
				dest_reg_str)):
			ROB_Master["Entries"][i]["Value"] = \
				instr["dest_value"];
			#print("debug: updated ROB value: ",\
			#	instr["dest_value"]);
			break;

# Write result to waiting tags in RS/LB. Write result to RoB
def instruction_writeback(instr,LB,addsub_RS\
				,muldiv_RS):
	print("LB:");
	instruction_writeback_LB(instr,LB);
	print("ADD/SUB:");
	instruction_writeback_RS(instr,addsub_RS);	
	print("MUL/DIV:");
	instruction_writeback_RS(instr,muldiv_RS);	

	instruction_writeback_ROB(instr);
	instr["current_stage"] = Stage.WRITEBACK;
	instr["cycles_completed"] += 1;

	#print("debug: Writeback complete: ",instr);
	update_instruction_cycle_table(instr);

# Write result to ARF. Clear the RAT mapping. Move RoB head
def instruction_commit(instr):
	Commit_Value = 0;
	Commit_Destination_Register = "";

	# Pick entry at the RoB head
	Commit_Destination_Tag = ROB_Master["Entries"][ROB_Master["Head"]]\
					["ROB_Name"];
	Commit_Value = ROB_Master["Entries"][ROB_Master["Head"]]["Value"];

	# Check if the instruction is at the head of the RoB. If not, return
	if (instr["dest_tag"] != Commit_Destination_Tag):
		#print("debug: ROB head commit tag: ",Commit_Destination_Tag,\
		#	" instr_destn_tag: ",instr["dest_tag"]);
		#print("debug: instruction ",instr," not at head..");
		return instr_not_at_head;	

	# Write to ARF
	Commit_Destination_Register = ROB_Master["Entries"][ROB_Master["Head"]]\
					["Destination"];
	ARF[Commit_Destination_Register] = Commit_Value;

	# Clear RAT mapping if the current RoB mapping is the latest entry for
	# the destination register

	destination_match_count = 0;
	for i in range(len(ROB_Master["Entries"])):
		# Count entries after RoB head
		if (i <= ROB_Master["Head"]):
			continue;
		if (ROB_Master["Entries"][i]["Destination"] == \
					Commit_Destination_Register):
			destination_match_count += 1;	

	if destination_match_count == 0: # The current mapping is the only destination
					 # mapping for RAT
		RAT[Commit_Destination_Register] = "--";	
	
	# move RoB Head
	ROB_Master["Head"] += 1;

	instr["current_stage"] = Stage.COMMIT;
	instr["cycles_completed"] += 1;
	update_instruction_cycle_table(instr);
	#print("debug: instruction commit complete: ",instr);
	#print("debug: modified ROB_Master head at: ",ROB_Master["Head"]);

	return stage_success;

# core routine
def _run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master):
# Check based on the current stage, number of cycles, what should be the next operation?
	return_value = -1;
	Issue_stage_used = 	False;
	StartEX_stage_Load_used=False;
	StartEX_stage_AddSub_used =False;
	StartEX_stage_MulDiv_used =False;
	Commit_stage_used = 	False;

	for i in range(len(flag_start_ex)):
		# clear donot_start_ex flag for all instructions that were set
		# in the previous cycle so that they can now start EX
		#print("debug: flag_start_ex: instruction ",i,": ",flag_start_ex[i]);
		if (flag_start_ex[i] == 1):
			flag_start_ex[i] = 0;

	for i in range(len(instr_store)):
		instr = instr_store[i];
		if (instr["current_stage"] == ""): # issue
			if (Issue_stage_used): # Already issued an instruction. 
				continue;
			return_value,LB,addsub_RS,muldiv_RS = instruction_issue(instr,\
							LB,addsub_RS,muldiv_RS);
			if (return_value == stage_success):
				Issue_stage_used = True;
				print_instruction_cycle_table();
			print_LB();
			print("ADD/SUB:");
			print_RS(addsub_RS);
			print("MUL/DIV:");
			print_RS(muldiv_RS);
			print_ROB();

		elif (instr["current_stage"]==Stage.ISSUE):
			#if (instr_store_copy[i]["donot_start_ex"] == 1):
			if (flag_start_ex[i] == 1):
				continue;	
			if ((instr["type"] == "LW") or (instr["type"] == "SW")):
				if (StartEX_stage_Load_used == True): 
						# start 1 load per cycle
					continue;
				if (instruction_ready_for_ex_type_load(instr,LB,\
							ROB_Master)):
					return_value = instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_Load_used = True;
						print_LB();
						print_instruction_cycle_table();

			elif ((instr["type"]=="ADD") or (instr["type"]=="SUB")):
				if (StartEX_stage_AddSub_used == True): 
						# Start only 1 add/sub at a time
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							addsub_RS,ROB_Master)):
					return_value = instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_AddSub_used = True;
						print("ADD/SUB:");
						print_RS(addsub_RS);
						print_instruction_cycle_table();

			elif ((instr["type"]=="MUL") or (instr["type"]=="DIV")):
				if (StartEX_stage_MulDiv_used == True):
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							muldiv_RS,ROB_Master)):
					return_value = instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_MulDiv_used = True;
						print("MUL/DIV:");
						print_RS(muldiv_RS);
						print_instruction_cycle_table();

		elif (instr["current_stage"]==Stage.START_EX):
			instr["execution_cycles_completed"] += 1;
			if (instr["execution_cycles_completed"] == \
					instr["total_execution_cycles"]-1):
				instruction_ex_complete(instr);
				print_ROB();
				print_instruction_cycle_table();

		elif (instr["current_stage"]==Stage.EX_COMPLETE):
			#return_value,ROB_Master = \
				instruction_writeback(instr,\
#						ROB_Master,LB,addsub_RS,muldiv_RS);
						LB,addsub_RS,muldiv_RS);
		# if the writeback gets another instruction ready in the current
		# cycle (just because the other instruction is later in the loop)
		# do not schedule it. Run it in the next cycle.
		# However, if the other readied instruction is earlier to the one for 
		# which writeback happened, then ensure it runs in the next cycle.
				print_LB();
				print("ADD/SUB:");
				print_RS(addsub_RS);
				print("MUL/DIV:");
				print_RS(muldiv_RS);
				print_instruction_cycle_table();

		elif (instr["current_stage"] == Stage.WRITEBACK):
			if (Commit_stage_used == True):
				continue;
			return_value = instruction_commit(instr);
			if (return_value == stage_success):
				Commit_stage_used = True;
				instr_completed_store.append(instr);
				print_ARF();
				print_RAT();
				print_ROB();
				print_instruction_cycle_table();

def run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master):
	current_cycle = 0;
	while(1):
		print("\n");
		current_cycle = overall_cycles_completed[0] + 1;	
		print("<<<<<< Cycle ",str(current_cycle)," >>>>>>");
		_run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master);
		overall_cycles_completed[0] += 1;
		#print("debug: overall_cycles_completed: ",overall_cycles_completed[0]);
		if (len(instr_completed_store) == len(instr_store)):
			break;

def print_LB():
	LB_entry_present = False;

	for i in range(len(LB)):
		if (LB[i]["Instruction"] != ""):
			LB_entry_present = True;
			break;

	# No LB entries present. Return
	if not LB_entry_present:
		return;

	print("LB:");

	header_row = "";
	header_row = "Instruction\tBusy\tDestination_Tag\tAddress_Offset\t" +\
			"Source_Register";
	print(header_row);

	for i in range(len(LB)):
		LB_row = "";
		LB_row = LB[i]["Instruction"] + "\t" + LB[i]["Busy"] + "\t" +\
			LB[i]["Destination_Tag"] + "\t" + str(LB[i]["Address_Offset"])\
			+ "\t" + LB[i]["Source_Register"];
		print(LB_row);

def print_RS(RS):
	RS_entry_present = False;

	for i in range(len(RS)):
		if (RS[i]["Instruction"] != ""):
			RS_entry_present = True;
			break;

	# No RS entries. return
	if (not RS_entry_present):
		return;
	
	header_row = "";
	header_row = "Instruction\tBusy\tDestination_Tag\tSource1_Tag\t" +\
			"Source2_Tag\tValue_Source1\tValue_Source2";
	print(header_row);

	for i in range(len(RS)):
		if (RS[i]["Instruction"] == ""):
			continue;
		RS_row = "";
		RS_row += RS[i]["Instruction"] + "\t"  + RS[i]["Busy"] + "\t" + \
			RS[i]["Destination_Tag"] + "\t\t" + RS[i]["Source1_Tag"] + \
			"\t\t" + RS[i]["Source2_Tag"] + "\t\t" + \
			str(RS[i]["Value_Source1"]) +  \
			 "\t\t" + str(RS[i]["Value_Source2"]);
		print(RS_row);

def print_ROB():
	print("ROB:");

	header_row = "";
	header_row += "ROB_Name\tInstruction\tDestination\tValue";
	print(header_row);

	for entry in ROB_Master["Entries"]:
		ROB_Entry_row = "";
		ROB_Entry_row += entry["ROB_Name"] + "\t\t" + entry["Instruction_Type"] \
				+ "\t\t" + entry["Destination"] + "\t\t" + \
				str(entry["Value"]);

		print(ROB_Entry_row);

def print_ARF():
	print("ARF:");

	register_row = "";
	value_row = "";

	for register,value in ARF.items():
		register_row += register + "\t";

	print(register_row);

	for register,value in ARF.items():
		value_row += str(value) + "\t";

	print(value_row);

def print_RAT():
	print("RAT:");

	register_row = "";

	for register in RAT.keys():
		register_row += register + "\t";

	print(register_row);

	ROB_row = "";
	
	for register in RAT.keys():
		ROB_row += RAT[register] + "\t";

	print(ROB_row);


def print_flag_ex():
	for i in range(len(flag_start_ex)):
		print("flag_start_ex: instruction ",i,": ",\
				flag_start_ex[i]);

def print_instruction_cycle_table():
	header_row = "";
	for column in instruction_cycle_table_header:
		header_row += column + " ";
	print("Instruction Cycle Table:");
	print(header_row," ");
	for instr in instruction_cycle_table:
		print(instr["Instruction"],"\t",instr["Issue"],"\t",\
				instr["Start_EX"],"\t",instr["EX_Complete"],\
				"\t",instr["Writeback"],"\t",\
				instr["Commit"]);

if __name__ == "__main__":
	# assume a list of instructions passed in
	#instructions = ["0x00012183","0x0241c133","0x026280b3","0x008381b3",\
	#		"0x023080b3","0x40508233","0x002200b3"];
	instructions = [0x00012183,0x0241c133,0x026280b3,0x008381b3,\
			0x023080b3,0x40508233,0x002200b3];

	ARF_values = [12,16,45,5,3,4,1,2,2,3];
	init_ARF(ARF_values);
	init_RAT(len(ARF_values));
	ROB_Master = init_ROB(len(instructions));

	LB = init_Load_Buffers(NUM_LOAD_BUFFERS);	
	addsub_RS,muldiv_RS = init_all_RS(NUM_ADDSUB_RS,NUM_MULDIV_RS);	

	for i in range(len(instructions)):
		parse_instruction(instructions[i]);

	init_instruction_cycle_table();

	run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master);
