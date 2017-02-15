'''
features as follow: 
a) download throttle
b) proxy pool
c) limit crawl depth
d) handle mixed url
'''
import urllib.request
import urllib.error
import urllib.parse

import datetime
import random

from bs4 import BeautifulSoup
from queue import Queue

class Downloader():

	def __init__(self, user_agent, delay =5, proxies = None, cache = None):
		self.throttle = Throttle(delay)
		self.proxies = proxies
		self.user_agent = user_agent
		self.cache = cache

	def __call__(self, url):
		result = None
		if self.cache:
			try:
				result = self.cache[url]
			except KeyError:
				result = None
				pass
			
		if not result:
			self.throttle.wait(url)
			proxy = random.choice(self.proxies) if self.proxies else None
			headers = {"User-agent": self.user_agent}
			result = self.download(url, headers, proxy)

		return result


	def download(self, url, headers, proxy):
		print("Downloading:", url)
		request = urllib.request.Request(url, headers = headers)
		opener = urllib.request.build_opener()
		if proxy:
			proxy_params = {urllib.request.urlparse(url).scheme : proxy}
			opener.add_handler(urllib.request.ProxyHandler(proxy_params))
		try:
			html = opener.open(request).read()
		except urllib.error.URLError as e:
			print("Download failed:", e.reason)
			html = None

		return html

class Throttle():
	def __init__(self, delay):
		self.delay = delay
		self.domains = {}

	def wait(self, url):
		domain = urllib.parse.urlparse(url).netloc
		last_accessed = self.domains.get(domain)

		if self.delay > 0 and last_accessed is not None:
			sleep_secs = self.delay - (datetime.datetime.now() - last_accessed).second

			if sleep_secs > 0:
				time.sleep(sleep_secs)

		self.domains[domain] = datetime.datetime.now()


class Parser():
	def __init__(self):
		pass

	def parse(self, url, html):
		components = urllib.parse.urlsplit(url)
		html = html.decode('utf8')
		soup = BeautifulSoup(html, "html.parser")
		links = []
		img_links = []
		tags = soup.find_all("table", class_="tagCol")
		for index in range(len(tags)):
			tag_links = tags[index].find_all('a')
			for tag_link in tag_links:
				tag_href = tag_link['href']
				tag_href = components.scheme + "://" + components.netloc + tag_href
				print(tag_href)
				links.append(tag_href)

		items = soup.find_all("a", class_='nbg')
		for item in items:
			href = item['href']
			title = item['title']
			img_src = item.img['src']
			print(href, title, img_src)
			links.append(href)
			img_links.append(img_src)

		return links, img_links

if __name__ == "__main__":
	max_depth = 5
	base_url = "https://movie.douban.com/tag"
	user_agent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36"
	crawl_queue = Queue()
	crawl_queue.put((base_url, 0))
	visited_url = []
	parser = Parser()

	while not crawl_queue.empty():
		item = crawl_queue.get()
		url = urllib.parse.quote(item[0], safe='/:?=') # handle english and chinese mixed url
		depth = item[1]
		d = Downloader(user_agent)
		html = d(url)
		visited_url.append(url)
		if html:
			links, img_links = parser.parse(url, html)
			for link in links:
				if link not in visited_url and depth < max_depth:
					crawl_queue.put((link, depth+1))




