__copyright__ = "Copyright (C) 2023 Rajarshi Das"

# A sample vector processor implementation based on the 
# Tomasulo algorithm and RISC-V vector instructions

from enum import Enum
import sys

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

# Vector specific
# Configure this section to check behaviour with multiple loops.
# Change VECTOR_REGISTER_LENGTH_BITS, AVL, default_sew and 
# LANE_COUNT. This behaviour can be tested with the 'skip_setvl'
# option passed to the command line (to use the default settings
# instead of fetching from the instruction). In order to modify
# the setvl instruction, the desired AVL and sew will have to coded
# into the instruction itself to see the behaviour through the
# setvl instruction.

# << start configuration section >>

VECTOR_REGISTER_LENGTH_BITS = 512
#AVL = 16
AVL = 32 # this should require 2 loops, with each covering 16 elements
LANE_COUNT = 8
sew = -1 # Standard Element Width as encoded in vtype register
default_sew = 32 

# Mimic v1's data at offset 100 and v2's data at offset 200
# Need as many elements as the AVL
# AVL=16
#Memory_vectors = {100:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16],
#		300:[16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1]};
# AVL=32
Memory_vectors = {100:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,\
		18,19,20,21,22,23,24,25,26,27,28,29,30,31,32],
		300:[32,31,30,29,28,27,26,25,24,23,22,21,20,19,18\
		,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1]};

# set 2nd vector to base offset 300 since the first vector's max
# range is 100 + 32*4 = 228
# << End configuration section >>

MAX_ELEMENTS_PER_ITERATION = 8
#NUM_VECTOR_LOAD_BUFFERS = int(AVL/MAX_ELEMENTS_PER_ITERATION) 
#				# assuming AVL=16 
#				# and #lanes = 8

LDST_UNITS_PER_LANE = 1
BITS_IN_BYTE = 8

#NUM_VECTOR_ADDSUB_RS = NUM_VECTOR_LOAD_BUFFERS # assuming one vector operation
#NUM_VECTOR_MULDIV_RS = NUM_VECTOR_LOAD_BUFFERS # assuming one vector operation

#vsetvl_in_progress = False # not required since vsetvl runs independently.
current_vl = 0 # Stores the current value of the VL CSR  (Vector Length\
		# Control and Status Register)
num_sequences = 0 # how many sequences per vector operation.

ex_busy_clear_instr_index = -1
ex_started_instr = {}

vload_ex_busy = False; # used for marking multi loop vload instruction if 
			# lane count < avl

ldst_unit_instr_map = [];

skip_setvl = False; # always run setvl. Use command line param to set it to True
#default_vl = 16;
default_vl = int(VECTOR_REGISTER_LENGTH_BITS/default_sew);

AVL_complete = False; # Used to denote that all elements have been processed. Set
			# by bnez instruction.
instrs_on_hold = False; # used by BNEZ to hold further instructions until its outcome
			# is known.
branch_taken = False;

completed_elements = 0; # Used to identify the vector loop and set element indices  in issue.

ARF = {}
RAT = {}

ARF_values = [];

stage_success=0
instr_not_at_head=99 # used in commit stage. Instr not at head of ROB
vector_not_last_sequence=98 # used in commit stage. Instruction sequence is not
			   # the last sequence for the vector. 

ready_for_ex=1 #  used to start ex
not_ready_for_ex=0

overall_cycles_completed = [0] # used to update cycle table

ROB_Entry_Header = ["ROB_Name",
	     "Instruction_Type",
	     "Destination",
	   #  "Value"
	     "Element Indices",
	     "Values"
];

ROB = []; # Array of ROB entries
ROB_Master = {};

ROB_assigned = "";

# Initialize the ROB
def init_ROB(num_ROB_entries):
	ROB = [];
	for i in range(0,num_ROB_entries):
		ROB_Name = "ROB" + str(i+1);
		# This structure can only handle scalar operations
		#ROB_Entry = {"ROB_Name":ROB_Name,
		#		"Instruction_Type":"",
		#		"Destination":"",
		#		"Value":""
		#};
		# This structure can handle both vectors and scalars
		# For vectors, one ROB entry per element group
		ROB_Entry = {"ROB_Name":ROB_Name,
				"Instruction_Type":"",
				"Destination":"",
				"Element_Indices":[],
				"Values":[]
		};
		ROB.append(ROB_Entry);

	ROB_Master = {"Head":0, # head is at the first entry
			"Entries":ROB,
			"Tail":0
	}

	return ROB_Master;

def init_ARF(values,num_vector_registers):
	reg_name = "";

	for i in range(len(values)):
		reg_name = "X"+ str(i+1); # X1 maps to 0th value
		if (not skip_setvl):
			if (i == 4): # with setvl, X5 is reserved for VSETVL
				     # therefore use X6
				reg_name = "X" + str(i+2);
		ARF[reg_name] = values[i];

	reg_name = "X" + str(len(values)+1); # X5
	ARF[reg_name] = "";

	for i in range(num_vector_registers):
		reg_name = "V" + str(i+1);
		ARF[reg_name] = [];

	#print("debug: init ARF complete. ARF: ",ARF);

def init_RAT(num_RAT_entries):
	#for i in range(num_RAT_entries):
	for reg in ARF.keys():
		reg_name = reg;
		RAT[reg_name] = "--";

	#return RAT;
	#print("debug: init RAT complete. RAT: ",RAT);

# One LB entry per element group (elements executing together)
Vector_Load_Buffer_Header = ["Instruction",
			"Busy",
			"Destination_Tag",
			"Address_Offset",
			"Source_Register",
			"Start_Element_Index", # used during writeback
			"Num_Elements" # number of elements to fetch starting at offset
];

Load_Buffer_Header = ["Instruction",
			"Busy",
			"Destination_Tag",
			"Address_Offset",
			"Source_Register",
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
VLB = []; # Vector loads

type_LB=1;
type_RS=2;

def init_Load_Buffers(num_Load_Buffers):
	LB = [];

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

def init_Vector_Load_Buffers(num_Vector_Load_Buffers):
	VLB = [];

	for i in range(num_Vector_Load_Buffers):
		VLB_entry = {
		"Instruction": "",
		"Busy": "",
		"Destination_Tag": "",
		"Address_Offset": "",
		"Source_Register": "",
		"Num_Elements": "",
		"Start_Element_Index":""
		}

		VLB.append(VLB_entry);

	#print("debug: VLB:",VLB);
	return VLB;

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

def init_vector_RS(num_RS):
	RS = [];
	for i in range(num_RS):
		RS_entry = {
		"Instruction": "",
		"Busy": "",
		"Destination_Tag": "",
		"Source1_Tag": "",
		"Source2_Tag": "",
		"Value_Source1": [], # array of values
		"Value_Source2": [], # array of values
		"Num_Elements":"",
		"Start_Element_Index":""
		}

		RS.append(RS_entry);
	
	return RS;

addsub_RS = [];
muldiv_RS = [];
addsub_vector_RS = [];
muldiv_vector_RS = [];

def init_all_RS(num_addsub_RS,num_muldiv_RS):
	#print("debug: num_addsub_RS:",num_addsub_RS);
	addsub_RS = init_RS(num_addsub_RS);
	#print("debug: init addsub_RS:",addsub_RS);

	#print("debug: num_muldiv_RS:",num_muldiv_RS);
	muldiv_RS = init_RS(num_muldiv_RS);
	#print("debug: init muldiv_RS:",muldiv_RS);
	return addsub_RS,muldiv_RS;

def init_all_vector_RS(num_addsub_vector_RS,num_muldiv_vector_RS):
	addsub_vector_RS = init_vector_RS(num_addsub_vector_RS);
	muldiv_vector_RS = init_vector_RS(num_muldiv_vector_RS);

	return addsub_vector_RS,muldiv_vector_RS;

# Use the Application Vector Length, Vector Register length,
# Std Element Width and LMUL to set the vl register
# This should be called per iteration if we can't complete
# all AVL elements in 1 iteration.
def instruction_start_ex_vsetvl(instr):
	global sew; # used by VDOT
	# first get the avl,sew,vector_reg_length and lmul
	avl = instr["avl"];

	vtype = instr["vtype"];
	
	mask_lmul = 7; # last 3 bits
	if ((vtype & mask_lmul) == 0):
		lmul = 1; # \b000 => lmul = 1

	shift_sew = 3; # next 3 bits
	mask_sew = 7; 

	sew_bits = (vtype >> shift_sew) & mask_sew;
	sew = vtype_sew_map[sew_bits];

	# Vector Tail Agnostic
	shift_vta = 6;
	mask_vta = 1;
	vta = vtype >> shift_vta & mask_vta;
	if (vta == 0): 
		print("Vector Tail Agnostic: undisturbed");
	elif (vta == 1):
		print("Vector Tail Agnostic: agnostic");

	# Vector Mask Agnostic
	shift_vma = 7;
	mask_vma = 1;
	vma = vtype >> shift_vma & mask_vma;
	if (vta == 0): 
		print("Vector Mask Agnostic: undisturbed");
	elif (vta == 1):
		print("Vector Mask Agnostic: agnostic");

	vector_reg_length = VECTOR_REGISTER_LENGTH_BITS;
	
	vlenmax = int(lmul * (vector_reg_length/ sew));

	if (avl > vlenmax):
		if (avl%vlenmax == 0):
			num_loops = int(avl/vlenmax);
		else:
			num_loops = int(avl/vlenmax) + 1;

		vl_value = vlenmax;

	else: # avl <= vlenmax
		num_loops = 1;
		vl_value = avl;

	instr["dest_value"] = vl_value;
	instr["cycles_completed"] += 1;
	instr["current_stage"] = Stage.START_EX;
	update_instruction_cycle_table(instr);

	#print("debug: vl_value: ",vl_value);

	return stage_success,vl_value

RS_entry_pending = 2;

instruction_cycle_table_header = ["Instruction",
				"Issue",
				"Start_EX",
				"EX_Complete",
				"Writeback",
				"Commit",
				"Sequence" # for vector instructions
				]

instruction_cycle_table_entry = {"Instruction":"",
				 "Issue":0,
				 "Start_EX":0,
				 "EX_Complete":0,
				 "Writeback":0,
				 "Commit":0,
				 "Sequence":0
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

# execution cycles
cycles_count = {"LW":2,
		"ADD":2,
		"SUB":2,
		"MUL":10,
		"DIV":40,
		"SLLI":2,
		"VLE32.V":2,
		"VADD.VV":2,
		"VSE32.V":2,
		"VSETVL":2,
		"VDOT.VV":2,
		"VMUL.VV":3,
		"BNEZ":2
};

opcode_map = {"LW":3,
	      "ALU":51,
	      "VLEx.V":7, # vector load: bits 6:0
	      "VSEx.V":39, # vector store: bits 6:0
	      "OP-V":87, # both vector add (OPIVV) and vsetvl have same opcode
	      #"VADD.Vx":87, # vector add: bits 6:0 (OPIVx: OPIVV or OPIVX)
	      #"VSETVL":87 # vsetvl: Same major opcode as VADD. pg 25. spec v0.10
	      "SLLI":19 # Shift Left Logical Immediate
};

opcode_RVC_Q_map = {0:0, # bits 1:0 if 0 => Quadrant 0
		    1:1,
	            2:2
};

opcode_RVC_Q0_map = {};

opcode_RVC_Q1_map = {"BNEZ":7 # bits 15:13
};

opcode_RVC_Q2_map = {};

vector_ldst_width_map = {0:8,
			 5:16,
			 6:32, # \b110 => 32-bit vector element
			 7:64
};

opv_funct3_type_map = {4:"VADD.VX", # OPIVX. Vector Add (V-X)
		        0:"VADD.VV",  # OPIVV. Vector Add (V-V) and Vector Dot (V-V)
					# and Vector Multiply (V-V)
		        7:"VSETVL" # VL set instruction
};

opv_funct6_subtype_map = {0:"VADD.VV", # OPIVV. Vector Add (V-V)
		          57:"VDOT.VV",  # OPIVV. Vector Dot (V-V)
			  37:"VMUL.VV"	 # OPIVV. Vector Multiply (V-V)
};

vtype_sew_map = {0:8, # \b000 => 8-bit
		 1:16, # \b001 => 16-bit
		 2:32,
		 3:64
};

ediv_map = {0:1, # \b00 => EDIV = 1
	    1:2, # \b01 => EDIV = 2
	    2:4,
	    3:8
};

instr_store = []; # to store mapped (non config) instructions
instr_completed_store = []; # store completed (non config) instructions

config_instr_store = []; # to store mapped config instructions
config_instr_completed_store = []; # store completed config instructions

flag_start_ex = []; # if start_ex should not happen, corresponding instruction
		   # index should be 1. Else 0.

# LW R3, 0(R2): 0x00012183
# lw:imm[11:0], rs1[5], funct3[3], rd[5], opcode[7]
# alu: funct7,rs2[5],rs1[5],funct3[3],rd[5],op[7]
# output: the instruction type, destination reg, source regs, cycles
# required for the instruction

# vle32.v v1,(x1): 0x0200e087
# vle32.v v2,(x2): 0x02016107
# vadd.vv v2,v1,v2: 0x02208157
# vdot.vv v2,v1,v2: 0xe6208157 # new. Encoding from v0.9 of spec. vtype reg layout\
				# as per v0.10 of spec (appendix D)
# vse32.v v2,(x2): 0x02016127

def parse_instruction(instruction):
	type = "";
	src1_reg = "";
	src2_reg = "";
	imm_value = "";
	dest_reg = "";
	funct7 = "";
	funct3 = "";
	total_execution_cycles = 0;
	width = -1;

	global num_sequences;
	global skip_setvl,default_vl,current_vl,sew,default_sew;
	global ARF_values;

	# first identify the instruction type
	# Get the opcode ( & 0b1111111 or & 127)
	opcode_mask = 127; # mask bits 31-8: opcode bits: 6-0
	opcode = int(instruction) & opcode_mask;

	for map_instr in opcode_map.keys():
		if (opcode == opcode_map[map_instr]):
			type = map_instr;
			break;

	# set width of vector load/store
	if ("VLE" in type or "VSEx" in type): # Vector Load/Store
		shift_width = 12;
		mask_width = 7;
		width = 0;

		instr_width_bit_value = (instruction >> shift_width) & mask_width;
		for map_width_bit_value in vector_ldst_width_map.keys():
			if (instr_width_bit_value == map_width_bit_value):
				width = vector_ldst_width_map[map_width_bit_value];	
				break;

		if (width == 0):
			print("Unable to find width of vector load/store:.",instruction);
			exit(-1);

	if (type == ""): # no matching type for bits 6:0
		RVC_Q_op_mask = 3; # bits 1:0
		
		opcode = int(instruction) & RVC_Q_op_mask;

		RVC_Q = opcode_RVC_Q_map[opcode];

		if (RVC_Q == 1):
			RVC_Q_map = opcode_RVC_Q1_map;
		else:
			RVC_Q_map = {};
	
		RVC_Q_instr_mask = 7; # bits 15:13
		RVC_Q_instr_shift = 13;

		instr_RVC_type = (int(instruction) >> RVC_Q_instr_shift) & RVC_Q_instr_mask;

		for map_instr_type in RVC_Q_map.keys():
			if (RVC_Q_map[map_instr_type] == instr_RVC_type):
				type = map_instr_type;
				break;
		
	if (type == ""):
		print("Unable to find matching type for instruction: ",instruction);
		exit(-1);
	
	instruction_entry = {};

	if ("V" in type):
		element_indices = [];
		dest_values = [];

	if ((type == "VLEx.V") or (type == "VSEx.V")):
		if ("VLE" in type):
			type = "VLE" + str(width) + ".V";
		else:
			type = "VSE" + str(width) + ".V";

		shift_src = 15;
		mask_src = 31;
		src1_reg = (instruction >> shift_src) & mask_src; # containing the 
						# address offset
		shift_dest = 7;
		mask_dest = mask_src;
		dest_reg = (instruction >> shift_dest) & mask_dest;
		#print("debug: VLEx.V. src1_reg: ",src1_reg," dest_reg: ",dest_reg);
	
		if ("VSE" in type): # The src1_reg is the destn reg (containing offset)
				    # and vice versa
			temp = dest_reg;
			dest_reg = src1_reg;
			src1_reg = temp;
		
		#There is only one LD/ST unit for every vle/vse32.v
		#Every additional iteration takes 1 additional cycle
		#to complete.
		#total_execution_cycles = cycles_count[type] + \
		#				num_iterations - 1;

		# with each element group of the same vector instruction
		# treated as a separate instruction, the total exec cycles
		# is per element group
		total_execution_cycles = cycles_count[type];	

	#elif (type == "VADD.Vx"):
	elif (type == "OP-V"): # OP-V major opcode: covers VADD.Vx,VSETVL and VDOT.Vx
		shift_funct3 = 12;
		mask_funct3 = 7;

		shift_funct6 = 26;
		mask_funct6 = 127; # bits 31-26
		
		funct3 = (instruction >> shift_funct3) & mask_funct3;
		type = opv_funct3_type_map[funct3];

		if ((type == "VADD.VV") or # Vector-vector add or vector-vector dot prod
			(type == "VSETVL")): # Vector set VL
			shift_src1 = 15;
			mask_src1 = 31;

			src1_reg = (instruction >> shift_src1) & mask_src1;
			
			shift_src2 = 20;
			mask_src2 = mask_src1;

			src2_reg = (instruction >> shift_src2) & mask_src2;
				
			shift_dest = 7;
			mask_dest = mask_src1;

			dest_reg = (instruction >> shift_dest) & mask_dest;

			# use funct6 to distinguish between VADD.VV and VDOT.VV
			if (type == "VADD.VV"):
				funct6 = (instruction >> shift_funct6) & mask_funct6;
				type = opv_funct6_subtype_map[funct6];

			total_execution_cycles = cycles_count[type];

	elif (type == "LW"): # LW. Find the immediate, source and destination
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

	elif (type == "SLLI"):
		mask_src1 = 31; # 2^5 - 1 (for the rightmost 5 bits)
		shift_src1 = 15; # bit 19-15 we have src1

		src1_reg = (instruction >> shift_src1) & mask_src1; 

		mask_dest = mask_src1; # 5 bits
		shift_dest = 7; # bit 11-7 we have dest

		dest_reg = (instruction >> shift_dest) & mask_dest;

		mask_shamt = 31; # shift amount
		shift_shamt = 20; # bits 20-24

		shamt = (instruction >> shift_shamt) & mask_shamt;

		total_execution_cycles = cycles_count[type];
	
	elif (type == "BNEZ"):
		mask_src1 = 7; # bits 9:7
		shift_src1 = 7;

		src1_reg = (instruction >> shift_src1) & mask_src1; 
	
		offset = 0;

		# offset bits 2:1 (instr bits 4:3)
		mask_offset_2_1 = 3;
		shift_offset_2_1 = 3;

		offset_2_1 = (instruction >> shift_offset_2_1) & mask_offset_2_1;

		# offset bits 4:3 (instr bits 11:10)
		mask_offset_4_3 = 3;
		shift_offset_4_3 = 10;

		offset_4_3 = (instruction >> shift_offset_4_3) & mask_offset_4_3;

		# offset bit 5 (instr bit 2)
		mask_offset_5 = 1;
		shift_offset_5 = 2;

		offset_5 = (instruction >> shift_offset_5) & mask_offset_5;

		# offset bits 7:6 (instr bits 6:5)
		mask_offset_7_6 = 3;
		shift_offset_7_6 = 5;

		offset_7_6 = (instruction >> shift_offset_7_6) & mask_offset_7_6;

		# offset bit 8 (instr bit 12)
		mask_offset_8 = 1;
		shift_offset_8 = 12;

		offset_8 = (instruction >> shift_offset_8) & mask_offset_8;

		offset = offset_8 << 7 | offset_7_6 << 5 | offset_5 << 4 \
			| offset_4_3 << 2 | offset_2_1;

		shift_sign_check = 16;
		mask_sign_check = 0xffff;

		offset = offset * 2;

		if (((instruction >> shift_sign_check) & mask_sign_check) == \
			mask_sign_check): # negative value
				offset = -offset;

		total_execution_cycles = cycles_count[type];

	if ((type == "VLE32.V") or (type == "VSE32.V")):
		readable_form = type + " " + "V" + str(dest_reg) + "," \
			+ "(" + "X" + str(src1_reg) + ")";
	elif (type == "VSETVL"):
		readable_form = type + " " + "X" + str(dest_reg) + "," \
			+ "X" + str(src1_reg) + "," + "X" + str(src2_reg);
	elif ((type == "VADD.VV") or (type == "VDOT.VV") or (type == "VMUL.VV")):
		readable_form = type + " " + "V" + str(dest_reg) + "," \
			+ "V" + str(src1_reg) + "," + "V" + str(src2_reg);
	elif (type == "LW"):
		readable_form = type + " " + "R" + str(dest_reg) + "," \
			+ str(imm_value) + "(" + "R" + str(src1_reg) + ")";
	elif ((type == "ADD") or (type == "SUB")):
		readable_form = type + " " + "X" + str(dest_reg) + "," \
			+ "X" + str(src1_reg) + "," + "X" + str(src2_reg);
	elif (type == "SLLI"):
		readable_form = type + " " + "X" + str(dest_reg) + "," \
			+ "X" + str(src1_reg) + "," + str(shamt);
	elif (type == "BNEZ"):
		readable_form = type + " " + "X" + str(src1_reg) + "," \
			+ str(offset);
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
			     "dest_tag":"",
			     "cycles_completed":0,
			     "execution_cycles_completed":0,
			     "sequence":0
			    }
	
	#if ((type == "VLE32.V") or (type == "VADD.VV")):
	if (type == "SLLI"):
		instruction_entry["shamt"] = shamt; # shift amount

	if (type == "BNEZ"):
		instruction_entry["offset"] = offset; # branch target offset
		# Allocate another GPR as "internal" dest reg for BNEZ

		# This is guaranteed to run after the current_vl setting
		# below since the BNEZ instruction appears after one or
		# more 'Vector' instructions
		ARF_values.append(-1); # since both 0 and 1 are valid for BNEZ
		if (skip_setvl):
			instruction_entry["dest_reg"] = str(len(ARF_values));
		else:
			instruction_entry["dest_reg"] = str(len(ARF_values)+1);
		reg_name = "X" + instruction_entry["dest_reg"];
		ARF[reg_name] = -1;

		RAT[reg_name] = "--";

	if (type == "VSETVL"):
		instruction_entry["vtype"] = -1; # VTYPE register
		instruction_entry["avl"] = -1; # Application Vector Length
		instruction_entry["dest_value"] = -1; # The current vl will be stored
							# here

		config_instr_store.append(instruction_entry);
		flag_start_ex.append(0);

	elif (("V" in type) and (type != "VSETVL")): # we start the VLE once VSETVL \
						   # has completed.
		
		if ((skip_setvl) and (current_vl == 0)): # set current_vl on the first
							# vector instruction.
			current_vl = default_vl;
			sew = default_sew;
			ARF_values.append(current_vl); # X5 which contains the current vl if vsetvl
							# was executed

			reg_name = "X" + str(len(ARF_values));
			ARF[reg_name] = current_vl;

			RAT[reg_name] = "--";

			ARF_values.append(0); # X6. For SLLI, and ADD
			reg_name = "X" + str(len(ARF_values));
			ARF[reg_name] = current_vl;

			RAT[reg_name] = "--";

		print("debug: skip_setvl: ",skip_setvl);
		
		# current_vl is the number of elements that can be processed by a single vector
		# operation given the vector register length and the sew
		if (current_vl > LANE_COUNT): # current_vl is already set by the vsetvl instruction
			instruction_entry["vlen"] = LANE_COUNT;
			num_sequences = int(current_vl/ LANE_COUNT);
			if (int(current_vl%LANE_COUNT) != 0):
				num_sequences += 1;
		else: 
			instruction_entry["vlen"] = current_vl;
			num_sequences = 1;

		if (type == "VDOT.VV"):
			shift_ediv = 8; # as per appendix D in v0.10 of spec
			mask_ediv = 3;  # 2 bits

			ediv_bits = (instruction >> shift_ediv) & mask_ediv;
			instruction_entry["ediv_value"] = ediv_map[ediv_bits];

		# instruction_entry["vlen"] = MAX_ELEMENTS_PER_ITERATION; # what if we have strip mining?

		if ((type == "VLE32.V") or (type == "VSE32.V")):
			instruction_entry["element_size"] = int(width/BITS_IN_BYTE);

		instruction_entry["ex_busy"] = False;
		instruction_entry["ex_started_elements"] = 0; # is this required?
		#num_iterations = int(AVL/ MAX_ELEMENTS_PER_ITERATION);

		#if (int(AVL%MAX_ELEMENTS_PER_ITERATION) != 0): # strip mining
		#	num_iterations += 1;
		
		# one instruction per element group
		for i in range(num_sequences):
			instruction_entry_copy = instruction_entry.copy();
			instruction_entry_copy["sequence"] = i;
			start_element_index = i * \
				instruction_entry_copy["vlen"];
			element_indices_copy = element_indices.copy();
			dest_values_copy = dest_values.copy();

			for i in range(instruction_entry_copy["vlen"]):
				element_indices_copy.append(start_element_index + i);
				dest_values_copy.append(-1);

			instruction_entry_copy["element_indices"] = \
							element_indices_copy;
			instruction_entry_copy["dest_values"] = dest_values_copy;

		#	if ((i==(num_iterations - 1)) and \
		#		(int(AVL%MAX_ELEMENTS_PER_ITERATION) != 0)):
		#		instruction_entry_copy["vlen"] = \
		#				int(AVL%MAX_ELEMENTS_PER_ITERATION);

			if ((i==(num_sequences - 1)) and \
				(int(current_vl%LANE_COUNT) != 0)):
				instruction_entry_copy["vlen"] = \
						int(current_vl%LANE_COUNT);
			instr_store.append(instruction_entry_copy);
			flag_start_ex.append(0);
	else:
		instruction_entry["sequence"] = 0;
		instruction_entry["dest_value"] = 0; # hold the result to pass to RS and ROB
		instr_store.append(instruction_entry);
		flag_start_ex.append(0);

#def init_instruction_cycle_table():
def init_instruction_cycle_table(instr_store):
	if (skip_setvl):
		instruction_count = len(instr_store);
	else:
		instruction_count = len(instr_store) + \
					len(config_instr_store);
	if (len(instruction_cycle_table) == \
		instruction_count): # We already initialized once
				   # Reset the table now as we are
				   # in the 2nd or higher loop
		for table_entry in instruction_cycle_table:
			if ("VSETVL" in table_entry["Instruction"]):
				# remove VSETVL entry since its
				# not used after the 1st loop
				instruction_cycle_table.pop(0);
				continue;

			table_entry["Issue"] = 0;
			table_entry["Start_EX"] = 0;
			table_entry["EX_Complete"] = 0;
			table_entry["Writeback"] = 0;
			table_entry["Commit"] = 0;
			table_entry["Sequence"] = -1; # for vectors
		#print("debug: cleared VSETVL entry");
		print(instruction_cycle_table);
	else:
		for instr in instr_store:
			instruction_cycle_table_entry = {};
			instruction_cycle_table_entry["Instruction"] = instr\
								["readable_form"];
			instruction_cycle_table_entry["Issue"] = 0;
			instruction_cycle_table_entry["Start_EX"] = 0;
			instruction_cycle_table_entry["EX_Complete"] = 0;
			instruction_cycle_table_entry["Writeback"] = 0;
			instruction_cycle_table_entry["Commit"] = 0;
			instruction_cycle_table_entry["Sequence"] = -1; # for vectors
		
			instruction_cycle_table.append(instruction_cycle_table_entry);

	#print("debug: in init_instruction_cycle_table()");
	#print_instruction_cycle_table();

def update_instruction_cycle_table(instr):
	current_stage = Stage_mapping_for_cycle_table[instr["current_stage"]];
	sequence_updated = False;

	for i in range(len(instruction_cycle_table)):
		if (instruction_cycle_table[i]["Instruction"]== \
			instr["readable_form"]):
			# The following condition is not required,since
			# we expect to come here only on the last iteration
			# of the vector instruction.
			#if ((current_stage == "Commit") and 
			#	((instr["type"] == "VLE32.V") and \
			#		(instr["sequence"] < ((AVL/\
			#		ELEMENTS_PER_ITERATION)-1)))):
			#	continue;

			# for a vector instruction, update all the iterations
			# with the latest cycle count for a commit, but
			# individually for all other stages.
			#if ((instr["type"] == "VLE32.V") and not sequence_updated):
			if (("V" in instr["type"]) and not sequence_updated):
				if (instruction_cycle_table[i]["Sequence"] == -1):
					instruction_cycle_table[i]["Sequence"] = \
						instr["sequence"];
					sequence_updated = True;
			if ("V" not in instr["type"]):
				if (instruction_cycle_table[i]["Sequence"] == -1): \
					instruction_cycle_table[i]["Sequence"] = 0;
				instruction_cycle_table[i][current_stage] =\
					overall_cycles_completed[0] + 1;
				break;
			# All vector operations
			elif ((instr["current_stage"] != Stage.COMMIT) and \
				(instruction_cycle_table[i]["Sequence"] ==
					instr["sequence"])):
				instruction_cycle_table[i][current_stage] =\
					overall_cycles_completed[0] + 1;
				break;
			elif (instr["current_stage"] == Stage.COMMIT):
				# we get here only on the last sequence of the vector
				# update all iterations with the commit cycle count
				# of the last iteration
				instruction_cycle_table[i][current_stage] =\
				overall_cycles_completed[0] + 1;


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

def get_values_from_ROB(instr,src_tag):
	element_array = [];

	for i in range(len(ROB_Master["Entries"])):
		if (ROB_Master["Entries"][i]["ROB_Name"] == \
		src_tag):
			ROB_Entry = ROB_Master["Entries"][i];
			break;

	if ("V" in instr["type"]): # vector
		elements_needed = instr["vlen"];
		start_element_index = instr["sequence"] * instr["vlen"];
		# If the first element exists, then it is likely that
		# all required elements also exist.
		if (ROB_Entry["Values"][start_element_index] != -1):
			for i in range(start_element_index,start_element_index +\
				elements_needed):
				element_array.append(ROB_Entry["Values"][i]);

	else: # scalar
		if (ROB_Entry["Values"][0] > -1): # initial value= -1.
			element_array.append(ROB_Entry["Values"][0]);

	return element_array;
	
# fetch value for the source register from the ARF
def fetch_value_from_ARF(src_reg):
	return ARF[src_reg];

def fetch_value_from_memory(address):
	return Memory[address];

# The address should be base_offset + n * element_size
def fetch_vector_values_from_memory(address,instr):
	element_values = [];
	start_element_index = -1;

	for base_offset in Memory_vectors.keys():
		#print("debug: address: ",address);
		#print("debug: fetch_vector_values_from_mem: base_offset: ",\
		#				base_offset);
		#print("debug: upper_limit: ",instr["element_size"]*\
		#		len(Memory_vectors[base_offset]));

		if ((address >= base_offset) and \
			(address <= (base_offset + instr["element_size"]*len(\
						Memory_vectors[base_offset])))):
			start_element_index = int((address - base_offset)/ \
						instr["element_size"]);
			#print("debug: start_element_index: ",start_element_index);
			for e_idx in range(instr["vlen"]):
				#instr["dest_values"][start_element_index + e_idx]\
				#since each instr will hold only 'vlen' dest_values
				instr["dest_values"][e_idx]\
					= Memory_vectors[base_offset]\
						[start_element_index + e_idx];
			#print("debug: instr[dest_values]:",instr["dest_values"]);
			#print("debug: instr[sequence]:", instr["sequence"]);
			break;

	if (start_element_index == -1):
		print("No elements found for vector in memory.. ! Exiting..")
		exit(-1);

	instr["ex_started_elements"] += instr["vlen"];
	
	return instr;

def write_vector_values_to_memory(VLB_entry,instr): # For Vector Store
	source_values = [];
	start_element_index = -1;

	# Get the values from the Source Register
	#print("debug: VLB_entry: ",VLB_entry);

	for i in range(instr["vlen"]):
		source_values.append(VLB_entry["Source_Register"][i]);

	address = VLB_entry["Address_Offset"];

	for base_offset in Memory_vectors.keys():
		#print("debug: address: ",address);
		#print("debug: write_vector_values_to_mem: base_offset: ",\
		#				base_offset);
		#print("debug: upper_limit: ",instr["element_size"]*\
		#		len(Memory_vectors[base_offset]));

		if ((address >= base_offset) and \
			(address <= (base_offset + instr["element_size"]*len(\
						Memory_vectors[base_offset])))):
			start_element_index = int((address - base_offset)/ \
						instr["element_size"]);
			#print("debug: start_element_index: ",start_element_index);
			#print("debug: Memory_vector before update: ",\
			#	Memory_vectors[base_offset]);
			for e_idx in range(instr["vlen"]):
				#instr["dest_values"][start_element_index + e_idx]\
				#since each instr will hold only 'vlen' dest_values
				Memory_vectors[base_offset]\
					[start_element_index + e_idx]\
					= source_values[e_idx];

			instr["dest_values"] = source_values.copy();

			#print("debug: Memory_vector after update: ",\
			#	Memory_vectors[base_offset]);
			#print("debug: instr[sequence]:", instr["sequence"]);
			#print("debug: instr[dest_values]:",instr["dest_values"]);
			break;

	if (start_element_index == -1):
		print("No elements found for vector in memory.. ! Exiting..")
		exit(-1);

	instr["ex_started_elements"] += instr["vlen"];
	
	return Memory_vectors,instr;


# common routine to add an entry in a RS
def add_RS_entry(instr,RS):
	check_reg = "";
	src1_tag = "";
	src2_tag = "";
	src1_val = "";
	src2_val = "";
	RS_entry_success = False;
	reg_prefix = "";
	ROB_values = [];

	# check if the source reg is a destination in the ROB
	if ("V" in instr["type"]): # Assuming that only vector instructions are V*
		reg_prefix = "V";
	else:
	#	reg_prefix = "R";
		reg_prefix = "X";

	#check_reg = "R" + str(instr["src1_reg"]);
	check_reg = reg_prefix + str(instr["src1_reg"]);
	src1_tag = check_src_reg_in_ROB(check_reg,instr["dest_tag"]);

	# In case of a vector instruction, 
	# The ROB entry corresponding to a src tag, may be partially filled.
	# In such a case, we must fetch the values from the ROB, since, 
	# a writeback from that dependent source entry has already completed
	# and we can not get another update, and the ROB is not written to
	# ARF yet since it is only partially filled.
	# Similarly, for a scalar, the data may already be available.

	if (src1_tag != ""): # both scalar and vector
		ROB_values = get_values_from_ROB(instr,src1_tag);
		if (ROB_values):
			if (reg_prefix == "V"): # vector
				src1_val = ROB_values;
			else:
				src1_val = ROB_values[0];

			src1_tag = "";

		#if (src1_val): # we have the values. Remove the tag
		#	src1_tag = "";

	# if it isn't, get the value from the ARF
	elif (src1_tag == ""):
		src1_val = fetch_value_from_ARF(check_reg);

	#check_reg = "R" + str(instr["src2_reg"]);

	if (instr["src2_reg"] != ""): # SLLI does not have a src2 
		check_reg = reg_prefix + str(instr["src2_reg"]);

		src2_tag = check_src_reg_in_ROB(check_reg,instr["dest_tag"]);

		if (src2_tag != ""): # scalar and vector
			ROB_values = get_values_from_ROB(instr,src2_tag);
			if (ROB_values):
				if (reg_prefix == "V"): # vector
					src2_val = ROB_values;
				else:
					src2_val = ROB_values[0];
			
			if (src2_val):# we have the values. Remove the tag
				src2_tag = "";
		elif (src2_tag == ""):
			src2_val = fetch_value_from_ARF(check_reg);
	else: # SLLI
		if (instr["type"] == "SLLI"):
			src2_val = instr["shamt"];	
		elif (instr["type"] == "BNEZ"):
			src2_val = 0;
			
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
		if ("V" in instr["type"]):
			instr["dest_tag"] = instr["dest_tag"] + "-" +\
				str(int(instr["sequence"]) + 1);
			RS[i]["Destination_Tag"] = instr["dest_tag"]; 

			#RS[i]["Destination_Tag"] = instr["dest_tag"] + "-" + \
			#		str(int(instr["sequence"]) + 1);

		else:
			RS[i]["Destination_Tag"] = instr["dest_tag"];

		if (src1_tag != ""):
			if ("V" in instr["type"]):
				RS[i]["Source1_Tag"] = src1_tag + "-" +\
					str(int(instr["sequence"]) + 1);
			else:
				RS[i]["Source1_Tag"] = src1_tag;
		else:
			RS[i]["Value_Source1"] = src1_val;

		if (src2_tag != ""):
			if ("V" in instr["type"]):
				RS[i]["Source2_Tag"] = src2_tag + "-" +\
					str(int(instr["sequence"]) + 1);
			else:
				RS[i]["Source2_Tag"] = src2_tag;
		else:
			RS[i]["Value_Source2"] = src2_val;

		if ("V" in instr["type"]):
			RS[i]["Start_Element_Index"] = completed_elements + \
						instr["sequence"] *\
						instr["vlen"];
					# MAX_ELEMENTS_PER_ITERATION;
			RS[i]["Num_Elements"] = instr["vlen"];

		#print("debug: iteration: ",i," done.");
		RS_entry_success = True;
		break;

	#print("debug: after adding: RS",RS);	
	#print("debug: RS_entry_success:",RS_entry_success);

	if (not RS_entry_success): # RS full. need to wait.
		print("RS full. Wait for next chance\n");
		return RS,RS_entry_pending;

	return RS,RS_entry_success;

#def instruction_issue(instr,LB,addsub_RS,muldiv_RS):
def instruction_issue(instr,LB,addsub_RS,muldiv_RS,VLB,addsub_vector_RS,\
			muldiv_vector_RS):
# create a RoB entry
# create a corresponding RAT entry
# create a LB/RS entry
	global ROB_assigned;
	LB_entry_success = False;
	addsub_RS_entry_success = False;
	muldiv_RS_entry_success = False;
	instr_type = "";
	ROB_Entry_Destination_string = "";

	global completed_elements; # set in main routine

	return_value = stage_success;

	RS = []; # temporary placeholder

	#print("debug: instr type: ",instr["type"]," sequence: ",instr["sequence"]);

	# Use a local variable to cover all vector instructions
	if ("V" in instr["type"]):
		instr_type = "Vector";
	else:
		instr_type = "Scalar";

	if (instr_type == "Scalar"):
		ROB_Master["Entries"][ROB_Master["Tail"]]["Instruction_Type"] = \
								instr["type"];

		#ROB_Master["Entries"][ROB_Master["Tail"]]["Destination"] = "R"+\
		#					str(instr["dest_reg"]);

		if (instr["type"] == "SW"):
			ROB_Entry_Destination_string = "(X" + str(instr["dest_reg"])\
							+ ")";
		else:
			ROB_Entry_Destination_string = "X" + str(instr["dest_reg"]);
			
		ROB_Master["Entries"][ROB_Master["Tail"]]["Destination"] = \
						ROB_Entry_Destination_string;	
		#dest_reg_str = "R" + str(instr["dest_reg"]);
		dest_reg_str = "X" + str(instr["dest_reg"]);

		ROB_Master["Entries"][ROB_Master["Tail"]]["Element_Indices"]\
			.append(0); # For a scalar operation, there is only one
				    # element
		ROB_Master["Entries"][ROB_Master["Tail"]]["Values"]\
			.append(-1); # For a scalar operation, there is only one

	elif ((instr_type == "Vector") and (instr["sequence"] == 0)):
		#print("debug: adding ROB entry for ",instr["type"]);
		all_element_indices = [];
		all_element_values = [];

		#print("debug: ROB_Master: ",ROB_Master);
		ROB_Master["Entries"][ROB_Master["Tail"]]["Instruction_Type"] = \
								instr["type"];
		if ("VSE" in instr["type"]): # Vector Store or VSETVL
			if (instr["type"] == "VSE32.V"):
				ROB_Entry_Destination_string = "(";
			ROB_Entry_Destination_string += "X" + str(instr["dest_reg"]);
			if (instr["type"] == "VSE32.V"):
				ROB_Entry_Destination_string += ")";
			ROB_Master["Entries"][ROB_Master["Tail"]]["Destination"] \
					= ROB_Entry_Destination_string;

			#dest_reg_str = "X" + str(instr["dest_reg"]);
			dest_reg_str = ROB_Entry_Destination_string;
		else:
			ROB_Master["Entries"][ROB_Master["Tail"]]["Destination"] \
					= "V" + str(instr["dest_reg"]);
			dest_reg_str = "V" + str(instr["dest_reg"]);

		#for i in range(AVL):
		#print("debug: in issue. current_vl: ",current_vl);

		if (instr["type"] == "VSETVL"):
			element_range = 1;
		else:
			element_range = current_vl;

		#print("debug: in issue. current_vl: ",current_vl);

		for i in range(element_range):
		#	all_element_indices.append(i);
			all_element_indices.append(completed_elements + i);
			all_element_values.append(-1);

		ROB_Master["Entries"][ROB_Master["Tail"]]["Element_Indices"] = \
							all_element_indices;
		ROB_Master["Entries"][ROB_Master["Tail"]]["Values"] = \
							all_element_values;	

	if ((instr_type == "Scalar") or ((instr_type == "Vector") and\
		(instr["sequence"] == 0))):
		ROB_assigned = ROB_Master["Entries"][ROB_Master["Tail"]]\
					["ROB_Name"];
		ROB_Master["Tail"] += 1; # move the tail one step ahead

		#print("debug: about to assign entry in RAT. dest reg: ",\
		#	dest_reg_str);
		#print("debug: RAT before modification. RAT: ",RAT);
		for reg_name in RAT.keys():
			#print("debug: RAT reg name: ",reg_name);
			if (reg_name == dest_reg_str):
				RAT[reg_name] = ROB_assigned;
				break;	

	print("debug: RAT modified. RAT: ",RAT);

	# dest_tag has to be set for all instructions within a vector
	instr["dest_tag"] = ROB_assigned;

	if (instr["type"] == "VSETVL"):
		Source_Register1 = "X" + str(instr["src1_reg"]);
		Source_Register2 = "X" + str(instr["src2_reg"]);
		instr["avl"] = fetch_value_from_ARF(Source_Register1);
		instr["vtype"] = fetch_value_from_ARF(Source_Register2);

	# The address offset is expected to change for every element group
	# One VLB per element group: required for chaining
	# if (instr["type"] == "VLE32.V"): # 32-bit vector load

	if (("VLE" in instr["type"]) or (instr["type"]=="VSE32.V")):
		vlen = instr["vlen"]; # number of elements in group

		for i in range(len(VLB)):
			if (VLB[i]["Busy"] == "Y"): # Occupied
				continue;
			VLB[i]["Instruction"] = instr["readable_form"];
			VLB[i]["Busy"] = "Y";

			# Using X* as the source registers for vectors
			if ("VSE" in instr["type"]):
				Source_Register = "V" + str(instr["src1_reg"]);
			else:
				Source_Register = "X" + str(instr["src1_reg"]);

			
			src_tag = check_src_reg_in_ROB(Source_Register,\
					instr["dest_tag"]);
			if ("ROB" in src_tag): # do we need per sequence ?
				Source_Register = src_tag;# no separate
						# source tag field
				Source_Register += "-" + str(instr["sequence"]\
							+1);	

			# VSE32.V
			# For a VLE32.V, the value is the offset.
			# VLB will use the source register value directly as
			# the offset into memory

			elif ("VSE" not in instr["type"]):#VLE
				Source_Register_Value = \
				fetch_value_from_ARF(Source_Register);
				VLB[i]["Address_Offset"] = int(\
					Source_Register_Value);

			if ("VSE" in instr["type"]):
				Destn_Register = "X" + str(instr["dest_reg"]);
				Destn_Register_Value = \
				fetch_value_from_ARF(Destn_Register);
				VLB[i]["Address_Offset"] = int(\
					Destn_Register_Value);

			VLB[i]["Source_Register"] = Source_Register;

			VLB[i]["Start_Element_Index"] = completed_elements + \
						instr["sequence"] *\
						instr["vlen"];
						# MAX_ELEMENTS_PER_ITERATION;

			VLB[i]["Address_Offset"] += int(instr["sequence"])*\
						int(instr["element_size"])\
						*instr["vlen"];
						# *MAX_ELEMENTS_PER_ITERATION;

			VLB[i]["Num_Elements"] = vlen;

			VLB[i]["Destination_Tag"] = ROB_assigned + "-" + \
					str(int(instr["sequence"]) + 1);
						# e.g. ROB1-1

			instr["dest_tag"] = VLB[i]["Destination_Tag"];

			#print("debug: inside _issue. VLB: ",print_LB());
			#print("debug: inside _issue. total_elements: ",total_elements);

			print_LB();
				#break;

			VLB_entry_success = True;
			break; # add a VLB just once, since we issue on each 
			       # iteration of the same load/store.

		if (not VLB_entry_success): # no free space. Need to wait
			print("Vector Load Buffer full. Wait for next chance\n");
			return_value = VLB_entry_pending;
			#return VLB_entry_pending,LB,addsub_RS,muldiv_RS;

	elif (instr["type"] == "LW"): # need a load buffer entry
		for i in range(len(LB)):
			if (LB[i]["Busy"] == "Y"): # Occupied
				continue;
			LB[i]["Instruction"] = instr["readable_form"];
			LB[i]["Busy"] = "Y";
			LB[i]["Destination_Tag"] = ROB_assigned;
			Source_Register = "R" + str(instr["src1_reg"]);

			src_tag = check_src_reg_in_ROB(Source_Register,\
					instr["dest_tag"]);
			if ("ROB" in src_tag):
				Source_Register = src_tag;# no separate
						# source tag field	
			else:
				Source_Register_Value = fetch_value_from_ARF(\
						Source_Register);
				LB[i]["Address_Offset"] = int(\
						instr["imm_value"]) + \
						int(Source_Register_Value);

			LB[i]["Source_Register"] = Source_Register;

			LB_entry_success = True;
			#print("debug: After adding LB entry,LB: ",LB);
			break;
		if (not LB_entry_success): # no free space. Need to wait
			print("Load Buffer full. Wait for next chance\n");
			return_value = LB_entry_pending;
			#return LB_entry_pending,LB,addsub_RS,muldiv_RS;

	elif (instr["type"] == "VADD.VV"):
		RS = addsub_vector_RS;	
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			addsub_vector_RS = RS;
			print_RS(addsub_vector_RS);
		else:
			return_value = return_code;

	elif ((instr["type"] == "VDOT.VV") or (instr["type"] == "VMUL.VV")):
		RS = muldiv_vector_RS;	
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			muldiv_vector_RS = RS;
			print_RS(muldiv_vector_RS);	
		else:
			return_value = return_code;
		
	elif ((instr["type"]=="ADD") or (instr["type"]=="SUB")\
		or (instr["type"]=="BNEZ")):
		#print("debug: adding instruction: ",instr," to RS");
		RS = addsub_RS;
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			addsub_RS = RS;
		#print("debug: added RS entry: addsub_RS:",addsub_RS);
		else:
			return_value = return_code;

	elif ((instr["type"]=="MUL") or (instr["type"]=="DIV") \
			or (instr["type"]=="SLLI")):
		#print("debug: adding instruction: ",instr," to RS");
		RS = muldiv_RS;
		RS,return_code = add_RS_entry(instr,RS);
		if (return_code != RS_entry_pending):
			muldiv_RS = RS;
		#print("debug: added RS entry: muldiv_RS:",muldiv_RS);
		else:
			return_value = return_code;

	if (return_value == stage_success):
		instr["current_stage"] = Stage.ISSUE;
		instr["cycles_completed"] += 1;
		update_instruction_cycle_table(instr);
		print_instruction_cycle_table();

	#print("debug: ROB_Master: ",ROB_Master);
	#print("debug: Issue stage complete. instruction: ",instr);

	#return stage_success,LB,addsub_RS,muldiv_RS;
	return return_value,LB,addsub_RS,muldiv_RS,VLB,addsub_vector_RS,\
			muldiv_vector_RS;

def instruction_ready_for_ex_type_load(instr,LB,ROB_Master):
	for i in range(len(LB)):
		if ((LB[i]["Instruction"]==instr["readable_form"]) and \
		(instr["dest_tag"]==LB[i]["Destination_Tag"])):
			if ("ROB" in LB[i]["Source_Register"]):
				print(instr["type"]," not yet ready..");
				return not_ready_for_ex;
			break;	

	return ready_for_ex;

def instruction_ready_for_ex_type_alu(instr,RS,ROB_Master):
	for i in range(len(RS)):
		if ((RS[i]["Instruction"] == \
				instr["readable_form"]) and (instr["dest_tag"] ==\
				RS[i]["Destination_Tag"])):
			if ("V" in RS[i]["Instruction"]):
				#print("debug: check if ready: RS[i]",RS[i]);
				if ((len(RS[i]["Value_Source1"])==0) or \
				(len(RS[i]["Value_Source2"])==0)):
					print(instr["type"]," not yet ready..");
					return not_ready_for_ex;
			else:
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
	set_busy = False;
	global vload_ex_busy;
	global ex_busy_clear_instr_index;

	for i in range(len(VLB)):
		if (VLB[i]["Busy"] == "Y"): # Occupied
			# Ready to start EX
			# The eff. address must be available at this stage
			# Fetch the values only for the element group starting
			# at Offset. instr["dest_values"] is updated.

			# The VLB entries may not be in the same order as the 
			# instruction sequences. Therefore, need to match the dest_tag
			if ((VLB[i]["Instruction"] == instr["readable_form"]) and\
				(VLB[i]["Destination_Tag"]==instr["dest_tag"])):

				if ("VLE" in instr["type"]):
					instr = fetch_vector_values_from_memory\
						(VLB[i]["Address_Offset"],\
							instr);
				else: # VSE : Vector Store
				# update both memory and dest_values in instr
					Memory_Vectors,instr = \
					write_vector_values_to_memory\
							(VLB[i],instr);
						
				VLB[i]["Instruction"] = "";
				VLB[i]["Busy"] = "";
				VLB[i]["Destination_Tag"] = "";
				VLB[i]["Address_Offset"] = "";
				VLB[i]["Source_Register"] = "";
				VLB[i]["Num_Elements"] = "";
				VLB[i]["Start_Element_Index"] = "";

				if (vload_ex_busy == False):
					vload_ex_busy = True;

				#set_busy = True;
				#update_ldst_unit_instr_map(instr,set_busy);

			# Change state to START_EX only after all elements are 
			# have entered START_EX. Clear VLB entry only then.
			# The following condition is applicable if we did all
			# loads with a single instruction. With one instruction
			# per sequence (element group), we set to START_EX for
			# each instruction.
			#	if (instr["total_elements"] == \
			#		instr["ex_started_elements"]):
			#		instr["current_stage"] = Stage.START_EX;
			#		vload_ex_busy = False; # another vload can start now

				instr["current_stage"] = Stage.START_EX;

				# last sequence for the vector instruction.
				#if (int(AVL%MAX_ELEMENTS_PER_ITERATION) != 0):#strip mining
				#	if (instr["sequence"] == (AVL/ \
				#			MAX_ELEMENTS_PER_ITERATION)):\

				if (int(current_vl%LANE_COUNT) != 0):#strip mining
					if (instr["sequence"] == (current_vl/ \
							LANE_COUNT)):\
						#set_busy = False;
						#update_ldst_unit_instr_map(instr,set_busy);
						vload_ex_busy = False;
				# elif (instr["sequence"] == int(AVL/ \
				# 		MAX_ELEMENTS_PER_ITERATION)-1):
				elif (instr["sequence"] == int(current_vl/ \
						LANE_COUNT)-1):
					vload_ex_busy = False; # another vload can start
					#set_busy = False;
					#update_ldst_unit_instr_map(instr,set_busy);

				# find the index of the instruction in instr_store
				if (vload_ex_busy == False):
					for i in range(len(instr_store)):
						if (instr_store[i]["readable_form"] == instr\
							["readable_form"]) and \
						(instr_store[i]["sequence"] == instr\
							["sequence"]):
							ex_busy_clear_instr_index = i;
							break;

				instr["cycles_completed"] += 1;
				update_instruction_cycle_table(instr);
				#print("debug: Completed start_ex stage for instr: ",instr);
				return stage_success,ex_busy_clear_instr_index;

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
				
				return stage_success,instr_index_clearing_ex_busy;

# Compute vdot value per element index
def compute_vdot_value(src1,src2,bits_per_sub_element):
	value_mask = pow(2,bits_per_sub_element)-1;
	final_value = 0;

	while(src1 and src2):
		src1_bits = src1 & value_mask;
		src2_bits = src2 & value_mask;
	
		final_value += src1_bits * src2_bits;

		src1 = src1 >> bits_per_sub_element;
		src2 = src2 >> bits_per_sub_element;

	return final_value;

#def instruction_compute_result(type,src1,src2):
def instruction_compute_result(instr,src1,src2):
	result = 0;
	result_array = [];

	global sew;

	#print("debug: src1: ",src1," src2:",src2);
	type = instr["type"];
	
	if (type == "VADD.VV"):
		for i in range(len(src1)):
			# '-1' is the initialization value. So, do not
			# compute for such an index.
			if (src1[i] == -1): 
				result_array.append(-1);
			else:
				result_array.append(int(src1[i]) + \
				int(src2[i]));
	elif (type == "VDOT.VV"):
		ediv = instr["ediv_value"];
		if (sew%int(ediv) != 0): 
			print("SEW: ",sew, " and EDIV: ",ediv, " values\
			are incompatible.. exiting..");
			exit(-1);
		
		bits_per_sub_element = int(sew / int(ediv));
		for i in range(len(src1)):
			# '-1' is the initialization value. So, do not
			# compute for such an index.
			if (src1[i] == -1): 
				result_array.append(-1);
			else:
				final_value = compute_vdot_value(src1[i],\
					src2[i],bits_per_sub_element);	
				result_array.append(final_value);
	elif (type == "VMUL.VV"):
		for i in range(len(src1)):
			# '-1' is the initialization value. So, do not
			# compute for such an index.
			if (src1[i] == -1): 
				result_array.append(-1);
			else:
				result_array.append(int(src1[i]) * \
				int(src2[i]));

	elif (type == "ADD"):
		#print("debug: ADD instr: ",instr["readable_form"],\
		#"src1: ",src1," src2: ",src2);
		result = int(src1) + int(src2);
	elif (type == "SUB"):
		result = int(src1) - int(src2);
	elif (type == "MUL"):
		result = int(src1) * int(src2);
	elif (type == "DIV"):
		result = int(int(src1) / int(src2));
	elif (type == "SLLI"):
		result = int(int(src1) << int(src2));
	elif (type == "BNEZ"):
		if (src1 == src2): # src reg contains zero
			result = 0; # branch not taken
		else:
			result = 1; # branch taken
	else:
		print("unknown instruction type	: ",type," exiting..");
		exit(-1);

	if ("V" not in type): # scalar
		result_array.append(result);
	
	#return result;
	return result_array;

def instruction_start_ex_type_alu(instr,RS):
	dummy_instr_index = -1;
	result_array = [];
	start_element_index = -1;
	vlen = 0;	

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
				# for VDOT.VV we need multiple fields inside
				# instr to be passed in.
				result_array = \
					instruction_compute_result(instr\
				#	instruction_compute_result(instr["type"]\
						,RS[i]["Value_Source1"]\
						,RS[i]["Value_Source2"]);
				if ("V" in instr["type"]):
					start_index = int(RS[i][\
						"Start_Element_Index"]);
					vlen = int(RS[i]["Num_Elements"]);
					#print("debug: RS at ",i," :",RS[i]);
					#print("debug: result_array: ",\
					#	result_array," start_index: ",\
					#	start_index);
					for j in range(vlen):
						instr["dest_values"][j] = \
						result_array[j];
				else:
					instr["dest_value"]  = result_array[0];

				# clear RS entry
				RS[i]["Instruction"] = "";	
				RS[i]["Busy"] = "";	
				RS[i]["Destination_Tag"] = "";	
				RS[i]["Source1_Tag"] = "";	
				RS[i]["Source2_Tag"] = "";	
				if ("V" in instr["type"]):
					RS[i]["Value_Source1"] = [];	
					RS[i]["Value_Source2"] = [];
					RS[i]["Start_Element_Index"] = "";
					RS[i]["Num_Elements"] = "";
				else:
					RS[i]["Value_Source1"] = "";	
					RS[i]["Value_Source2"] = "";

				instr["current_stage"] = Stage.START_EX;
				instr["cycles_completed"] += 1;
				update_instruction_cycle_table(instr);
					
				return stage_success,dummy_instr_index;

def instruction_start_ex(instr):
	return_value = -1;
	instr_index = -1;

	if (instr["type"] == "VSETVL"):
		return_value,vl = instruction_start_ex_vsetvl(instr);
		instr_index = vl; # placeholder

	elif ((instr["type"] == "VLE32.V") or (instr["type"] == "VSE32.V") \
			or (instr["type"] == "LW")):
		#return_value = instruction_start_ex_type_load(instr);
		return_value,instr_index = instruction_start_ex_type_load(instr);

	elif ((instr["type"] == "MUL") or (instr["type"] == "DIV") or\
				(instr["type"] == "SLLI")):
		#return_value = instruction_start_ex_type_alu(instr,muldiv_RS);
		return_value,instr_index = instruction_start_ex_type_alu(instr,muldiv_RS);

	elif ((instr["type"] == "ADD") or (instr["type"] == "SUB")\
			or (instr["type"] == "BNEZ")):
		#return_value = instruction_start_ex_type_alu(instr,addsub_RS);
		return_value,instr_index = instruction_start_ex_type_alu(instr,addsub_RS);

	elif (instr["type"] == "VADD.VV"):
		#return_value = instruction_start_ex_type_alu(instr,addsub_vector_RS);
		return_value,instr_index = instruction_start_ex_type_alu(instr,\
								addsub_vector_RS);

	elif ((instr["type"] == "VDOT.VV") or (instr["type"] == "VMUL.VV")):
		return_value,instr_index = instruction_start_ex_type_alu(instr,\
								muldiv_vector_RS);

	#print("debug: started EX. instruction: ",instr);

	#return return_value;
	return return_value,instr_index;

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
			if ((instr_store[j]["readable_form"] == \
				instr["readable_form"]) and (instr["dest_tag"]\
				==instr_store[j]["dest_tag"])):
				current_instr_index = j;
				continue;
			# LB_or_RS is actually LB below
			if ((instr_store[j]["readable_form"] == \
				LB_or_RS[updated_instr_index]["Instruction"]) and\
			(instr_store[j]["dest_tag"] == \
				LB_or_RS[updated_instr_index]["Destination_Tag"])):
				if (j > current_instr_index):
					#instr_store[j]["donot_start_ex"]=1;
					flag_start_ex[j] = 1; 
					break;

	# LB_or_RS is actually RS below
	elif ((LB_or_RS[updated_instr_index]["Value_Source1"] != "") and \
		(LB_or_RS[updated_instr_index]["Value_Source2"] != "")):
		for j in range(len(instr_store)):
		# check dest_tag as well. Required for "V" instructions
			if ((instr_store[j]["readable_form"] == \
				instr["readable_form"]) and \
			(instr_store[j]["dest_tag"] == \
				instr["dest_tag"])):
				current_instr_index = j;
				continue;
		# check dest_tag to identify the matching "V" instruction
		# as well.
			if ((instr_store[j]["readable_form"] == \
				LB_or_RS[updated_instr_index]["Instruction"])\
			and (instr_store[j]["dest_tag"] == \
				LB_or_RS[updated_instr_index]["Destination_Tag"])):
				if (j > current_instr_index):
					#instr_store[j]["donot_start_ex"]=1;
					flag_start_ex[j] = 1;
					print("debug: j: ",j," set donot start ex for \
					instr: ",instr_store[j]["readable_form"]," dest\
					tag:",instr_store[j]["dest_tag"]);	
					break;
					
	#return instr_store;

#def instruction_writeback_LB(instr,LB,instr_store):
# For vector instructions, a separate writeback happens per sequence
#def instruction_writeback_LB(instr,LB):
def instruction_writeback_LB(instr,LB,VLB):
	values_array = [];

	for i in range(len(VLB)):
		if ((VLB[i]["Busy"] == "Y") and (VLB[i]["Source_Register"]\
		 == instr["dest_tag"])):
			# copy over instr["dest_values"]. But there are multiple
			# VLB entries, one per element group.
			#for j in range(instr["vlen"]):
			#	values_array.append(instr["dest_values"][\
			#	VLB[i]["Start_Element_Index"]+j]);

			# Since now we writeback only the elements in one group
			values_array = instr["dest_values"];

			VLB[i]["Source_Register"] = values_array.copy();	
			#break; # one WB per instruction/ iteration of a vector op
			# There could be multiple vector operations waiting on 
			# the same dest_tag (e.g. ROB1-1). Hence, do not break.
			instruction_set_donot_start_ex(\
#				instr,type_LB,LB,i,instr_store);
				instr,type_LB,VLB,i);

	
	for i in range(len(LB)):
		#print_flag_ex();

		# LB entry has the source register waiting for the result.
		if (LB[i]["Busy"] == "Y") and (LB[i]["Source_Register"] == \
					instr["dest_tag"]):
			LB[i]["Source_Register"] = instr["dest_value"];

		#instr_store = instruction_set_donot_start_ex(\
		# check and set flag_start_ex only if we updated the LB
		# for the instruction in this iteration. Otherwise, we
		# end up checking for all instructions that have source_reg
		# available.
			instruction_set_donot_start_ex(\
#				instr,type_LB,LB,i,instr_store);
				instr,type_LB,LB,i);

		#return instr_store;

	print_LB();

#def instruction_writeback_RS(instr,RS,instr_store):
def instruction_writeback_RS_core(instr,RS):
	instruction_ready_index = []; #index of instructions which will now
					#be ready to run

	#print(">> writeback RS for instruction: ",instr["readable_form"]," with\
	#		dest tag: ",instr["dest_tag"]," and values: ",\
	#		instr["dest_values"]," and sequence: ", instr["sequence"]\
	#		," <<");

	for i in range(len(RS)):
		#print_flag_ex();

		Source1_set = False;
		Source2_set = False;
	
		#print("debug: check option to writeback to RS");
		#print("debug: RS Source1_tag: ",RS[i]["Source1_Tag"]," dest \
		#	tag: ",instr["dest_tag"]);

		if (RS[i]["Source1_Tag"] == instr["dest_tag"]):
			RS[i]["Source1_Tag"] = "";
			if ("V" in instr["type"]):
				RS[i]["Value_Source1"] = \
					instr["dest_values"];
			else:
				RS[i]["Value_Source1"] = \
					instr["dest_value"];
			Source1_set = True;
			
		if (RS[i]["Source2_Tag"] == instr["dest_tag"]):
			RS[i]["Source2_Tag"] = "";
			if ("V" in instr["type"]):
				RS[i]["Value_Source2"] = \
					instr["dest_values"];
			else:
				RS[i]["Value_Source2"] = \
					instr["dest_value"];
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

def instruction_writeback_RS(instr,RS,vector_RS):
	instruction_writeback_RS_core(instr,RS);
	instruction_writeback_RS_core(instr,vector_RS);
		
#def instruction_writeback_ROB(instr,ROB_Master):
def instruction_writeback_ROB(instr):
	dest_reg_str = "";

	for i in range(len(ROB_Master["Entries"])):
		instr_dest_tag = "";
		#if (instr["type"] == "VLE32.V"):
		if ("V" in instr["type"]):
			#if (instr["type"]=="VSE32.V"):
			if ("VSE32" in instr["type"]): # for VSE32.V 
				dest_reg_str = "(X" + str(instr["dest_reg"]) +\
						")";
			elif ("VSET" in instr["type"]): # VSETVL
				dest_reg_str = "X" + str(instr["dest_reg"]);
			else:
				dest_reg_str = "V" + str(instr["dest_reg"]);
			# We do not have sequence specific ROB entries for VSETVL
			if (instr["type"] == "VSETVL"):
				instr_dest_tag = instr["dest_tag"];
			else:
			# strip out the trailing -1 from ROB1-1
				instr_dest_tag = instr["dest_tag"].split("-")[0];
			#print("debug: instr dest_tag: ",instr_dest_tag);
		else:
			#dest_reg_str = "R" + str(instr["dest_reg"]);
			dest_reg_str = "X" + str(instr["dest_reg"]);
			instr_dest_tag = instr["dest_tag"];


		if ((ROB_Master["Entries"][i]["ROB_Name"] == \
				instr_dest_tag) and \
		   (ROB_Master["Entries"][i]["Destination"] == \
				dest_reg_str)):

			# Assuming that since EX_COMPLETE is done
			# all elements have been computed and stored
			# in the 'Source Register'
			#if (instr["type"] == "VLE32.V"):
			if (("V" in instr["type"]) and \
				(instr["type"] != "VSETVL")):
				#print("debug: committing instruction: ", \
				#instr["readable_form"],instr["dest_values"]);
				start_index = instr["sequence"] * \
					instr["vlen"];
	
				for j in range(instr["vlen"]):
					ROB_Master["Entries"][i]["Values"]\
					[start_index+j] = \
					instr["dest_values"][j];
					#instr["dest_values"][start_index+j];
				#print("debug: in wb. updated_ROB: ");
				print_ROB();
			else:
				#print("debug: committing instruction: ", \
				#instr["readable_form"],instr["dest_value"]);
				ROB_Master["Entries"][i]["Values"][0] = \
						instr["dest_value"];
				#ROB_Master["Entries"][i]["Value"] = \
				#instr["dest_value"];
			#print("debug: updated ROB value: ",\
			#	instr["dest_value"]);
			break;

# Write result to waiting tags in RS/LB. Write result to RoB
#def instruction_writeback(instr,LB,addsub_RS\
#				,muldiv_RS):
def instruction_writeback(instr,LB,VLB,addsub_RS\
			,muldiv_RS,addsub_vector_RS,muldiv_vector_RS):
	print("LB:");
	#instruction_writeback_LB(instr,LB);
	# There are no instructions waiting on data from vsetvl
	# hence only update the ROB
	if (instr["type"] != "VSETVL"):
		instruction_writeback_LB(instr,LB,VLB);
		print("ADD/SUB:");
		#instruction_writeback_RS(instr,addsub_RS);	
		instruction_writeback_RS(instr,addsub_RS,addsub_vector_RS);	
		print("MUL/DIV:");
		#instruction_writeback_RS(instr,muldiv_RS);	
		instruction_writeback_RS(instr,muldiv_RS,muldiv_vector_RS);	

	instruction_writeback_ROB(instr);

	instr["current_stage"] = Stage.WRITEBACK;
	instr["cycles_completed"] += 1;

	#print("debug: Writeback complete: ",instr);
	update_instruction_cycle_table(instr);

# Write result to ARF. Clear the RAT mapping. Move RoB head
def instruction_commit(instr):
	Commit_Value = 0;
	Commit_Destination_Register = "";
	instr_dest_tag = "";
	
	last_sequence_number = -1;

	#if (instr["type"] == "VLE32.V"):
	if (("V" in instr["type"]) and (instr["type"] != "VSETVL")):
		#if (int(AVL%MAX_ELEMENTS_PER_ITERATION) != 0):
		#	last_sequence_number = int(AVL/\
		#		MAX_ELEMENTS_PER_ITERATION);
		#else:
		#	last_sequence_number = int(AVL/\
		#		MAX_ELEMENTS_PER_ITERATION)-1;

		if (int(current_vl%LANE_COUNT) != 0):
			last_sequence_number = int(current_vl/\
				LANE_COUNT);
		else:
			last_sequence_number = int(current_vl/\
				LANE_COUNT)-1;

	#if ((instr["type"] == "VLE32.V") and \
	if ((instr["type"] != "VSETVL") and ("V" in instr["type"]) and \
		(instr["sequence"] < last_sequence_number)):
		instr["current_stage"] = Stage.COMMIT;
		instr["cycles_completed"] += 1;
		return vector_not_last_sequence; # commit only on the last iteration 
		# / sequence but set stage to commit so that the cycle table can be 
		# updated for all sequences in the last iteration

	# Pick entry at the RoB head
	Commit_Destination_Tag = ROB_Master["Entries"][ROB_Master["Head"]]\
					["ROB_Name"];
	#Commit_Value = ROB_Master["Entries"][ROB_Master["Head"]]["Value"];
	if (len(ROB_Master["Entries"][ROB_Master["Head"]]["Element_Indices"]) == 1):
		Commit_Value = ROB_Master["Entries"][ROB_Master["Head"]]\
					["Values"][0];
	else:
		Commit_Value = ROB_Master["Entries"][ROB_Master["Head"]]\
					["Values"];

	# Check if the instruction is at the head of the RoB. If not, return
	if (("V" in instr["type"]) and (instr["type"] != "VSETVL")):
		instr_dest_tag = instr["dest_tag"].split("-")[0];
	else:
		instr_dest_tag = instr["dest_tag"];

#	if (instr["dest_tag"] != Commit_Destination_Tag):
	if (instr_dest_tag != Commit_Destination_Tag):
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

	# For a vector instruction, the update_..table() should happen only on the \
	# sequence of the iteration 
	update_instruction_cycle_table(instr);
	#print("debug: instruction commit complete: ",instr);
	#print("debug: modified ROB_Master head at: ",ROB_Master["Head"]);

	return stage_success;

# core routine
#def _run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master):
#def _run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master):
#def _run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,addsub_vector_RS\
#			,muldiv_vector_RS):
def _run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,addsub_vector_RS\
			,muldiv_vector_RS,instr_store): # to allow separate config_store
# Check based on the current stage, number of cycles, what should be the next operation?
	return_value = -1;
	Issue_stage_used = 	False;
	Vector_Secondary_Issue_stage_used = False; # only for vectors with sequence > 0
	StartEX_stage_Load_used=False;
	StartEX_stage_AddSub_used =False;
	StartEX_stage_MulDiv_used =False;
	Commit_stage_used = 	False;
	StartEX_stage_Vector_Load_used=False;
	StartEX_stage_Vector_AddSub_used =False;
	StartEX_stage_Vector_MulDiv_used =False;
	global ex_busy_clear_instr_index; 
#	global vsetvl_in_progress; # All other vector instructions need to wait until
				    # vsetvl is complete
	global current_vl;
	global instrs_on_hold;
	global branch_taken;
	global AVL_complete;

	Vector_Issued_instr_form = "";
	block_further_start_ex = False;

	for i in range(len(flag_start_ex)):
		# clear donot_start_ex flag for all instructions that were set
		# in the previous cycle so that they can now start EX
		#print("debug: flag_start_ex: instruction ",i,": ",flag_start_ex[i]);
		if (flag_start_ex[i] == 1):
			flag_start_ex[i] = 0;

	#print("debug: LB:",LB," addsub RS: ",addsub_RS," muldiv RS: ",muldiv_RS);
	#print_RS(addsub_RS);
	#print_RS(muldiv_RS);
	print_ROB();

	for i in range(len(instr_store)):
		instr = instr_store[i];
	
		if (instr["current_stage"] == ""): # issue
			if (instrs_on_hold):
				continue; # no further instructions can issue.

			if (Issue_stage_used): # Already issued an instruction. 
				continue;

			#if (vsetvl_in_progress): # what about scalar instructions?
			#	continue;

			# if sequence 1 of a vector has been issued in this cycle,
			# additional sequences of the same vector can not start.
			# however a sequence 0 of another vector can be issued,
			# since the sequence 0 of the previous vector was issued
			# in the previous cycle.
			if ((Vector_Secondary_Issue_stage_used == True) and \
			(instr["readable_form"] == Vector_Issued_instr_form)):
				continue;
				
			#return_value,LB,addsub_RS,muldiv_RS = instruction_issue(instr,\
			#				LB,addsub_RS,muldiv_RS);
			#print("debug: about to issue. instr: ",instr);
			return_value,LB,addsub_RS,muldiv_RS,VLB,addsub_vector_RS, \
			muldiv_vector_RS = instruction_issue(instr,LB,addsub_RS,muldiv_RS\
							,VLB,addsub_vector_RS,\
							muldiv_vector_RS);
			if (return_value == stage_success):
				#if ((instr["type"] == "VLE32.V") and (instr["sequence"]\
				if (("V" in instr["type"]) and (instr["sequence"]\
					> 0)):
					Vector_Secondary_Issue_stage_used = True;	
					Vector_Issued_instr_form = instr["readable_form"];
				else:
					Issue_stage_used = True; # Primary for vector
					# If BNEZ, do not issue further instructions until
					# we know the branch is not taken
					if (instr["type"] == "BNEZ"):
						instrs_on_hold = True;

				#if (instr["type"] == "VSETVL"):
				#	vsetvl_in_progress = True;
			# Issue can fail if a LB/ VLB / RS is not free. In such a case,
			# break the loop since all issues have to be in order. Try the 
			# same issue in the next cycle
			else:
				break;

			#print("debug: completed instruction_issue.");
			print_LB();
			print("ADD/SUB:");
			print_RS(addsub_RS);
			print("MUL/DIV:");
			print_RS(muldiv_RS);
			print_ROB();

		elif (instr["current_stage"]==Stage.ISSUE):
			# no more start ex allowed.
			#if (block_further_start_ex):
			#	continue;

			#if (instr_store_copy[i]["donot_start_ex"] == 1):
			if ((flag_start_ex) and (flag_start_ex[i] == 1)):
				continue;

			# previous vload yet to start for all element groups
			# if (instr["type"] == "VLE32.V"):
			if (instr["type"] == "VSETVL"):
				return_value,vl = instruction_start_ex(instr);
				if (return_value == stage_success):
					print_instruction_cycle_table();
		
			elif (("VLE" in instr["type"]) or ("VSE" in instr["type"])):
				if (StartEX_stage_Vector_Load_used == True):
					continue;

				#print("debug: current instr: ",instr["readable_form"]);
				#if (ex_started_instr):
					#print("debug: ex_started instr: ",ex_started_instr\
					#	["readable_form"]);
				#else:
					#print("debug: ex_started_instr empty");
				print("debug: vload_ex_busy: ",vload_ex_busy);

				# allow sequences > 0 of the same instruction to load.
				# in the next invocation
				if (ex_started_instr and (instr["readable_form"] != 
					ex_started_instr["readable_form"]) and\
					vload_ex_busy):
					continue;

				for i in range(len(instr_store)):
					if (instr_store[i]["readable_form"] ==\
						instr["readable_form"]):
						current_instr_index = i;	

				# The current instruction is AFTER the one that cleared
				# the ex_busy flag. Therefore, it must start EX in the 
				# next cycle.
				#if ((ex_busy_clear_instr_index > -1) and\
				#	(current_instr_index > ex_busy_clear_instr_index)):
				#	print("debug: current instr: ",instr\
				#		["readable_form"]);
				#	print("debug: cur instr index: ",current_instr_index\
				#	," ex_busy_clr_instr_idx: ",ex_busy_clear_instr_index);
				#	flag_start_ex[current_instr_index] = 1;
				#	ex_busy_clear_instr_index = -1; # reset 
				#	continue;
				# The above steps are currently not required since a new vector
				# load appears only after the last sequence of the previous vload.
				# If we get to run the last sequence of a vload, the stage_used
				# flag automatically prevents a new vector load (seq 0) from starting ex 
				# in the same cycle. 

				# The clear instr index is used only for vectors
				if (instruction_ready_for_ex_type_load(instr,\
					VLB,ROB_Master)):
					return_value,ex_busy_clear_instr_index = \
						instruction_start_ex(instr);
					#print("debug: start_ex done for instr: ",instr);
					if (return_value == stage_success):
					#instr["ex_busy"] == True; # useful with multiple sequences
								# issuing on 1 instruction
						StartEX_stage_Vector_Load_used = True;		
						ex_started_instr["readable_form"] = \
						instr["readable_form"];
				#else:
				#	block_further_start_ex = True; # do not allow further \
								# instructions to start ex \
								# as we need to start ex in order \
								# however, any future instrs waiting \
								# to issue should proceed as long as\
								# no other instruction is already issued\
								# in this cycle \
					#break; # issue the VLE instructions in 
					    # in order. 

			elif ((instr["type"] == "LW") or (instr["type"] == "SW")):
				if (StartEX_stage_Load_used == True): 
						# start 1 load per cycle
					continue;
				if (instruction_ready_for_ex_type_load(instr,LB,\
							ROB_Master)):
					return_value,instr_index = \
						instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_Load_used = True;
						print_LB();
						print_instruction_cycle_table();
				#else: # not ready yet. Stop this iteration since
				      # we need to issue in order
				#	block_further_start_ex = True;
				#	break;
		
			elif (instr["type"]=="VADD.VV"):	
				if (StartEX_stage_Vector_AddSub_used == True): 
						# Start only 1 add/sub at a time
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							addsub_vector_RS,\
							ROB_Master)):
					return_value,instr_index = \
						instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_vector_AddSub_used \
								= True;
						print("Vector ADD/SUB:");
						print_RS(addsub_vector_RS);
						print_instruction_cycle_table();
				#else: # not ready yet. Stop this iteration since
				      # we need to issue in order
				#	block_further_start_ex = True;
					#break;

			elif ((instr["type"]=="VDOT.VV") or (instr["type"]==\
						"VMUL.VV")):
				if (StartEX_stage_Vector_MulDiv_used == True): 
						# Start only 1 Mul/Div/Dot at a time
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							muldiv_vector_RS,\
							ROB_Master)):
					return_value,instr_index = \
						instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_vector_MulDiv_used \
								= True;
						print("Vector MUL/DIV/DOT:");
						print_RS(muldiv_vector_RS);
						print_instruction_cycle_table();
				#else: # not ready yet. Stop this iteration since
				      # we need to issue in order
				#	block_further_start_ex = True;
					#break;

			elif ((instr["type"]=="ADD") or (instr["type"]=="SUB")\
				or (instr["type"]=="BNEZ")):
				if ((StartEX_stage_AddSub_used == True) and \
					(instr["type"] != "BNEZ")): 
						# Start only 1 add/sub at a time
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							addsub_RS,ROB_Master)):
					return_value,instr_index = \
						instruction_start_ex(instr);
					if (return_value == stage_success):
						if (instr["type"] != "BNEZ"):
							StartEX_stage_AddSub_used \
								= True;
						print("ADD/SUB:");
						print_RS(addsub_RS);
						print_instruction_cycle_table();
				
				#else: # not ready yet. Stop this iteration since
				      # we need to issue in order
				#	block_further_start_ex  = True;
					#break;

			elif ((instr["type"]=="MUL") or (instr["type"]=="DIV") \
				or (instr["type"]=="SLLI")):
				if (StartEX_stage_MulDiv_used == True):
					continue;
				if (instruction_ready_for_ex_type_alu(instr,\
							muldiv_RS,ROB_Master)):
					return_value,instr_index = \
						instruction_start_ex(instr);
					if (return_value == stage_success):
						StartEX_stage_MulDiv_used = True;
						print("MUL/DIV:");
						print_RS(muldiv_RS);
						print_instruction_cycle_table();
				#else: # not ready yet. Stop this iteration since
				      # we need to issue in order
				#	block_further_start_ex  = True;
					#break;

		elif (instr["current_stage"]==Stage.START_EX):
			instr["execution_cycles_completed"] += 1;

			#if (instr["type"] == "BNEZ"):
				#print("debug: BNEZ: exec_cycles_completed:",\
				#	instr["execution_cycles_completed"]);
				#print("debug: BNEZ: total_exec_cycles: ",\
				#	instr["total_execution_cycles"]);
			
			if (instr["execution_cycles_completed"] == \
					instr["total_execution_cycles"]-1):
				instruction_ex_complete(instr);
				#print("debug: instr: ",instr["type"]," completed EX");
				if (instr["type"] != "VSETVL"):
					print_ROB();
				if (instr["type"] == "BNEZ"):
					#print("debug: branch_taken:",branch_taken);
					if (instr["dest_value"] == 0): # branch not\
									# taken. 
						branch_taken = False;
						instrs_on_hold = False;
						AVL_complete = True; # All elements done
					else: # branch taken.  Do not allow subsequent\
					      # instructions to issue. But current BNEZ
					      # has to commit.
						branch_taken = True;
						# break;

				print_instruction_cycle_table();

		elif (instr["current_stage"]==Stage.EX_COMPLETE):
				#print("debug: instr: ",instr["type"]," completed EX");
			#return_value,ROB_Master = \
				instruction_writeback(instr,\
#						ROB_Master,LB,addsub_RS,muldiv_RS);
#						LB,addsub_RS,muldiv_RS);
						LB,VLB,addsub_RS,muldiv_RS,\
						addsub_vector_RS,muldiv_vector_RS);
		# if the writeback gets another instruction ready in the current
		# cycle (just because the other instruction is later in the loop)
		# do not schedule it. Run it in the next cycle.
		# However, if the other readied instruction is earlier to the one for 
		# which writeback happened, then ensure it runs in the next cycle.
				if (instr["type"] != "VSETVL"):
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
			if (instr["type"] == "VSETVL"):
				#vsetvl_in_progress = False; # Now other vector ops can start
				# not reqd since vsetvl runs separately
				Commit_stage_used = True;
				current_vl = instr["dest_value"]; # This is to be used by
						# all vector ops hereafter
				config_instr_completed_store.append\
					(instr);
				print_ARF();
				print_instruction_cycle_table();
				continue;

			if (return_value == vector_not_last_sequence):# not the 
			# last sequence of a vector. Only append to completed_store
			# but do not commit
				instr_completed_store.append(instr);

			if (return_value == stage_success):
				Commit_stage_used = True;
				instr_completed_store.append(instr);
				print_ARF();
				print_RAT();
				print_ROB();
				print_instruction_cycle_table();

#def run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master):
#def run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master):
def run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,instr_store\
			,instr_completed_store):
	current_cycle = 0;

	while(1):
		print("\n");
		current_cycle = overall_cycles_completed[0] + 1;	
		print("<<<<<< Cycle ",str(current_cycle)," >>>>>>");

		#_run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master);
		#_run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master);
		#_run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,\
		#		addsub_vector_RS,muldiv_vector_RS);
		_run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,\
				addsub_vector_RS,muldiv_vector_RS,instr_store);

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

	VLB_entry_present = False;

	for i in range(len(VLB)):
		if (VLB[i]["Instruction"] != ""):
			VLB_entry_present = True;
			break;

	# No LB entries present. Return
	if not LB_entry_present and not VLB_entry_present:
		return;

	if (LB_entry_present):
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

	if (VLB_entry_present): # VLB entry present
		print("VLB:");

		header_row = "";
		header_row = "Instruction\tBusy\tDestination_Tag\tAddress_Offset\t" +\
				"Source_Register\tStart_Element_Index\tNum_Elements";
		print(header_row);

		for i in range(len(VLB)):
			VLB_row = "";
			VLB_row = VLB[i]["Instruction"] + "\t" + VLB[i]["Busy"] + "\t" +\
				VLB[i]["Destination_Tag"] + "\t" + str(VLB[i]["Address_Offset"])\
				+ "\t" + str(VLB[i]["Source_Register"]) + "\t" + \
				str(VLB[i]["Start_Element_Index"]) + "\t" + \
				str(VLB[i]["Num_Elements"]);
			print(VLB_row);

def print_RS(RS):
	RS_entry_present = False;
	vector_type = False;

	for i in range(len(RS)):
		if (RS[i]["Instruction"] != ""):
			if ("V" in RS[i]["Instruction"]):
				vector_type = True;
			RS_entry_present = True;
			break;

	# No RS entries. return
	if (not RS_entry_present):
		return;

	header_row = "";
	header_row = "Instruction\tBusy\tDestination_Tag\tSource1_Tag\t" +\
			"Source2_Tag\tValue_Source1\tValue_Source2";
	if (vector_type == True):
		header_row += "\tStart_Element_Index\tNum_Elements";

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

		if (vector_type == True):
			RS_row += "\t\t" + str(RS[i]["Start_Element_Index"]) +"\t" \
					+ str(RS[i]["Num_Elements"]);

		print(RS_row);

def print_ROB():
	print("ROB:");

	header_row = "";
#	header_row += "ROB_Name\tInstruction\tDestination\tValue";
	header_row += "ROB_Name\tInstruction\tDestination\tElement Indices\t\t\t\t\t\t\tValues";
	print(header_row);

	for entry in ROB_Master["Entries"]:
		ROB_Entry_row = "";
		ROB_Entry_row += entry["ROB_Name"] + "\t\t" + entry["Instruction_Type"] \
				+ "\t\t" + entry["Destination"] + "\t\t" + \
				str(entry["Element_Indices"]) + "\t\t" + \
				str(entry["Values"]);

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
	base_instruction_print_length = 15; # for VLE32.
	header_row = "";
	column_count = 0;
	for column in instruction_cycle_table_header:
		#header_row += column + " ";
		if (column_count == 0):
			delim = "\t\t";
		elif (column == "Writeback"):
			delim = "\t\t";
		else:
			delim = "\t";
		header_row += column + delim;
		column_count += 1;

	print("Instruction Cycle Table:");
	print(header_row," ");
	for instr in instruction_cycle_table:
		data = str(instr["Instruction"]);
		# Print Issue cycle only for sequence 0
		if (instr["Sequence"] > 0):
		  instr["Issue"] = "";

		if (len(str(instr["Instruction"])) > base_instruction_print_length):
			instruction_delim = "\t";
		else:
			instruction_delim = "\t\t";
		data = str(instr["Instruction"]) + instruction_delim + str(instr["Issue"]) \
			+ "\t\t"\
			+ str(instr["Start_EX"]) + "\t\t" + str(instr["EX_Complete"])\
			+ "\t\t" + str(instr["Writeback"]) +"\t\t"\
			+ str(instr["Commit"]) + "\t\t" + str(instr["Sequence"]);

		print(data);

if __name__ == "__main__":
	# assume a list of instructions passed in
	#instructions = [0x00012183,0x0241c133,0x026280b3,0x008381b3,\
	#		0x023080b3,0x40508233,0x002200b3];
	# instructions:
	# vsetvl x5,x3,x4 (loop:)
	# vle32.v v1,(x1)
	# vle32.v v2,(x2)
	# vadd.vv v2,v1,v2
	# vdot.vv v2,v1,v2 # new. Encoding from v0.9 of spec. vtype reg layout\ 
                                # as per v0.10 of spec (appendix D)
	# vmul.vv v3,v1,v2
	# vse32.v v2,(x2)

	# sub x3,x3,x5
	# slli x5,x5,2 --> incorrect
	# slli x6,x5,2
	# add x1,x1,x5 --> incorrect
	# add x1,x1,x6
	# add x2,x2,x5 --> incorrect
	# add x2,x2,x6
	# bnez x3,loop

	#instructions = [0x0200e087,0x02016107,0x02208157,0x02016127]; 
	instructions = [0x0200e087,0x02016107,0x02208157,0xe6208157,0x961101d7,\
			0x02016127];
	#instructions_scalar = [0x405181b3,0x00229293,0x005080b3,0x00510133,\
			# 0xffffe595];

	# Fixed slli, and adds to use x6.
	instructions_scalar = [0x405181b3,0x00229313,0x006080b3,0x00610133,\
			0xffffe585]; # offset is -20 to get to the vload V1

	config_instructions = [0x8041f2d7]; # vsetvl

	instructions += instructions_scalar;	

	#ARF_values = [12,16,45,5,3,4,1,2,2,3];
	#ARF_values = [100,200];
	ARF_values = [100,300];

	if ((len(sys.argv) > 1) and (sys.argv[1] == "skip_setvl")):
			skip_setvl = True;

	# X3 and X4 for setvl
	#ARF_values.append(16); # X3
	#ARF_values.append(16); # X4
	
	if (skip_setvl):
		print("debug: skip_setvl set. current_vl: ",current_vl);
		ARF_values.append(AVL); # X3. As specified in configuration section
		ARF_values.append(16); # X4. Placeholder only. Unused.
				      # X5 is set within parse_instruction
		ROB_Master = init_ROB(len(instructions));
	else:
		ARF_values.append(32); # X3. Set this as per the required \
	#	ARF_values.append(16); # X3. Set this as per the required \
					# input to vsetvl
		ARF_values.append(16); # X4. Set this as per the required \
					# input to vsetvl
		ARF_values.append(0); # X6. This is handled differently in\
					# in init_ARF
		ROB_Master = init_ROB(len(config_instructions) + \
				len(instructions));

	#num_vector_registers  = 2; # need only 2 for the sequence of operations
	num_vector_registers  = 3; # need 3 for the sequence of operations
	init_ARF(ARF_values,num_vector_registers);

	init_RAT(len(ARF));
	#ROB_Master = init_ROB(len(config_instructions) + \
	#			len(instructions));
	#print("debug: ROB_Master: ",ROB_Master);

	LB = init_Load_Buffers(NUM_LOAD_BUFFERS);	
	addsub_RS,muldiv_RS = init_all_RS(NUM_ADDSUB_RS,NUM_MULDIV_RS);	

	if (not skip_setvl):
		for i in range(len(config_instructions)):
			parse_instruction(config_instructions[i]);

		#print("debug: parse vsetvl complete.");

		#init_instruction_cycle_table();
		init_instruction_cycle_table(config_instr_store);

		#run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,config_instr_store);
		run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,\
			config_instr_store,config_instr_completed_store);

		#print("debug: run vsetvl complete.");

	for i in range(len(instructions)):
		parse_instruction(instructions[i]);

	NUM_VECTOR_LOAD_BUFFERS = num_sequences;
	NUM_VECTOR_ADDSUB_RS = num_sequences;
	NUM_VECTOR_MULDIV_RS = num_sequences*2; # vdot and vmul
	VLB = init_Vector_Load_Buffers(NUM_VECTOR_LOAD_BUFFERS);	
	addsub_vector_RS,muldiv_vector_RS = init_all_vector_RS(NUM_VECTOR_ADDSUB_RS,\
					NUM_VECTOR_MULDIV_RS);

	init_instruction_cycle_table(instr_store);

	#run_instructions(LB,addsub_RS,muldiv_RS,ROB_Master);
	#run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master);
	run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,instr_store,\
						instr_completed_store);

	while(not AVL_complete):
		completed_elements = completed_elements + current_vl;
		print("debug: completed_elements: ",completed_elements);
		# if (not skip_setvl): # not applicable since we need to rerun from
				       # vload V1 onwards (and not vsetvl)
		# 	run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,\
		# 		config_instr_store,config_instr_completed_store);

		# We completed the first loop. Reset ROB
		ROB_Master = init_ROB(len(instructions));

		#print("debug: ROB_Master after 1st loop. ROB_Master: ",ROB_Master);
		instr_completed_store = [];

		for instr in instr_store:
			instr["current_stage"] = ""; # reset stage
			instr["execution_cycles_completed"] = 0; # reset exec cycle count

		if (instrs_on_hold):
			instrs_on_hold = False; # allow the next loop to run

		print("debug: num_sequences: ",num_sequences);

		NUM_VECTOR_LOAD_BUFFERS = num_sequences;
		NUM_VECTOR_ADDSUB_RS = num_sequences;
		NUM_VECTOR_MULDIV_RS = num_sequences*2; # vdot and vmul

		LB = init_Load_Buffers(NUM_LOAD_BUFFERS);	
		addsub_RS,muldiv_RS = init_all_RS(NUM_ADDSUB_RS,NUM_MULDIV_RS);	
		VLB = init_Vector_Load_Buffers(NUM_VECTOR_LOAD_BUFFERS);	
		addsub_vector_RS,muldiv_vector_RS = init_all_vector_RS(NUM_VECTOR_ADDSUB_RS,\
						NUM_VECTOR_MULDIV_RS);

		init_instruction_cycle_table(instr_store);
		run_instructions(LB,VLB,addsub_RS,muldiv_RS,ROB_Master,instr_store,\
						instr_completed_store);
		
