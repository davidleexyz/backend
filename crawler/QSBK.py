import urllib.request
import urllib.error
import urllib.parse

import time

from bs4 import BeautifulSoup
from queue import Queue

user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36"

q = Queue()
visited_links = []
contents = []
base_url = "http://www.qiushibaike.com"

def download(url, user_agent):
	print("Downloading:", url)
	headers = {'User-agent': user_agent}
	request = urllib.request.Request(url, headers = headers)
	try:
		html = urllib.request.urlopen(request).read()
	except urllib.error.URLError as e:
		print("Download failed :", e.reason)

	visited_links.append(url)
	return html

def parse(html):
	html = html.decode("utf8")
	soup = BeautifulSoup(html, "html.parser")
	#print(soup.prettify())
	content_herf = soup.find_all('a', class_='contentHerf')
	for index in range(len(content_herf)):
		link = content_herf[index]['href']
		link = urllib.parse.urljoin(base_url, link)
		print(link)
		visited_links.append(link)

		content = content_herf[index].span.get_text()
		print(content)
		contents.append(content)

	navi = soup.find('ul', class_='pagination')
	navi_page_links = navi.find_all('a')
	for i in range(len(navi_page_links)):
		page_link = navi_page_links[i]['href']
		page_link = urllib.parse.urljoin(base_url, page_link)
		#print(page_link)
		q.put(page_link)

if __name__ == '__main__':
	#window print function default using gbk encode
	import sys
	import io
	sys.stdout = io.TextIOWrapper(sys.stdout.buffer,encoding='gb18030')

	q.put(base_url)
	while not q.empty():
		url = q.get()
		if not url in visited_links:
			html = download(url, user_agent)
			parse(html)
			time.sleep(1) # in case download too fast

