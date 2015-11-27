# svg_parser.py
# Copyright Max Kolosov 2009 maxkolosov@inbox.ru
# http://saxi.nm.ru/
# BSD license

import sys
from StringIO import StringIO
from xml.etree import cElementTree
from svg_path_regex import svg_path_parser

def print_error():
	exc, err, traceback = sys.exc_info()
	print exc, traceback.tb_frame.f_code.co_filename, 'ERROR ON LINE', traceback.tb_lineno, '\n', err
	del exc, err, traceback

px_x, px_y = 100, 100
relative_length_units = ('em', 'ex', 'px')
absolute_length_units = ('in', 'cm', 'mm', 'pt', 'pc')

def convert_length_units(value = None, func = float):
	if value.strip()[-2:] == 'in':
		value = func(value.strip()[:-2]) * px_x
	elif value.strip()[-2:] == 'mm':
		value = func(value.strip()[:-2]) * px_x / 25.2
	elif value.strip()[-2:] == 'cm':
		value = func(value.strip()[:-2]) * px_x / 2.52
	elif value.strip()[-2:] == 'pt':
		value = func(value.strip()[:-2]) * px_x / 72
	elif value.strip()[-2:] == 'pc':
		value = func(value.strip()[:-2]) * px_x / 72 * 12
	return value

def to_int(value = None):
	result = 1
	try:
		result = int(value)
	except:
		if value.strip()[-2:] in absolute_length_units:
			value = convert_length_units(value, int)
		elif value.strip()[-2:] in relative_length_units:
			value = value.strip()[:-2]
		elif value.strip()[-1:] == '%':
			value = float(value.strip()[:-1])/100
		try:
			result = int(value)
		except:
			try:
				result = int(float(value))
			except:
				print_error()
	return result

def to_float(value = None):
	result = 1.0
	try:
		result = float(value)
	except:
		if value.strip()[-2:] in absolute_length_units:
			value = convert_length_units(value)
		elif value.strip()[-2:] in relative_length_units:
			value = value.strip()[:-2]
		elif value.strip()[-1:] == '%':
			value = float(value.strip()[:-1])/100
		try:
			result = float(value)
		except:
			print_error()
	return result


def normal_color(value = '#000000'):
	if value[:2] == 'rgb':
		value = eval(value)
	elif value[0] == '#':
		if len(value[1:]) == 3:
			value = value[0]+value[1]*2+value[2]*2+value[3]*2
	elif 'url(#' in value:
		return value
	elif value.strip().lower() == 'none':
		value = None
	return value

def wx_alpha_opaque(value = 1.0):
	if value == 1.0:
		value = 255
	elif isinstance(value, float):
		if value < 0.0:
			value = abs(value)
		if 0.0 < value < 1.0:
			value = int(value * 255)
		if value > 255.0:
			value = 255
	if not isinstance(value, int):
		value = int(value)
	return value

def wx_color(value = '#000000', alpha_opaque = 255):
	if value is None:
		return '#000000'
	elif 'url(#' in value:
		return value
	else:
		return value

def parse_polyline_points(value = '', separator = ' '):
	result = []
	pre_result = value.split(separator)
	for item in pre_result:
		x, y = item.split(',')
		result.append((to_float(x), to_float(y)))
	return result

def parse_polygon_points(value = '', separator = ' ', alternative_separator = ', '):
	result = []
	pre_result = value.strip().split(separator)
	if len(pre_result) < 2:
		pre_result = pre_result[1].split(alternative_separator)
	for item in pre_result:
		xy = item.split(',')
		result.append((to_float(xy[0]), to_float(xy[1])))
	if pre_result[0] != pre_result[-1]:
		xy = pre_result[0].split(',')
		result.append((to_float(xy[0]), to_float(xy[1])))
	return result

def parse_style(value = ''):
	result = {}
	for item in value.split(';'):
		key_value = item.split(':')
		if len(key_value) > 1:
			key = key_value[0].strip()
			value = key_value[1].strip()
			if key in ('stroke', 'fill'):
				value = normal_color(value)
			elif key in ('stroke-width', ):
				value = to_float(value)
			elif key in ('stroke-opacity', 'fill-opacity'):
				value = wx_alpha_opaque(float(value))
			result[key] = value
	if result.has_key('stroke'):
		if result['stroke'] is None:
			del result['stroke']
		else:
			if not result.has_key('stroke-width'):
				result['stroke-width'] = 1.0
			if not result.has_key('stroke-opacity'):
				result['stroke-opacity'] = 255
			result['stroke'] = wx_color(result['stroke'], result['stroke-opacity'])
	if result.has_key('fill'):
		if result['fill'] is None:
			del result['fill']
		else:
			if result['fill'].find('url(#') == -1:
				if not result.has_key('fill-opacity'):
					result['fill-opacity'] = 255
				result['fill'] = wx_color(result['fill'], result['fill-opacity'])
	return result

def parse_text_style(value = ''):
	result = parse_style(value)
	if result.has_key('font-size'):
		real_value = to_int(result['font-size'])
		if result['font-size'].strip()[-2:] == 'px':
			result['font-size'] = int(real_value * 72 / px_x)
		else:
			result['font-size'] = real_value
	if result.has_key('font-style'):
		if result['font-style'].lower() == 'normal':
			result['font-style'] = 'normal'
		elif result['font-style'].lower() == 'slant':
			result['font-style'] = 'slant'
		elif result['font-style'].lower() == 'italic':
			result['font-style'] = 'italic'
	if result.has_key('font-weight'):
		if result['font-weight'].lower() == 'normal':
			result['font-weight'] = 'normal'
		elif result['font-weight'].lower() == 'light':
			result['font-weight'] = 'light'
		elif result['font-weight'].lower() == 'bold':
			result['font-weight'] = 'bold'
	return result

def parse_stop_style(element_dict, value = ''):
	for item in value.split(';'):
		key_value = item.split(':')
		if len(key_value) > 1:
			key = key_value[0].strip()
			value = key_value[1].strip()
			if key == 'stop-color':
				element_dict['stop-color'] = wx_color(normal_color(value))
			elif key == 'stop-opacity':
				element_dict['stop-opacity'] = wx_alpha_opaque(float(value))

def parse_transform(value = ''):
	result = {}
	for item in value.split(';'):
		if item.find('matrix') > -1:
				result['matrix'] = eval(item[item.find('matrix'):])
		elif item.find('translate') > -1:
				result['translate'] = eval(item[item.find('translate'):])
		elif item.find('rotate') > -1:
				result['rotate'] = eval(item[item.find('rotate'):])
		elif item.find('scale') > -1:
				result['scale'] = eval(item[item.find('scale'):])
		elif item.find('skewX') > -1:
				result['skewX'] = eval(item[item.find('skewX'):])
		elif item.find('skewY') > -1:
				result['skewY'] = eval(item[item.find('skewY'):])
	return result

def fill_svg_container(root, result = {}):
	for element in root.getchildren():
		element_dict = None
		if element.tag == 'defs' or element.tag[-5:] == '}defs':
			element_dict = {'svg_key':'defs', 'children':[]}
			fill_svg_container(element, element_dict)
		elif element.tag == 'metadata' or element.tag[-9:] == '}metadata':
			element_dict = {'svg_key':'metadata', 'value':element}
		elif element.tag == 'title' or element.tag[-6:] == '}title':
			result['title'] = element.text
			continue
		elif element.tag == 'desc' or element.tag[-5:] == '}desc':
			result['desc'] = element.text
			continue
		elif element.tag == 'stop' or element.tag[-5:] == '}stop':
			element_dict = {'svg_key':'stop',
				'offset':to_float(element.attrib.get('offset', 0)),
				'stop-color':wx_color(element.attrib.get('stop-color', '#000000')),
				'stop-opacity':wx_alpha_opaque(element.attrib.get('stop-opacity', 1.0))}
			if element.attrib.has_key('style'):
				parse_stop_style(element_dict, element.attrib['style'])
		elif element.tag == 'linearGradient' or element.tag[-15:] == '}linearGradient':
			element_dict = {'svg_key':'linearGradient', 'children':[]}
			for key, value in element.attrib.iteritems():
				if key == 'href' or key[-5:] == '}href':
					for item in result['children']:
						if item.get('id', '') == value.strip('#'):
							element_dict = dict(item)
			element_dict['x1'] = to_float(element.attrib.get('x1', 0))
			element_dict['y1'] = to_float(element.attrib.get('y1', 0))
			element_dict['x2'] = to_float(element.attrib.get('x2', 0))
			element_dict['y2'] = to_float(element.attrib.get('y2', 0))
			fill_svg_container(element, element_dict)
		elif element.tag == 'radialGradient' or element.tag[-15:] == '}radialGradient':
			element_dict = {'svg_key':'radialGradient', 'children':[]}
			for key, value in element.attrib.iteritems():
				if key == 'href' or key[-5:] == '}href':
					for item in result['children']:
						if item.get('id', '') == value.strip('#'):
							element_dict = dict(item)
			element_dict['cx'] = to_float(element.attrib.get('cx', 0))
			element_dict['cy'] = to_float(element.attrib.get('cy', 0))
			element_dict['r'] = to_float(element.attrib.get('r', 0))
			element_dict['fx'] = to_float(element.attrib.get('fx', 0))
			element_dict['fy'] = to_float(element.attrib.get('fy', 0))
			fill_svg_container(element, element_dict)
		elif element.tag == 'text' or element.tag[-5:] == '}text':
			text = element.text
			if text is None:
				text = ''
			element_dict = {'svg_key':'text', 'value':text, 'x':to_float(element.attrib['x']), 'y':to_float(element.attrib['y'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_text_style(element.attrib['style'])
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
		elif element.tag == 'line' or element.tag[-5:] == '}line':
			element_dict = {'svg_key':'line', 'x1':to_float(element.attrib['x1']), 'x2':to_float(element.attrib['x2']), 'y1':to_float(element.attrib['y1']), 'y2':to_float(element.attrib['y2'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			elif element.attrib.has_key('stroke'):
				element_dict['stroke'] = wx_color(normal_color(element.attrib['stroke']))
				if element.attrib.has_key('stroke-width'):
					element_dict['stroke-width'] = to_float(element.attrib['stroke-width'])
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
		elif element.tag == 'polyline' or element.tag[-9:] == '}polyline':
			element_dict = {'svg_key':'polyline', 'points':parse_polyline_points(element.attrib['points'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
		elif element.tag == 'polygon' or element.tag[-8:] == '}polygon':
			element_dict = {'svg_key':'polyline', 'points':parse_polygon_points(element.attrib['points'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
		elif element.tag == 'circle' or element.tag[-7:] == '}circle':
			element_dict = {'svg_key':'circle', 'cx':to_float(element.attrib['cx']), 'cy':to_float(element.attrib['cy']), 'r':to_float(element.attrib['r'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
		elif element.tag == 'ellipse' or element.tag[-8:] == '}ellipse':
			element_dict = {'svg_key':'ellipse', 'cx':to_float(element.attrib['cx']), 'cy':to_float(element.attrib['cy']), 'rx':to_float(element.attrib['rx']), 'ry':to_float(element.attrib['ry'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
		elif element.tag == 'rect' or element.tag[-5:] == '}rect':
			element_dict = {'svg_key':'rect', 'x':to_float(element.attrib['x']), 'y':to_float(element.attrib['y']), 'width':to_float(element.attrib['width']), 'height':to_float(element.attrib['height'])}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			if element.attrib.has_key('stroke'):
				element_dict['stroke'] = wx_color(normal_color(element.attrib['stroke']))
				if element.attrib.has_key('stroke-width'):
					element_dict['stroke-width'] = to_float(element.attrib['stroke-width'])
			if element.attrib.has_key('fill'):
				element_dict['fill'] = wx_color(normal_color(element.attrib['fill']))
			if element.attrib.has_key('rx'):
				element_dict['rx'] = to_float(element.attrib['rx'])
		elif element.tag == 'path' or element.tag[-5:] == '}path':
			try:
				d = svg_path_parser.parse(element.attrib['d'])
			except:
				print_error()
				print element.attrib['d']
				continue
			element_dict = {'svg_key':'path', 'd':d}
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
		elif element.tag == 'image' or element.tag[-6:] == '}image':
			element_dict = {'svg_key':'image',
				'x':to_float(element.attrib.get('x', 0)),
				'y':to_float(element.attrib.get('y', 0)),
				'width':to_float(element.attrib.get('width', 0)),
				'height':to_float(element.attrib.get('height', 0))}
			for key, value in element.attrib.iteritems():
				if key == 'href' or key[-5:] == '}href':
					element_dict['href'] = value
		elif element.tag == 'g' or element.tag[-2:] == '}g':
			element_dict = {'svg_key':'g', 'children':[]}
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			fill_svg_container(element, element_dict)
		elif element.tag == 'a' or element.tag[-2:] == '}a':
			element_dict = {'svg_key':'a', 'children':[]}
			if element.attrib.has_key('transform'):
				element_dict['transform'] = element.attrib['transform']
			if element.attrib.has_key('style'):
				element_dict['style'] = parse_style(element.attrib['style'])
			for key, value in element.attrib.iteritems():
				if key == 'href' or key[-5:] == '}href':
					element_dict['href'] = value
			fill_svg_container(element, element_dict)
		else:
			comment = 'Sorry, unimplemented svg tag'
			element_dict = {'svg_key':element.tag, 'value':element, 'comment':comment}
			print comment, ': ', element.tag
		element_dict['id'] = element.attrib.get('id', str(id(element)))
		result['children'].append(element_dict)

def parse_xml_data(xml_data = ''):
	result = {'width':100.0, 'height':100.0,
		'viewBox':[0, 0, 1000, 1000],
		'origin_x':0, 'origin_y':0,
		'scale_x':0, 'scale_y':0,
		'children':[]}
	dom = cElementTree.parse(StringIO(xml_data))
	if isinstance(dom, cElementTree.ElementTree):
		svg_root = dom.getroot()
		width, height = '0', '0'
		if svg_root.attrib.has_key('width'):
			width = svg_root.attrib['width']
			result['width'] = to_float(width)
		else:
			result['width'] = 0
		if svg_root.attrib.has_key('height'):
			height = svg_root.attrib['height']
			result['height'] = to_float(height)
		else:
			result['height'] = 0
		if svg_root.attrib.has_key('viewBox'):
			result['viewBox'] = []
			for item in svg_root.attrib['viewBox'].split():
				result['viewBox'].append(float(item))
			if width[-1] == '%':
				result['width'] = result['viewBox'][2]*result['width']
			if height[-1] == '%':
				result['height'] = result['viewBox'][3]*result['height']
		else:
			result['viewBox'][2] = result['width']
			result['viewBox'][3] = result['height']
		result['origin_x'], result['origin_y'] = result['viewBox'][0], result['viewBox'][1]
		if result['origin_x'] < 0:
			result['origin_x'] *= -1
		if result['origin_y'] < 0:
			result['origin_y'] *= -1
		if result['width'] != result['viewBox'][2]:
			result['scale_x'] = result['width'] / result['viewBox'][2]
			if result['width'] < result['viewBox'][2]:
				result['scale_x'] *= -1
		if result['height'] != result['viewBox'][3]:
			result['scale_y'] = result['height'] / result['viewBox'][3]
			if result['height'] < result['viewBox'][3]:
				result['scale_y'] *= -1
		fill_svg_container(svg_root, result)
	return result
