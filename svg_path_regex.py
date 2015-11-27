""" Small hand-written recursive descent parser for SVG <path> data.

This software is OSI Certified Open Source Software.
OSI Certified is a certification mark of the Open Source Initiative.

Copyright (c) 2006, Enthought, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of Enthought, Inc. nor the names of its contributors may
   be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys, re

def print_error():
	exc, err, traceback = sys.exc_info()
	print exc, traceback.tb_frame.f_code.co_filename, 'ERROR ON LINE', traceback.tb_lineno, '\n', err
	del exc, err, traceback

class _EOF(object):
	def __repr__(self):
		return 'EOF'
EOF = _EOF()

lexicon = [
	('float', r'[-\+]?(?:(?:[0-9]*\.[0-9]+)|(?:[0-9]+\.))(?:[Ee][-\+]?[0-9]+)?'),
	('int', r'[-\+]?[0-9]+'),
	('command', r'[AaCcHhLlMmQqSsTtVvZz]'),
]

class Lexer(object):
	""" Break SVG path data into tokens.

	The SVG spec requires that tokens are greedy. This lexer relies on Python's
	regexes defaulting to greediness.

	This style of implementation was inspired by this article:

		http://www.gooli.org/blog/a-simple-lexer-in-python/
	"""
	def __init__(self, lexicon):
		self.lexicon = lexicon
		parts = []
		for name, regex in lexicon:
			parts.append('(?P<%s>%s)' % (name, regex))
		self.regex_string = '|'.join(parts)
		self.regex = re.compile(self.regex_string)

	def lex(self, text):
		#~ self.text = text
		""" Yield (token_type, str_data) tokens.

		The last token will be (EOF, None) where EOF is the singleton object
		defined in this module.
		"""
		for match in self.regex.finditer(text):
			for name, _ in self.lexicon:
				m = match.group(name)
				if m is not None:
					yield (name, m)
					break
		yield (EOF, None)

svg_path_lexer = Lexer(lexicon)

class SVGPathParser(object):
	""" Parse SVG <path> data into a list of commands.

	Each distinct command will take the form of a tuple (command, data). The
	`command` is just the character string that starts the command group in the
	<path> data, so 'M' for absolute moveto, 'm' for relative moveto, 'Z' for
	closepath, etc. The kind of data it carries with it depends on the command.
	For 'Z' (closepath), it's just None. The others are lists of individual
	argument groups. Multiple elements in these lists usually mean to repeat the
	command. The notable exception is 'M' (moveto) where only the first element
	is truly a moveto. The remainder are implicit linetos.

	See the SVG documentation for the interpretation of the individual elements
	for each command.

	The main method is `parse(text)`. It can only consume actual strings, not
	filelike objects or iterators.
	"""

	def __init__(self, lexer = svg_path_lexer):
		self.lexer = lexer

		self.command_dispatch = {
			'Z': self.rule_closepath,
			'z': self.rule_closepath,
			'M': self.rule_moveto_or_lineto,
			'm': self.rule_moveto_or_lineto,
			'L': self.rule_moveto_or_lineto,
			'l': self.rule_moveto_or_lineto,
			'H': self.rule_orthogonal_lineto,
			'h': self.rule_orthogonal_lineto,
			'V': self.rule_orthogonal_lineto,
			'v': self.rule_orthogonal_lineto,
			'C': self.rule_curveto3,
			'c': self.rule_curveto3,
			'S': self.rule_curveto2,
			's': self.rule_curveto2,
			'Q': self.rule_curveto2,
			'q': self.rule_curveto2,
			'T': self.rule_curveto1,
			't': self.rule_curveto1,
			'A': self.rule_elliptical_arc,
			'a': self.rule_elliptical_arc,
		}

		self.number_tokens = set(['int', 'float'])

	def parse(self, text):
		""" Parse a string of SVG <path> data.
		"""
		next = self.lexer.lex(text).next
		token = next()
		return self.rule_svg_path(next, token)

	def rule_svg_path(self, next, token):
		commands = []
		while token[0] is not EOF:
			if token[0] != 'command':
				raise SyntaxError("expecting a command; got %r" % (token,))
			rule = self.command_dispatch[token[1]]
			command_group, token = rule(next, token)
			commands.append(command_group)
		return commands

	def rule_closepath(self, next, token):
		command = token[1]
		token = next()
		return (command, None), token

	def rule_moveto_or_lineto(self, next, token):
		command = token[1]
		token = next()
		coordinates = []
		while token[0] in self.number_tokens:
			try:
				pair, token = self.rule_coordinate_pair(next, token)
			except:
				pair, token = (0.0, 0.0), next()
			coordinates.append(pair)
		return (command, coordinates), token

	def rule_orthogonal_lineto(self, next, token):
		command = token[1]
		token = next()
		coordinates = []
		while token[0] in self.number_tokens:
			try:
				coord, token = self.rule_coordinate(next, token)
			except:
				coord, token = 0.0, next()
			coordinates.append(coord)
		return (command, coordinates), token

	def rule_curveto3(self, next, token):
		command = token[1]
		token = next()
		coordinates = []
		while token[0] in self.number_tokens:
			try:
				pair1, token = self.rule_coordinate_pair(next, token)
			except:
				try:
					pair1, token = (0.0, 0.0), next()
				except StopIteration:
					break
			try:
				pair2, token = self.rule_coordinate_pair(next, token)
			except:
				try:
					pair2, token = (0.0, 0.0), next()
				except StopIteration:
					break
			try:
				pair3, token = self.rule_coordinate_pair(next, token)
			except:
				#~ print_error()
				#~ print self.lexer.text
				try:
					pair3, token = (0.0, 0.0), next()
				except StopIteration:
					break
			coordinates.append((pair1, pair2, pair3))
		return (command, coordinates), token

	def rule_curveto2(self, next, token):
		command = token[1]
		token = next()
		coordinates = []
		while token[0] in self.number_tokens:
			try:
				pair1, token = self.rule_coordinate_pair(next, token)
			except:
				pair1, token = (0.0, 0.0), next()
			try:
				pair2, token = self.rule_coordinate_pair(next, token)
			except:
				pair2, token = (0.0, 0.0), next()
			coordinates.append((pair1, pair2))
		return (command, coordinates), token

	def rule_curveto1(self, next, token):
		command = token[1]
		token = next()
		coordinates = []
		while token[0] in self.number_tokens:
			try:
				pair1, token = self.rule_coordinate_pair(next, token)
			except:
				pair1, token = (0.0, 0.0), next()
			coordinates.append(pair1)
		return (command, coordinates), token

	def rule_elliptical_arc(self, next, token):
		command = token[1]
		token = next()
		arguments = []
		while token[0] in self.number_tokens:
			rx = float(token[1])
			if rx < 0.0:
				raise SyntaxError("expecting a nonnegative number; got %r" % (token,))

			token = next()
			if token[0] not in self.number_tokens:
				raise SyntaxError("expecting a number; got %r" % (token,))
			ry = float(token[1])
			if ry < 0.0:
				raise SyntaxError("expecting a nonnegative number; got %r" % (token,))

			token = next()
			if token[0] not in self.number_tokens:
				raise SyntaxError("expecting a number; got %r" % (token,))
			axis_rotation = float(token[1])

			token = next()
			if token[1] not in ('0', '1'):
				raise SyntaxError("expecting a boolean flag; got %r" % (token,))
			large_arc_flag = bool(int(token[1]))

			token = next()
			if token[1] not in ('0', '1'):
				raise SyntaxError("expecting a boolean flag; got %r" % (token,))
			sweep_flag = bool(int(token[1]))

			token = next()
			if token[0] not in self.number_tokens:
				raise SyntaxError("expecting a number; got %r" % (token,))
			x = float(token[1])

			token = next()
			if token[0] not in self.number_tokens:
				raise SyntaxError("expecting a number; got %r" % (token,))
			y = float(token[1])

			token = next()
			arguments.append(((rx,ry), axis_rotation, large_arc_flag, sweep_flag, (x,y)))

		return (command, arguments), token

	def rule_coordinate(self, next, token):
		if token[0] not in self.number_tokens:
			raise SyntaxError("expecting a number; got %r" % (token,))
		x = float(token[1])
		token = next()
		return x, token

	def rule_coordinate_pair(self, next, token):
		# Inline these since this rule is so common.
		if token[0] not in self.number_tokens:
			raise SyntaxError("expecting a number; got %r" % (token,))
		x = float(token[1])
		token = next()
		if token[0] not in self.number_tokens:
			raise SyntaxError("expecting a number; got %r" % (token,))
		y = float(token[1])
		token = next()
		return (x,y), token


svg_path_parser = SVGPathParser()
