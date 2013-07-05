#!/usr/bin/python
#
#  Build Duktape website.  Must be run with cwd in the website/ directory.
#

import os
import sys
import re
import tempfile
import atexit
from bs4 import BeautifulSoup

colorize = True
fancy_stack = True
remove_fixme = False

def readFile(x):
	f = open(x, 'rb')
	data = f.read()
	f.close()
	return data

def htmlEscape(x):
	res = ''
	esc = '&<>'
	for c in x:
		if ord(c) >= 0x20 and ord(c) <= 0x7e and c not in esc:
			res += c
		else:
			res += '&#x%04x;' % ord(c)
	return res

def getAutodeleteTempname():
	tmp = tempfile.mktemp(suffix='duktape-website')
	def f():
		os.remove(tmp)
	atexit.register(f)
	return tmp

# also escapes text automatically
def sourceHighlight(x, sourceLang):
	tmp1 = getAutodeleteTempname()
	tmp2 = getAutodeleteTempname()

	f = open(tmp1, 'wb')  # FIXME
	f.write(x)
	f.close()

	# FIXME: safer execution
	os.system('source-highlight -s %s -c highlight.css --no-doc <"%s" >"%s"' % \
	          (sourceLang, tmp1, tmp2))

	f = open(tmp2, 'rb')
	res = f.read()
	f.close()

	return res

def stripNewline(x):
	if len(x) > 0 and x[-1] == '\n':
		return x[:-1]
	return x

def validateAndParseHtml(data):
	# first parse as xml to get errors out
	ign_soup = BeautifulSoup(data, 'xml')

	# then parse as lenient html, no xml tags etc
	soup = BeautifulSoup(data)

	return soup

re_stack_line = re.compile(r'^(\[[^\x5d]+\])(?:\s+->\s+(\[[^\x5d]+\]))?(?:\s+(.*?))?\s*$')
def renderFancyStack(inp_line):
	# Support various notations here:
	#
	#   [ a b c ]
	#   [ a b c ] -> [ d e f ]
	#   [ a b c ] -> [ d e f ]  (if foo)
	#

	m = re_stack_line.match(inp_line)
	#print(inp_line)
	assert(m is not None)
	stacks = [ m.group(1) ]
	if m.group(2) is not None:
		stacks.append(m.group(2))

	res = []

	res.append('<div class="stack-wrapper">')
	for idx, stk in enumerate(stacks):
		if idx > 0:
			res.append('<span class="arrow"><b>&rarr;</b></span>')
		res.append('<span class="stack">')
		for part in stk.split(' '):
			part = part.strip()
			elem_classes = []
			elem_classes.append('elem')  #FIXME
			if len(part) > 0 and part[-1] == '!':
				part = part[:-1]
				elem_classes.append('active')
			elif len(part) > 0 and part[-1] == '*':
				part = part[:-1]
				elem_classes.append('referred')
			elif len(part) > 0 and part[-1] == '?':
				part = part[:-1]
				elem_classes.append('ghost')

			text = part

			# FIXME: detect special constants like "true", "null", etc?
			if text in [ 'undefined', 'null', 'true', 'false', 'NaN' ] or \
			   (len(text) > 0 and text[0] == '"' and text[-1] == '"'):
				elem_classes.append('literal')

			# FIXME: inline elements for reduced size?
			# The stack elements use a classless markup to minimize result
			# HTML size.  HTML inline elements are used to denote different
			# kinds of elements; the elements should be reasonable for text
			# browsers so a limited set can be used.
			use_inline = False

			if part == '':
				continue
			if part == '[':
				#res.append('<em>[</em>')
				res.append('<span class="cap">[</span>')
				continue
			if part == ']':
				#res.append('<em>]</em>')
				res.append('<span class="cap">]</span>')
				continue

			if part == '...':
				text = '. . .'
				elem_classes.append('ellipsis')
			else:
				text = part

			if 'ellipsis' in elem_classes and use_inline:
				res.append('<i>' + htmlEscape(text) + '</i>')
			elif 'active' in elem_classes and use_inline:
				res.append('<b>' + htmlEscape(text) + '</b>')
			else:
				res.append('<span class="' + ' '.join(elem_classes) + '">' + htmlEscape(text) + '</span>')

		res.append('</span>')

	# FIXME: pretty badly styled now
	if m.group(3) is not None:
		res.append('<span class="stack-comment">' + htmlEscape(m.group(3)) + '</span>')

	res.append('</div>')

	return ' '.join(res) + '\n'  # stack is a one-liner; spaces are for text browser rendering

def parseApiDoc(filename):
	f = open(filename, 'rb')
	parts = {}
	state = None
	for line in f.readlines():
		line = stripNewline(line)
		if line.startswith('='):
			state = line[1:]
		elif state is not None:
			if not parts.has_key(state):
				parts[state] = []
			parts[state].append(line)
		else:
			if line != '':
				raise Exception('unparsed non-empty line: %r' % line)
			else:
				# ignore
				pass
	f.close()

	# remove leading and trailing empty lines
	for k in parts:
		p = parts[k]
		while len(p) > 0 and p[0] == '':
			p.pop(0)
		while len(p) > 0 and p[-1] == '':
			p.pop()

	return parts

def processApiDoc(filename):
	parts = parseApiDoc(filename)
	res = []

	funcname = os.path.splitext(os.path.basename(filename))[0]

	# this improves readability on e.g. elinks and w3m
	res.append('<hr />')
	#res.append('<hr>')

	# the 'hidechar' span is to allow browser search without showing the char
	res.append('<h2 id="%s"><a href="#%s"><span class="hidechar">.</span>%s()</a></h2>' % (funcname, funcname, funcname))

	if parts.has_key('proto'):
		p = parts['proto']
		res.append('<h3>Prototype</h3>')
		res.append('<pre class="c-code">')
		for i in p:
			res.append(htmlEscape(i))
		res.append('</pre>')
		res.append('')
	else:
		pass

	if parts.has_key('stack'):
		p = parts['stack']
		res.append('<h3>Stack</h3>')
		for line in p:
			res.append('<pre class="stack">' + \
			           '%s' % htmlEscape(line) + \
			           '</pre>')
		res.append('')
	else:
		res.append('<h3>Stack</h3>')
		res.append('<p>No effect.</p>')
		res.append('')

	if parts.has_key('summary'):
		p = parts['summary']
		res.append('<h3>Summary</h3>')

		# If text contains a '<p>', assume it is raw HTML; otherwise
		# assume it is a single paragraph (with no markup) and generate
		# paragraph tags, escaping into HTML

		raw_html = False
		for i in p:
			if '<p>' in i:
				raw_html = True

		if raw_html:
			for i in p:
				res.append(i)
		else:
			res.append('<p>')
			for i in p:
				res.append(htmlEscape(i))
			res.append('</p>')
		res.append('')

	if parts.has_key('example'):
		p = parts['example']
		res.append('<h3>Example</h3>')
		res.append('<pre class="c-code">')
		for i in p:
			res.append(htmlEscape(i))
		res.append('</pre>')
		res.append('')

	if parts.has_key('fixme'):
		p = parts['fixme']
		res.append('<div class="fixme">')
		for i in p:
			res.append(htmlEscape(i))
		res.append('</div>')
		res.append('')

	return res

def processRawDoc(filename):
	f = open(filename, 'rb')
	res = []
	for line in f.readlines():
		line = stripNewline(line)
		res.append(line)
	f.close()
	res.append('')
	return res

def transformColorizeCode(soup, cssClass, sourceLang):
	for elem in soup.select('pre.' + cssClass):
		input_str = elem.string
		if len(input_str) > 0 and input_str[0] == '\n':
			# hack for leading empty line
			input_str = input_str[1:]

		colorized = sourceHighlight(input_str, sourceLang)

		# source-highlight generates <pre><tt>...</tt></pre>, get rid of <tt>
		new_elem = BeautifulSoup(colorized).tt    # XXX: parse just a fragment - how?
		new_elem.name = 'pre'
		new_elem['class'] = cssClass

		elem.replace_with(new_elem)

def transformFancyStacks(soup):
	for elem in soup.select('pre.stack'):
		input_str = elem.string
		if len(input_str) > 0 and input_str[0] == '\n':
			# hack for leading empty line
			input_str = input_str[1:]

		new_elem = BeautifulSoup(renderFancyStack(input_str)).div  # XXX: fragment?
		elem.replace_with(new_elem)

def transformRemoveClass(soup, cssClass):
	for elem in soup.select('.' + cssClass):
		elem.remove()

# FIXME: refactor shared parts

def generateApiDoc(apidocdir):
	templ_soup = validateAndParseHtml(readFile('template.html'))

	title_elem = templ_soup.select('#template-title')[0]
	del title_elem['id']
	title_elem.string = 'Duktape API'

	tmpfiles = os.listdir(apidocdir)
	apifiles = []
	for filename in tmpfiles:
		if os.path.splitext(filename)[1] == '.txt':
			apifiles.append(filename)
	apifiles.sort()

	# nav

	res = []
	navlinks = []
	navlinks.append(['#introduction', 'Introduction'])
	navlinks.append(['#concepts', 'Concepts'])
	navlinks.append(['#notation', 'Notation'])
	navlinks.append(['#structsandtypedefs', 'Structs and typedefs'])
	for filename in apifiles:
		funcname = os.path.splitext(os.path.basename(filename))[0]
		navlinks.append(['#' + funcname, funcname])
	res.append('<ul>')
	for nav in navlinks:
		res.append('<li><a href="' + htmlEscape(nav[0]) + '">' + htmlEscape(nav[1]) + '</a></li>')
	res.append('</ul>')

	nav_soup = validateAndParseHtml('\n'.join(res))
	tmp_soup = templ_soup.select('#site-middle-nav')[0]
	tmp_soup.clear()
	for i in nav_soup.select('body')[0]:
		tmp_soup.append(i)

	# content

	res = []
	res += [ '<h1 class="main-title">Duktape API</h1>' ]

	# FIXME: generate from the same list as nav links for these
	res += processRawDoc('api/intro.html')
	res += processRawDoc('api/concepts.html')
	res += processRawDoc('api/notation.html')
	res += processRawDoc('api/structsandtypedefs.html')

	for filename in apifiles:
		# FIXME: Here we'd like to validate individual processApiDoc() results so
		# that they don't e.g. have unbalanced tags.  Or at least normalize them so
		# that they don't break the entire page.

		try:
			data = processApiDoc(os.path.join('api', filename))
			res += data
		except:
			print repr(data)
			print 'FAIL: ' + repr(filename)
			raise
		res += data

	res += [ '<hr>' ]

	content_soup = validateAndParseHtml('\n'.join(res))
	tmp_soup = templ_soup.select('#site-middle-content')[0]
	tmp_soup.clear()
	for i in content_soup.select('body')[0]:
		tmp_soup.append(i)
	tmp_soup['class'] = 'content'

	return templ_soup

def generateFrontPage():
	templ_soup = validateAndParseHtml(readFile('template.html'))
	front_soup = validateAndParseHtml(readFile('frontpage/frontpage.html'))

	title_elem = templ_soup.select('#template-title')[0]
	del title_elem['id']
	title_elem.string = 'Duktape'

	tmp_soup = templ_soup.select('#site-middle')[0]
	tmp_soup.clear()
	for i in front_soup.select('body')[0]:
		tmp_soup.append(i)
	tmp_soup['class'] = 'content'

	return templ_soup

def generateGuide():
	templ_soup = validateAndParseHtml(readFile('template.html'))
	front_soup = validateAndParseHtml(readFile('guide/guide.html'))

	title_elem = templ_soup.select('#template-title')[0]
	del title_elem['id']
	title_elem.string = 'Duktape Guide'

	# nav

	res = []
	navlinks = []
	navlinks.append(['#fixme', 'FIXME'])
	for nav in navlinks:
		res.append('<li><a href="' + htmlEscape(nav[0]) + '">' + htmlEscape(nav[1]) + '</a></li>')
	res.append('</ul>')

	nav_soup = validateAndParseHtml('\n'.join(res))
	tmp_soup = templ_soup.select('#site-middle-nav')[0]
	tmp_soup.clear()
	for i in nav_soup.select('body')[0]:
		tmp_soup.append(i)

	# content

	res = []
	res += [ '<h1 class="main-title">Duktape Programmer\'s Guide</h1>' ]

	res += processRawDoc('guide/guide.html')  # FIXME

	res += [ '<hr>' ]
	content_soup = validateAndParseHtml('\n'.join(res))
	tmp_soup = templ_soup.select('#site-middle-content')[0]
	tmp_soup.clear()
	for i in content_soup.select('body')[0]:
		tmp_soup.append(i)
	tmp_soup['class'] = 'content'

	return templ_soup

def generateStyleCss():
	styles = [
		'reset.css',
		'style-html.css',
		'style-content.css',
		'style-top.css',
		'style-middle.css',
		'style-bottom.css',
		'style-front.css',
		'highlight.css'
	]

	style = ''
	for i in styles:
		style += '/* === %s === */\n' % i
		style += readFile(i)

	return style

def postProcess(soup):
	if colorize:
		transformColorizeCode(soup, 'c-code', 'c')
		transformColorizeCode(soup, 'ecmascript-code', 'javascript')

	if fancy_stack:
		transformFancyStacks(soup)

	if remove_fixme:
		transformRemoveClass(soup, 'fixme')

	return soup

def writeFile(name, data):
	f = open(name, 'wb')
	f.write(data)
	f.close()

def main():
	outdir = sys.argv[1]; assert(outdir)
	apidocdir = 'api'

	data = generateStyleCss()
	writeFile(os.path.join(outdir, 'style.css'), data)
	#writeFile(os.path.join(outdir, 'reset.css'), readFile('reset.css'))
	#writeFile(os.path.join(outdir, 'highlight.css'), readFile('highlight.css'))

	soup = generateApiDoc(apidocdir)
	soup = postProcess(soup)
	writeFile(os.path.join(outdir, 'api.html'), soup.encode('ascii'))

	soup = generateGuide()
	soup = postProcess(soup)
	writeFile(os.path.join(outdir, 'guide.html'), soup.encode('ascii'))

	soup = generateFrontPage()
	soup = postProcess(soup)
	writeFile(os.path.join(outdir, 'frontpage.html'), soup.encode('ascii'))

if __name__ == '__main__':
	main()

