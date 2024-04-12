from drepr.readers.prelude import read_source_csv
from drepr.utils.attr_data import AttributeData
from drepr.utils.attr_data import AttributeData
from drepr.utils.attr_data import AttributeData
from drepr.program_generation.preprocessing import ContextImpl
from drepr.utils.attr_data import AttributeData
from drepr.program_generation.preprocessing import ContextImpl
from drepr.utils.attr_data import AttributeData
from drepr.program_generation.preprocessing import ContextImpl
from drepr.utils.attr_data import AttributeData
from drepr.program_generation.preprocessing import ContextImpl
from drepr.utils.attr_data import AttributeData
from drepr.writers.rdfgraph_writer import RDFGraphWriter

def main(resource_default_0, output_file_1):
	resource_data_default_2 = read_source_csv(resource_default_0)
	
	deposit_type_missing_values_3 = {""}
	ore_missing_values_4 = {"", "0.0"}
	ni_missing_values_5 = {""}
	co_missing_values_6 = {""}
	project_uri_missing_values_7 = {None}
	deposit_type_uri_missing_values_8 = {None}
	lat_long_missing_values_9 = {None}
	loc_id_missing_values_10 = {None}
	ni_uri_missing_values_11 = {None}
	co_uri_missing_values_12 = {None}
	document_uri_missing_values_13 = {None}
	resource_data___preproc__project_uri_25 = preprocess_0(resource_data_default_2)
	resource_data___preproc__deposit_type_uri_40 = preprocess_1(resource_data_default_2)
	preprocess_2(resource_data_default_2)
	resource_data___preproc__lat_long_59 = preprocess_3(resource_data_default_2)
	resource_data___preproc__loc_id_72 = preprocess_4(resource_data_default_2)
	resource_data___preproc__ni_uri_85 = preprocess_5(resource_data_default_2)
	resource_data___preproc__co_uri_98 = preprocess_6(resource_data_default_2)
	resource_data___preproc__document_uri_106 = preprocess_7(resource_data_default_2)
	writer_107 = RDFGraphWriter({"mndr": "https://minmod.isi.edu/resource/", "geokb": "https://geokb.wikibase.cloud/entity/", "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "xsd": "http://www.w3.org/2001/XMLSchema#", "owl": "http://www.w3.org/2002/07/owl#", "drepr": "https://purl.org/drepr/1.0/", "geo": "http://www.opengis.net/ont/geosparql#"})
	
	# Transform records of class mndr:DepositTypeCandidate:1
	start_108 = 1
	end_109 = len(resource_data___preproc__deposit_type_uri_40)
	for deposit_type_uri_index_0_110 in range(start_108, end_109):
		deposit_type_uri_value_0_111 = resource_data___preproc__deposit_type_uri_40[deposit_type_uri_index_0_110]
		start_112 = 8
		end_113 = 11
		for deposit_type_uri_index_1_114 in range(start_112, end_113):
			deposit_type_uri_value_1_115 = deposit_type_uri_value_0_111[deposit_type_uri_index_1_114]
			if deposit_type_uri_value_1_115 in deposit_type_uri_missing_values_8:
				continue
			writer_107.begin_record("https://minmod.isi.edu/resource/DepositTypeCandidate", deposit_type_uri_value_1_115, False, True)
			
			# Retrieve value of data property: deposit_type
			deposit_type_index_0_116 = deposit_type_uri_index_0_110
			deposit_type_value_0_117 = resource_data_default_2[deposit_type_index_0_116]
			deposit_type_index_1_118 = deposit_type_uri_index_1_114
			deposit_type_value_1_119 = deposit_type_value_0_117[deposit_type_index_1_118]
			if not (deposit_type_value_1_119 in deposit_type_missing_values_3):
				writer_107.write_data_property("https://minmod.isi.edu/resource/observed_name", deposit_type_value_1_119, "http://www.w3.org/2001/XMLSchema#string")
			else:
				writer_107.abort_record()
				continue
			
			# Set static properties
			writer_107.write_data_property("https://minmod.isi.edu/resource/confidence", 0.5, None)
			writer_107.write_data_property("https://minmod.isi.edu/resource/source", "sand", None)
			
			writer_107.end_record()
	
	# Transform records of class mndr:LocationInfo:1
	start_120 = 1
	end_121 = len(resource_data___preproc__loc_id_72)
	for loc_id_index_0_122 in range(start_120, end_121):
		loc_id_value_0_123 = resource_data___preproc__loc_id_72[loc_id_index_0_122]
		loc_id_value_1_124 = loc_id_value_0_123[0]
		if ((15, loc_id_value_1_124)) in loc_id_missing_values_10:
			continue
		writer_107.begin_record("https://minmod.isi.edu/resource/LocationInfo", (15, loc_id_value_1_124), True, False)
		
		# Retrieve value of data property: lat_long
		lat_long_index_0_125 = loc_id_index_0_122
		lat_long_value_0_126 = resource_data___preproc__lat_long_59[lat_long_index_0_125]
		lat_long_value_1_127 = lat_long_value_0_126[2]
		if not (lat_long_value_1_127 in lat_long_missing_values_9):
			writer_107.write_data_property("https://minmod.isi.edu/resource/location", lat_long_value_1_127, "http://www.opengis.net/ont/geosparql#wktLiteral")
		
		# Retrieve value of data property: country
		country_index_0_128 = loc_id_index_0_122
		country_value_0_129 = resource_data_default_2[country_index_0_128]
		country_value_1_130 = country_value_0_129[0]
		writer_107.write_data_property("https://minmod.isi.edu/resource/country", country_value_1_130, None)
		
		writer_107.end_record()
	
	# Transform records of class mndr:Ore:1
	start_131 = 1
	end_132 = len(resource_data_default_2)
	for ore_index_0_133 in range(start_131, end_132):
		ore_value_0_134 = resource_data_default_2[ore_index_0_133]
		ore_value_1_135 = ore_value_0_134[12]
		writer_107.begin_record("https://minmod.isi.edu/resource/Ore", (8, ore_index_0_133), True, True)
		
		# Retrieve value of data property: ore
		if not (ore_value_1_135 in ore_missing_values_4):
			writer_107.write_data_property("https://minmod.isi.edu/resource/ore_value", ore_value_1_135, "http://www.w3.org/2001/XMLSchema#decimal")
		else:
			writer_107.abort_record()
			continue
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/ore_unit", "https://minmod.isi.edu/resource/Q202", "https://purl.org/drepr/1.0/uri")
		
		if writer_107.is_record_empty():
			writer_107.abort_record()
		else:
			writer_107.end_record()
	
	# Transform records of class mndr:Grade:Ni
	start_136 = 1
	end_137 = len(resource_data_default_2)
	for ni_index_0_138 in range(start_136, end_137):
		ni_value_0_139 = resource_data_default_2[ni_index_0_138]
		ni_value_1_140 = ni_value_0_139[13]
		writer_107.begin_record("https://minmod.isi.edu/resource/Grade", (9, ni_index_0_138), True, True)
		
		# Retrieve value of data property: ni
		if not (ni_value_1_140 in ni_missing_values_5):
			writer_107.write_data_property("https://minmod.isi.edu/resource/grade_value", ni_value_1_140, "http://www.w3.org/2001/XMLSchema#decimal")
		else:
			writer_107.abort_record()
			continue
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/grade_unit", "https://minmod.isi.edu/resource/Q201", "https://purl.org/drepr/1.0/uri")
		
		if writer_107.is_record_empty():
			writer_107.abort_record()
		else:
			writer_107.end_record()
	
	# Transform records of class mndr:Document:1
	document_uri_value_0_141 = resource_data___preproc__document_uri_106[1]
	document_uri_value_1_142 = document_uri_value_0_141[1]
	if not (document_uri_value_1_142 in document_uri_missing_values_13):
		writer_107.begin_record("https://minmod.isi.edu/resource/Document", document_uri_value_1_142, False, False)
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/title", "The New Century for Nickel Resources, Reserves, and Mining: Reassessing the Sustainability of the Devil\u2019s Metal", None)
		writer_107.write_data_property("https://minmod.isi.edu/resource/doi", "10.5382/econgeo.4950", None)
		writer_107.write_data_property("https://minmod.isi.edu/resource/uri", "https://doi.org/10.5382/econgeo.4950", None)
		
		writer_107.end_record()
	
	# Transform records of class mndr:Reference:1
	refval_value_0_143 = resource_data_default_2[0]
	refval_value_1_144 = refval_value_0_143[0]
	writer_107.begin_record("https://minmod.isi.edu/resource/Reference", (11, refval_value_1_144), True, False)
	
	# Retrieve value of object property: document_uri
	document_uri_value_0_145 = resource_data___preproc__document_uri_106[1]
	document_uri_value_1_146 = document_uri_value_0_145[1]
	if writer_107.has_written_record(document_uri_value_1_146):
		writer_107.write_object_property("https://minmod.isi.edu/resource/document", document_uri_value_1_146, True, False, False)
	
	writer_107.end_record()
	
	# Transform records of class mndr:MineralInventory:Ni
	start_147 = 1
	end_148 = len(resource_data___preproc__ni_uri_85)
	for ni_uri_index_0_149 in range(start_147, end_148):
		ni_uri_value_0_150 = resource_data___preproc__ni_uri_85[ni_uri_index_0_149]
		ni_uri_value_1_151 = ni_uri_value_0_150[13]
		if ni_uri_value_1_151 in ni_uri_missing_values_11:
			continue
		writer_107.begin_record("https://minmod.isi.edu/resource/MineralInventory", ni_uri_value_1_151, False, True)
		
		# Retrieve value of data property: category
		category_index_0_152 = ni_uri_index_0_149
		category_value_0_153 = resource_data_default_2[category_index_0_152]
		category_value_1_154 = category_value_0_153[11]
		writer_107.write_data_property("https://minmod.isi.edu/resource/category", category_value_1_154, "https://purl.org/drepr/1.0/uri")
		
		# Retrieve value of object property: ore
		ore_index_0_155 = ni_uri_index_0_149
		ore_value_0_156 = resource_data_default_2[ore_index_0_155]
		ore_value_1_157 = ore_value_0_156[12]
		if writer_107.has_written_record((8, ore_index_0_155)):
			writer_107.write_object_property("https://minmod.isi.edu/resource/ore", (8, ore_index_0_155), False, True, False)
		
		# Retrieve value of object property: ni
		ni_index_0_158 = ni_uri_index_0_149
		ni_value_0_159 = resource_data_default_2[ni_index_0_158]
		ni_value_1_160 = ni_value_0_159[13]
		if writer_107.has_written_record((9, ni_index_0_158)):
			writer_107.write_object_property("https://minmod.isi.edu/resource/grade", (9, ni_index_0_158), False, True, False)
		else:
			writer_107.abort_record()
			continue
		
		# Retrieve value of object property: refval
		refval_value_0_161 = resource_data_default_2[0]
		refval_value_1_162 = refval_value_0_161[0]
		writer_107.write_object_property("https://minmod.isi.edu/resource/reference", (11, refval_value_1_162), False, True, False)
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/commodity", "https://minmod.isi.edu/resource/Q578", "https://purl.org/drepr/1.0/uri")
		
		writer_107.end_record()
	
	# Transform records of class mndr:Grade:Co
	start_163 = 1
	end_164 = len(resource_data_default_2)
	for co_index_0_165 in range(start_163, end_164):
		co_value_0_166 = resource_data_default_2[co_index_0_165]
		co_value_1_167 = co_value_0_166[14]
		writer_107.begin_record("https://minmod.isi.edu/resource/Grade", (10, co_index_0_165), True, True)
		
		# Retrieve value of data property: co
		if not (co_value_1_167 in co_missing_values_6):
			writer_107.write_data_property("https://minmod.isi.edu/resource/grade_value", co_value_1_167, "http://www.w3.org/2001/XMLSchema#decimal")
		else:
			writer_107.abort_record()
			continue
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/grade_unit", "https://minmod.isi.edu/resource/Q201", "https://purl.org/drepr/1.0/uri")
		
		if writer_107.is_record_empty():
			writer_107.abort_record()
		else:
			writer_107.end_record()
	
	# Transform records of class mndr:MineralInventory:Co
	start_168 = 1
	end_169 = len(resource_data___preproc__co_uri_98)
	for co_uri_index_0_170 in range(start_168, end_169):
		co_uri_value_0_171 = resource_data___preproc__co_uri_98[co_uri_index_0_170]
		co_uri_value_1_172 = co_uri_value_0_171[14]
		if co_uri_value_1_172 in co_uri_missing_values_12:
			continue
		writer_107.begin_record("https://minmod.isi.edu/resource/MineralInventory", co_uri_value_1_172, False, True)
		
		# Retrieve value of data property: category
		category_index_0_173 = co_uri_index_0_170
		category_value_0_174 = resource_data_default_2[category_index_0_173]
		category_value_1_175 = category_value_0_174[11]
		writer_107.write_data_property("https://minmod.isi.edu/resource/category", category_value_1_175, "https://purl.org/drepr/1.0/uri")
		
		# Retrieve value of object property: ore
		ore_index_0_176 = co_uri_index_0_170
		ore_value_0_177 = resource_data_default_2[ore_index_0_176]
		ore_value_1_178 = ore_value_0_177[12]
		if writer_107.has_written_record((8, ore_index_0_176)):
			writer_107.write_object_property("https://minmod.isi.edu/resource/ore", (8, ore_index_0_176), False, True, False)
		
		# Retrieve value of object property: co
		co_index_0_179 = co_uri_index_0_170
		co_value_0_180 = resource_data_default_2[co_index_0_179]
		co_value_1_181 = co_value_0_180[14]
		if writer_107.has_written_record((10, co_index_0_179)):
			writer_107.write_object_property("https://minmod.isi.edu/resource/grade", (10, co_index_0_179), False, True, False)
		else:
			writer_107.abort_record()
			continue
		
		# Retrieve value of object property: refval
		refval_value_0_182 = resource_data_default_2[0]
		refval_value_1_183 = refval_value_0_182[0]
		writer_107.write_object_property("https://minmod.isi.edu/resource/reference", (11, refval_value_1_183), False, True, False)
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/commodity", "https://minmod.isi.edu/resource/Q537", "https://purl.org/drepr/1.0/uri")
		
		writer_107.end_record()
	
	# Transform records of class mndr:MineralSite:1
	start_184 = 1
	end_185 = len(resource_data___preproc__project_uri_25)
	for project_uri_index_0_186 in range(start_184, end_185):
		project_uri_value_0_187 = resource_data___preproc__project_uri_25[project_uri_index_0_186]
		project_uri_value_1_188 = project_uri_value_0_187[1]
		if project_uri_value_1_188 in project_uri_missing_values_7:
			continue
		writer_107.begin_record("https://minmod.isi.edu/resource/MineralSite", project_uri_value_1_188, False, False)
		
		# Retrieve value of data property: project
		project_index_0_189 = project_uri_index_0_186
		project_value_0_190 = resource_data_default_2[project_index_0_189]
		project_value_1_191 = project_value_0_190[1]
		writer_107.write_data_property("http://www.w3.org/2000/01/rdf-schema#label", project_value_1_191, None)
		
		# Retrieve value of data property: project
		project_index_0_192 = project_uri_index_0_186
		project_value_0_193 = resource_data_default_2[project_index_0_192]
		project_value_1_194 = project_value_0_193[1]
		writer_107.write_data_property("https://minmod.isi.edu/resource/name", project_value_1_194, None)
		
		# Retrieve value of data property: project
		project_index_0_195 = project_uri_index_0_186
		project_value_0_196 = resource_data_default_2[project_index_0_195]
		project_value_1_197 = project_value_0_196[1]
		writer_107.write_data_property("https://minmod.isi.edu/resource/record_id", project_value_1_197, None)
		
		# Retrieve value of object property: deposit_type_uri
		deposit_type_uri_index_0_198 = project_uri_index_0_186
		deposit_type_uri_value_0_199 = resource_data___preproc__deposit_type_uri_40[deposit_type_uri_index_0_198]
		start_200 = 8
		end_201 = 11
		for deposit_type_uri_index_1_202 in range(start_200, end_201):
			deposit_type_uri_value_1_203 = deposit_type_uri_value_0_199[deposit_type_uri_index_1_202]
			if writer_107.has_written_record(deposit_type_uri_value_1_203):
				writer_107.write_object_property("https://minmod.isi.edu/resource/deposit_type_candidate", deposit_type_uri_value_1_203, False, False, False)
		
		# Retrieve value of object property: loc_id
		loc_id_index_0_204 = project_uri_index_0_186
		loc_id_value_0_205 = resource_data___preproc__loc_id_72[loc_id_index_0_204]
		loc_id_value_1_206 = loc_id_value_0_205[0]
		writer_107.write_object_property("https://minmod.isi.edu/resource/location_info", (15, loc_id_value_1_206), False, True, False)
		
		# Retrieve value of object property: ni_uri
		ni_uri_index_0_207 = project_uri_index_0_186
		ni_uri_value_0_208 = resource_data___preproc__ni_uri_85[ni_uri_index_0_207]
		ni_uri_value_1_209 = ni_uri_value_0_208[13]
		if writer_107.has_written_record(ni_uri_value_1_209):
			writer_107.write_object_property("https://minmod.isi.edu/resource/mineral_inventory", ni_uri_value_1_209, False, False, False)
		
		# Retrieve value of object property: co_uri
		co_uri_index_0_210 = project_uri_index_0_186
		co_uri_value_0_211 = resource_data___preproc__co_uri_98[co_uri_index_0_210]
		co_uri_value_1_212 = co_uri_value_0_211[14]
		if writer_107.has_written_record(co_uri_value_1_212):
			writer_107.write_object_property("https://minmod.isi.edu/resource/mineral_inventory", co_uri_value_1_212, False, False, False)
		
		# Set static properties
		writer_107.write_data_property("https://minmod.isi.edu/resource/source_id", "https://doi.org/10.5382/econgeo.4950", None)
		
		writer_107.end_record()
	
	writer_107.write_to_file(output_file_1)

def preprocess_0(resource_data_14):
	project_uri_17 = AttributeData.from_raw_path(["1..:1", 1])
	start_18 = 1
	end_19 = len(resource_data_14)
	for preproc_0_path_index_0_20 in range(start_18, end_19):
		preproc_0_path_value_0_21 = resource_data_14[preproc_0_path_index_0_20]
		project_uri_value_0_22 = project_uri_17[preproc_0_path_index_0_20]
		preproc_0_path_value_1_23 = preproc_0_path_value_0_21[1]
		project_uri_value_1_24 = project_uri_value_0_22[1]
		project_uri_value_0_22[1] = preproc_0_customfn_16(preproc_0_path_value_1_23)
	return project_uri_17

def get_preproc_0_customfn():
	from slugify import slugify
	def preproc_0_customfn(value):
		value = "__".join(["site", slugify("10.5382/econgeo.4950"), slugify(value)])
		return "https://minmod.isi.edu/resource/" + value
	return preproc_0_customfn

preproc_0_customfn_16 = get_preproc_0_customfn()

def preprocess_1(resource_data_26):
	deposit_type_uri_29 = AttributeData.from_raw_path(["1..:1", "8..11:1"])
	start_30 = 1
	end_31 = len(resource_data_26)
	for preproc_1_path_index_0_32 in range(start_30, end_31):
		preproc_1_path_value_0_33 = resource_data_26[preproc_1_path_index_0_32]
		deposit_type_uri_value_0_34 = deposit_type_uri_29[preproc_1_path_index_0_32]
		start_35 = 8
		end_36 = 11
		for preproc_1_path_index_1_37 in range(start_35, end_36):
			preproc_1_path_value_1_38 = preproc_1_path_value_0_33[preproc_1_path_index_1_37]
			deposit_type_uri_value_1_39 = deposit_type_uri_value_0_34[preproc_1_path_index_1_37]
			deposit_type_uri_value_0_34[preproc_1_path_index_1_37] = preproc_1_customfn_28(preproc_1_path_value_1_38)
	return deposit_type_uri_29

def get_preproc_1_customfn():
	from slugify import slugify
	def preproc_1_customfn(value):
		if value != "":
			value = "__".join(["dety", slugify("10.5382/econgeo.4950"), slugify(value)])
			return "https://minmod.isi.edu/resource/" + value
	return preproc_1_customfn

preproc_1_customfn_28 = get_preproc_1_customfn()

def preprocess_2(resource_data_41):
	start_43 = 1
	end_44 = len(resource_data_41)
	for preproc_2_path_index_0_45 in range(start_43, end_44):
		preproc_2_path_value_0_46 = resource_data_41[preproc_2_path_index_0_45]
		preproc_2_path_value_1_47 = preproc_2_path_value_0_46[11]
		preproc_2_path_value_0_46[11] = preproc_2_customfn(preproc_2_path_value_1_47)

def preproc_2_customfn(value):
	return "https://minmod.isi.edu/resource/" + value


def preprocess_3(resource_data_48):
	lat_long_51 = AttributeData.from_raw_path(["1..:1", 2])
	start_52 = 1
	end_53 = len(resource_data_48)
	for preproc_3_path_index_0_54 in range(start_52, end_53):
		preproc_3_path_value_0_55 = resource_data_48[preproc_3_path_index_0_54]
		lat_long_value_0_56 = lat_long_51[preproc_3_path_index_0_54]
		preproc_3_path_value_1_57 = preproc_3_path_value_0_55[2]
		lat_long_value_1_58 = lat_long_value_0_56[2]
		lat_long_value_0_56[2] = preproc_3_customfn(preproc_3_path_value_1_57, ContextImpl(resource_data_48, (preproc_3_path_index_0_54, 2)))
	return lat_long_51

def preproc_3_customfn(value, context):
	lat = value.strip()
	long = context.get_value((context.get_index()[0], 3)).strip()
	if lat != "" and long != "":
		return f"POINT ({long} {lat})"


def preprocess_4(resource_data_60):
	loc_id_64 = AttributeData.from_raw_path(["1..:1", 0])
	start_65 = 1
	end_66 = len(resource_data_60)
	for preproc_4_path_index_0_67 in range(start_65, end_66):
		preproc_4_path_value_0_68 = resource_data_60[preproc_4_path_index_0_67]
		loc_id_value_0_69 = loc_id_64[preproc_4_path_index_0_67]
		preproc_4_path_value_1_70 = preproc_4_path_value_0_68[0]
		loc_id_value_1_71 = loc_id_value_0_69[0]
		loc_id_value_0_69[0] = preproc_4_customfn_63(preproc_4_path_value_1_70, ContextImpl(resource_data_60, (preproc_4_path_index_0_67, 0)))
	return loc_id_64

def get_preproc_4_customfn():
	from slugify import slugify
	def preproc_4_customfn(value, context):
		idx = context.get_index()[0]
		country, lat, long = context.get_value((idx, 1)), context.get_value((idx, 2)), context.get_value((idx, 3))
		if country == "" and lat == "" and long == "":
			return None
		return (country, lat, long)
	return preproc_4_customfn

preproc_4_customfn_63 = get_preproc_4_customfn()

def preprocess_5(resource_data_73):
	ni_uri_77 = AttributeData.from_raw_path(["1..:1", 13])
	start_78 = 1
	end_79 = len(resource_data_73)
	for preproc_5_path_index_0_80 in range(start_78, end_79):
		preproc_5_path_value_0_81 = resource_data_73[preproc_5_path_index_0_80]
		ni_uri_value_0_82 = ni_uri_77[preproc_5_path_index_0_80]
		preproc_5_path_value_1_83 = preproc_5_path_value_0_81[13]
		ni_uri_value_1_84 = ni_uri_value_0_82[13]
		ni_uri_value_0_82[13] = preproc_5_customfn_76(preproc_5_path_value_1_83, ContextImpl(resource_data_73, (preproc_5_path_index_0_80, 13)))
	return ni_uri_77

def get_preproc_5_customfn():
	from slugify import slugify
	def preproc_5_customfn(value, context):
		if value == "":
			return None
		row_idx = context.get_index()[0]
		category = context.get_value((row_idx, 11))
		mineral_site = context.get_value((row_idx, 1))
		value = "__".join([
  "inv", slugify("10.5382/econgeo.4950"),
  slugify(mineral_site), "Q578", slugify(category),
])
		return "https://minmod.isi.edu/resource/" + value
	return preproc_5_customfn

preproc_5_customfn_76 = get_preproc_5_customfn()

def preprocess_6(resource_data_86):
	co_uri_90 = AttributeData.from_raw_path(["1..:1", 14])
	start_91 = 1
	end_92 = len(resource_data_86)
	for preproc_6_path_index_0_93 in range(start_91, end_92):
		preproc_6_path_value_0_94 = resource_data_86[preproc_6_path_index_0_93]
		co_uri_value_0_95 = co_uri_90[preproc_6_path_index_0_93]
		preproc_6_path_value_1_96 = preproc_6_path_value_0_94[14]
		co_uri_value_1_97 = co_uri_value_0_95[14]
		co_uri_value_0_95[14] = preproc_6_customfn_89(preproc_6_path_value_1_96, ContextImpl(resource_data_86, (preproc_6_path_index_0_93, 14)))
	return co_uri_90

def get_preproc_6_customfn():
	from slugify import slugify
	def preproc_6_customfn(value, context):
		if value == "":
			return None
		row_idx = context.get_index()[0]
		category = context.get_value((row_idx, 11))
		mineral_site = context.get_value((row_idx, 1))
		value = "__".join([
  "inv", slugify("10.5382/econgeo.4950"),
  slugify(mineral_site), "Q537", slugify(category),
])
		return "https://minmod.isi.edu/resource/" + value
	return preproc_6_customfn

preproc_6_customfn_89 = get_preproc_6_customfn()

def preprocess_7(resource_data_99):
	document_uri_101 = AttributeData.from_raw_path([1, 1])
	preproc_7_path_value_0_102 = resource_data_99[1]
	document_uri_value_0_103 = document_uri_101[1]
	preproc_7_path_value_1_104 = preproc_7_path_value_0_102[1]
	document_uri_value_1_105 = document_uri_value_0_103[1]
	document_uri_value_0_103[1] = preproc_7_customfn(preproc_7_path_value_1_104)
	return document_uri_101

def preproc_7_customfn(value):
	return "https://doi.org/10.5382/econgeo.4950"


if __name__ == "__main__":
	import sys
	
	main(*sys.argv[1:])